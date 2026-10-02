"""The engine interface used by the game service (Stockfish in production)."""

from typing import Protocol

import chess

from stockfish.engine import Evaluation, StockfishEngine
from app.models.enums import Difficulty


class EngineService(Protocol):
    async def play(self, board: chess.Board, difficulty: Difficulty) -> chess.Move: ...

    async def evaluate(self, board: chess.Board) -> Evaluation: ...


__all__ = ["EngineService", "Evaluation", "StockfishEngine"]
