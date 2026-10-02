from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    Color,
    Difficulty,
    GameResult,
    GameStatus,
    Player,
    TerminationReason,
)


class StartGameRequest(BaseModel):
    color: Color
    difficulty: Difficulty
    time_base_sec: int = Field(ge=30, le=3 * 3600)
    time_increment_sec: int = Field(ge=0, le=180)


class DebugMoveRequest(BaseModel):
    uci: str = Field(min_length=4, max_length=5)


class MoveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    move_id: int
    move_number: int
    move: str
    uci: str
    fen_after: str
    player: Player
    time_taken_ms: int
    eval_cp: int | None
    eval_mate: int | None
    detection_confidence: float | None


class GameSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: int
    user_id: int
    username: str | None = None
    start_time: datetime
    end_time: datetime | None
    difficulty: Difficulty
    result: GameResult | None
    status: GameStatus
    termination_reason: TerminationReason | None
    user_color: Color
    time_base_sec: int
    time_increment_sec: int
    move_count: int = 0


class GameDetail(GameSummary):
    initial_fen: str
    final_fen: str | None
    pgn: str | None
    moves: list[MoveOut]
