"""Explain why the move the camera saw is not legal.

We compare the last valid position with what the camera now sees, infer the
single move the player attempted, and use python-chess to say exactly why it
is illegal. If the change doesn't look like one move (e.g. several pieces
changed, which suggests a detection error) we say so and list the squares
instead of guessing.
"""

from dataclasses import dataclass, field

import chess

# Square name -> FEN symbol of what the camera sees there (absent = empty).
Placement = dict[str, str]

_NAMES = {
    chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
    chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king",
}
_HOW_IT_MOVES = {
    chess.KNIGHT: "knights move in an L-shape (two squares one way, one square sideways)",
    chess.BISHOP: "bishops move diagonally",
    chess.ROOK: "rooks move in straight lines along ranks and files",
    chess.QUEEN: "queens move in straight lines or diagonally",
    chess.KING: "kings move one square in any direction",
}


@dataclass
class MoveExplanation:
    # "illegal" | "legal" | "no_change" | "unclear"
    kind: str
    message: str
    # Short machine-readable reason, e.g. "blocked", "leaves_king_in_check".
    reason: str = ""
    from_square: str | None = None
    to_square: str | None = None
    piece: str | None = None
    # Squares that differ from the last valid position.
    changed_squares: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "message": self.message, "reason": self.reason,
            "from_square": self.from_square, "to_square": self.to_square,
            "piece": self.piece, "changed_squares": self.changed_squares,
        }


def _color(color: chess.Color) -> str:
    return "White" if color == chess.WHITE else "Black"


def _piece_name(piece: chess.Piece) -> str:
    return f"{_color(piece.color).lower()} {_NAMES[piece.piece_type]}"


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def explain_attempt(board: chess.Board, seen: Placement) -> MoveExplanation:
    """Infer the attempted move from `board` -> `seen` and explain why it's illegal."""
    before = {chess.square_name(sq): p.symbol() for sq, p in board.piece_map().items()}
    changed = sorted(
        (sq for sq in set(before) | set(seen) if before.get(sq) != seen.get(sq)),
        key=chess.parse_square,
    )
    if not changed:
        return MoveExplanation("no_change", "The board looks unchanged. Make your move, then press the clock.")

    inferred = _infer_move(board, seen, changed)
    if inferred is None:
        return MoveExplanation(
            "unclear",
            f"Couldn't work out which move was played: {len(changed)} squares differ from the last "
            f"valid position ({', '.join(changed)}). This may be a detection error. Check those squares "
            "match the position, or put the pieces back and play the move again.",
            reason="unclear",
            changed_squares=changed,
        )
    move = inferred
    if board.is_legal(move):
        return MoveExplanation(
            "legal", f"{board.san(move)} is legal, but the camera couldn't confirm it clearly.",
            reason="legal", from_square=chess.square_name(move.from_square),
            to_square=chess.square_name(move.to_square),
            piece=_piece_name(board.piece_at(move.from_square)), changed_squares=changed,
        )
    reason, why = _why_illegal(board, move)
    piece = board.piece_at(move.from_square)
    frm, to = chess.square_name(move.from_square), chess.square_name(move.to_square)
    return MoveExplanation(
        "illegal",
        f"Illegal move: {_piece_name(piece)} from {frm} to {to}. {why}",
        reason=reason, from_square=frm, to_square=to, piece=_piece_name(piece), changed_squares=changed,
    )


def _infer_move(board: chess.Board, seen: Placement, changed: list[str]) -> chess.Move | None:
    """The one move that explains the change, or None if it doesn't look like one move."""
    vacated = [sq for sq in changed if sq not in seen and board.piece_at(chess.parse_square(sq))]
    arrived = [sq for sq in changed if sq in seen]

    # Castling: a king and a rook of the same colour both moved.
    if len(changed) == 4 and len(vacated) == 2 and len(arrived) == 2:
        kings = [sq for sq in vacated if board.piece_at(chess.parse_square(sq)).piece_type == chess.KING]
        king_to = [sq for sq in arrived if seen[sq].lower() == "k"]
        if len(kings) == 1 and len(king_to) == 1:
            return chess.Move(chess.parse_square(kings[0]), chess.parse_square(king_to[0]))
        return None

    # En passant: own pawn moved diagonally, the passed pawn disappeared.
    if len(changed) == 3 and len(vacated) == 2 and len(arrived) == 1:
        to = chess.parse_square(arrived[0])
        movers = [sq for sq in vacated if _same_colour(board, sq, seen[arrived[0]])]
        if len(movers) == 1 and board.piece_at(chess.parse_square(movers[0])).piece_type == chess.PAWN:
            return chess.Move(chess.parse_square(movers[0]), to)
        return None

    # Ordinary move or capture: one square emptied, one square now holds that colour's piece.
    if len(changed) == 2 and len(vacated) == 1 and len(arrived) == 1:
        frm, to = chess.parse_square(vacated[0]), chess.parse_square(arrived[0])
        piece = board.piece_at(frm)
        landed = chess.Piece.from_symbol(seen[arrived[0]])
        if landed.color != piece.color:
            return None
        promotion = None
        if piece.piece_type == chess.PAWN and chess.square_rank(to) in (0, 7):
            # A pawn that reached the last rank must turn into what the camera sees there.
            promotion = None if landed.piece_type == chess.PAWN else landed.piece_type
        return chess.Move(frm, to, promotion=promotion)
    return None


