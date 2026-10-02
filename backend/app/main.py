import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, camera, games, setup, ws
from controller.driver import MockArmDriver, SerialArmDriver
from app.camera.app_upload import AppUploadCameraSource
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from stockfish.engine import StockfishEngine
from app.services.arm_service import ArmService
from app.services.detection_service import DetectionService
from app.services.errors import ServiceError
from app.services.game_service import GameService
from app.services.repository import Repository
from app.services.state_machine import InvalidTransition, WrongState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    repo = Repository(SessionLocal)
    stale = await repo.abort_stale_games()
    if stale:
        log.info("Marked %d unfinished game(s) from a previous run as aborted", stale)

    stockfish = StockfishEngine(str(settings.resolve(Path(settings.stockfish_path))), settings.analysis_time_sec)
    await stockfish.start()

    detection = DetectionService(
        settings.resolve(settings.calibration_path),
        settings.resolve(settings.yolo_model_path),
        settings.detection_min_confidence,
    )
    warm_up = asyncio.create_task(detection.warm_up())

    if settings.arm_mode == "serial":
        driver = SerialArmDriver(settings.arm_serial_port, settings.arm_baud_rate, settings.arm_command_timeout_sec)
    else:
        driver = MockArmDriver(settings.arm_mock_delay_sec)
    log.info("Arm mode: %s", settings.arm_mode)
    arm = ArmService(driver, settings.resolve(settings.arm_angles_path), repo, strict=settings.arm_mode == "serial")

    camera = AppUploadCameraSource(settings.camera_capture_timeout_sec)
    app.state.game_service = GameService(repo, stockfish, detection, camera, arm)
    try:
        yield
    finally:
        warm_up.cancel()
        await app.state.game_service.shutdown()
        await repo.abort_stale_games()
        driver.close()
        await stockfish.stop()
        await engine.dispose()


app = FastAPI(title="Robot Arm Chess", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ServiceError)
async def service_error(_: Request, exc: ServiceError):
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


@app.exception_handler(WrongState)
@app.exception_handler(InvalidTransition)
async def state_error(_: Request, exc: Exception):
    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


for router in (auth.router, setup.router, games.router, camera.router, ws.router):
    app.include_router(router)
