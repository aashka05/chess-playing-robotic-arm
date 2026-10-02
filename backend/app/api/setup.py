from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, Games
from app.core.config import get_settings
from app.schemas.setup import CalibrateOut, SetupState, VerifyOut

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post("/start", response_model=SetupState)
async def start_setup(user: CurrentUser, games: Games) -> SetupState:
    s = games.start_setup(user.user_id, user.username)
    return SetupState(state=s.sm.state, camera_connected=games.camera.connected)


@router.get("", response_model=SetupState)
async def get_setup(user: CurrentUser, games: Games) -> SetupState:
    s = games.session_for_user(user.user_id)
    if s is None:
        raise HTTPException(404, "No setup in progress")
    return SetupState(state=s.sm.state, camera_connected=games.camera.connected)


@router.delete("", status_code=204)
async def cancel_setup(user: CurrentUser, games: Games) -> None:
    games.cancel_setup(user.user_id)


@router.post("/calibrate", response_model=CalibrateOut)
async def calibrate(user: CurrentUser, games: Games) -> dict:
    """Step 1: photograph the empty board and rectify it."""
    return await games.calibrate_empty_board(user.user_id)


@router.post("/verify", response_model=VerifyOut)
async def verify(user: CurrentUser, games: Games) -> dict:
    """Step 2: photograph the set-up pieces and compare with the initial position."""
    return await games.verify_pieces(user.user_id)


@router.post("/debug/skip", response_model=SetupState)
async def debug_skip(user: CurrentUser, games: Games) -> SetupState:
    if not get_settings().debug_endpoints:
        raise HTTPException(404, "Not found")
    result = games.debug_skip_setup(user.user_id)
    return SetupState(state=result["state"], camera_connected=games.camera.connected)
