"""The whole game loop with fakes for DB, engine, camera and vision (arm mocked)."""

import asyncio
import itertools

import chess
import pytest

from controller.driver import MockArmDriver
from stockfish.engine import Evaluation
from app.models.enums import Color, Difficulty, GameResult, GameStatus, TerminationReason
from app.services.arm_service import ArmService
from app.services.errors import Unprocessable
from app.services.game_service import GameService
from app.services.state_machine import GameState as S
from app.services.state_machine import WrongState
from vision.move_matcher import match_move


class FakeRepo:
    def __init__(self):
        self.ids = itertools.count(1)
        self.moves, self.finished, self.motor = {}, {}, []

    async def create_game(self, *args):
        return next(self.ids)

    async def add_move(self, game_id, ply, san, uci, fen, player, ms, conf):
        mid = next(self.ids)
        self.moves[mid] = dict(ply=ply, san=san, uci=uci, player=player, conf=conf)
        return mid

    async def set_move_eval(self, mid, cp, mate):
        self.moves[mid].update(cp=cp, mate=mate)

    async def set_move_time(self, mid, ms):
        self.moves[mid]["ms"] = ms

    async def finish_game(self, game_id, status, result, reason, fen, pgn):
        self.finished[game_id] = dict(status=status, result=result, reason=reason, fen=fen, pgn=pgn)

    async def add_motor_logs(self, entries):
        self.motor.extend(entries)


class ScriptedEngine:
    """Plays the given UCI moves in order."""

    def __init__(self, moves):
        self.moves = list(moves)

    async def play(self, board, difficulty):
        return chess.Move.from_uci(self.moves.pop(0))

    async def evaluate(self, board):
        return Evaluation(cp=17, mate=None)


class FakeCamera:
    """The 'image' is simply the board position the human left on the table."""

    connected = True

    def __init__(self):
        self.table = chess.Board()

    async def capture(self):
        return self.table.copy()


class FakeDetection:
    async def calibrate(self, image, fen):
        return {"preview_jpeg_base64": ""}

    async def verify_position(self, image, fen):
        expected = chess.Board(fen).board_fen()
        return [] if image.board_fen() == expected else [{"square": "e2", "expected": "P", "detected": None}]

    async def detect_move(self, image, board):
        det = {chess.square_name(s): (p.symbol(), 0.95) for s, p in image.piece_map().items()}
        return match_move(board, det)


def make_service(engine_moves, camera=None):
    repo = FakeRepo()
    camera = camera or FakeCamera()
    svc = GameService(
        repo, ScriptedEngine(engine_moves), FakeDetection(), camera,
        ArmService(MockArmDriver(0), __import__("pathlib").Path("/nope"), repo, strict=False),
    )
    return svc, repo, camera


async def wait_for(svc, s, state, timeout=2.0):
    for _ in range(int(timeout / 0.01)):
        if s.sm.state == state and (state != S.HUMAN_TURN or s.sm.state == state):
            return
        await asyncio.sleep(0.01)
    pytest.fail(f"state is {s.sm.state}, expected {state}")


async def setup_session(svc, camera, uid=1):
    svc.start_setup(uid, "alice")
    await svc.calibrate_empty_board(uid)
    wrong = camera.table
    camera.table = chess.Board("8/8/8/8/8/8/8/8 w - - 0 1")
    result = await svc.verify_pieces(uid)
    assert not result["correct"] and result["state"] == S.SETUP_PIECES
    camera.table = wrong
    result = await svc.verify_pieces(uid)
    assert result["correct"] and result["state"] == S.COLOR_SELECT


async def human_moves(svc, s, camera, uci):
    camera.table.push_uci(uci)
    await svc.press_clock(s.user_id, s.game_id)


async def robot_moved(camera, s):
    # The arm (mocked) moved the robot's piece on the "real" table.
    camera.table.push(s.board.peek())


async def test_full_game_user_white_scholars_mate():
    svc, repo, camera = make_service(["e7e5", "b8c6", "g8f6"])
    await setup_session(svc, camera)
    s = await svc.start_game(1, Color.white, Difficulty.easy, 300, 2)
    assert s.sm.state == S.HUMAN_TURN and s.clock.running == chess.WHITE

    for uci in ["e2e4", "f1c4", "d1h5"]:
        await human_moves(svc, s, camera, uci)
        await wait_for(svc, s, S.HUMAN_TURN)
        await robot_moved(camera, s)

    await human_moves(svc, s, camera, "h5f7")
    await wait_for(svc, s, S.GAME_OVER)
    assert s.result == GameResult.win and s.termination_reason == TerminationReason.checkmate
    fin = repo.finished[s.game_id]
    assert fin["status"] == GameStatus.finished and "Qxf7#" in fin["pgn"] and "1-0" in fin["pgn"]
    assert [m["san"] for m in sorted(repo.moves.values(), key=lambda m: m["ply"])] == [
        "e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7#"]
    human_confs = [m["conf"] for m in repo.moves.values() if m["player"] == "human"]
    assert all(c and c > 0.9 for c in human_confs)
    await asyncio.sleep(0.05)
    assert all(m.get("cp") == 17 for m in repo.moves.values())  # evals stored
    assert repo.motor  # arm commands logged