def _same_colour(board: chess.Board, square: str, symbol: str) -> bool:
    piece = board.piece_at(chess.parse_square(square))
    return piece is not None and piece.color == chess.Piece.from_symbol(symbol).color


def _why_illegal(board: chess.Board, move: chess.Move) -> tuple[str, str]:
    piece = board.piece_at(move.from_square)
    frm, to = move.from_square, move.to_square
    frm_name, to_name = chess.square_name(frm), chess.square_name(to)
    name = _NAMES[piece.piece_type]
    target = board.piece_at(to)

    if piece.color != board.turn:
        return "wrong_turn", f"It's {_color(board.turn)}'s turn, not {_color(piece.color)}'s."
    if target is not None and target.color == piece.color:
        return "own_piece", f"You can't capture your own piece ({_piece_name(target)} on {to_name})."

    if piece.piece_type == chess.KING and abs(chess.square_file(to) - chess.square_file(frm)) == 2 \
            and chess.square_rank(frm) == chess.square_rank(to):
        return _why_castling_illegal(board, move)

    if piece.piece_type == chess.PAWN:
        found = _why_pawn_illegal(board, move)
        if found:
            return found
    elif not _geometry_ok(piece.piece_type, frm, to):
        return "bad_geometry", f"{_cap(name)} can't move from {frm_name} to {to_name}: {_HOW_IT_MOVES[piece.piece_type]}."

    if piece.piece_type in (chess.BISHOP, chess.ROOK, chess.QUEEN) or piece.piece_type == chess.PAWN:
        blockers = [sq for sq in chess.SquareSet(chess.between(frm, to)) if board.piece_at(sq)]
        if blockers:
            sq = blockers[0]
            return "blocked", (f"The path is blocked by the {_piece_name(board.piece_at(sq))} "
                               f"on {chess.square_name(sq)}.")

    if move.promotion is None and piece.piece_type == chess.PAWN and chess.square_rank(to) in (0, 7):
        return "bad_promotion", "A pawn reaching the last rank must be promoted (to a queen, rook, bishop or knight)."
    if move.promotion in (chess.KING, chess.PAWN):
        return "bad_promotion", f"A pawn can't promote to a {_NAMES[move.promotion]}; choose a queen, rook, bishop or knight."
    if move.promotion is not None and not (piece.piece_type == chess.PAWN and chess.square_rank(to) in (0, 7)):
        return "bad_promotion", "Only a pawn reaching the last rank can be promoted."

    if board.is_pseudo_legal(move):
        return _why_king_unsafe(board, move)
    return "illegal", "That move isn't allowed by the rules of chess."


def _geometry_ok(piece_type: chess.PieceType, frm: chess.Square, to: chess.Square) -> bool:
    df = abs(chess.square_file(to) - chess.square_file(frm))
    dr = abs(chess.square_rank(to) - chess.square_rank(frm))
    return {
        chess.KNIGHT: {df, dr} == {1, 2},
        chess.BISHOP: df == dr and df > 0,
        chess.ROOK: (df == 0) != (dr == 0),
        chess.QUEEN: (df == dr and df > 0) or ((df == 0) != (dr == 0)),
        chess.KING: max(df, dr) == 1,
    }[piece_type]


