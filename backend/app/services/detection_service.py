"""Vision: calibration (rectify_board), piece detection (YOLO) and move matching."""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import chess
import cv2
import numpy as np

from vision import map_pieces_to_squares, move_detection
from vision.move_matcher import Detections, MatchResult, diff_against_fen, match_move
from vision.rectify_board import rectify_board

log = logging.getLogger(__name__)


class VisionError(Exception):
    """Calibration/detection failed in a way the user can fix (e.g. markers hidden)."""


@dataclass
class Calibration:
    squares: list[dict]
    homography: list[list[float]]
    initial_fen: str
    created_at: str


def _jpeg_b64(image: np.ndarray, max_side: int = 480) -> str:
    h, w = image.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1:
        image = cv2.resize(image, (int(w * scale), int(h * scale)))
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf.tobytes()).decode() if ok else ""


class DetectionService:
    def __init__(self, calibration_path: Path, model_path: Path, min_confidence: float):
        self.calibration_path = calibration_path
        self.model_path = map_pieces_to_squares.require_model_path(model_path)
        self.min_confidence = min_confidence
        self.calibration: Calibration | None = self._load_calibration()

    def _load_calibration(self) -> Calibration | None:
        if not self.calibration_path.exists():
            return None
        try:
            return Calibration(**json.loads(self.calibration_path.read_text()))
        except (json.JSONDecodeError, TypeError) as exc:
            log.warning("Ignoring unreadable calibration file %s: %s", self.calibration_path, exc)
            return None

    async def warm_up(self) -> None:
        """Load the YOLO model in the background so the first move isn't slow."""
        await asyncio.to_thread(map_pieces_to_squares.load_model, self.model_path)
        log.info("YOLO model loaded from %s", self.model_path)

    # ---- setup step 1 -------------------------------------------------

    async def calibrate(self, image: np.ndarray, initial_fen: str = chess.STARTING_FEN) -> dict:
        try:
            result = await asyncio.to_thread(rectify_board, image)
        except RuntimeError as exc:
            raise VisionError(f"Could not find the board: {exc} Make sure all four corner markers are visible.") from exc
        self.calibration = Calibration(
            squares=result["squares"],
            homography=np.asarray(result["homography"]).tolist(),
            initial_fen=initial_fen,
            created_at=datetime.now(UTC).isoformat(),
        )
        self.calibration_path.parent.mkdir(parents=True, exist_ok=True)
        self.calibration_path.write_text(json.dumps(self.calibration.__dict__))
        return {"preview_jpeg_base64": _jpeg_b64(result["rectified"])}

    # ---- detection ----------------------------------------------------

    def _require_calibration(self) -> Calibration:
        if self.calibration is None:
            raise VisionError("The board has not been calibrated. Start a new game setup.")
        return self.calibration

    def _detect_blocking(self, image: np.ndarray) -> tuple[Detections, dict]:
        calibration = self._require_calibration()
        model = map_pieces_to_squares.load_model(self.model_path)
        board, details = map_pieces_to_squares.detect_pieces(
            image, squares=calibration.squares, model=model, return_details=True
        )
        detections = {
            square: (move_detection.PIECE_TO_FEN[name], float(details[square]["confidence"]))
            for square, name in board.items()
            if name in move_detection.PIECE_TO_FEN
        }
        return detections, board

    async def read_board(self, image: np.ndarray) -> Detections:
        detections, _ = await asyncio.to_thread(self._detect_blocking, image)
        return detections

    # ---- setup step 2 -------------------------------------------------

    async def verify_position(self, image: np.ndarray, expected_fen: str) -> list[dict]:
        detections = await self.read_board(image)
        return diff_against_fen(expected_fen, detections)

    # ---- during the game ----------------------------------------------

    async def detect_move(self, image: np.ndarray, board: chess.Board) -> MatchResult:
        detections, raw_board = await asyncio.to_thread(self._detect_blocking, image)
        result = match_move(board, detections, self.min_confidence)
        self._cross_check(board, raw_board, result)
        return result

    def _cross_check(self, board: chess.Board, raw_board: dict, result: MatchResult) -> None:
        """Log when the original diff-based detect_move() disagrees with the matcher."""
        try:
            previous, side, _, ep, _, _ = move_detection.parse_fen(board.fen())
            legacy = move_detection.detect_move(
                previous, move_detection.convert_detection_to_fen_board(raw_board), side, ep
            )
            legacy_uci = None if legacy["type"] == "ambiguous" else legacy["source"] + legacy["destination"]
            matched = result.move.uci()[:4] if result.move else None
            if legacy_uci != matched:
                log.info("Legacy detect_move=%s, legal-move matcher=%s (%s, conf %.2f)",
                         legacy_uci, matched, result.reason, result.confidence)
        except Exception:  # never let the cross-check break a game
            log.exception("Legacy move detection cross-check failed")
