import json

import chess
import pytest

from controller.angles import AngleMap, build_move_commands, mirror_square
from controller.driver import MockArmDriver
from controller.planner import GRAVEYARD, ArmOp, plan_move
from app.services.arm_service import ArmService


def ops(board_fen, uci):
    board = chess.Board(board_fen)
    return plan_move(board, chess.Move.from_uci(uci))


def test_normal_move():
    plan = ops(chess.STARTING_FEN, "g1f3")
    assert plan.ops == [ArmOp("pick", "g1", "n"), ArmOp("place", "f3", "n")]
    assert plan.manual is None


def test_capture_removes_captured_piece_first():
    plan = ops("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", "e4d5")
    assert plan.ops == [
        ArmOp("pick", "d5", "p"), ArmOp("place", GRAVEYARD, "p"),
        ArmOp("pick", "e4", "p"), ArmOp("place", "d5", "p"),
    ]


def test_castling_both_sides():
    fen = "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1"
    assert ops(fen, "e8g8").ops == [
        ArmOp("pick", "e8", "k"), ArmOp("place", "g8", "k"),
        ArmOp("pick", "h8", "r"), ArmOp("place", "f8", "r"),
    ]
    assert [o.square for o in ops(fen, "e8c8").ops] == ["e8", "c8", "a8", "d8"]


def test_en_passant():
    plan = ops("rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3", "e5f6")
    assert [(o.action, o.square) for o in plan.ops] == [
        ("pick", "f5"), ("place", GRAVEYARD), ("pick", "e5"), ("place", "f6"),
    ]


def test_promotion_with_capture_needs_manual_piece():
    plan = ops("3r4/2P5/8/8/8/2k5/8/4K3 w - - 0 1", "c7d8q")
    assert [o.square for o in plan.ops] == ["d8", GRAVEYARD, "c7", GRAVEYARD]
    assert plan.manual.square == "d8" and plan.manual.piece == "Q"
    black = ops("4k3/8/8/8/8/8/p7/4K3 b - - 0 1", "a2a1n")
    assert black.manual.piece == "n"


def test_mirror_and_m_commands():
    assert mirror_square("a1") == "h8" and mirror_square("e2") == "d7"
    # When robot plays BLACK, use mirrored keys
    amap_black = AngleMap({"h8": [10, 20, 30, 40]}, chess.BLACK)
    angles = amap_black.arm_angles("a1")
    # JSON order [m0, m3, m2, m1] -> servo order, wrist roll = base - 5
    assert angles == [10.0, 40.0, 30.0, 20.0, 5.0]

    # When robot plays WHITE, use direct keys (no mirroring)
    amap_white = AngleMap({"a1": [10, 20, 30, 40]}, chess.WHITE)
    assert amap_white.arm_angles("a1") == [10.0, 40.0, 30.0, 20.0, 5.0]

    pick_cmds = build_move_commands(ArmOp("pick", "a1", "p"), angles)
    assert len(pick_cmds) == 3  # open gripper, move arm, close gripper
    assert pick_cmds[0] == "M 20 5:70"  # open gripper
    assert pick_cmds[1] == "M 15 0:10 1:40 2:30 3:20 4:5"  # move arm
    assert pick_cmds[2] == "M 20 5:88"  # close gripper
    place_cmds = build_move_commands(ArmOp("place", "a1", "p"), angles)
    assert len(place_cmds) == 2  # move arm, open gripper
    assert place_cmds[0] == "M 15 0:10 1:40 2:30 3:20 4:5"  # move arm
    assert place_cmds[1] == "M 20 5:70"  # release piece


class LogRepo:
    def __init__(self):
        self.rows = []

    async def add_motor_logs(self, entries):
        self.rows.extend(entries)


async def test_arm_service_logs_every_motor(tmp_path):
    # Robot plays WHITE → no mirroring, keys used directly
    path = tmp_path / "angles.json"
    path.write_text(json.dumps({s: [1, 2, 3, 4] for s in ["g1", "f3"]}))
    repo = LogRepo()
    svc = ArmService(MockArmDriver(0), path, repo, strict=True)
    result = await svc.execute(1, 7, chess.Board(), chess.Move.from_uci("g1f3"), chess.WHITE)
    assert result.success
    # pick=3 M-cmds + home=1 + place=2 M-cmds + home=1 = 7
    assert result.commands_sent == 7
    assert len(repo.rows) == 12  # 2 ops x (5 servos + gripper)
    assert {r.motor_id for r in repo.rows} == {0, 1, 2, 3, 4, 5}
    assert all(r.move_id == 7 and r.status == "success" for r in repo.rows)


async def test_strict_arm_refuses_uncalibrated_graveyard(tmp_path):
    path = tmp_path / "angles.json"
    path.write_text(json.dumps({mirror_square(s): [1, 2, 3, 4] for s in ["d5", "e4"]}))
    driver = MockArmDriver(0)
    svc = ArmService(driver, path, LogRepo(), strict=True)
    board = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
    result = await svc.execute(1, None, board, chess.Move.from_uci("e4d5"))
    assert not result.success and "graveyard" in result.error
    assert driver.sent == []  # nothing moved


async def test_arm_failure_is_logged_and_stops():
    driver = MockArmDriver(0)
    driver.fail_next = "servo stall"
    repo = LogRepo()
    svc = ArmService(driver, pytest.importorskip("pathlib").Path("/nonexistent"), repo, strict=False)
    result = await svc.execute(1, None, chess.Board(), chess.Move.from_uci("e2e4"))
    assert not result.success and "servo stall" in result.error
    assert len(driver.sent) == 1
    assert all(r.status == "failure" for r in repo.rows)
