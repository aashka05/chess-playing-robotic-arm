"""Identify the human's move by matching legal moves against the camera.

We never read the board from scratch. Instead we take the known position,
enumerate every legal move, and score how well each resulting position
agrees with the per-square piece detections. The best-scoring move is
accepted only if it is clearly better than every alternative, including
"no move was made".
"""

from dataclasses import dataclass, field

import chess

# Detections: square name ("e4") -> (FEN symbol "P"/"n"/..., YOLO confidence 0..1).
# Squares with no detection are absent.
Detections = dict[str, tuple[str, float]]

# A same-colour piece of the wrong type still says "occupied by my colour",
# which is most of what distinguishes one legal move from another.
SAME_COLOR_WRONG_TYPE = 0.25
# A score gap (in "squares") at which we are fully confident.
FULL_CONFIDENCE_MARGIN = 0.75
# Below this fraction of the 64 squares agreeing, the board is too disturbed.
MIN_GLOBAL_AGREEMENT = 0.8


def square_score(expected: str | None, detected: tuple[str, float] | None) -> float:
    """How well one detection agrees with one expected square (0..1)."""
    if detected is None:
        return 1.0 if expected is None else 0.0  # empty/empty, or a missed piece
    symbol, confidence = detected
    if expected is None:
        return 1.0 - confidence  # phantom piece; weak detections cost less
    if symbol == expected:
        return 1.0
    if symbol.isupper() == expected.isupper():
        return SAME_COLOR_WRONG_TYPE
    return 0.0


def position_score(board: chess.Board, detections: Detections) -> float:
    total = 0.0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        expected = piece.symbol() if piece else None
        total += square_score(expected, detections.get(chess.square_name(square)))
    return total


def changed_squares(before: chess.Board, after: chess.Board) -> list[str]:
    return [
        chess.square_name(sq)
        for sq in chess.SQUARES
        if before.piece_at(sq) != after.piece_at(sq)
    ]


@dataclass
class Candidate:
    uci: str
    san: str
    score: float


@dataclass
class MatchResult:
    recognized: bool
    move: chess.Move | None
    confidence: float
    reason: str  # "ok" | "no_change" | "low_confidence" | "board_mismatch" | "no_legal_moves"
    global_agreement: float
    candidates: list[Candidate] = field(default_factory=list)
    # Squares where the best candidate disagrees with the camera.
    mismatched_squares: list[str] = field(default_factory=list)


def match_move(
    board: chess.Board,
    detections: Detections,
    min_confidence: float = 0.6,
) -> MatchResult:
    """Pick the legal move whose resulting position best matches `detections`."""
    null_score = position_score(board, detections)

    scored: list[tuple[float, chess.Move, chess.Board]] = []
    for move in board.legal_moves:
        after = board.copy(stack=False)
        after.push(move)
        scored.append((position_score(after, detections), move, after))

    if not scored:
        return MatchResult(False, None, 0.0, "no_legal_moves", null_score / 64)

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_move, best_board = scored[0]
    runner_up = max(scored[1][0] if len(scored) > 1 else 0.0, null_score)

    local = changed_squares(board, best_board)
    local_agreement = sum(
        square_score(_symbol_at(best_board, sq), detections.get(sq)) for sq in local
    ) / len(local)
    margin = best_score - runner_up
    confidence = max(0.0, min(1.0, margin / FULL_CONFIDENCE_MARGIN)) * local_agreement
    global_agreement = best_score / 64

    candidates = [
        Candidate(m.uci(), board.san(m), round(s, 3)) for s, m, _ in scored[:3]
    ]
    mismatched = [
        chess.square_name(sq)
        for sq in chess.SQUARES
        if square_score(_symbol_at(best_board, chess.square_name(sq)),
                        detections.get(chess.square_name(sq))) < 0.5
    ]

    if null_score >= best_score:
        reason = "no_change"
    elif global_agreement < MIN_GLOBAL_AGREEMENT:
        reason = "board_mismatch"
    elif confidence < min_confidence:
        reason = "low_confidence"
    else:
        reason = "ok"

    recognized = reason == "ok"
    return MatchResult(
        recognized=recognized,
        move=best_move if recognized else None,
        confidence=round(confidence, 3),
        reason=reason,
        global_agreement=round(global_agreement, 3),
        candidates=candidates,
        mismatched_squares=mismatched,
    )


def _symbol_at(board: chess.Board, square_name: str) -> str | None:
    piece = board.piece_at(chess.parse_square(square_name))
    return piece.symbol() if piece else None


def diff_against_fen(fen: str, detections: Detections) -> list[dict]:
    """Squares where the camera disagrees with `fen` (used for setup verification)."""
    board = chess.Board(fen)
    wrong = []
    for square in chess.SQUARES:
        name = chess.square_name(square)
        expected = _symbol_at(board, name)
        detected = detections.get(name)
        detected_symbol = detected[0] if detected else None
        if expected != detected_symbol:
            wrong.append({"square": name, "expected": expected, "detected": detected_symbol})
    return wrong
