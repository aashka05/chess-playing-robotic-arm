import cv2
import numpy as np
import json
from pathlib import Path
from ultralytics import YOLO


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    PROJECT_DIR
    / "runs"
    / "detect"
    / "merged-from-scratch2"
    / "weights"
    / "best.pt"
)

COORDINATES_PATH = (
    PROJECT_DIR
    / "vision"
    / "outputs"
    / "square_coordinates.json"
)

OUTPUT_PATH = (
    PROJECT_DIR
    / "vision"
    / "outputs"
    / "piece_square_debug.jpg"
)


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
# LOAD MODEL
# ============================================================

model = YOLO(str(MODEL_PATH))


# ============================================================
# LOAD SQUARE COORDINATES
# ============================================================

with open(COORDINATES_PATH, "r") as f:
    squares = json.load(f)


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

squares = {
    item["name"]: item
    for item in squares
}


# ============================================================
# FIND SQUARE
# ============================================================

def find_square(x, y):
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

def detect_pieces(image_path):
    """
    Detect chess pieces in the supplied image
    and map them to chessboard squares.

    Returns:
        dict:
            {
                "a8": "black_rook",
                "b8": "black_knight",
                ...
            }

    This function does NOT generate FEN.
    """

    image_path = Path(image_path)

    # --------------------------------------------------------
    # Check image
    # --------------------------------------------------------

    if not image_path.exists():

        raise FileNotFoundError(
            f"Image not found:\n{image_path}"
        )

    image = cv2.imread(
        str(image_path)
    )

    if image is None:

        raise ValueError(
            f"Could not read image:\n{image_path}"
        )

    # ========================================================
    # YOLO DETECTION
    # ========================================================

    results = model.predict(
        source=str(image_path),
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
                center_y
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

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    cv2.imwrite(
        str(OUTPUT_PATH),
        debug_image
    )

    # ========================================================
    # CREATE BOARD STATE
    # ========================================================

    board = {}

    for square, detection in (
        best_detection_per_square.items()
    ):

        board[
            square.lower()
        ] = detection["piece"]

    # ========================================================
    # PRINT BOARD STATE
    # ========================================================

    print(
        "\nDetected board state:"
    )

    for square in sorted(board.keys()):

        detection = (
            best_detection_per_square[
                square.upper()
            ]
            if square.upper()
            in best_detection_per_square
            else best_detection_per_square[
                square
            ]
        )

        print(
            f"{board[square]:15s} -> "
            f"{square.upper()} "
            f"confidence="
            f"{detection['confidence']:.3f}"
        )

    print(
        f"\nTotal detected pieces: "
        f"{len(board)}"
    )

    print(
        f"Debug image saved to:\n"
        f"{OUTPUT_PATH}"
    )

    # ========================================================
    # RETURN BOARD TO MOVE DETECTION
    # ========================================================

    return board