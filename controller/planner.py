"""Turn a chess move into the arm's pick/place operations.

Captured pieces go to the off-board "graveyard" first, then the moving
piece is carried. Promotions: the arm removes the pawn and the user places
the promoted piece by hand (the app shows a prompt).
"""

from dataclasses import dataclass, field

import chess

GRAVEYARD = "graveyard"


@dataclass(frozen=True)
class ArmOp:
    action: str  # "pick" | "place"
    square: str  # "e2" or GRAVEYARD
    piece: str  # lowercase piece letter for the gripper: p n b r q k


@dataclass(frozen=True)
class ManualAction:
    kind: str  # "place_promoted_piece"
    square: str
    piece: str  # FEN symbol, e.g. "Q" or "q"
    message: str


@dataclass
class ArmPlan:
    ops: list[ArmOp] = field(default_factory=list)
    manual: ManualAction | None = None

    def carry(self, src: str, dst: str, piece: str) -> None:
        self.ops.append(ArmOp("pick", src, piece))
        self.ops.append(ArmOp("place", dst, piece))


_NAMES = {"q": "queen", "r": "rook", "b": "bishop", "n": "knight"}


def plan_move(board: chess.Board, move: chess.Move) -> ArmPlan:
    """`board` is the position BEFORE `move`."""
    plan = ArmPlan()
    src = chess.square_name(move.from_square)
    dst = chess.square_name(move.to_square)
    mover = board.piece_at(move.from_square)
    if mover is None:
        raise ValueError(f"No piece on {src}")
    mover_letter = mover.symbol().lower()

    if board.is_castling(move):
        rank = chess.square_rank(move.from_square)
        kingside = chess.square_file(move.to_square) > chess.square_file(move.from_square)
        rook_src = chess.square(7 if kingside else 0, rank)
        rook_dst = chess.square(5 if kingside else 3, rank)
        plan.carry(src, dst, "k")
        plan.carry(chess.square_name(rook_src), chess.square_name(rook_dst), "r")
        return plan

    # Remove the captured piece first.
    if board.is_en_passant(move):
        captured_sq = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        plan.carry(chess.square_name(captured_sq), GRAVEYARD, "p")
    elif board.is_capture(move):
        captured = board.piece_at(move.to_square)
        plan.carry(dst, GRAVEYARD, captured.symbol().lower())

    if move.promotion:
        plan.carry(src, GRAVEYARD, "p")
        symbol = chess.piece_symbol(move.promotion)
        symbol = symbol.upper() if mover.color == chess.WHITE else symbol
        color = "white" if mover.color == chess.WHITE else "black"
        plan.manual = ManualAction(
            kind="place_promoted_piece",
            square=dst,
            piece=symbol,
            message=f"Promotion: please place a {color} {_NAMES[symbol.lower()]} on {dst}, then press OK.",
        )
        return plan

    plan.carry(src, dst, mover_letter)
    return plan
