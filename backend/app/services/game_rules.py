"""Game-end detection and result mapping (results are from the user's view)."""

from dataclasses import dataclass

import chess

from app.models.enums import GameResult, TerminationReason

_TERMINATION_MAP = {
    chess.Termination.CHECKMATE: TerminationReason.checkmate,
    chess.Termination.STALEMATE: TerminationReason.stalemate,
    chess.Termination.INSUFFICIENT_MATERIAL: TerminationReason.draw_rule,
    chess.Termination.SEVENTYFIVE_MOVES: TerminationReason.draw_rule,
    chess.Termination.FIVEFOLD_REPETITION: TerminationReason.draw_rule,
    chess.Termination.FIFTY_MOVES: TerminationReason.draw_rule,
    chess.Termination.THREEFOLD_REPETITION: TerminationReason.draw_rule,
}


@dataclass(frozen=True)
class GameEnd:
    result: GameResult
    reason: TerminationReason
    detail: str


def _result_for(winner: chess.Color | None, user_color: chess.Color) -> GameResult:
    if winner is None:
        return GameResult.draw
    return GameResult.win if winner == user_color else GameResult.loss


def check_game_end(board: chess.Board, user_color: chess.Color) -> GameEnd | None:
    """Return how the game ended, or None if play continues.

    The board must contain the full move stack for repetition to be detected.
    """
    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        return None
    return GameEnd(
        result=_result_for(outcome.winner, user_color),
        reason=_TERMINATION_MAP.get(outcome.termination, TerminationReason.draw_rule),
        detail=outcome.termination.name.lower(),
    )


def timeout_end(board: chess.Board, flagged: chess.Color, user_color: chess.Color) -> GameEnd:
    """The side `flagged` ran out of time.

    FIDE: it's a draw if the opponent cannot possibly checkmate.
    """
    opponent = not flagged
    winner = None if board.has_insufficient_material(opponent) else opponent
    return GameEnd(_result_for(winner, user_color), TerminationReason.timeout, "timeout")


def resignation_end() -> GameEnd:
    # Only the human can resign.
    return GameEnd(GameResult.loss, TerminationReason.resignation, "resignation")
