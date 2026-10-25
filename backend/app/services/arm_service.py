"""Executes robot moves on the arm and logs every command to motor_log."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import chess

from controller.angles import (
    GRIPPER_MOTOR_ID,
    GRIPPER_SETTLE_SEC,
    AngleMap,
    CalibrationError,
    build_home_command,
    build_move_commands,
    gripper_angles,
)
from controller.driver import ArmDriver
from controller.planner import ArmPlan, ManualAction, plan_move
from app.models.enums import MotorStatus
from app.services.repository import MotorLogEntry

log = logging.getLogger(__name__)


@dataclass
class ArmResult:
    success: bool
    error: str | None = None
    manual: ManualAction | None = None
    commands_sent: int = 0


class ArmService:
    def __init__(self, driver: ArmDriver, angles_path: Path, repo, strict: bool):
        """strict=True (real arm): refuse to move if any square is uncalibrated.

        strict=False (mock arm): uncalibrated squares use 0-degree angles.
        """
        self.driver = driver
        self.angles_path = angles_path
        self.repo = repo
        self.strict = strict

    def _angles(self, angle_map: AngleMap | None, square: str) -> list[float]:
        if angle_map is not None and (self.strict or angle_map.has(square)):
            return angle_map.arm_angles(square)
        log.warning("[mock arm] no calibrated angles for %s; using zeros", square)
        return [0.0] * 5

    async def execute(
        self,
        game_id: int,
        move_id: int | None,
        board: chess.Board,
        move: chess.Move,
        robot_color: chess.Color = chess.BLACK,
    ) -> ArmResult:
        """`board` is the position before `move`.

        `robot_color` controls whether squares are mirrored for the lookup.
        When the robot plays white the JSON keys already match; when it plays
        black, squares are mirrored (a1 <-> h8).
        """
        plan: ArmPlan = plan_move(board, move)

        # Resolve every command before moving anything, so a missing calibration
        # entry can never leave a piece hanging in the gripper.
        try:
            angle_map = (
                AngleMap.load(self.angles_path, robot_color)
                if (self.strict or self.angles_path.exists())
                else None
            )
            commands = [(op, self._angles(angle_map, op.square)) for op in plan.ops]
        except CalibrationError as exc:
            return ArmResult(False, f"Arm calibration problem: {exc}", plan.manual)

        sent = 0
        for op, angles in commands:
            m_commands = build_move_commands(op, angles)
            for m_cmd in m_commands:
                reply = await self.driver.send(m_cmd)
                sent += 1
                if not reply.ok:
                    log.error("Arm failed on %s %s (cmd %s): %s", op.action, op.square, m_cmd, reply.message)
                    await self._log(game_id, move_id, op, angles, False)
                    return ArmResult(False, reply.message, plan.manual, sent)
            # Pause after gripper action so the servo has time to settle
            # and the piece is firmly gripped / cleanly released.
            await asyncio.sleep(GRIPPER_SETTLE_SEC)
            await self._log(game_id, move_id, op, angles, True)

            # Return to home after every operation (pick and place).
            # After pick: arm carries the piece safely via home before placing.
            # After place: arm returns to rest position.
            home_reply = await self.driver.send(build_home_command())
            sent += 1
            if not home_reply.ok:
                log.warning("Arm failed to return home after %s %s: %s", op.action, op.square, home_reply.message)

        return ArmResult(True, None, plan.manual, sent)

    async def _log(self, game_id, move_id, op, angles: list[float], ok: bool) -> None:
        now = datetime.now(UTC)
        status = MotorStatus.success if ok else MotorStatus.failure
        entries = [
            MotorLogEntry(game_id, move_id, motor_id, angle, status, now)
            for motor_id, angle in enumerate(angles)
        ]
        _, final_grip = gripper_angles(op)
        entries.append(MotorLogEntry(game_id, move_id, GRIPPER_MOTOR_ID, float(final_grip), status, now))
        try:
            await self.repo.add_motor_logs(entries)
        except Exception:
            log.exception("Could not write motor_log")
