"""Uploaded photos are center-cropped to a square before detection."""

import asyncio

import cv2
import numpy as np
import pytest

from app.camera.app_upload import AppUploadCameraSource, center_square


@pytest.mark.parametrize("shape", [(1920, 1080, 3), (1080, 1920, 3), (800, 800, 3)])
def test_center_square(shape):
    image = np.zeros(shape, np.uint8)
    h, w = shape[:2]
    image[h // 2, w // 2] = 255  # the center pixel must survive the crop
    out = center_square(image)
    side = min(h, w)
    assert out.shape[:2] == (side, side)
    assert out[side // 2, side // 2].tolist() == [255, 255, 255]


async def test_uploaded_landscape_photo_arrives_square():
    camera = AppUploadCameraSource()
    future = asyncio.get_running_loop().create_future()
    camera._pending["r1"] = future
    ok, jpeg = cv2.imencode(".jpg", np.zeros((480, 640, 3), np.uint8))
    assert camera.deliver("r1", jpeg.tobytes())
    assert (await future).shape[:2] == (480, 480)
