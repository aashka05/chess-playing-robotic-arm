"""Stockfish via python-chess's asyncio UCI API.

Two engine processes: one plays the robot's moves at the chosen strength,
the other analyses every position at full strength for the eval graph.
"""

import asyncio
import logging
from dataclasses import dataclass

import chess
import chess.engine

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Strength:
    skill_level: int  # Stockfish "Skill Level", 0..20
    move_time: float  # seconds per move


# Keyed by difficulty name ("easy" / "medium" / "hard").
STRENGTH = {
    "easy": Strength(skill_level=3, move_time=0.2),
    "medium": Strength(skill_level=10, move_time=0.6),
    "hard": Strength(skill_level=20, move_time=1.5),
}


@dataclass(frozen=True)
class Evaluation:
    """From White's point of view. eval_mate=0 means the side to move is checkmated."""

    cp: int | None
    mate: int | None


class StockfishEngine:
    def __init__(self, path: str, analysis_time: float = 0.2):
        self.path = path
        self.analysis_time = analysis_time
        self._player: chess.engine.UciProtocol | None = None
        self._analyser: chess.engine.UciProtocol | None = None
        self._play_lock = asyncio.Lock()
        self._analyse_lock = asyncio.Lock()

    async def start(self) -> None:
        _, self._player = await chess.engine.popen_uci(self.path)
        _, self._analyser = await chess.engine.popen_uci(self.path)
        log.info("Stockfish started: %s", self._player.id.get("name"))

    async def stop(self) -> None:
        for engine in (self._player, self._analyser):
            if engine is not None:
                try:
                    await engine.quit()
                except chess.engine.EngineError:
                    pass

    async def play(self, board: chess.Board, difficulty: str) -> chess.Move:
        strength = STRENGTH[difficulty]
        async with self._play_lock:
            result = await self._player.play(
                board,
                chess.engine.Limit(time=strength.move_time),
                options={"Skill Level": strength.skill_level},
            )
        return result.move

    async def evaluate(self, board: chess.Board) -> Evaluation:
        if board.is_checkmate():
            return Evaluation(cp=None, mate=0)
        async with self._analyse_lock:
            info = await self._analyser.analyse(board, chess.engine.Limit(time=self.analysis_time))
        score = info["score"].white()
        if score.is_mate():
            return Evaluation(cp=None, mate=score.mate())
        return Evaluation(cp=score.score(), mate=None)
