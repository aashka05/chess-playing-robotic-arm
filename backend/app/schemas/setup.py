from pydantic import BaseModel


class Mismatch(BaseModel):
    square: str
    expected: str | None
    detected: str | None


class SetupState(BaseModel):
    state: str
    camera_connected: bool


class CalibrateOut(BaseModel):
    state: str
    preview_jpeg_base64: str = ""


class VerifyOut(BaseModel):
    state: str
    correct: bool
    expected_fen: str
    mismatches: list[Mismatch]
