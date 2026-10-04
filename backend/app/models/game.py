from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Color, Difficulty, GameResult, GameStatus, TerminationReason


def _enum(cls, name: str) -> Enum:
    return Enum(cls, name=name, native_enum=False, create_constraint=True, length=20)


class Game(Base):
    __tablename__ = "game_table"

    game_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_table.user_id", ondelete="CASCADE"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    difficulty: Mapped[Difficulty] = mapped_column(_enum(Difficulty, "difficulty"))
    result: Mapped[GameResult | None] = mapped_column(_enum(GameResult, "game_result"))
    status: Mapped[GameStatus] = mapped_column(_enum(GameStatus, "game_status"))
    termination_reason: Mapped[TerminationReason | None] = mapped_column(
        _enum(TerminationReason, "termination_reason")
    )
    user_color: Mapped[Color] = mapped_column(_enum(Color, "user_color"))
    initial_fen: Mapped[str] = mapped_column(String(100))
    final_fen: Mapped[str | None] = mapped_column(String(100))
    pgn: Mapped[str | None] = mapped_column(Text)
    time_base_sec: Mapped[int] = mapped_column(Integer)
    time_increment_sec: Mapped[int] = mapped_column(Integer)

    moves: Mapped[list["Move"]] = relationship(  # noqa: F821
        back_populates="game", order_by="Move.move_number", cascade="all, delete-orphan"
    )