def _why_pawn_illegal(board: chess.Board, move: chess.Move) -> tuple[str, str] | None:
    piece = board.piece_at(move.from_square)
    frm, to = move.from_square, move.to_square
    frm_name, to_name = chess.square_name(frm), chess.square_name(to)
    forward = 1 if piece.color == chess.WHITE else -1
    df = chess.square_file(to) - chess.square_file(frm)
    dr = (chess.square_rank(to) - chess.square_rank(frm)) * forward
    start_rank = 1 if piece.color == chess.WHITE else 6
    target = board.piece_at(to)

    if dr <= 0:
        how = "backwards" if dr < 0 else "sideways"
        return "pawn_direction", f"Pawns can't move {how} (the pawn moved from {frm_name} to {to_name})."
    if abs(df) == 1 and dr == 1:
        if target is not None:
            return None  # a normal capture; other checks follow
        if board.ep_square is not None and to == board.ep_square:
            return None
        return "bad_en_passant", (
            f"Pawns only move diagonally to capture, and {to_name} is empty. En passant is only allowed "
            "immediately after the opponent's pawn has moved two squares past yours."
        )
    if df != 0:
        return "pawn_direction", f"Pawns can't move from {frm_name} to {to_name}: they move straight ahead and capture one square diagonally."
    if dr == 2:
        if chess.square_rank(frm) != start_rank:
            return "pawn_double", "A pawn can only move two squares on its first move."
        mid = frm + 8 * forward
        if board.piece_at(mid):
            return "blocked", f"The path is blocked by the {_piece_name(board.piece_at(mid))} on {chess.square_name(mid)}."
    elif dr > 2:
        return "pawn_double", "Pawns move one square forward (two on their first move)."
    if target is not None:
        return "pawn_blocked", f"Pawns can't capture straight ahead; {to_name} is occupied by the {_piece_name(target)}."
    return None


def _why_castling_illegal(board: chess.Board, move: chess.Move) -> tuple[str, str]:
    color = board.turn
    kingside = chess.square_file(move.to_square) > chess.square_file(move.from_square)
    side = "kingside" if kingside else "queenside"
    rook_sq = chess.H1 if kingside else chess.A1
    if color == chess.BLACK:
        rook_sq = chess.square_mirror(rook_sq)
    king_home = chess.E1 if color == chess.WHITE else chess.E8

    if move.from_square != king_home:
        return "castling", "You can't castle: your king has already moved."
    if not board.has_castling_rights(color):
        return "castling", "You can't castle any more: your king or rooks have already moved."
    has_right = board.has_kingside_castling_rights(color) if kingside else board.has_queenside_castling_rights(color)
    if not has_right:
        return "castling", f"You can't castle {side}: the rook on {chess.square_name(rook_sq)} has already moved."
    blockers = [sq for sq in chess.SquareSet(chess.between(move.from_square, rook_sq)) if board.piece_at(sq)]
    if blockers:
        sq = blockers[0]
        return "castling", (f"You can't castle {side}: the path is blocked by the "
                            f"{_piece_name(board.piece_at(sq))} on {chess.square_name(sq)}.")
    if board.is_check():
        return "castling", f"You can't castle while in check (from the {_checkers(board, color)})."
    step = 1 if kingside else -1
    passed = move.from_square + step
    if board.is_attacked_by(not color, passed):
        attacker = _first_attacker(board, not color, passed)
        return "castling", (f"You can't castle {side}: the king would pass through {chess.square_name(passed)}, "
                            f"which is attacked by the {attacker}.")
    if board.is_attacked_by(not color, move.to_square):
        attacker = _first_attacker(board, not color, move.to_square)
        return "castling", (f"You can't castle {side}: the king would end in check on "
                            f"{chess.square_name(move.to_square)} from the {attacker}.")
    return "castling", f"You can't castle {side} here."


def _first_attacker(board: chess.Board, color: chess.Color, square: chess.Square) -> str:
    sq = next(iter(board.attackers(color, square)))
    return f"{_piece_name(board.piece_at(sq))} on {chess.square_name(sq)}"


def _checkers(board: chess.Board, color: chess.Color) -> str:
    """The pieces giving check to `color`'s king in `board`."""
    king = board.king(color)
    pieces = [f"{_piece_name(board.piece_at(sq))} on {chess.square_name(sq)}"
              for sq in board.attackers(not color, king)]
    return " and ".join(pieces)


def _why_king_unsafe(board: chess.Board, move: chess.Move) -> tuple[str, str]:
    """The move obeys how the piece moves, but your king would be in check afterwards."""
    color = board.turn
    piece = board.piece_at(move.from_square)
    after = board.copy(stack=False)
    after.push(move)
    checkers = _checkers(after, color)
    if piece.piece_type == chess.KING:
        return "king_into_check", (f"Your king can't move into check: {chess.square_name(move.to_square)} "
                                   f"is attacked by the {checkers}.")
    if board.is_check():
        return "still_in_check", f"Your king is in check from the {checkers}, and this move doesn't stop it."
    return "leaves_king_in_check", (f"Moving the {_NAMES[piece.piece_type]} would leave your king in check "
                                    f"from the {checkers}.")
