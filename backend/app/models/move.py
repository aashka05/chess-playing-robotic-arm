from sqlalchemy import Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Player


class Move(Base):
    __tablename__ = "move_table"
    __table_args__ = (UniqueConstraint("game_id", "move_number", name="uq_move_game_number"),)

    move_id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game_table.game_id", ondelete="CASCADE"), index=True)
    # Ply number: 1 for the first move of the game, 2 for the reply, ...
    move_number: Mapped[int] = mapped_column(Integer)
    move: Mapped[str] = mapped_column(String(10))  # SAN
    uci: Mapped[str] = mapped_column(String(5))
    fen_after: Mapped[str] = mapped_column(String(100))
    player: Mapped[Player] = mapped_column(
        Enum(Player, name="player", native_enum=False, create_constraint=True, length=20)
    )
    time_taken_ms: Mapped[int] = mapped_column(Integer)
    # Evaluation after the move, from White's point of view.
    eval_cp: Mapped[int | None] = mapped_column(Integer)
    eval_mate: Mapped[int | None] = mapped_column(Integer)
    detection_confidence: Mapped[float | None] = mapped_column(Float)

    game: Mapped["Game"] = relationship(back_populates="moves")  # noqa: F821
