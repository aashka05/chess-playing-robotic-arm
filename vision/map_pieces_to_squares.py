import sys
import cv2
import numpy as np
import json
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

VISION_DIR = Path(__file__).resolve().parent

MODEL_PATH = VISION_DIR / "models" / "best.pt"

COORDINATES_PATH = VISION_DIR / "outputs" / "square_coordinates.json"

OUTPUT_PATH = VISION_DIR / "outputs" / "piece_square_debug.jpg"


# ============================================================
# CLASS NAMES
# ============================================================

CLASS_NAMES = [
    "black_bishop",
    "black_king",
    "black_knight",
    "black_pawn",
    "black_queen",
    "black_rook",
    "white_bishop",
    "white_king",
    "white_knight",
    "white_pawn",
    "white_queen",
    "white_rook",
]


# ============================================================
# LOAD MODEL (lazily, once per path)
# ============================================================

_models = {}


def load_model(model_path=MODEL_PATH):
    from ultralytics import YOLO

    model_path = str(model_path)

    if model_path not in _models:
        _models[model_path] = YOLO(model_path)

    return _models[model_path]


# ============================================================
# LOAD SQUARE COORDINATES
# ============================================================

def load_squares(coordinates_path=COORDINATES_PATH):
    with open(coordinates_path, "r") as f:
        return json.load(f)


def index_squares(squares):
    # square_coordinates.json stores squares as a LIST:
    #
    # [
    #     {
    #         "name": "A8",
    #         "row": 0,
    #         "column": 0,
    #         "rectified": {...},
    #         "original_image": {...}
    #     },
    #     ...
    # ]
    #
    # Convert it into a dictionary indexed by square name.

    if isinstance(squares, dict):
        return squares

    return {
        item["name"]: item
        for item in squares
    }


# ============================================================
# FIND SQUARE
# ============================================================

def find_square(x, y, squares):
    """
    Given an (x, y) point in the original image,
    return the corresponding chess square.
    """

    point = (float(x), float(y))

    closest_square = None
    closest_distance = float("inf")

    for square_name, data in squares.items():

        corners = data["original_image"]

        polygon = np.array(
            [
                corners["top_left"],
                corners["top_right"],
                corners["bottom_right"],
                corners["bottom_left"],
            ],
            dtype=np.float32,
        )

        # ----------------------------------------------------
        # Check if point lies inside the square
        # ----------------------------------------------------

        inside = cv2.pointPolygonTest(
            polygon,
            point,
            False
        )

        if inside >= 0:
            return square_name

        # ----------------------------------------------------
        # Fallback:
        # Find closest square center
        # ----------------------------------------------------

        center = np.array(
            corners["center"],
            dtype=np.float32
        )

        distance = np.linalg.norm(
            np.array(point) - center
        )

        if distance < closest_distance:

            closest_distance = distance
            closest_square = square_name

    return closest_square


# ============================================================
# DETECT PIECES
# ============================================================

