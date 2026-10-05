"""Camera = the Flutter app running in "camera mode" on phone A.

The phone keeps a WebSocket open to /ws/camera. To take a picture we send
it {"type": "capture_request", "request_id": ...}; it snaps a photo and
POSTs it to /camera/upload/{request_id}, which resolves the waiting future.
"""

import asyncio
import logging
import uuid

import cv2
import numpy as np
from fastapi import WebSocket

from app.camera.base import CameraError

log = logging.getLogger(__name__)


def center_square(image: np.ndarray) -> np.ndarray:
    """Centered 1:1 crop. The app already crops; this covers clients that don't."""
    h, w = image.shape[:2]
    side = min(h, w)
    top, left = (h - side) // 2, (w - side) // 2
    return image[top : top + side, left : left + side]


class AppUploadCameraSource:
    def __init__(self, timeout_sec: float = 20.0):
        self.timeout_sec = timeout_sec
        self._sockets: list[WebSocket] = []
        self._pending: dict[str, asyncio.Future[np.ndarray]] = {}
        self._lock = asyncio.Lock()  # one capture at a time

    @property
    def connected(self) -> bool:
        return bool(self._sockets)

    def register(self, ws: WebSocket) -> None:
        self._sockets.append(ws)
        log.info("Camera phone connected (%d total)", len(self._sockets))

    def unregister(self, ws: WebSocket) -> None:
        if ws in self._sockets:
            self._sockets.remove(ws)
        log.info("Camera phone disconnected (%d left)", len(self._sockets))

    async def capture(self) -> np.ndarray:
        async with self._lock:
            if not self._sockets:
                raise CameraError("The camera phone is not connected. Open the app in Camera mode on phone A.")
            request_id = uuid.uuid4().hex
            future: asyncio.Future[np.ndarray] = asyncio.get_running_loop().create_future()
            self._pending[request_id] = future
            ws = self._sockets[-1]  # most recently connected phone
            try:
                await ws.send_json({"type": "capture_request", "request_id": request_id})
                return await asyncio.wait_for(future, self.timeout_sec)
            except TimeoutError as exc:
                raise CameraError("The camera phone did not send a picture in time.") from exc
            except RuntimeError as exc:  # socket closed while sending
                raise CameraError(f"Could not reach the camera phone: {exc}") from exc
            finally:
                self._pending.pop(request_id, None)

    def deliver(self, request_id: str, data: bytes) -> bool:
        """Called by the upload endpoint. Returns False if nobody is waiting."""
        future = self._pending.get(request_id)
        if future is None or future.done():
            return False
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            future.set_exception(CameraError("The uploaded file is not a readable image."))
        else:
            future.set_result(center_square(image))
        return True
