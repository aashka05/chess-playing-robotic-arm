"""WebSockets: live game state for the controller phone, capture requests for the camera phone.

Auth: pass the JWT as ?token=... (browsers/phones can't set headers on WS).
"""

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.api.deps import user_from_token
from app.core.database import SessionLocal
from app.services.errors import NotFound

router = APIRouter()

HEARTBEAT_SEC = 5


async def _authenticate(ws: WebSocket):
    async with SessionLocal() as db:
        user = await user_from_token(db, ws.query_params.get("token"))
    if user is None:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
    return user


@router.websocket("/ws/games/{game_id}")
async def game_socket(ws: WebSocket, game_id: int):
    await ws.accept()
    user = await _authenticate(ws)
    if user is None:
        return
    games = ws.app.state.game_service
    try:
        session = games.game_session(game_id, user.user_id)
    except NotFound:
        await ws.send_json({"type": "error", "message": "This game is not running."})
        await ws.close()
        return

    queue = games.subscribe(session)
    # Drain client messages so we notice disconnects; the app sends actions over REST.
    reader = asyncio.create_task(_drain(ws))
    try:
        while not reader.done():
            try:
                event = await asyncio.wait_for(queue.get(), HEARTBEAT_SEC)
            except TimeoutError:
                event = games.snapshot(session)  # keeps clocks in sync
            await ws.send_json(event)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        games.unsubscribe(session, queue)
        reader.cancel()


async def _drain(ws: WebSocket) -> None:
    with contextlib.suppress(WebSocketDisconnect, RuntimeError):
        while True:
            await ws.receive_text()


@router.websocket("/ws/camera")
async def camera_socket(ws: WebSocket):
    await ws.accept()
    user = await _authenticate(ws)
    if user is None:
        return
    camera = ws.app.state.game_service.camera
    camera.register(ws)
    try:
        await ws.send_json({"type": "hello", "message": "Camera mode connected"})
        while True:
            await ws.receive_text()  # pings from the phone
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        camera.unregister(ws)
