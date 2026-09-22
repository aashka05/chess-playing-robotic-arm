from pathlib import Path

from map_pieces_to_squares import detect_pieces

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from stockfish_engine import StockfishEngine


# ============================================================
# CONFIGURATION
# ============================================================

VISION_DIR = Path(
    r"C:\Users\veera\Desktop\chess-playing-robotic-arm\vision"
)

OUTPUT_DIR = VISION_DIR / "outputs"

FEN_PATH = OUTPUT_DIR / "fen.txt"

# ------------------------------------------------------------
# IMAGE TO PROCESS
#
# Change this path when processing a different board image.
# Later this can be replaced by a camera frame without
# changing the rest of the architecture.
# ------------------------------------------------------------

IMAGE_PATH = Path(
    r"C:\Users\veera\Desktop\chess-playing-robotic-arm\datasets\board_image\test16.jpg"
)

# IMAGE_PATH = Path(
#     r"C:\Users\veera\Downloads\IMG_20260906_092309894.jpg"
# )
IMAGE_PATH = Path(
    r"C:\Users\veera\Downloads\IMG_20260906_092316483.jpg"
)

# ============================================================
# PIECE <-> FEN MAPPING
# ============================================================

PIECE_TO_FEN = {
    "white_pawn": "P",
    "white_knight": "N",
    "white_bishop": "B",
    "white_rook": "R",
    "white_queen": "Q",
    "white_king": "K",

    "black_pawn": "p",
    "black_knight": "n",
    "black_bishop": "b",
    "black_rook": "r",
    "black_queen": "q",
    "black_king": "k",
}


FEN_TO_NAME = {
    "P": "white_pawn",
    "N": "white_knight",
    "B": "white_bishop",
    "R": "white_rook",
    "Q": "white_queen",
    "K": "white_king",

    "p": "black_pawn",
    "n": "black_knight",
    "b": "black_bishop",
    "r": "black_rook",
    "q": "black_queen",
    "k": "black_king",
}


# ============================================================
# PIECE COLOR
# ============================================================

def piece_color(piece):
    """
    Determine color from FEN piece character.
    """

    if piece.isupper():
        return "w"

    return "b"

# ============================================================
# GET PIECE INITIAL FROM FEN CHARACTER
# ============================================================

def get_piece_initial(piece):
    """
    Convert a FEN piece character into the piece initial,
    ignoring color.

    P/p -> P
    N/n -> N
    B/b -> B
    R/r -> R
    Q/q -> Q
    K/k -> K
    """

    piece_initials = {
        "P": "P",
        "N": "N",
        "B": "B",
        "R": "R",
        "Q": "Q",
        "K": "K",

        "p": "P",
        "n": "N",
        "b": "B",
        "r": "R",
        "q": "Q",
        "k": "K",
    }

    return piece_initials.get(piece)

def get_robot_arm_move(robot_move, human_fen):
    """
    Convert Stockfish move into the format required by
    the robotic arm:

        [initial_square, destination_square, piece_initial]

    Example:
        e2e4 -> ["e2", "e4", "P"]
        g8f6 -> ["g8", "f6", "N"]
    """

    robot_move = robot_move.lower()

    source = robot_move[:2]
    destination = robot_move[2:4]

    # Board BEFORE robot move
    human_board = fen_placement_to_board(
        human_fen.split()[0]
    )

    # Piece being moved
    moving_piece = human_board.get(source)

    if moving_piece is None:
        raise ValueError(
            f"No piece found on robot source square {source}"
        )

    piece_initial = get_piece_initial(
        moving_piece
    )

    return [
        source,
        destination,
        piece_initial
    ]

# ============================================================
# BOARD -> FEN PLACEMENT
# ============================================================

def board_to_fen_placement(board):
    """
    Convert a board dictionary containing FEN piece characters
    into the first field of a FEN string.
    """

    ranks = []

    for rank in range(8, 0, -1):

        empty_count = 0
        rank_string = ""

        for file in "abcdefgh":

            square = f"{file}{rank}"

            if square in board:

                if empty_count > 0:
                    rank_string += str(empty_count)
                    empty_count = 0

                rank_string += board[square]

            else:

                empty_count += 1

        if empty_count > 0:
            rank_string += str(empty_count)

        ranks.append(rank_string)

    return "/".join(ranks)


