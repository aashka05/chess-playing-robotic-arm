import chess
import pytest

from app.services.move_explainer import explain_attempt


def seen_after(board: chess.Board, *moves: tuple[str, str], promote: str | None = None, remove=()) -> dict:
    """What the camera sees after physically moving pieces (no rule checks)."""
    placement = {chess.square_name(sq): p.symbol() for sq, p in board.piece_map().items()}
    for frm, to in moves:
        placement[to] = placement.pop(frm)
    if promote:
        placement[moves[-1][1]] = promote
    for sq in remove:
        placement.pop(sq)
    return placement


def explain(fen: str, *moves, **kw):
    board = chess.Board(fen)
    return explain_attempt(board, seen_after(board, *moves, **kw))


START = chess.STARTING_FEN


def test_unchanged_board():
    board = chess.Board()
    assert explain_attempt(board, seen_after(board)).kind == "no_change"


def test_legal_move_is_reported_as_legal():
    r = explain(START, ("e2", "e4"))
    assert r.kind == "legal" and "e4" in r.message


def test_wrong_turn():
    r = explain(START, ("g8", "f6"))
    assert (r.kind, r.reason) == ("illegal", "wrong_turn")
    assert r.message == "Illegal move: black knight from g8 to f6. It's White's turn, not Black's."


def test_bishop_geometry():
    r = explain("rnbqkbnr/pppppppp/8/8/8/8/PP1PPPPP/RNBQKBNR w KQkq - 0 1", ("c1", "c3"))
    assert r.reason == "bad_geometry"
    assert "Bishop can't move from c1 to c3: bishops move diagonally" in r.message
    assert r.piece == "white bishop" and (r.from_square, r.to_square) == ("c1", "c3")


@pytest.mark.parametrize("frm,to,phrase", [
    ("g1", "g3", "knights move in an L-shape"),
    ("d1", "c3", "queens move in straight lines or diagonally"),
])
def test_other_piece_geometry(frm, to, phrase):
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PP1P1P1P/RNBQKBNR w KQkq - 0 1"
    assert phrase in explain(fen, (frm, to)).message


def test_rook_geometry():
    r = explain("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", ("a1", "b2"))
    assert "rooks move in straight lines" in r.message


def test_king_geometry():
    r = explain("4k3/8/8/8/8/8/8/4K3 w - - 0 1", ("e1", "e3"))
    assert "kings move one square in any direction" in r.message


def test_path_blocked():
    r = explain(START, ("a1", "a3"))
    assert r.reason == "blocked"
    assert "The path is blocked by the white pawn on a2." in r.message


def test_capturing_own_piece():
    board = chess.Board("4k3/8/8/8/8/8/8/R2NK3 w - - 0 1")
    seen = seen_after(board, ("a1", "d1"))  # rook "takes" own knight
    r = explain_attempt(board, seen)
    assert r.reason == "own_piece"
    assert "can't capture your own piece (white knight on d1)" in r.message


def test_leaves_king_in_check_names_the_checker():
    # The e2 knight is pinned by the rook on e8.
    r = explain("4r1k1/8/8/8/8/8/4N3/4K3 w - - 0 1", ("e2", "c3"))
    assert r.reason == "leaves_king_in_check"
    assert "black rook on e8" in r.message


def test_keeps_king_in_check():
    r = explain("4r1k1/8/8/8/8/8/P7/4K3 w - - 0 1", ("a2", "a3"))
    assert r.reason == "still_in_check"
    assert "in check from the black rook on e8" in r.message


def test_king_moves_into_check():
    r = explain("3r2k1/8/8/8/8/8/8/4K3 w - - 0 1", ("e1", "d1"))
    assert r.reason == "king_into_check"
    assert "d1 is attacked by the black rook on d8" in r.message


@pytest.mark.parametrize("fen,phrase", [
    ("4k3/8/8/8/8/8/8/4K2R w - - 0 1", "king or rooks have already moved"),
    ("4k3/8/8/8/8/8/8/R3K2R w Q - 0 1", "rook on h1 has already moved"),
    ("4k3/8/8/8/8/8/8/4KB1R w K - 0 1", "blocked by the white bishop on f1"),
    ("4r1k1/8/8/8/8/8/8/4K2R w K - 0 1", "while in check (from the black rook on e8)"),
    ("5rk1/8/8/8/8/8/8/4K2R w K - 0 1", "pass through f1, which is attacked by the black rook on f8"),
    ("6rk/8/8/8/8/8/8/4K2R w K - 0 1", "end in check on g1 from the black rook on g8"),
])
def test_castling_not_allowed(fen, phrase):
    r = explain(fen, ("e1", "g1"), ("h1", "f1"))
    assert r.reason == "castling" and phrase in r.message, r.message


def test_castling_attempt_with_only_the_king_moved():
    r = explain("4k3/8/8/8/8/8/8/4KB1R w K - 0 1", ("e1", "g1"))
    assert r.reason == "castling"


def test_invalid_en_passant():
    # Black pawn on d5 got there long ago: no en passant square.
    r = explain("4k3/8/8/3pP3/8/8/8/4K3 w - - 0 5", ("e5", "d6"), remove=["d5"])
    assert r.reason == "bad_en_passant"


def test_valid_en_passant_is_legal():
    r = explain("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 5", ("e5", "d6"), remove=["d5"])
    assert r.kind == "legal"


@pytest.mark.parametrize("promote,phrase", [
    ("K", "can't promote to a king"),
    ("P", "must be promoted"),
])
def test_invalid_promotion(promote, phrase):
    r = explain("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", ("a7", "a8"), promote=promote)
    assert r.reason == "bad_promotion" and phrase in r.message


def test_valid_promotion_is_legal():
    assert explain("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", ("a7", "a8"), promote="Q").kind == "legal"


@pytest.mark.parametrize("fen,move,reason,phrase", [
    ("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1", ("e4", "e3"), "pawn_direction", "can't move backwards"),
    ("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1", ("e4", "f4"), "pawn_direction", "can't move sideways"),
    ("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1", ("e4", "e6"), "pawn_double", "only move two squares on its first move"),
    ("4k3/8/8/8/8/4n3/4P3/4K3 w - - 0 1", ("e2", "e4"), "blocked", "blocked by the black knight on e3"),
    ("4k3/8/8/8/4n3/8/4P3/4K3 w - - 0 1", ("e2", "e4"), "pawn_blocked", "can't capture straight ahead"),
])
def test_pawn_moved_incorrectly(fen, move, reason, phrase):
    r = explain(fen, move)
    assert r.reason == reason and phrase in r.message, r.message


def test_several_pieces_changed_is_unclear_and_lists_squares():
    board = chess.Board()
    seen = seen_after(board, ("e2", "e4"), ("d2", "d4"), ("g1", "f3"))
    r = explain_attempt(board, seen)
    assert r.kind == "unclear"
    assert r.changed_squares == ["g1", "d2", "e2", "f3", "d4", "e4"]  # board order a1..h8
    assert "6 squares differ" in r.message and "g1, d2, e2, f3, d4, e4" in r.message


def test_piece_appearing_from_nowhere_is_unclear():
    board = chess.Board()
    seen = seen_after(board)
    seen["e5"] = "Q"
    assert explain_attempt(board, seen).kind == "unclear"
