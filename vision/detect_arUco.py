import cv2
import numpy as np
from pathlib import Path
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

IMAGE_PATH = Path(
    r"C:\Users\veera\Desktop\chess-playing-robotic-arm"
    r"\datasets\3merged\train\images\my5_IMG_20260906_092944352_jpg.rf.aa13d20816f7402aba96798096fc71aa.jpg"
)

OUTPUT_DIR = Path(
    r"C:\Users\veera\Desktop\chess-playing-robotic-arm"
    r"\vision\outputs"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# EXPECTED MARKER IDs
# ============================================================
#
# IMPORTANT:
# Change these if your online-generated markers have
# different IDs.
#
# Our planned orientation is:
#
#       ID 1                 ID 2
#
#       A8                   H8
#
#       ┌─────────────────────┐
#       │                     │
#       │       CHESS         │
#       │       BOARD         │
#       │                     │
#       └─────────────────────┘
#
#       A1                   H1
#
#       ID 0                 ID 3
#
# ============================================================

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

result = image.copy()

height, width = image.shape[:2]

print("=" * 60)
print("ARUCO BOARD DETECTION")
print("=" * 60)

print(f"Image: {IMAGE_PATH}")
print(f"Image size: {width} x {height}")


# ============================================================
# ARUCO DICTIONARY
# ============================================================
#
# This MUST be the same dictionary used when you generated
# your markers.
#
# If you used another dictionary online, change this.
#
# ============================================================

aruco = cv2.aruco

dictionary = aruco.getPredefinedDictionary(
    aruco.DICT_4X4_50
)


# ============================================================
# DETECTOR PARAMETERS
# ============================================================

parameters = aruco.DetectorParameters()


# Slightly improve detection of small markers
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

corners, ids, rejected = detector.detectMarkers(
    image
)


# ============================================================
# NO MARKERS
# ============================================================

if ids is None:

    print("\n❌ NO MARKERS DETECTED")

    print(
        f"Rejected candidates: {len(rejected)}"
    )

    output_path = (
        OUTPUT_DIR /
        f"aruco_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    )

    cv2.imwrite(
        str(output_path),
        result
    )

    print(
        f"\nSaved result to:\n{output_path}"
    )

    raise SystemExit


# ============================================================
# FLATTEN IDS
# ============================================================

ids = ids.flatten()

print(
    f"\nDetected marker IDs: {list(ids)}"
)

print(
    f"Number detected: {len(ids)}"
)

print(
    f"Rejected candidates: {len(rejected)}"
)


# ============================================================
# DRAW DETECTED MARKERS
# ============================================================

aruco.drawDetectedMarkers(
    result,
    corners,
    ids
)


# ============================================================
# STORE MARKER CENTERS
# ============================================================

detected_markers = {}


for marker_corners, marker_id in zip(
    corners,
    ids
):

    # Four corners of this marker
    points = marker_corners[0]

    # Marker center
    center = np.mean(
        points,
        axis=0
    )

    cx = float(center[0])
    cy = float(center[1])

    detected_markers[int(marker_id)] = {
        "corners": points,
        "center": np.array([cx, cy])
    }


# ============================================================
# PRINT DETECTED MARKERS
# ============================================================

print("\nDetected marker information:")
print("-" * 60)

for marker_id in sorted(detected_markers):

    marker = detected_markers[marker_id]

    center = marker["center"]

    corner_points = marker["corners"]

    marker_width = max(
        np.linalg.norm(
            corner_points[0] -
            corner_points[1]
        ),
        np.linalg.norm(
            corner_points[1] -
            corner_points[2]
        )
    )

    chess_corner = EXPECTED_IDS.get(
        marker_id,
        "UNKNOWN"
    )

    print(
        f"ID {marker_id:2d} | "
        f"Chess corner: {chess_corner:2s} | "
        f"Center: ({center[0]:7.1f}, {center[1]:7.1f}) | "
        f"Size: {marker_width:6.1f} px"
    )


# ============================================================
# CHECK EXPECTED IDS
# ============================================================

expected = set(
    EXPECTED_IDS.keys()
)

detected = set(
    detected_markers.keys()
)


missing = expected - detected
unexpected = detected - expected


print("\n" + "=" * 60)
print("MARKER CHECK")
print("=" * 60)


if not missing and not unexpected:

    print(
        "✅ SUCCESS: All 4 expected markers detected."
    )

elif missing:

    print(
        f"❌ Missing markers: {sorted(missing)}"
    )

    if unexpected:
        print(
            f"⚠ Unexpected IDs: {sorted(unexpected)}"
        )


# ============================================================
# DRAW LABELS
# ============================================================

for marker_id, marker in detected_markers.items():

    center = marker["center"]

    cx = int(center[0])
    cy = int(center[1])

    chess_corner = EXPECTED_IDS.get(
        marker_id,
        "UNKNOWN"
    )

    label = (
        f"ID {marker_id} = {chess_corner}"
    )

    cv2.circle(
        result,
        (cx, cy),
        5,
        (0, 0, 255),
        -1
    )

    cv2.putText(
        result,
        label,
        (cx + 10, cy),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2,
        cv2.LINE_AA
    )


# ============================================================
# DRAW BOARD ORIENTATION
# ============================================================

if all(
    marker_id in detected_markers
    for marker_id in EXPECTED_IDS
):

    A1 = detected_markers[0]["center"]
    A8 = detected_markers[1]["center"]
    H8 = detected_markers[2]["center"]
    H1 = detected_markers[3]["center"]

    board_points = np.array(
        [
            A8,
            H8,
            H1,
            A1
        ],
        dtype=np.int32
    )

    cv2.polylines(
        result,
        [board_points],
        True,
        (255, 0, 0),
        3
    )

    # Draw corner names
    corner_positions = {
        "A8": A8,
        "H8": H8,
        "H1": H1,
        "A1": A1
    }

    for name, point in corner_positions.items():

        x = int(point[0])
        y = int(point[1])

        cv2.putText(
            result,
            name,
            (x + 10, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 0, 0),
            2,
            cv2.LINE_AA
        )


# ============================================================
# SAVE RESULT
# ============================================================

timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

output_path = (
    OUTPUT_DIR /
    f"aruco_detection_{timestamp}.jpg"
)

cv2.imwrite(
    str(output_path),
    result
)


print("\n" + "=" * 60)
print(
    f"Output saved to:\n{output_path}"
)
print("=" * 60)