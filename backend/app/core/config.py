from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://chess:chess@localhost:5432/chess_robot"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    password_reset_expire_minutes: int = 30
    # Leave SMTP_HOST empty in development: reset codes are then logged to the console.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    smtp_from: str = "Robot Chess <no-reply@localhost>"

    stockfish_path: str = str(PROJECT_ROOT / "stockfish" / "stockfish")
    analysis_time_sec: float = 0.2

    calibration_path: Path = BACKEND_DIR / "data" / "calibration.json"
    detection_min_confidence: float = 0.6
    camera_capture_timeout_sec: float = 20.0

    arm_mode: Literal["mock", "serial"] = "mock"
    arm_serial_port: str = "/dev/cu.usbserial-2130"
    arm_baud_rate: int = 115200
    arm_command_timeout_sec: float = 30.0
    arm_angles_path: Path = PROJECT_ROOT / "controller" / "angles_dict.json"
    arm_mock_delay_sec: float = 0.3

    debug_endpoints: bool = False

    def resolve(self, path: Path) -> Path:
        """Relative paths in .env are relative to the project root."""
        return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
