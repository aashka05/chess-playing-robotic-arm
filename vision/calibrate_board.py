# 1. Read the empty-board image.
# 2. Detect ArUco markers.
# 3. Determine the board corners.
# 4. Perspective-transform the board.
# 5. Detect the 64 squares from the rectified image.
# 6. Save the calibration data.
# 7. Save a visualization so we can verify everything.

import cv2
import numpy as np
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Empty board image
IMAGE_PATH = (
    PROJECT_ROOT
    / "datasets"
    / "board_image"
    / "test15.jpg"
)

# Calibration output
CALIBRATION_DIR = (
    PROJECT_ROOT
    / "vision"
    / "calibration"
)

CALIBRATION_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CALIBRATION_FILE = (
    CALIBRATION_DIR
    / "board_calibration.npz"
)

# Visual verification output
OUTPUT_IMAGE = (
    CALIBRATION_DIR
    / "calibrated_board.jpg"
)


# ============================================================
# SETTINGS
# ============================================================

BOARD_SIZE = 800


# ============================================================
# EXPECTED MARKER IDs
# ============================================================

# Your existing marker arrangement:
#
#       ID 1 (A8) ---------------- ID 2 (H8)
#          |                         |
#          |                         |
#          |       CHESS BOARD       |
#          |                         |
#       ID 0 (A1) ---------------- ID 3 (H1)

EXPECTED_IDS = {
    0: "A1",
    1: "A8",
    2: "H8",
    3: "H1"
}


# ============================================================
# LOAD IMAGE
# ============================================================

image = cv2.imread(
    str(IMAGE_PATH)
)

if image is None:
    raise RuntimeError(
        f"Could not read image:\n{IMAGE_PATH}"
    )

print("=" * 70)
print("CHESS BOARD CALIBRATION")
print("=" * 70)

print(f"Image: {IMAGE_PATH}")

height, width = image.shape[:2]

print(
    f"Image size: {width} x {height}"
)


# ============================================================
# ARUCO DICTIONARY
# ============================================================

aruco = cv2.aruco

dictionary = aruco.getPredefinedDictionary(
    aruco.DICT_4X4_50
)


# ============================================================
# DETECTOR PARAMETERS
# ============================================================

parameters = aruco.DetectorParameters()

parameters.adaptiveThreshWinSizeMin = 3
parameters.adaptiveThreshWinSizeMax = 23
parameters.adaptiveThreshWinSizeStep = 4

parameters.minMarkerPerimeterRate = 0.01
parameters.maxMarkerPerimeterRate = 4.0

parameters.cornerRefinementMethod = (
    aruco.CORNER_REFINE_SUBPIX
)


# ============================================================
# CREATE DETECTOR
# ============================================================

detector = aruco.ArucoDetector(
    dictionary,
    parameters
)


# ============================================================
# DETECT MARKERS
# ============================================================

print("\n[1] Detecting ArUco markers...")

corners, ids, rejected = (
    detector.detectMarkers(image)
)


if ids is None:

    raise RuntimeError(
        "No ArUco markers detected."
    )


ids = ids.flatten()

print(
    f"Detected IDs: {list(ids)}"
)

print(
    f"Rejected candidates: {len(rejected)}"
)


# ============================================================
# STORE MARKERS
# ============================================================

detected_markers = {}


for marker_corners, marker_id in zip(
    corners,
    ids
):

    marker_id = int(marker_id)

    points = marker_corners[0]

    center = np.mean(
        points,
        axis=0
    )

    detected_markers[marker_id] = {
        "corners": points,
        "center": center
    }


# ============================================================
# CHECK REQUIRED MARKERS
# ============================================================

missing = [
    marker_id
    for marker_id in EXPECTED_IDS
    if marker_id not in detected_markers
]


if missing:

    raise RuntimeError(
        f"Missing markers: {missing}\n"
        f"Detected: {list(detected_markers.keys())}"
    )


print(
    "\nAll four required markers detected."
)


# ============================================================
# PRINT MARKER INFORMATION
# ============================================================

print("\nMarker positions:")
print("-" * 70)

