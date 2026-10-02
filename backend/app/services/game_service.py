"""Game orchestration: setup, turns, clocks, detection, engine and arm.

One Session per user covers the whole flow from "Play New Game" to
GAME_OVER. The backend is authoritative: the app only sends intents
(press clock, resign, OK) and renders the snapshots broadcast here.
"""

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import asdict, dataclass
from datetime import date

import chess
import chess.pgn

from app.camera.base import CameraError, CameraSource
from app.models.enums import (
    Color,
    Difficulty,
    GameResult,
    GameStatus,
    Player,
    TerminationReason,
)
from app.services.arm_service import ArmService
from app.services.clock_service import ChessClock
from app.services.detection_service import DetectionService, VisionError
from app.services.engine_service import EngineService
from app.services.errors import BadRequest, Conflict, NotFound, Unprocessable
from app.services.game_rules import GameEnd, check_game_end, resignation_end, timeout_end
from app.services.state_machine import GameState as S
from app.services.state_machine import StateMachine

log = logging.getLogger(__name__)

CLOCK_POLL_SEC = 0.1


@dataclass
class MoveRecord:
    ply: int
    san: str
    uci: str
    player: Player
    fen_after: str
    time_taken_ms: int
    detection_confidence: float | None = None
    eval_cp: int | None = None
    eval_mate: int | None = None
    move_id: int | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["player"] = self.player.value
        return data


class Session:
    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username
        self.sm = StateMachine(S.SETUP_EMPTY)
        self.initial_fen = chess.STARTING_FEN
        self.game_id: int | None = None
        self.user_color: chess.Color = chess.WHITE
        self.difficulty = Difficulty.medium
        self.board = chess.Board()
        self.clock: ChessClock | None = None
        self.moves: list[MoveRecord] = []
        self.message: str | None = None
        self.manual_action: dict | None = None
        self.manual_done = asyncio.Event()
        self.status = GameStatus.in_progress
        self.result: GameResult | None = None
        self.termination_reason: TerminationReason | None = None
        self.subscribers: set[asyncio.Queue] = set()
        self.pipeline: asyncio.Task | None = None
        self.turn_started = 0.0
        self.robot_ms_at_press = 0.0

    @property
    def robot_color(self) -> chess.Color:
        return not self.user_color


