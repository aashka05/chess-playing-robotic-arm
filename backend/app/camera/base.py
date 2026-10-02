from typing import Protocol

import numpy as np


class CameraError(Exception):
    """The camera could not deliver an image (not connected, timeout, bad upload)."""


class CameraSource(Protocol):
    @property
    def connected(self) -> bool: ...

    async def capture(self) -> np.ndarray:
        """Return a BGR image of the board."""
        ...