# ============================================================
# DETECTION BOARD -> FEN BOARD
# ============================================================

def convert_detection_to_fen_board(detected_board):
    """
    Convert:

        {
            "e2": "white_pawn"
        }

    into:

        {
            "e2": "P"
        }
    """

    fen_board = {}

    for square, piece_name in detected_board.items():

        if piece_name not in PIECE_TO_FEN:
            continue

        fen_board[square.lower()] = PIECE_TO_FEN[piece_name]

    return fen_board


# ============================================================
# PARSE FEN
# ============================================================

def parse_fen(fen):
    """
    Parse all six FEN fields.
    """

    fields = fen.split()

    if len(fields) != 6:
        raise ValueError(
            f"Invalid FEN. Expected 6 fields:\n{fen}"
        )

    placement = fields[0]
    side_to_move = fields[1]
    castling_rights = fields[2]
    en_passant = fields[3]
    halfmove_clock = int(fields[4])
    fullmove_number = int(fields[5])

    board = fen_placement_to_board(
        placement
    )

    return (
        board,
        side_to_move,
        castling_rights,
        en_passant,
        halfmove_clock,
        fullmove_number,
    )


# ============================================================
# FEN PLACEMENT -> BOARD
# ============================================================

def fen_placement_to_board(placement):
    """
    Convert the first FEN field into:
        square -> FEN piece
    """

    board = {}

    ranks = placement.split("/")

    if len(ranks) != 8:
        raise ValueError(
            "Invalid FEN board placement."
        )

    for rank_index, rank_data in enumerate(ranks):

        rank = 8 - rank_index
        file_index = 0

        for character in rank_data:

            if character.isdigit():

                file_index += int(character)

            elif character in FEN_TO_NAME:

                if file_index >= 8:
                    raise ValueError(
                        "Invalid FEN rank."
                    )

                file_name = "abcdefgh"[file_index]

                square = (
                    f"{file_name}{rank}"
                )

                board[square] = character

                file_index += 1

            else:

                raise ValueError(
                    f"Invalid FEN character: "
                    f"{character}"
                )

        if file_index != 8:
            raise ValueError(
                f"Invalid FEN rank: {rank}"
            )

    return board


# ============================================================
# READ PREVIOUS FEN
# ============================================================

def read_previous_fen():
    """
    Read the previous FEN from fen.txt.
    """

    if not FEN_PATH.exists():
        return None

    fen = FEN_PATH.read_text(
        encoding="utf-8"
    ).strip()

    if not fen:
        return None

    return fen


# ============================================================
# WRITE FEN
# ============================================================