for marker_id in sorted(
    detected_markers
):

    center = detected_markers[
        marker_id
    ]["center"]

    name = EXPECTED_IDS[
        marker_id
    ]

    print(
        f"ID {marker_id} = {name:2s}   "
        f"center = "
        f"({center[0]:.2f}, "
        f"{center[1]:.2f})"
    )


# ============================================================
# GET BOARD CORNER POINTS
# ============================================================

A1 = detected_markers[0]["center"]
A8 = detected_markers[1]["center"]
H8 = detected_markers[2]["center"]
H1 = detected_markers[3]["center"]


# IMPORTANT:
#
# Perspective transform order:
#
# top-left     = A8
# top-right    = H8
# bottom-right = H1
# bottom-left  = A1

src = np.array(
    [
        A8,
        H8,
        H1,
        A1
    ],
    dtype=np.float32
)


# ============================================================
# DESTINATION BOARD
# ============================================================

dst = np.array(
    [
        [0, 0],
        [BOARD_SIZE - 1, 0],
        [BOARD_SIZE - 1, BOARD_SIZE - 1],
        [0, BOARD_SIZE - 1]
    ],
    dtype=np.float32
)


# ============================================================
# CALCULATE HOMOGRAPHY
# ============================================================

print(
    "\n[2] Calculating perspective transformation..."
)

H = cv2.getPerspectiveTransform(
    src,
    dst
)


# ============================================================
# RECTIFY BOARD
# ============================================================

print(
    "[3] Rectifying board..."
)

rectified = cv2.warpPerspective(
    image,
    H,
    (
        BOARD_SIZE,
        BOARD_SIZE
    )
)


# ============================================================
# CREATE VISUALIZATION
# ============================================================

visualization = rectified.copy()


# ============================================================
# DRAW 64 SQUARES
# ============================================================

square_size = BOARD_SIZE / 8

files = "abcdefgh"

print(
    "\n[4] Generating 64 square coordinates..."
)


square_names = []
square_polygons = []


for row in range(8):

    rank = 8 - row

    for col in range(8):

        file = files[col]

        x1 = col * square_size
        y1 = row * square_size

        x2 = (col + 1) * square_size
        y2 = (row + 1) * square_size

        polygon = np.array(
            [
                [x1, y1],
                [x2, y1],
                [x2, y2],
                [x1, y2]
            ],
            dtype=np.float32
        )

        square_name = (
            f"{file}{rank}"
        )

        square_names.append(
            square_name
        )

        square_polygons.append(
            polygon
        )

        # Draw square
        pts = polygon.astype(
            np.int32
        )

        cv2.polylines(
            visualization,
            [pts],
            True,
            (0, 255, 0),
            2
        )

        # Square label
        center = np.mean(
            polygon,
            axis=0
        )

        cv2.putText(
            visualization,
            square_name,
            (
                int(center[0] - 10),
                int(center[1] + 5)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 0, 255),
            1,
            cv2.LINE_AA
        )


print(
    f"Generated {len(square_names)} squares."
)


# ============================================================
# SAVE CALIBRATION
# ============================================================

print(
    "\n[5] Saving calibration..."
)

np.savez(
    CALIBRATION_FILE,

    # Perspective transformation
    H=H,

    # Board dimensions
    board_size=BOARD_SIZE,

    # Marker information
    marker_ids=np.array(
        [0, 1, 2, 3],
        dtype=np.int32
    ),

    marker_centers=np.array(
        [
            A1,
            A8,
            H8,
            H1
        ],
        dtype=np.float32
    ),

    # Square information
    square_names=np.array(
        square_names
    ),

    square_polygons=np.array(
        square_polygons,
        dtype=np.float32
    )
)


# ============================================================
# SAVE VISUALIZATION
# ============================================================

cv2.imwrite(
    str(OUTPUT_IMAGE),
    visualization
)


print(
    f"Calibration saved:\n"
    f"{CALIBRATION_FILE}"
)

print(
    f"\nVisualization saved:\n"
    f"{OUTPUT_IMAGE}"
)


# ============================================================
# DISPLAY
# ============================================================

cv2.imshow(
    "Calibrated Board",
    visualization
)

print(
    "\nPress any key to close."
)

cv2.waitKey(0)

cv2.destroyAllWindows()


print(
    "\n" + "=" * 70
)

print(
    "CALIBRATION COMPLETE"
)

print(
    "=" * 70
)