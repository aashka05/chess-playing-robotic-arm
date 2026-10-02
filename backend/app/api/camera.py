from fastapi import APIRouter, HTTPException, UploadFile

from app.api.deps import CurrentUser, Games

router = APIRouter(prefix="/camera", tags=["camera"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@router.get("/status")
async def camera_status(_: CurrentUser, games: Games) -> dict:
    return {"connected": games.camera.connected}


@router.post("/upload/{request_id}")
async def upload(request_id: str, file: UploadFile, _: CurrentUser, games: Games) -> dict:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image too large")
    if not games.camera.deliver(request_id, data):
        raise HTTPException(404, "No capture is waiting for this request id (it may have timed out)")
    return {"ok": True}
