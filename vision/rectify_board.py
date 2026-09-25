import cv2
import numpy as np
from pathlib import Path
import json


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

IMAGE_PATH = PROJECT_DIR / "datasets" / "3merged" / "train" / "images" / "my5_IMG_20260906_092944352_jpg.rf.aa13d20816f7402aba96798096fc71aa.jpg"

IMAGE_PATH = "C:/Users/veera/Downloads/IMG_20260906_092126069.jpg"

OUTPUT_DIR = PROJECT_DIR / "vision" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_OUTPUT_PATH = OUTPUT_DIR / "64_squares_debug.jpg"
RECTIFIED_OUTPUT_PATH = OUTPUT_DIR / "rectified_board.jpg"
COORDINATES_OUTPUT_PATH = OUTPUT_DIR / "square_coordinates.json"


# ============================================================
# ARUCO CONFIGURATION
# ============================================================

ARUCO_DICT = cv2.aruco.DICT_4X4_50

# Your four corner marker IDs
A1_ID = 0
H1_ID = 1
H8_ID = 2
A8_ID = 3


# ============================================================
# RECTIFICATION CONFIGURATION
# ============================================================

RECTIFIED_SIZE = 1000


# ============================================================
# LOAD IMAGE
# ============================================================

image = cv2.imread(str(IMAGE_PATH))

if image is None:
    raise FileNotFoundError(
        f"Could not load image:\n{IMAGE_PATH}"
    )

print()
print("=" * 70)
print("CHESSBOARD 64-SQUARE COORDINATE GENERATION")
print("=" * 70)


# ============================================================
# ARUCO DETECTION
# ============================================================

aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)

try:
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(
        aruco_dict,
        parameters
    )

    corners, ids, rejected = detector.detectMarkers(image)

except AttributeError:
    parameters = cv2.aruco.DetectorParameters_create()

    corners, ids, rejected = cv2.aruco.detectMarkers(
        image,
        aruco_dict,
        parameters=parameters
    )


if ids is None:
    raise RuntimeError(
        "No ArUco markers detected."
    )

ids = ids.flatten()

print("Detected ArUco IDs:", ids.tolist())


# ============================================================
# GET CENTER OF EACH MARKER
# ============================================================

def marker_center(marker_corners):
    """
    marker_corners:
        4x2 array containing marker corner coordinates.
    """

    return np.mean(marker_corners, axis=0)


marker_points = {}

for marker_corner, marker_id in zip(corners, ids):

    marker_corner = marker_corner.reshape(4, 2)

    center = marker_center(marker_corner)

    marker_points[int(marker_id)] = center


# ============================================================
# CHECK REQUIRED MARKERS
# ============================================================

required_ids = [
    A1_ID,
    A8_ID,
    H8_ID,
    H1_ID
]

for marker_id in required_ids:

    if marker_id not in marker_points:

        raise RuntimeError(
            f"Required ArUco marker {marker_id} "
            f"was not detected."
        )


# ============================================================
# BOARD CORNERS
# ============================================================
#
# IMPORTANT:
#
# We keep this exact ordering:
#
#     A8 ---------------- H8
#      |                    |
#      |                    |
#     A1 ---------------- H1
#
# In the original image the order is:
#
# A1 -> A8 -> H8 -> H1
#
# which corresponds to:
#
# bottom-left
# top-left
# top-right
# bottom-right
#
# ============================================================

src = np.array(
    [
        marker_points[A1_ID],
        marker_points[A8_ID],
        marker_points[H8_ID],
        marker_points[H1_ID]
    ],
    dtype=np.float32
)


# ============================================================
# RECTIFICATION
# ============================================================

dst = np.array(
    [
        [0, RECTIFIED_SIZE],
        [0, 0],
        [RECTIFIED_SIZE, 0],
        [RECTIFIED_SIZE, RECTIFIED_SIZE]
    ],
    dtype=np.float32
)


H = cv2.getPerspectiveTransform(
    src,
    dst
)


rectified = cv2.warpPerspective(
    image,
    H,
    (RECTIFIED_SIZE, RECTIFIED_SIZE)
)


cv2.imwrite(
    str(RECTIFIED_OUTPUT_PATH),
    rectified
)


print()
print("Rectified board saved:")
print(RECTIFIED_OUTPUT_PATH)


# ============================================================
# GENERATE EXACTLY 64 SQUARES
# ============================================================
#
# NO CONTOURS
# NO COLOR DETECTION
# NO THRESHOLDING
#
# We know that the rectified board is:
#
#       8 x 8
#
# Therefore each square is one eighth of the
# corresponding board dimension.
#
# ============================================================

square_size = RECTIFIED_SIZE / 8.0


