import chess

from app.models.enums import GameResult, TerminationReason
from app.services.game_rules import check_game_end, resignation_end, timeout_end


def play(board, *sans):
    for san in sans:
        board.push_san(san)
    return board


def test_ongoing_game():
    assert check_game_end(chess.Board(), chess.WHITE) is None


def test_checkmate_user_loses():
    board = play(chess.Board(), "f3", "e5", "g4", "Qh4#")  # fool's mate
    end = check_game_end(board, chess.WHITE)
    assert end.reason == TerminationReason.checkmate
    assert end.result == GameResult.loss
    assert check_game_end(board, chess.BLACK).result == GameResult.win


def test_stalemate():
    board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    end = check_game_end(board, chess.WHITE)
    assert end.reason == TerminationReason.stalemate
    assert end.result == GameResult.draw


def test_insufficient_material():
    board = chess.Board("8/8/4k3/8/8/3K4/8/8 w - - 0 1")
    end = check_game_end(board, chess.WHITE)
    assert end.reason == TerminationReason.draw_rule
    assert end.detail == "insufficient_material"


def test_threefold_repetition_is_claimed():
    board = play(chess.Board(), "Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8")
    end = check_game_end(board, chess.BLACK)
    assert end.reason == TerminationReason.draw_rule
    assert end.detail == "threefold_repetition"


def test_fifty_move_rule():
    board = chess.Board("8/8/4k3/8/8/3K4/R7/8 w - - 99 80")
    board.push_san("Ra3")
    end = check_game_end(board, chess.WHITE)
    assert end.reason == TerminationReason.draw_rule
    assert end.detail == "fifty_moves"


def test_timeout_opponent_can_mate():
    board = chess.Board()
    end = timeout_end(board, flagged=chess.WHITE, user_color=chess.WHITE)
    assert end.result == GameResult.loss
    assert end.reason == TerminationReason.timeout
    # Robot flags -> user wins.
    assert timeout_end(board, chess.BLACK, chess.WHITE).result == GameResult.win


def test_timeout_is_draw_when_opponent_has_bare_king():
    board = chess.Board("8/8/4k3/8/8/3K4/R7/8 w - - 0 1")
    end = timeout_end(board, flagged=chess.WHITE, user_color=chess.WHITE)
    assert end.result == GameResult.draw


def test_resignation():
    end = resignation_end()
    assert end.result == GameResult.loss
    assert end.reason == TerminationReason.resignation