class GameService:
    def __init__(
        self,
        repo,
        engine: EngineService,
        detection: DetectionService,
        camera: CameraSource,
        arm: ArmService,
        now: Callable[[], float] = time.monotonic,
    ):
        self.repo = repo
        self.engine = engine
        self.detection = detection
        self.camera = camera
        self.arm = arm
        self._now = now
        self._by_user: dict[int, Session] = {}
        self._by_game: dict[int, Session] = {}
        self._tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------------
    # lookup helpers
    # ------------------------------------------------------------------

    def session_for_user(self, user_id: int) -> Session | None:
        return self._by_user.get(user_id)

    def _setup_session(self, user_id: int) -> Session:
        s = self._by_user.get(user_id)
        if s is None or not s.sm.is_setup:
            raise NotFound("No game setup in progress. Tap 'Play New Game' first.")
        return s

    def game_session(self, game_id: int, user_id: int | None = None) -> Session:
        s = self._by_game.get(game_id)
        if s is None or (user_id is not None and s.user_id != user_id):
            raise NotFound("This game is not running.")
        return s

    def active_game_id(self, user_id: int) -> int | None:
        s = self._by_user.get(user_id)
        return s.game_id if s and s.sm.is_playing else None

    def _spawn(self, coro: Coroutine) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    # ------------------------------------------------------------------
    # setup
    # ------------------------------------------------------------------

    def start_setup(self, user_id: int, username: str) -> Session:
        for other in self._by_user.values():
            if other.sm.is_playing:
                if other.user_id == user_id:
                    raise Conflict("You already have a game in progress.")
                raise Conflict("The board is in use by another player's game.")
        s = Session(user_id, username)
        self._by_user[user_id] = s
        return s

    def cancel_setup(self, user_id: int) -> None:
        s = self._by_user.get(user_id)
        if s is not None and s.sm.is_setup:
            del self._by_user[user_id]

    async def _capture(self):
        try:
            return await self.camera.capture()
        except CameraError as exc:
            raise Unprocessable(str(exc)) from exc

    async def calibrate_empty_board(self, user_id: int) -> dict:
        s = self._setup_session(user_id)
        s.sm.require(S.SETUP_EMPTY)
        image = await self._capture()
        try:
            info = await self.detection.calibrate(image, s.initial_fen)
        except VisionError as exc:
            raise Unprocessable(str(exc)) from exc
        s.sm.transition(S.SETUP_PIECES)
        return {"state": s.sm.state, **info}

    async def verify_pieces(self, user_id: int) -> dict:
        s = self._setup_session(user_id)
        s.sm.require(S.SETUP_PIECES)
        s.sm.transition(S.VERIFY)
        try:
            image = await self.camera.capture()
            mismatches = await self.detection.verify_position(image, s.initial_fen)
        except (CameraError, VisionError) as exc:
            s.sm.transition(S.SETUP_PIECES)
            raise Unprocessable(str(exc)) from exc
        s.sm.transition(S.COLOR_SELECT if not mismatches else S.SETUP_PIECES)
        return {
            "state": s.sm.state,
            "correct": not mismatches,
            "expected_fen": s.initial_fen,
            "mismatches": mismatches,
        }

    def debug_skip_setup(self, user_id: int) -> dict:
        """Dev only: pretend calibration and verification succeeded."""
        s = self._setup_session(user_id)
        for state in (S.SETUP_PIECES, S.VERIFY, S.COLOR_SELECT):
            if s.sm.can(state):
                s.sm.transition(state)
        return {"state": s.sm.state}

    async def start_game(
        self,
        user_id: int,
        color: Color,
        difficulty: Difficulty,
        time_base_sec: int,
        time_increment_sec: int,
    ) -> Session:
        s = self._setup_session(user_id)
        s.sm.require(S.COLOR_SELECT)
        s.user_color = chess.WHITE if color == Color.white else chess.BLACK
        s.difficulty = difficulty
        s.board = chess.Board(s.initial_fen)
        s.clock = ChessClock(time_base_sec * 1000, time_increment_sec * 1000, now=self._now)
        s.game_id = await self.repo.create_game(
            user_id, difficulty, color, s.initial_fen, time_base_sec, time_increment_sec
        )
        self._by_game[s.game_id] = s
        self._spawn(self._watch_clock(s))

        if s.user_color == s.board.turn:
            self._begin_human_turn(s)
        else:
            s.sm.transition(S.ENGINE_THINKING)
            s.clock.start(s.robot_color)
            s.pipeline = self._spawn(self._guard(s, self._robot_turn(s)))
        self._broadcast_state(s)
        return s

    # ------------------------------------------------------------------
    # player actions
    # ------------------------------------------------------------------

    async def press_clock(self, user_id: int, game_id: int, forced_uci: str | None = None) -> None:
        s = self.game_session(game_id, user_id)
        s.sm.require(S.HUMAN_TURN)
        forced = None
        if forced_uci is not None:
            try:
                forced = chess.Move.from_uci(forced_uci)
            except ValueError as exc:
                raise BadRequest(f"Not a UCI move: {forced_uci}") from exc
            if forced not in s.board.legal_moves:
                raise BadRequest(f"Illegal move: {forced_uci}")

        think_ms = int((self._now() - s.turn_started) * 1000)
        # The robot's clock runs while we look at the board.
        s.robot_ms_at_press = s.clock.remaining_exact(s.robot_color)
        s.clock.start(s.robot_color)
        s.sm.transition(S.DETECTING)
        s.message = "Checking your move..."
        self._broadcast_state(s)
        s.pipeline = self._spawn(self._guard(s, self._after_clock_press(s, think_ms, forced)))

    async def resign(self, user_id: int, game_id: int) -> None:
        s = self.game_session(game_id, user_id)
        if not s.sm.is_playing:
            raise Conflict("The game is already over.")
        await self._finish(s, resignation_end())

    async def abort(self, user_id: int, game_id: int) -> None:
        s = self.game_session(game_id, user_id)
        if not s.sm.is_playing:
            raise Conflict("The game is already over.")
        await self._finish(s, GameEnd(None, TerminationReason.aborted, "aborted"), GameStatus.aborted)

    def manual_action_done(self, user_id: int, game_id: int) -> None:
        s = self.game_session(game_id, user_id)
        if s.manual_action is None:
            raise Conflict("Nothing to confirm.")
        s.manual_done.set()

    # ------------------------------------------------------------------
    # turn pipeline
    # ------------------------------------------------------------------

    async def _guard(self, s: Session, coro: Coroutine) -> None:
        """Run a pipeline step; an unexpected crash aborts the game instead of hanging it."""
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("Game %s pipeline crashed", s.game_id)
            s.message = f"Internal error: {exc}"
            if not s.sm.is_over:
                await self._finish(s, GameEnd(None, TerminationReason.aborted, "error"), GameStatus.aborted)

    def _begin_human_turn(self, s: Session) -> None:
        s.sm.transition(S.HUMAN_TURN)
        s.clock.start(s.user_color)
        s.turn_started = self._now()
        s.message = "Your move. Press your clock when done."

    async def _after_clock_press(self, s: Session, think_ms: int, forced: chess.Move | None) -> None:
        confidence = None
        if forced is not None:
            move = forced
        else:
            try:
                image = await self.camera.capture()
                result = await self.detection.detect_move(image, s.board)
            except (CameraError, VisionError) as exc:
                self._reject_move(s, "camera_error", str(exc))
                return
            if s.sm.is_over:
                return
            if not result.recognized:
                self._reject_move(s, result.reason, _REJECT_MESSAGES.get(result.reason, ""), result)
                return
            move, confidence = result.move, result.confidence

        if s.sm.is_over:
            return
        await self._apply_move(s, move, Player.human, think_ms, confidence)
        s.clock.add_increment(s.user_color)
        if await self._check_end(s):
            return
        s.sm.transition(S.ENGINE_THINKING)
        await self._robot_turn(s)

    def _reject_move(self, s: Session, reason: str, message: str, result=None) -> None:
        """Never apply an unrecognized move: refund the robot, hand the turn back."""
        s.clock.stop()
        s.clock.set_remaining(s.robot_color, s.robot_ms_at_press)
        s.clock.start(s.user_color)
        s.sm.transition(S.HUMAN_TURN)
        s.message = "Move not recognized. Restore the position, make your move again and press the clock."
        event = {"type": "move_not_recognized", "reason": reason, "message": message}
        if result is not None:
            event.update(
                confidence=result.confidence,
                mismatched_squares=result.mismatched_squares[:12],
                candidates=[asdict(c) for c in result.candidates],
            )
        self._broadcast(s, event)
        self._broadcast_state(s)

    async def _robot_turn(self, s: Session) -> None:
        started = self._now()
        if s.clock.running != s.robot_color:
            s.clock.start(s.robot_color)
        s.message = "Robot is thinking..."
        self._broadcast_state(s)

        board_before = s.board.copy()
        move = await self.engine.play(s.board.copy(), s.difficulty)
        if s.sm.is_over:
            return
        record = await self._apply_move(s, move, Player.robot, 0, None)
        s.sm.transition(S.ARM_EXECUTING)
        s.message = f"Robot plays {record.san}"
        self._broadcast_state(s)

        arm = await self.arm.execute(s.game_id, record.move_id, board_before, move)
        if s.sm.is_over:
            return
        if not arm.success or arm.manual is not None:
            await self._wait_for_manual_action(s, record, arm)
            if s.sm.is_over:
                return

        record.time_taken_ms = int((self._now() - started) * 1000)
        await self.repo.set_move_time(record.move_id, record.time_taken_ms)
        s.clock.add_increment(s.robot_color)
        if await self._check_end(s):
            return
        self._begin_human_turn(s)
        self._broadcast_state(s)

    async def _wait_for_manual_action(self, s: Session, record: MoveRecord, arm) -> None:
        """Pause the clocks until the user confirms they finished the robot's move."""
        s.clock.stop()
        move = chess.Move.from_uci(record.uci)
        if not arm.success:
            text = (
                f"The arm reported a problem ({arm.error}). Please finish the robot's move "
                f"{record.san} ({chess.square_name(move.from_square)} to "
                f"{chess.square_name(move.to_square)}) by hand, then press OK."
            )
            kind = "arm_error"
        else:
            text = arm.manual.message
            kind = arm.manual.kind
        s.manual_action = {
            "kind": kind,
            "message": text,
            "move": record.uci,
            "san": record.san,
            "square": arm.manual.square if arm.manual else None,
            "piece": arm.manual.piece if arm.manual else None,
        }
        s.manual_done.clear()
        s.message = text
        self._broadcast_state(s)
        await s.manual_done.wait()
        s.manual_action = None
        # Hand control back to the robot's clock until the turn switches.
        if not s.sm.is_over:
            s.clock.start(s.robot_color)

    async def _apply_move(
        self, s: Session, move: chess.Move, player: Player, time_ms: int, confidence: float | None
    ) -> MoveRecord:
        san = s.board.san(move)
        s.board.push(move)
        record = MoveRecord(
            ply=len(s.moves) + 1,
            san=san,
            uci=move.uci(),
            player=player,
            fen_after=s.board.fen(),
            time_taken_ms=time_ms,
            detection_confidence=confidence,
        )
        record.move_id = await self.repo.add_move(
            s.game_id, record.ply, san, record.uci, record.fen_after, player, time_ms, confidence
        )
        s.moves.append(record)
        self._spawn(self._evaluate(s, record, s.board.copy()))
        return record

    async def _evaluate(self, s: Session, record: MoveRecord, board: chess.Board) -> None:
        try:
            evaluation = await self.engine.evaluate(board)
            record.eval_cp, record.eval_mate = evaluation.cp, evaluation.mate
            await self.repo.set_move_eval(record.move_id, evaluation.cp, evaluation.mate)
            self._broadcast(
                s, {"type": "eval", "ply": record.ply, "eval_cp": evaluation.cp, "eval_mate": evaluation.mate}
            )
        except Exception:
            log.exception("Evaluation failed for game %s ply %s", s.game_id, record.ply)

    # ------------------------------------------------------------------
    # game end
    # ------------------------------------------------------------------

    async def _check_end(self, s: Session) -> bool:
        end = check_game_end(s.board, s.user_color)
        if end is None:
            return False
        await self._finish(s, end)
        return True

    async def _watch_clock(self, s: Session) -> None:
        while not s.sm.is_over:
            await asyncio.sleep(CLOCK_POLL_SEC)
            flagged = s.clock.flagged()
            if flagged is not None and s.sm.is_playing:
                await self._finish(s, timeout_end(s.board, flagged, s.user_color))

    async def _finish(self, s: Session, end: GameEnd, status: GameStatus = GameStatus.finished) -> None:
        if s.sm.is_over:
            return
        state_before = s.sm.state
        s.sm.transition(S.GAME_OVER)
        s.clock.stop()
        s.status = status
        s.result = end.result
        s.termination_reason = end.reason
        s.message = _END_MESSAGES.get(end.detail, end.reason.value)
        s.manual_done.set()  # release a pipeline waiting for the user
        # Don't interrupt the arm mid-move; the pipeline notices GAME_OVER afterwards.
        current = asyncio.current_task()
        if s.pipeline is not None and s.pipeline is not current and state_before != S.ARM_EXECUTING:
            s.pipeline.cancel()

        await self.repo.finish_game(
            s.game_id, status, end.result, end.reason, s.board.fen(), self._pgn(s)
        )
        self._broadcast_state(s)
        self._by_user.pop(s.user_id, None)
        self._spawn(self._forget_later(s.game_id))

    async def _forget_later(self, game_id: int, delay: float = 600) -> None:
        await asyncio.sleep(delay)
        self._by_game.pop(game_id, None)

    def _pgn(self, s: Session) -> str:
        game = chess.pgn.Game.from_board(s.board)
        human = s.username or "Human"
        robot = f"Robot (Stockfish {s.difficulty.value})"
        game.headers["Event"] = "Robot arm chess"
        game.headers["Date"] = date.today().strftime("%Y.%m.%d")
        game.headers["White"] = human if s.user_color == chess.WHITE else robot
        game.headers["Black"] = robot if s.user_color == chess.WHITE else human
        game.headers["TimeControl"] = f"{s.clock.base_ms // 1000}+{s.clock.increment_ms // 1000}"
        game.headers["Result"] = _pgn_result(s.result, s.user_color)
        if s.termination_reason is not None:
            game.headers["Termination"] = s.termination_reason.value
        return str(game)

    async def shutdown(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        for s in list(self._by_game.values()):
            if s.sm.is_playing:
                s.sm.transition(S.GAME_OVER)
                s.message = "The server was stopped."

    # ------------------------------------------------------------------
    # live updates
    # ------------------------------------------------------------------

    def subscribe(self, s: Session) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        s.subscribers.add(queue)
        queue.put_nowait(self.snapshot(s))
        return queue

    def unsubscribe(self, s: Session, queue: asyncio.Queue) -> None:
        s.subscribers.discard(queue)

    def _broadcast(self, s: Session, event: dict) -> None:
        for queue in s.subscribers:
            queue.put_nowait(event)

    def _broadcast_state(self, s: Session) -> None:
        self._broadcast(s, self.snapshot(s))

    def snapshot(self, s: Session) -> dict:
        last = s.board.peek().uci() if s.board.move_stack else None
        return {
            "type": "state",
            "game_id": s.game_id,
            "state": s.sm.state.value,
            "fen": s.board.fen(),
            "turn": chess.COLOR_NAMES[s.board.turn],
            "in_check": s.board.is_check(),
            "user_color": chess.COLOR_NAMES[s.user_color],
            "difficulty": s.difficulty.value,
            "clock": s.clock.snapshot() if s.clock else None,
            "moves": [m.to_dict() for m in s.moves],
            "last_move": last,
            "message": s.message,
            "manual_action": s.manual_action,
            "status": s.status.value,
            "result": s.result.value if s.result else None,
            "termination_reason": s.termination_reason.value if s.termination_reason else None,
            "camera_connected": self.camera.connected,
        }


_REJECT_MESSAGES = {
    "no_change": "The board looks unchanged. Make your move, then press the clock.",
    "low_confidence": "Could not tell which move you made.",
    "board_mismatch": "The board doesn't match the game. Check nothing is blocking the camera.",
    "no_legal_moves": "There are no legal moves.",
}

_END_MESSAGES = {
    "checkmate": "Checkmate!",
    "stalemate": "Stalemate: draw.",
    "insufficient_material": "Draw: insufficient material.",
    "fifty_moves": "Draw: 50-move rule.",
    "seventyfive_moves": "Draw: 75-move rule.",
    "threefold_repetition": "Draw by threefold repetition.",
    "fivefold_repetition": "Draw by fivefold repetition.",
    "resignation": "You resigned.",
    "timeout": "Time is up.",
    "aborted": "Game aborted.",
    "error": "Game aborted because of an internal error.",
}


def _pgn_result(result: GameResult | None, user_color: chess.Color) -> str:
    if result is None:
        return "*"
    if result == GameResult.draw:
        return "1/2-1/2"
    white_won = (result == GameResult.win) == (user_color == chess.WHITE)
    return "1-0" if white_won else "0-1"
