from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import MotorStatus


class MotorLog(Base):
    __tablename__ = "motor_log"

    log_id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game_table.game_id", ondelete="CASCADE"), index=True)
    move_id: Mapped[int | None] = mapped_column(ForeignKey("move_table.move_id", ondelete="SET NULL"))
    motor_id: Mapped[int] = mapped_column(Integer)
    angle: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[MotorStatus] = mapped_column(
        Enum(MotorStatus, name="motor_status", native_enum=False, create_constraint=True, length=20)
    )
