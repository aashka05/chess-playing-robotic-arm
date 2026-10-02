"""Database writes used by the game service (kept separate so tests can fake them)."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Game, MotorLog, Move
from app.models.enums import (
    Color,
    Difficulty,
    GameResult,
    GameStatus,
    MotorStatus,
    Player,
    TerminationReason,
)


@dataclass
class MotorLogEntry:
    game_id: int
    move_id: int | None
    motor_id: int
    angle: float
    status: MotorStatus
    timestamp: datetime


class Repository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._sessions = session_factory

    async def create_game(
        self,
        user_id: int,
        difficulty: Difficulty,
        user_color: Color,
        initial_fen: str,
        time_base_sec: int,
        time_increment_sec: int,
    ) -> int:
        async with self._sessions() as db:
            game = Game(
                user_id=user_id,
                start_time=datetime.now(UTC),
                difficulty=difficulty,
                status=GameStatus.in_progress,
                user_color=user_color,
                initial_fen=initial_fen,
                time_base_sec=time_base_sec,
                time_increment_sec=time_increment_sec,
            )
            db.add(game)
            await db.commit()
            return game.game_id

    async def add_move(
        self,
        game_id: int,
        move_number: int,
        san: str,
        uci: str,
        fen_after: str,
        player: Player,
        time_taken_ms: int,
        detection_confidence: float | None,
    ) -> int:
        async with self._sessions() as db:
            move = Move(
                game_id=game_id,
                move_number=move_number,
                move=san,
                uci=uci,
                fen_after=fen_after,
                player=player,
                time_taken_ms=time_taken_ms,
                detection_confidence=detection_confidence,
            )
            db.add(move)
            await db.commit()
            return move.move_id

    async def set_move_eval(self, move_id: int, eval_cp: int | None, eval_mate: int | None) -> None:
        async with self._sessions() as db:
            await db.execute(
                update(Move).where(Move.move_id == move_id).values(eval_cp=eval_cp, eval_mate=eval_mate)
            )
            await db.commit()

    async def set_move_time(self, move_id: int, time_taken_ms: int) -> None:
        async with self._sessions() as db:
            await db.execute(update(Move).where(Move.move_id == move_id).values(time_taken_ms=time_taken_ms))
            await db.commit()

    async def finish_game(
        self,
        game_id: int,
        status: GameStatus,
        result: GameResult | None,
        reason: TerminationReason,
        final_fen: str,
        pgn: str,
    ) -> None:
        async with self._sessions() as db:
            await db.execute(
                update(Game)
                .where(Game.game_id == game_id)
                .values(
                    status=status,
                    result=result,
                    termination_reason=reason,
                    final_fen=final_fen,
                    pgn=pgn,
                    end_time=datetime.now(UTC),
                )
            )
            await db.commit()

    async def add_motor_logs(self, entries: list[MotorLogEntry]) -> None:
        if not entries:
            return
        async with self._sessions() as db:
            db.add_all(
                MotorLog(
                    game_id=e.game_id,
                    move_id=e.move_id,
                    motor_id=e.motor_id,
                    angle=e.angle,
                    status=e.status,
                    timestamp=e.timestamp,
                )
                for e in entries
            )
            await db.commit()

    async def abort_stale_games(self) -> int:
        """Games left in_progress by a previous server run can't be resumed."""
        async with self._sessions() as db:
            result = await db.execute(
                update(Game)
                .where(Game.status == GameStatus.in_progress)
                .values(
                    status=GameStatus.aborted,
                    termination_reason=TerminationReason.aborted,
                    end_time=datetime.now(UTC),
                )
            )
            await db.commit()
            return result.rowcount
