import chess

from vision.move_matcher import diff_against_fen, match_move


def detections_for(board: chess.Board, conf: float = 0.9) -> dict:
    return {
        chess.square_name(sq): (p.symbol(), conf)
        for sq, p in board.piece_map().items()
    }


def after(board: chess.Board, uci: str) -> chess.Board:
    b = board.copy()
    b.push_uci(uci)
    return b


def test_simple_pawn_move():
    board = chess.Board()
    result = match_move(board, detections_for(after(board, "e2e4")))
    assert result.recognized
    assert result.move.uci() == "e2e4"
    assert result.confidence >= 0.9


def test_no_change_is_rejected():
    board = chess.Board()
    result = match_move(board, detections_for(board))
    assert not result.recognized
    assert result.reason == "no_change"
    assert result.move is None


def test_capture():
    board = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
    result = match_move(board, detections_for(after(board, "e4d5")))
    assert result.recognized and result.move.uci() == "e4d5"


def test_castling():
    board = chess.Board("r3k2r/pppqbppp/2np1n2/4p3/2B1P1b1/2NP1N2/PPPQBPPP/R3K2R w KQkq - 0 1")
    result = match_move(board, detections_for(after(board, "e1g1")))
    assert result.recognized and result.move.uci() == "e1g1"


def test_en_passant():
    board = chess.Board("rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3")
    result = match_move(board, detections_for(after(board, "e5f6")))
    assert result.recognized and result.move.uci() == "e5f6"


def test_promotion_picks_detected_piece_type():
    board = chess.Board("8/4P3/8/8/8/2k5/8/4K3 w - - 0 1")
    result = match_move(board, detections_for(after(board, "e7e8n")))
    assert result.recognized and result.move.uci() == "e7e8n"


def test_tolerates_misclassified_piece_type():
    # The knight lands on f3 but YOLO calls it a bishop.
    board = chess.Board()
    det = detections_for(after(board, "g1f3"))
    det["f3"] = ("B", 0.7)
    result = match_move(board, det)
    assert result.recognized and result.move.uci() == "g1f3"


def test_tolerates_a_missed_unrelated_piece():
    board = chess.Board()
    det = detections_for(after(board, "d2d4"))
    del det["h8"]
    result = match_move(board, det)
    assert result.recognized and result.move.uci() == "d2d4"


def test_illegal_move_is_not_applied():
    # Pawn "moves" e2 -> e5: not legal; must not be recognized as e2e4.
    board = chess.Board()
    det = detections_for(board)
    del det["e2"]
    det["e5"] = ("P", 0.9)
    result = match_move(board, det)
    assert not result.recognized


def test_ambiguous_piece_disappeared():
    # The e2 pawn vanished (hand in the way?) - nothing matches confidently.
    board = chess.Board()
    det = detections_for(board)
    del det["e2"]
    result = match_move(board, det)
    assert not result.recognized


def test_heavily_disturbed_board():
    board = chess.Board()
    det = detections_for(after(board, "e2e4"))
    for sq in ["a1", "b1", "c1", "d1", "f1", "g1", "h1", "a2", "b2", "c2", "d2", "f2", "g2", "h2"]:
        det.pop(sq, None)
    result = match_move(board, det)
    assert not result.recognized
    assert result.reason == "board_mismatch"


def test_black_move():
    board = chess.Board()
    board.push_uci("e2e4")
    result = match_move(board, detections_for(after(board, "c7c5")))
    assert result.recognized and result.move.uci() == "c7c5"


def test_diff_against_fen():
    det = detections_for(chess.Board())
    det["e2"] = ("p", 0.8)  # wrong colour
    del det["d1"]           # missing queen
    det["e4"] = ("N", 0.9)  # extra piece
    wrong = {d["square"]: d for d in diff_against_fen(chess.STARTING_FEN, det)}
    assert set(wrong) == {"e2", "d1", "e4"}
    assert wrong["d1"] == {"square": "d1", "expected": "Q", "detected": None}
    assert wrong["e4"]["expected"] is None