def detect_pieces(
    image,
    squares=None,
    model=None,
    return_details=False,
    debug_output_path=None,
    verbose=False,
):
    """
    Detect chess pieces in the supplied image
    and map them to chessboard squares.

    Args:
        image: BGR numpy array (cv2.imread / cv2.imdecode).
        squares: square coordinates from rectify_board()
            (list or dict by name). Defaults to COORDINATES_PATH.
        model: a loaded YOLO model. Defaults to MODEL_PATH.
        return_details: also return per-square detections
            (piece, confidence, bbox, center).
        debug_output_path: where to save the annotated image (optional).

    Returns:
        dict:
            {
                "a8": "black_rook",
                "b8": "black_knight",
                ...
            }

        or, with return_details=True, (board, details) where details
        is {"a8": {"piece", "confidence", "square", "center", "bbox"}}.

    This function does NOT generate FEN.
    """

    # --------------------------------------------------------
    # Check image
    # --------------------------------------------------------

    if image is None:

        raise ValueError(
            "No image given to detect_pieces()"
        )

    if squares is None:
        squares = load_squares()

    squares = index_squares(squares)

    if model is None:
        model = load_model()

    # ========================================================
    # YOLO DETECTION
    # ========================================================

    results = model.predict(
        source=image,
        conf=0.25,
        verbose=False
    )

    detections = []

    # ========================================================
    # PROCESS YOLO DETECTIONS
    # ========================================================

    for result in results:

        for box in result.boxes:

            class_id = int(
                box.cls[0]
            )

            confidence = float(
                box.conf[0]
            )

            x1, y1, x2, y2 = (
                box.xyxy[0].tolist()
            )

            # ------------------------------------------------
            # Bounding-box center
            # ------------------------------------------------

            center_x = (
                x1 + x2
            ) / 2

            center_y = (
                y1 + y2
            ) / 2

            # ------------------------------------------------
            # Map center to chess square
            # ------------------------------------------------

            square = find_square(
                center_x,
                center_y,
                squares
            )

            if square is None:
                continue

            # ------------------------------------------------
            # Class name
            # ------------------------------------------------

            if (
                class_id < 0
                or class_id >= len(CLASS_NAMES)
            ):
                continue

            piece_name = CLASS_NAMES[
                class_id
            ]

            detections.append(
                {
                    "piece": piece_name,
                    "confidence": confidence,
                    "square": square,
                    "center": (
                        int(center_x),
                        int(center_y)
                    ),
                    "bbox": (
                        int(x1),
                        int(y1),
                        int(x2),
                        int(y2)
                    ),
                }
            )

    # ========================================================
    # RESOLVE DUPLICATE DETECTIONS
    # ========================================================

    best_detection_per_square = {}

    for detection in detections:

        square = detection["square"]

        if square not in best_detection_per_square:

            best_detection_per_square[
                square
            ] = detection

        else:

            existing = (
                best_detection_per_square[
                    square
                ]
            )

            if (
                detection["confidence"]
                > existing["confidence"]
            ):

                best_detection_per_square[
                    square
                ] = detection

    # ========================================================
    # DRAW DEBUG IMAGE
    # ========================================================

    if debug_output_path is not None:

        debug_image = image.copy()

        for square, detection in (
            best_detection_per_square.items()
        ):

            piece = detection["piece"]
            confidence = detection["confidence"]

            x1, y1, x2, y2 = (
                detection["bbox"]
            )

            center_x, center_y = (
                detection["center"]
            )

            # ----------------------------------------------------
            # Bounding box
            # ----------------------------------------------------

            cv2.rectangle(
                debug_image,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            # ----------------------------------------------------
            # Label
            # ----------------------------------------------------

            label = (
                f"{piece} -> "
                f"{square} "
                f"{confidence:.3f}"
            )

            cv2.putText(
                debug_image,
                label,
                (
                    x1,
                    max(20, y1 - 8)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 0),
                1,
                cv2.LINE_AA
            )

            # ----------------------------------------------------
            # Center point
            # ----------------------------------------------------

            cv2.circle(
                debug_image,
                (center_x, center_y),
                4,
                (0, 0, 255),
                -1
            )

        # ========================================================
        # SAVE DEBUG IMAGE
        # ========================================================

        debug_output_path = Path(debug_output_path)

        debug_output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        cv2.imwrite(
            str(debug_output_path),
            debug_image
        )

    # ========================================================
    # CREATE BOARD STATE
    # ========================================================

    board = {}
    details = {}

    for square, detection in (
        best_detection_per_square.items()
    ):

        board[
            square.lower()
        ] = detection["piece"]

        details[
            square.lower()
        ] = detection

    # ========================================================
    # PRINT BOARD STATE
    # ========================================================

    if verbose:

        print(
            "\nDetected board state:"
        )

        for square in sorted(board.keys()):

            print(
                f"{board[square]:15s} -> "
                f"{square.upper()} "
                f"confidence="
                f"{details[square]['confidence']:.3f}"
            )

        print(
            f"\nTotal detected pieces: "
            f"{len(board)}"
        )

        if debug_output_path is not None:
            print(
                f"Debug image saved to:\n"
                f"{debug_output_path}"
            )

    # ========================================================
    # RETURN BOARD TO MOVE DETECTION
    # ========================================================

    if return_details:
        return board, details

    return board


# ============================================================
# COMMAND LINE ENTRY POINT
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage:")
        print(r'python vision/map_pieces_to_squares.py "path\to\image.jpg"')
        sys.exit(1)

    image_path = Path(sys.argv[1])

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(f"Could not read image:\n{image_path}")

    detect_pieces(image, debug_output_path=OUTPUT_PATH, verbose=True)
