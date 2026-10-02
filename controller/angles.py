"""Square -> servo angles, from the calibration file (angles_dict.json).

Mapping rules come from controller/send_angles.py:
  * board squares are mirrored (a1 <-> h8) before lookup,
  * the JSON value [v0, v1, v2, v3] is servo order [0, 3, 2, 1],
  * servo 4 (wrist roll) is fixed at 180,
  * the gripper (servo 5) angles depend on the piece type.
The off-board "graveyard" entry is looked up as-is (no mirroring).
"""

import json
from pathlib import Path

from controller.planner import GRAVEYARD, ArmOp

JSON_MOTOR_ORDER = [0, 3, 2, 1]
WRIST_ROLL_FIXED = 180.0
GRIPPER_MOTOR_ID = 5

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
    def __init__(self, data: dict[str, list[float]]):
        self.data = data

    @classmethod
    def load(cls, path: Path) -> "AngleMap":
        if not path.exists():
            raise CalibrationError(f"Angles calibration file not found: {path}")
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise CalibrationError(f"Could not parse {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise CalibrationError(f"{path} must map 'square' -> [v0, v1, v2, v3]")
        return cls(data)

    def key_for(self, square: str) -> str:
        return GRAVEYARD if square == GRAVEYARD else mirror_square(square)

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
        angles[4] = WRIST_ROLL_FIXED
        return angles


def gripper_angles(op: ArmOp) -> tuple[float, float]:
    """(g0, g1) for a SEQ command. pick: open then grip; place: skip, then open."""
    try:
        gripper_open, gripper_grip = GRIPPER_ANGLES[op.piece]
    except KeyError as exc:
        raise ValueError(f"Unsupported piece '{op.piece}'") from exc
    if op.action == "pick":
        return gripper_open, gripper_grip
    return -1, gripper_open


def build_seq_command(op: ArmOp, arm_angles: list[float]) -> str:
    """SEQ,g0,base,shoulder,elbow,wristPitch,wristRoll,g1"""
    g0, g1 = gripper_angles(op)
    values = [g0] + arm_angles + [g1]
    return "SEQ," + ",".join(f"{v:.1f}" for v in values)
