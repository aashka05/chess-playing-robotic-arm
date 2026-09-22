import cv2
import numpy as np
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

IMAGE_PATH = Path(
    r"C:\Users\veera\Desktop\chess-playing-robotic-arm"
    r"\datasets\board_image\test14.jpg"
)

OUTPUT_DIR = Path(
    r"C:\Users\veera\Desktop\chess-playing-robotic-arm"
    r"\vision\outputs"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ------------------------------------------------------------
# ONLY THESE IDs ARE VALID
# ------------------------------------------------------------

EXPECTED_IDS = {0, 1, 2, 3}


# ============================================================
# LOAD IMAGE
# ============================================================

image = cv2.imread(str(IMAGE_PATH))

if image is None:
    raise RuntimeError(
        f"Could not read image:\n{IMAGE_PATH}"
    )

result = image.copy()

height, width = image.shape[:2]

print("=" * 65)
print("ARUCO ACCURACY TEST")
print("=" * 65)

print(f"Image: {IMAGE_PATH}")
print(f"Resolution: {width} x {height}")


# ============================================================
# ARUCO DICTIONARY
# ============================================================

aruco = cv2.aruco

# MUST match the dictionary used to generate your markers
dictionary = aruco.getPredefinedDictionary(
    aruco.DICT_4X4_50
)


# ============================================================
# DETECTOR PARAMETERS
# ============================================================

parameters = aruco.DetectorParameters()

# These are useful for small markers such as your 1.8 cm ones
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
# DETECT
# ============================================================

corners, ids, rejected = detector.detectMarkers(
    image
)


# ============================================================
# NO DETECTIONS
# ============================================================

if ids is None:

    print("\n❌ NO MARKERS DETECTED")

    print(
        f"Rejected candidates: {len(rejected)}"
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    output_path = (
        OUTPUT_DIR /
        f"aruco_test_{timestamp}.jpg"
    )

    cv2.imwrite(
        str(output_path),
        result
    )

    print(
        f"\nSaved:\n{output_path}"
    )

    raise SystemExit


# ============================================================
# PROCESS DETECTIONS
# ============================================================

ids = ids.flatten()

detected_ids = set(
    int(x) for x in ids
)


print("\nDetected IDs:")
print(
    sorted(detected_ids)
)

print(
    f"Total ArUco detections: {len(ids)}"
)

print(
    f"Rejected candidates: {len(rejected)}"
)


# ============================================================
# CLASSIFY EACH DETECTION
# ============================================================

valid_ids = []
invalid_ids = []


for marker_corners, marker_id in zip(
    corners,
    ids
):

    marker_id = int(marker_id)

    points = marker_corners[0]

    # --------------------------------------------------------
    # Calculate center
    # --------------------------------------------------------

    center = np.mean(
        points,
        axis=0
    )

    cx = int(center[0])
    cy = int(center[1])

    # --------------------------------------------------------
    # Calculate marker size in pixels
    # --------------------------------------------------------

    side_lengths = []

    for i in range(4):

        p1 = points[i]
        p2 = points[(i + 1) % 4]

        length = np.linalg.norm(
            p1 - p2
        )

        side_lengths.append(length)

    marker_size = np.mean(
        side_lengths
    )

    # --------------------------------------------------------
    # VALID / INVALID
    # --------------------------------------------------------

    if marker_id in EXPECTED_IDS:

        valid_ids.append(marker_id)

        color = (0, 255, 0)       # GREEN
        status = "VALID"

    else:

        invalid_ids.append(marker_id)

        color = (0, 0, 255)       # RED
        status = "UNEXPECTED"

    # --------------------------------------------------------
    # Draw marker boundary
    # --------------------------------------------------------

    pts = points.astype(np.int32)

    cv2.polylines(
        result,
        [pts],
        True,
        color,
        3
    )

    # --------------------------------------------------------
    # Draw center
    # --------------------------------------------------------

    cv2.circle(
        result,
        (cx, cy),
        5,
        color,
        -1
    )

    # --------------------------------------------------------
    # Label
    # --------------------------------------------------------

    label = (
        f"ID {marker_id} | "
        f"{status} | "
        f"{marker_size:.1f}px"
    )

    cv2.putText(
        result,
        label,
        (cx + 10, cy),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2,
        cv2.LINE_AA
    )

    # --------------------------------------------------------
    # Print information
    # --------------------------------------------------------

    print(
        f"ID {marker_id:3d} | "
        f"{status:10s} | "
        f"center=({cx:4d},{cy:4d}) | "
        f"size={marker_size:6.1f}px"
    )


# ============================================================
# CHECK RESULTS
# ============================================================

missing_ids = EXPECTED_IDS - detected_ids

unexpected_ids = detected_ids - EXPECTED_IDS


print("\n" + "=" * 65)
print("RESULT")
print("=" * 65)


# ------------------------------------------------------------
# Expected markers
# ------------------------------------------------------------

if len(valid_ids) == 4:

    print(
        "✅ All 4 expected markers detected."
    )

else:

    print(
        f"⚠ Expected markers detected: "
        f"{sorted(set(valid_ids))}"
    )


# ------------------------------------------------------------
# Missing markers
# ------------------------------------------------------------

if missing_ids:

    print(
        f"❌ Missing expected IDs: "
        f"{sorted(missing_ids)}"
    )

else:

    print(
        "✅ No expected markers missing."
    )


# ------------------------------------------------------------
# Unexpected markers
# ------------------------------------------------------------

if unexpected_ids:

    print(
        f"⚠ Unexpected IDs detected: "
        f"{sorted(unexpected_ids)}"
    )

else:

    print(
        "✅ No unexpected ArUco IDs detected."
    )


# ============================================================
# OVERALL STATUS
# ============================================================

if (
    len(valid_ids) == 4
    and not missing_ids
    and not unexpected_ids
):

    print(
        "\n🟢 TEST PASSED"
    )

    print(
        "Only the four expected marker IDs were detected."
    )

else:

    print(
        "\n🔴 TEST FAILED"
    )

    print(
        "The detector needs further testing/tuning."
    )


# ============================================================
# SAVE RESULT
# ============================================================

timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S_%f"
)

output_path = (
    OUTPUT_DIR /
    f"aruco_test_{timestamp}.jpg"
)

cv2.imwrite(
    str(output_path),
    result
)

print("\n" + "=" * 65)
print(
    f"Output saved to:\n{output_path}"
)
print("=" * 65)