files = ["A", "B", "C", "D", "E", "F", "G", "H"]
ranks = ["8", "7", "6", "5", "4", "3", "2", "1"]


squares = []


# ============================================================
# BUILD 8 x 8 GRID
# ============================================================

for row in range(8):

    for col in range(8):

        # Rectified coordinates
        x1 = col * square_size
        y1 = row * square_size

        x2 = (col + 1) * square_size
        y2 = (row + 1) * square_size

        # Chess name
        square_name = files[col] + ranks[row]

        # Four corners
        points_rectified = np.array(
            [
                [x1, y1],
                [x2, y1],
                [x2, y2],
                [x1, y2]
            ],
            dtype=np.float32
        )

        # Center
        center_rectified = np.array(
            [
                (x1 + x2) / 2.0,
                (y1 + y2) / 2.0
            ],
            dtype=np.float32
        )

        # ----------------------------------------------------
        # Convert square corners back to ORIGINAL IMAGE
        # ----------------------------------------------------

        inverse_H = np.linalg.inv(H)

        points_original = cv2.perspectiveTransform(
            points_rectified.reshape(1, 4, 2),
            inverse_H
        ).reshape(4, 2)

        center_original = cv2.perspectiveTransform(
            center_rectified.reshape(1, 1, 2),
            inverse_H
        ).reshape(2)

        square = {
            "name": square_name,
            "row": row,
            "column": col,

            "rectified": {
                "top_left": [
                    float(x1),
                    float(y1)
                ],

                "top_right": [
                    float(x2),
                    float(y1)
                ],

                "bottom_right": [
                    float(x2),
                    float(y2)
                ],

                "bottom_left": [
                    float(x1),
                    float(y2)
                ],

                "center": [
                    float(center_rectified[0]),
                    float(center_rectified[1])
                ]
            },

            "original_image": {
                "top_left": [
                    float(points_original[0][0]),
                    float(points_original[0][1])
                ],

                "top_right": [
                    float(points_original[1][0]),
                    float(points_original[1][1])
                ],

                "bottom_right": [
                    float(points_original[2][0]),
                    float(points_original[2][1])
                ],

                "bottom_left": [
                    float(points_original[3][0]),
                    float(points_original[3][1])
                ],

                "center": [
                    float(center_original[0]),
                    float(center_original[1])
                ]
            }
        }

        squares.append(square)


# ============================================================
# VERIFY EXACTLY 64
# ============================================================

if len(squares) != 64:

    raise RuntimeError(
        f"Expected 64 squares, got {len(squares)}"
    )


print()
print("TOTAL SQUARES:", len(squares))
print()


# ============================================================
# PRINT SQUARE TABLE
# ============================================================

print("=" * 70)
print("CHESSBOARD")
print("=" * 70)

for row in range(8):

    row_names = []

    for col in range(8):

        index = row * 8 + col

        row_names.append(
            squares[index]["name"]
        )

    print(
        " | ".join(row_names)
    )


# ============================================================
# SAVE COORDINATES
# ============================================================

with open(
    COORDINATES_OUTPUT_PATH,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        squares,
        f,
        indent=4
    )


print()
print("Coordinates saved:")
print(COORDINATES_OUTPUT_PATH)


# ============================================================
# DRAW DEBUG IMAGE
# ============================================================

debug = image.copy()


inverse_H = np.linalg.inv(H)


for square in squares:

    points_rectified = np.array(
        [
            square["rectified"]["top_left"],
            square["rectified"]["top_right"],
            square["rectified"]["bottom_right"],
            square["rectified"]["bottom_left"]
        ],
        dtype=np.float32
    )

    # Convert to original image
    points_original = cv2.perspectiveTransform(
        points_rectified.reshape(1, 4, 2),
        inverse_H
    ).reshape(4, 2)

    points_original = (
        np.round(points_original)
        .astype(np.int32)
    )

    # Draw square boundary
    cv2.polylines(
        debug,
        [points_original],
        True,
        (0, 255, 0),
        2
    )

    # Center
    center = np.array(
        square["original_image"]["center"]
    )

    center = (
        np.round(center)
        .astype(np.int32)
    )

    # Draw center
    cv2.circle(
        debug,
        tuple(center),
        5,
        (0, 0, 255),
        -1
    )

    # Draw chess square name
    text_position = (
        int(center[0] - 15),
        int(center[1] + 5)
    )

    cv2.putText(
        debug,
        square["name"],
        text_position,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 0, 0),
        2,
        cv2.LINE_AA
    )


# ============================================================
# SAVE DEBUG IMAGE
# ============================================================

cv2.imwrite(
    str(DEBUG_OUTPUT_PATH),
    debug
)


print()
print("Debug image saved:")
print(DEBUG_OUTPUT_PATH)

print()
print("=" * 70)
print("DONE")
print("=" * 70)