"""Square -> servo angles, from the calibration file (angles_dict.json).

Mapping rules come from controller/send_angles.py:
  * When the robot plays BLACK, board squares are mirrored (a1 <-> h8)
    before lookup.  When the robot plays WHITE the JSON keys already
    match the chess square names — no mirroring needed.
  * the JSON value [v0, v1, v2, v3] is servo order [0, 3, 2, 1],
  * servo 4 (wrist roll) is fixed at 180,
  * the gripper (servo 5) angles depend on the piece type.
The off-board "graveyard" entry is looked up as-is (no mirroring).
"""

import json
from pathlib import Path

import chess

from controller.planner import GRAVEYARD, ArmOp

JSON_MOTOR_ORDER = [0, 3, 2, 1]
WRIST_ROLL_OFFSET = -5  # servo 4 = base angle + this offset
GRIPPER_MOTOR_ID = 5
HOME_ANGLES = [95, 180, 70, 80, 90, 90]  # same as send_angles.py HOME
GRIPPER_SETTLE_SEC = 2.0  # seconds to pause after gripper open/close

GRIPPER_ANGLES = {
    "p": (70, 88),  # pawn: open, grip
    "n": (70, 95),  # knight: open, grip
    "b": (65, 85),  # bishop: open, grip
    "r": (65, 85),  # rook: open, grip
    "q": (65, 85),  # queen: open, grip
    "k": (65, 85),  # king: open, grip
}


class CalibrationError(Exception):
    pass


def mirror_square(square: str) -> str:
    f, r = square.strip().lower()
    f = chr(ord("a") + ord("h") - ord(f))
    r = str(9 - int(r))
    return f + r


class AngleMap:
    def __init__(self, data: dict[str, list[float]], robot_color: chess.Color = chess.BLACK):
        self.data = data
        self.robot_color = robot_color

    @classmethod
    def load(cls, path: Path, robot_color: chess.Color = chess.BLACK) -> "AngleMap":
        if not path.exists():
            raise CalibrationError(f"Angles calibration file not found: {path}")
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise CalibrationError(f"Could not parse {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise CalibrationError(f"{path} must map 'square' -> [v0, v1, v2, v3]")
        return cls(data, robot_color)

    def key_for(self, square: str) -> str:
        if square == GRAVEYARD:
            return GRAVEYARD
        # Mirror only when the robot plays black (board is flipped).
        # When the robot plays white, the JSON keys match the chess squares directly.
        if self.robot_color == chess.BLACK:
            return mirror_square(square)
        return square

    def has(self, square: str) -> bool:
        return self.key_for(square) in self.data

    def arm_angles(self, square: str) -> list[float]:
        """The 5 arm servo angles in Arduino order: base, shoulder, elbow, wristPitch, wristRoll."""
        key = self.key_for(square)
        if key not in self.data:
            raise CalibrationError(f"No calibrated angles for '{key}' (board square {square})")
        value = self.data[key]
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            raise CalibrationError(f"Entry '{key}' has an unexpected shape: {value!r}")
        angles = [0.0] * 5
        for json_index, servo_index in enumerate(JSON_MOTOR_ORDER):
            angles[servo_index] = float(value[json_index])
        angles[4] = angles[0] + WRIST_ROLL_OFFSET  # servo 4 always tracks base
        return angles


def gripper_angles(op: ArmOp) -> tuple[float, float]:
    """(g0, g1) for a pick/place. pick: open then grip; place: skip (-1), then open."""
    try:
        gripper_open, gripper_grip = GRIPPER_ANGLES[op.piece]
    except KeyError as exc:
        raise ValueError(f"Unsupported piece '{op.piece}'") from exc
    if op.action == "pick":
        return gripper_open, gripper_grip
    return -1, gripper_open


def _build_m_command(angles: list[float], delay: int = 15,
                     indices: list[int] | None = None) -> str:
    """Build an M-command string matching the Arduino protocol.

    Format:  ``M <delay_ms> <idx>:<angle> [<idx>:<angle> ...]``
    """
    if indices is None:
        indices = list(range(len(angles)))
    pairs = " ".join(f"{i}:{int(round(angles[i]))}" for i in indices)
    return f"M {delay} {pairs}"


def build_move_commands(op: ArmOp, arm_angles: list[float]) -> list[str]:
    """Return the list of M-commands for a pick or place operation.

    A pick sends:
      1. M-command to open the gripper  (servo 5 → open angle)
      2. M-command to move the arm      (servos 0-4 to the target angles)
      3. M-command to close the gripper  (servo 5 → grip angle)

    A place sends:
      1. M-command to move the arm      (servos 0-4 to the target angles)
      2. M-command to release the piece  (servo 5 → open angle)
    """
    try:
        g_open, g_grip = GRIPPER_ANGLES[op.piece]
    except KeyError as exc:
        raise ValueError(f"Unsupported piece '{op.piece}'") from exc

    # Full 6-element angle list: arm angles (0-4) + gripper (5, placeholder)
    full = list(arm_angles[:5]) + [0.0]
    commands: list[str] = []

    if op.action == "pick":
        # 1. Open gripper
        full[5] = g_open
        commands.append(_build_m_command(full, delay=20, indices=[5]))
        # 2. Move arm to square
        commands.append(_build_m_command(full, delay=15, indices=list(range(5))))
        # 3. Close gripper (grab piece)
        full[5] = g_grip
        commands.append(_build_m_command(full, delay=20, indices=[5]))
    elif op.action == "place":
        # 1. Move arm to square
        commands.append(_build_m_command(full, delay=15, indices=list(range(5))))
        # 2. Open gripper (release piece)
        full[5] = g_open
        commands.append(_build_m_command(full, delay=20, indices=[5]))
    else:
        raise ValueError(f"Unknown arm action: {op.action!r}")

    return commands


def build_home_command() -> str:
    """Return a single M-command that sends all 6 servos to the home position."""
    return _build_m_command(HOME_ANGLES, delay=20, indices=list(range(6)))
