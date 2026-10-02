"""initial schema: users, games, moves, motor log

Revision ID: 0001
Revises:
Create Date: 2026-09-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=20)


def upgrade() -> None:
    op.create_table(
        "user_table",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", _enum("role", "admin", "client"), nullable=False),
    )

    op.create_table(
        "game_table",
        sa.Column("game_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user_table.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("difficulty", _enum("difficulty", "easy", "medium", "hard"), nullable=False),
        sa.Column("result", _enum("game_result", "win", "loss", "draw"), nullable=True),
        sa.Column("status", _enum("game_status", "in_progress", "finished", "aborted"), nullable=False),
        sa.Column(
            "termination_reason",
            _enum("termination_reason", "checkmate", "stalemate", "draw_rule", "resignation", "timeout", "aborted"),
            nullable=True,
        ),
        sa.Column("user_color", _enum("user_color", "white", "black"), nullable=False),
        sa.Column("initial_fen", sa.String(100), nullable=False),
        sa.Column("final_fen", sa.String(100), nullable=True),
        sa.Column("pgn", sa.Text(), nullable=True),
        sa.Column("time_base_sec", sa.Integer(), nullable=False),
        sa.Column("time_increment_sec", sa.Integer(), nullable=False),
    )
    op.create_index("ix_game_table_user_id", "game_table", ["user_id"])

    op.create_table(
        "move_table",
        sa.Column("move_id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("game_table.game_id", ondelete="CASCADE"), nullable=False),
        sa.Column("move_number", sa.Integer(), nullable=False),
        sa.Column("move", sa.String(10), nullable=False),
        sa.Column("uci", sa.String(5), nullable=False),
        sa.Column("fen_after", sa.String(100), nullable=False),
        sa.Column("player", _enum("player", "human", "robot"), nullable=False),
        sa.Column("time_taken_ms", sa.Integer(), nullable=False),
        sa.Column("eval_cp", sa.Integer(), nullable=True),
        sa.Column("eval_mate", sa.Integer(), nullable=True),
        sa.Column("detection_confidence", sa.Float(), nullable=True),
        sa.UniqueConstraint("game_id", "move_number", name="uq_move_game_number"),
    )
    op.create_index("ix_move_table_game_id", "move_table", ["game_id"])

    op.create_table(
        "motor_log",
        sa.Column("log_id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("game_table.game_id", ondelete="CASCADE"), nullable=False),
        sa.Column("move_id", sa.Integer(), sa.ForeignKey("move_table.move_id", ondelete="SET NULL"), nullable=True),
        sa.Column("motor_id", sa.Integer(), nullable=False),
        sa.Column("angle", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", _enum("motor_status", "success", "failure"), nullable=False),
    )
    op.create_index("ix_motor_log_game_id", "motor_log", ["game_id"])


def downgrade() -> None:
    op.drop_table("motor_log")
    op.drop_table("move_table")
    op.drop_table("game_table")
    op.drop_table("user_table")