async def test_user_black_robot_moves_first_without_detection():
    svc, repo, camera = make_service(["d2d4"])
    await setup_session(svc, camera)
    s = await svc.start_game(1, Color.black, Difficulty.hard, 60, 0)
    await wait_for(svc, s, S.HUMAN_TURN)
    assert s.board.peek().uci() == "d2d4"
    assert s.clock.running == chess.BLACK


async def test_unrecognized_move_is_never_applied_and_robot_time_refunded():
    svc, repo, camera = make_service(["e7e5"])
    await setup_session(svc, camera)
    s = await svc.start_game(1, Color.white, Difficulty.easy, 300, 0)
    events = svc.subscribe(s)
    await svc.press_clock(1, s.game_id)  # nothing moved on the table
    await wait_for(svc, s, S.HUMAN_TURN)
    assert s.board.move_stack == [] and repo.moves == {}
    assert s.clock.remaining_ms(chess.BLACK) == 300_000
    seen = []
    while not events.empty():
        seen.append(events.get_nowait())
    rejected = [e for e in seen if e["type"] == "move_not_recognized"]
    assert rejected and rejected[0]["reason"] == "no_change"

    # Now actually move.
    await human_moves(svc, s, camera, "e2e4")
    await wait_for(svc, s, S.HUMAN_TURN)
    assert [m.uci() for m in s.board.move_stack] == ["e2e4", "e7e5"]


async def test_press_clock_only_on_human_turn():
    svc, repo, camera = make_service(["e7e5"])
    await setup_session(svc, camera)
    s = await svc.start_game(1, Color.white, Difficulty.easy, 300, 0)
    camera.table.push_uci("e2e4")
    await svc.press_clock(1, s.game_id)
    with pytest.raises(WrongState):
        await svc.press_clock(1, s.game_id)  # double tap


async def test_promotion_waits_for_user_and_pauses_clock():
    svc, repo, camera = make_service(["b2b1q"])
    svc.start_setup(1, "a")
    svc.debug_skip_setup(1)
    s = svc._by_user[1]
    s.initial_fen = "8/8/8/8/8/6k1/1p6/4K3 w - - 0 1"
    camera.table = chess.Board(s.initial_fen)
    s = await svc.start_game(1, Color.white, Difficulty.easy, 300, 0)
    await human_moves(svc, s, camera, "e1d2")
    for _ in range(200):
        if s.manual_action:
            break
        await asyncio.sleep(0.01)
    assert s.manual_action["kind"] == "place_promoted_piece" and s.manual_action["square"] == "b1"
    assert s.clock.running is None
    svc.manual_action_done(1, s.game_id)
    await wait_for(svc, s, S.HUMAN_TURN)
    assert s.clock.running == chess.WHITE


async def test_resign_and_timeout():
    svc, repo, camera = make_service([])
    await setup_session(svc, camera)
    s = await svc.start_game(1, Color.white, Difficulty.easy, 300, 0)
    await svc.resign(1, s.game_id)
    assert s.result == GameResult.loss and s.termination_reason == TerminationReason.resignation
    assert svc.session_for_user(1) is None

    t = [0.0]
    svc2, repo2, camera2 = make_service([])
    svc2._now = lambda: t[0]
    await setup_session(svc2, camera2, uid=2)
    s2 = await svc2.start_game(2, Color.white, Difficulty.easy, 30, 0)
    t[0] += 31
    await wait_for(svc2, s2, S.GAME_OVER)
    assert s2.termination_reason == TerminationReason.timeout and s2.result == GameResult.loss


async def test_one_game_at_a_time():
    svc, repo, camera = make_service([])
    await setup_session(svc, camera)
    await svc.start_game(1, Color.white, Difficulty.easy, 300, 0)
    with pytest.raises(Exception, match="in use"):
        svc.start_setup(2, "bob")


async def test_camera_disconnected_during_setup():
    class NoCamera(FakeCamera):
        connected = False

        async def capture(self):
            from app.camera.base import CameraError
            raise CameraError("not connected")

    svc, _, _ = make_service([], camera=NoCamera())
    svc.start_setup(1, "a")
    with pytest.raises(Unprocessable):
        await svc.calibrate_empty_board(1)