def write_fen(fen):
    """
    Save current FEN.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    FEN_PATH.write_text(
        fen,
        encoding="utf-8"
    )


# ============================================================
# BOARD DIFFERENCES
# ============================================================

def get_board_differences(
    previous_board,
    current_board
):
    """
    Return all squares whose contents changed.
    """

    all_squares = set(
        previous_board.keys()
    ) | set(
        current_board.keys()
    )

    differences = []

    for square in sorted(all_squares):

        old_piece = previous_board.get(
            square
        )

        new_piece = current_board.get(
            square
        )

        if old_piece != new_piece:

            differences.append(
                (
                    square,
                    old_piece,
                    new_piece
                )
            )

    return differences


# ============================================================
# CASTLING DETECTION
# ============================================================

def detect_castling(
    previous_board,
    current_board
):
    """
    Detect king + rook movement corresponding to castling.
    """

    castling_patterns = [

        # White kingside
        (
            "e1",
            "g1",
            "h1",
            "f1",
            "K",
            "R",
            "O-O"
        ),

        # White queenside
        (
            "e1",
            "c1",
            "a1",
            "d1",
            "K",
            "R",
            "O-O-O"
        ),

        # Black kingside
        (
            "e8",
            "g8",
            "h8",
            "f8",
            "k",
            "r",
            "O-O"
        ),

        # Black queenside
        (
            "e8",
            "c8",
            "a8",
            "d8",
            "k",
            "r",
            "O-O-O"
        ),
    ]

    for (
        king_from,
        king_to,
        rook_from,
        rook_to,
        king_piece,
        rook_piece,
        notation
    ) in castling_patterns:

        if (
            previous_board.get(king_from)
            == king_piece
            and previous_board.get(rook_from)
            == rook_piece
            and current_board.get(king_from)
            is None
            and current_board.get(rook_from)
            is None
            and current_board.get(king_to)
            == king_piece
            and current_board.get(rook_to)
            == rook_piece
        ):

            return {
                "type": "castling",
                "source": king_from,
                "destination": king_to,
                "notation": notation,
                "moving_piece": king_piece,
            }

    return None


# ============================================================
# EN PASSANT DETECTION
# ============================================================

def detect_en_passant(
    previous_board,
    current_board,
    previous_en_passant
):
    """
    Detect en-passant capture.
    """

    if previous_en_passant == "-":
        return None

    differences = get_board_differences(
        previous_board,
        current_board
    )

    removed = []
    added = []

    for square, old_piece, new_piece in differences:

        if old_piece is not None and new_piece is None:
            removed.append(
                (square, old_piece)
            )

        elif old_piece is None and new_piece is not None:
            added.append(
                (square, new_piece)
            )

    if len(removed) != 2 or len(added) != 1:
        return None

    destination, new_piece = added[0]

    if destination != previous_en_passant:
        return None

    if new_piece not in ("P", "p"):
        return None

    moving_pawn = new_piece

    source_candidates = []

    for square, piece in removed:

        if piece == moving_pawn:
            source_candidates.append(square)

    if len(source_candidates) != 1:
        return None

    source = source_candidates[0]

    captured_candidates = []

    for square, piece in removed:

        if square != source:
            captured_candidates.append(
                (square, piece)
            )

    if len(captured_candidates) != 1:
        return None

    captured_square, captured_piece = (
        captured_candidates[0]
    )

    if moving_pawn == "P":

        if captured_piece != "p":
            return None

    else:

        if captured_piece != "P":
            return None

    return {
        "type": "en_passant",
        "source": source,
        "destination": destination,
        "captured_square": captured_square,
        "moving_piece": moving_pawn,
        "captured_piece": captured_piece,
    }


# ============================================================
# PROMOTION DETECTION
# ============================================================

def detect_promotion(
    previous_board,
    current_board,
    side_to_move
):
    """
    Detect pawn promotion.
    """

    differences = get_board_differences(
        previous_board,
        current_board
    )

    removed_pawns = []
    promoted_pieces = []

    pawn = (
        "P"
        if side_to_move == "w"
        else "p"
    )

    promoted_set = (
        {"Q", "R", "B", "N"}
        if side_to_move == "w"
        else {"q", "r", "b", "n"}
    )

    for square, old_piece, new_piece in differences:

        if old_piece == pawn:
            removed_pawns.append(square)

        if new_piece in promoted_set:
            promoted_pieces.append(
                (square, new_piece)
            )

    if len(removed_pawns) != 1:
        return None

    if len(promoted_pieces) != 1:
        return None

    source = removed_pawns[0]
    destination, promoted_piece = (
        promoted_pieces[0]
    )

    destination_rank = int(destination[1])

    if side_to_move == "w":

        if destination_rank != 8:
            return None

    else:

        if destination_rank != 1:
            return None

    source_file = ord(source[0]) - ord("a")
    destination_file = (
        ord(destination[0]) - ord("a")
    )

    file_difference = abs(
        destination_file - source_file
    )

    if file_difference > 1:
        return None

    captured_piece = previous_board.get(
        destination
    )

    return {
        "type": "promotion",
        "source": source,
        "destination": destination,
        "moving_piece": pawn,
        "promoted_piece": promoted_piece,
        "captured_piece": captured_piece,
    }


# ============================================================
# NORMAL MOVE DETECTION
# ============================================================

def detect_normal_move(
    previous_board,
    current_board,
    side_to_move
):
    """
    Detect ordinary move or capture.
    """

    differences = get_board_differences(
        previous_board,
        current_board
    )

    removed = []
    added = []

    for square, old_piece, new_piece in differences:

        if old_piece is not None and new_piece is None:

            if piece_color(old_piece) == side_to_move:

                removed.append(
                    (square, old_piece)
                )

        elif new_piece is not None:

            if piece_color(new_piece) == side_to_move:

                added.append(
                    (square, new_piece)
                )

    if len(removed) != 1 or len(added) != 1:
        return None

    source, moving_piece = removed[0]
    destination, new_piece = added[0]

    if moving_piece != new_piece:
        return None

    captured_piece = previous_board.get(
        destination
    )

    if captured_piece is not None:

        if piece_color(captured_piece) == side_to_move:
            return None

        move_type = "capture"

    else:

        move_type = "normal"

    return {
        "type": move_type,
        "source": source,
        "destination": destination,
        "moving_piece": moving_piece,
        "captured_piece": captured_piece,
    }


# ============================================================
# DETECT MOVE
# ============================================================

def detect_move(
    previous_board,
    current_board,
    side_to_move,
    previous_en_passant
):
    """
    Detect the move between two board states.
    """

    # --------------------------------------------------------
    # Castling
    # --------------------------------------------------------

    move = detect_castling(
        previous_board,
        current_board
    )

    if move is not None:
        return move

    # --------------------------------------------------------
    # Promotion
    # --------------------------------------------------------

    move = detect_promotion(
        previous_board,
        current_board,
        side_to_move
    )

    if move is not None:
        return move

    # --------------------------------------------------------
    # En passant
    # --------------------------------------------------------

    move = detect_en_passant(
        previous_board,
        current_board,
        previous_en_passant
    )

    if move is not None:
        return move

    # --------------------------------------------------------
    # Normal move / capture
    # --------------------------------------------------------

    move = detect_normal_move(
        previous_board,
        current_board,
        side_to_move
    )

    if move is not None:
        return move

    return {
        "type": "ambiguous"
    }


# ============================================================
# UPDATE CASTLING RIGHTS
# ============================================================

def update_castling_rights(
    old_rights,
    previous_board,
    source,
    destination,
    moving_piece
):
    """
    Update castling rights after a move.
    """

    if old_rights == "-":
        rights = set()
    else:
        rights = set(old_rights)

    # --------------------------------------------------------
    # White king
    # --------------------------------------------------------

    if moving_piece == "K":

        rights.discard("K")
        rights.discard("Q")

    # --------------------------------------------------------
    # Black king
    # --------------------------------------------------------

    elif moving_piece == "k":

        rights.discard("k")
        rights.discard("q")

    # --------------------------------------------------------
    # White rooks
    # --------------------------------------------------------

    elif moving_piece == "R":

        if source == "h1":
            rights.discard("K")

        elif source == "a1":
            rights.discard("Q")

    # --------------------------------------------------------
    # Black rooks
    # --------------------------------------------------------

    elif moving_piece == "r":

        if source == "h8":
            rights.discard("k")

        elif source == "a8":
            rights.discard("q")

    # --------------------------------------------------------
    # Rook captured on original square
    # --------------------------------------------------------

    if destination == "h1":
        rights.discard("K")

    elif destination == "a1":
        rights.discard("Q")

    elif destination == "h8":
        rights.discard("k")

    elif destination == "a8":
        rights.discard("q")

    if not rights:
        return "-"

    order = "KQkq"

    return "".join(
        character
        for character in order
        if character in rights
    )


# ============================================================
# CALCULATE EN-PASSANT TARGET
# ============================================================

def calculate_en_passant(move):
    """
    Calculate the en-passant target square created
    by a two-square pawn move.
    """

    if move["moving_piece"] not in ("P", "p"):
        return "-"

    source = move["source"]
    destination = move["destination"]

    source_rank = int(source[1])
    destination_rank = int(destination[1])

    if abs(destination_rank - source_rank) != 2:
        return "-"

    middle_rank = (
        source_rank + destination_rank
    ) // 2

    return (
        f"{source[0]}"
        f"{middle_rank}"
    )


# ============================================================
# CREATE FEN
# ============================================================

def create_fen(
    placement,
    side_to_move,
    castling_rights,
    en_passant,
    halfmove_clock,
    fullmove_number
):
    """
    Create complete six-field FEN.
    """

    return (
        f"{placement} "
        f"{side_to_move} "
        f"{castling_rights} "
        f"{en_passant} "
        f"{halfmove_clock} "
        f"{fullmove_number}"
    )


# ============================================================
# UPDATE GAME STATE
# ============================================================

def update_game_state(
    previous_fen,
    current_board,
    move
):
    """
    Update every FEN field after a detected move.
    """

    (
        previous_board,
        side_to_move,
        old_castling_rights,
        previous_en_passant,
        previous_halfmove_clock,
        previous_fullmove_number,
    ) = parse_fen(previous_fen)

    # --------------------------------------------------------
    # New side to move
    # --------------------------------------------------------

    new_side_to_move = (
        "b"
        if side_to_move == "w"
        else "w"
    )

    # --------------------------------------------------------
    # Castling rights
    # --------------------------------------------------------

    new_castling_rights = update_castling_rights(
        old_castling_rights,
        previous_board,
        move["source"],
        move["destination"],
        move["moving_piece"]
    )

    # --------------------------------------------------------
    # En-passant
    # --------------------------------------------------------

    new_en_passant = calculate_en_passant(
        move
    )

    # --------------------------------------------------------
    # Halfmove clock
    # --------------------------------------------------------

    if (
        move["moving_piece"] in ("P", "p")
        or move["type"] in (
            "capture",
            "en_passant",
            "promotion",
        )
    ):

        new_halfmove_clock = 0

    else:

        new_halfmove_clock = (
            previous_halfmove_clock + 1
        )

    # --------------------------------------------------------
    # Fullmove number
    # --------------------------------------------------------

    if side_to_move == "b":

        new_fullmove_number = (
            previous_fullmove_number + 1
        )

    else:

        new_fullmove_number = (
            previous_fullmove_number
        )

    # --------------------------------------------------------
    # New placement
    # --------------------------------------------------------

    new_placement = board_to_fen_placement(
        current_board
    )

    # --------------------------------------------------------
    # Create FEN
    # --------------------------------------------------------

    return create_fen(
        new_placement,
        new_side_to_move,
        new_castling_rights,
        new_en_passant,
        new_halfmove_clock,
        new_fullmove_number
    )


# ============================================================
# PRINT MOVE
# ============================================================

def print_move(move):
    """
    Print detected move information.
    """

    move_type = move["type"]

    if move_type == "castling":

        print(
            f"\nCastling detected: "
            f"{move['notation']}"
        )

    elif move_type == "en_passant":

        print(
            f"\nEn passant detected: "
            f"{move['source'].upper()} -> "
            f"{move['destination'].upper()}"
        )

    elif move_type == "promotion":

        print(
            f"\nPromotion detected: "
            f"{move['source'].upper()} -> "
            f"{move['destination'].upper()} "
            f"to {move['promoted_piece']}"
        )

        if move["captured_piece"] is not None:
            print("Capture during promotion")

    elif move_type == "capture":

        print(
            f"\nCapture detected: "
            f"{move['source'].upper()} -> "
            f"{move['destination'].upper()}"
        )

    elif move_type == "normal":

        print(
            f"\nMove detected: "
            f"{move['source'].upper()} -> "
            f"{move['destination'].upper()}"
        )

    else:

        print(
            "\nCould not determine a unique move."
        )

# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("CHESS MOVE DETECTION")
    print("=" * 60)

    print(
        f"\nImage:\n{IMAGE_PATH}"
    )

    # ========================================================
    # STEP 1
    # GET BOARD STATE FROM MAP FILE
    # ========================================================

    print(
        "\n[1/5] Detecting pieces and mapping "
        "them to squares..."
    )

    detected_board = detect_pieces(
        IMAGE_PATH
    )

    # ========================================================
    # STEP 2
    # CONVERT BOARD TO FEN REPRESENTATION
    # ========================================================

    current_board = convert_detection_to_fen_board(
        detected_board
    )

    current_placement = board_to_fen_placement(
        current_board
    )

    # ========================================================
    # STEP 3
    # READ PREVIOUS FEN
    # ========================================================

    previous_fen = read_previous_fen()

    # --------------------------------------------------------
    # FIRST IMAGE
    # --------------------------------------------------------

    if previous_fen is None:

        print(
            "\nNo previous FEN found."
        )

        print(
            "Saving this board as the initial "
            "game position."
        )

        initial_fen = create_fen(
            current_placement,
            "w",
            "KQkq",
            "-",
            0,
            1
        )

        write_fen(initial_fen)

        print(
            f"\nInitial FEN:\n{initial_fen}"
        )

        return

    # ========================================================
    # PARSE PREVIOUS FEN
    # ========================================================

    (
        previous_board,
        side_to_move,
        castling_rights,
        previous_en_passant,
        halfmove_clock,
        fullmove_number,
    ) = parse_fen(previous_fen)

    # ========================================================
    # STEP 4
    # DETECT HUMAN MOVE
    # ========================================================

    print(
        "\n[2/5] Detecting human move..."
    )

    move = detect_move(
        previous_board,
        current_board,
        side_to_move,
        previous_en_passant
    )

    print_move(move)

    # --------------------------------------------------------
    # Ambiguous / invalid detection
    # --------------------------------------------------------

    if move["type"] == "ambiguous":

        print(
            "\nFEN was NOT updated because "
            "the move could not be uniquely determined."
        )

        print(
            f"\nPrevious FEN:\n{previous_fen}"
        )

        print(
            f"\nCurrent board placement:\n"
            f"{current_placement}"
        )

        return

    # ========================================================
    # UPDATE FEN AFTER HUMAN MOVE
    # ========================================================

    print(
        "\n[3/5] Updating FEN after human move..."
    )

    human_fen = update_game_state(
        previous_fen,
        current_board,
        move
    )

    write_fen(human_fen)

    print(
        f"\nFEN after human move:\n{human_fen}"
    )

    # ========================================================
    # CALL STOCKFISH
    # ========================================================

    print(
        "\n[4/5] Asking Stockfish for best move..."
    )

    stockfish = StockfishEngine()

    try:

        robot_move, robot_fen = (
            stockfish.get_best_move_and_fen(
                human_fen
            )
        )
        

    except Exception as error:

        print(
            "\nStockfish error:"
        )

        print(error)

        return

    finally:

        stockfish.close()

    # ========================================================
    # STOCKFISH MOVE
    # ========================================================

    print(
        f"\nStockfish best move: "
        f"{robot_move.upper()}"
    )

    print(
        f"\nFEN after robot move:\n"
        f"{robot_fen}"
    )

    # ========================================================
    # SAVE FEN AFTER ROBOT MOVE
    # ========================================================

    print(
        "\n[5/5] Saving FEN after robot move..."
    )

    write_fen(robot_fen)

    print(
        f"\nFinal FEN saved to:\n{FEN_PATH}"
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "MOVE PROCESS COMPLETE"
    )

    print(
        "=" * 60
    )

    print(
        f"\nHuman move : "
        f"{move['source'].upper()} -> "
        f"{move['destination'].upper()}"
    )

    print(
    f"Robot move : "
    f"{robot_move[:2].upper()} -> "
    f"{robot_move[2:4].upper()}"
)

    # ========================================================
    # DETERMINE ROBOT ARM MOVE
    # ========================================================

    robot_arm_move = get_robot_arm_move(
        robot_move,
        human_fen
    )

    print(
        f"\nRobot arm move: {robot_arm_move}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()