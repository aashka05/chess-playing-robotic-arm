import cv2
import numpy as np
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = Path(
    r"C:\Users\veera\Desktop\chess-playing-robotic-arm"
)

OUTPUT_DIR = PROJECT_DIR / "vision" / "outputs"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# GREEN HSV RANGE
# ============================================================

LOWER_GREEN = np.array(
    [35, 40, 30],
    dtype=np.uint8
)

UPPER_GREEN = np.array(
    [90, 255, 255],
    dtype=np.uint8
)


# ============================================================
# WHITE HSV RANGE
# ============================================================
#
# White has:
#   - low saturation
#   - high value
#
# These values are intentionally not too strict.
#

LOWER_WHITE = np.array(
    [0, 0, 100],
    dtype=np.uint8
)

UPPER_WHITE = np.array(
    [180, 80, 255],
    dtype=np.uint8
)


# ============================================================
# EROSION
# ============================================================

EROSION_SIZE = 11


# ============================================================
# MINIMUM COMPONENT AREA
# ============================================================

MIN_COMPONENT_AREA = 3000


# ============================================================
# FIND LATEST RECTIFIED IMAGE
# ============================================================

rectified_files = list(
    OUTPUT_DIR.glob("board_rectified_*.jpg")
)

if not rectified_files:

    raise RuntimeError(
        "No rectified board image found in:\n"
        f"{OUTPUT_DIR}"
    )

IMAGE_PATH = max(
    rectified_files,
    key=lambda p: p.stat().st_mtime
)


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

height, width = image.shape[:2]


print("=" * 70)
print("CHESSBOARD GREEN + WHITE SQUARE DETECTION")
print("=" * 70)

print(
    f"Image:\n{IMAGE_PATH}"
)

print(
    f"Size : {width} x {height}"
)


# ============================================================
# CONVERT TO HSV
# ============================================================

hsv = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2HSV
)


# ============================================================
# EXPECTED SQUARE AREA
# ============================================================

expected_square_area = (
    (width / 8.0) *
    (height / 8.0)
)

print(
    f"\nExpected full square area:"
    f" {expected_square_area:.1f} px"
)


# ============================================================
# FUNCTION TO COLLECT COMPONENTS
# ============================================================

def detect_components(
    mask,
    color_name
):

    # --------------------------------------------------------
    # ERODE
    # --------------------------------------------------------

    kernel = np.ones(
        (
            EROSION_SIZE,
            EROSION_SIZE
        ),
        dtype=np.uint8
    )

    eroded = cv2.erode(
        mask,
        kernel,
        iterations=1
    )

    # --------------------------------------------------------
    # CONNECTED COMPONENTS
    # --------------------------------------------------------

    num_labels, labels, stats, centroids = (
        cv2.connectedComponentsWithStats(
            eroded,
            connectivity=4
        )
    )

    components = []

    for component_id in range(
        1,
        num_labels
    ):

        x = stats[
            component_id,
            cv2.CC_STAT_LEFT
        ]

        y = stats[
            component_id,
            cv2.CC_STAT_TOP
        ]

        w = stats[
            component_id,
            cv2.CC_STAT_WIDTH
        ]

        h = stats[
            component_id,
            cv2.CC_STAT_HEIGHT
        ]

        area = stats[
            component_id,
            cv2.CC_STAT_AREA
        ]

        cx, cy = centroids[
            component_id
        ]

        # ----------------------------------------------------
        # Ignore tiny components
        # ----------------------------------------------------

        if area < MIN_COMPONENT_AREA:
            continue

        # ----------------------------------------------------
        # Ignore abnormally huge components
        # ----------------------------------------------------

        if area > expected_square_area * 1.2:
            continue

        # ----------------------------------------------------
        # Aspect ratio
        # ----------------------------------------------------

        aspect_ratio = (
            w / float(h)
        )

        if aspect_ratio < 0.55:
            continue

        if aspect_ratio > 1.8:
            continue

        components.append(
            {
                "id": component_id,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "area": area,
                "cx": float(cx),
                "cy": float(cy),
                "color": color_name
            }
        )

    return components, eroded


# ============================================================
# GREEN MASK
# ============================================================

green_mask = cv2.inRange(
    hsv,
    LOWER_GREEN,
    UPPER_GREEN
)


# ============================================================
# SAVE RAW GREEN MASK
# ============================================================

green_raw_path = (
    OUTPUT_DIR /
    "green_mask_raw.jpg"
)

cv2.imwrite(
    str(green_raw_path),
    green_mask
)


# ============================================================
# DETECT GREEN COMPONENTS
# ============================================================

green_components, green_eroded = detect_components(
    green_mask,
    "green"
)


# ============================================================
# SAVE ERODED GREEN MASK
# ============================================================

green_eroded_path = (
    OUTPUT_DIR /
    "green_mask_eroded.jpg"
)

cv2.imwrite(
    str(green_eroded_path),
    green_eroded
)


# ============================================================
# WHITE MASK
# ============================================================

white_mask = cv2.inRange(
    hsv,
    LOWER_WHITE,
    UPPER_WHITE
)


# ============================================================
# SAVE RAW WHITE MASK
# ============================================================

white_raw_path = (
    OUTPUT_DIR /
    "white_mask_raw.jpg"
)

cv2.imwrite(
    str(white_raw_path),
    white_mask
)


# ============================================================
# DETECT WHITE COMPONENTS
# ============================================================

white_components, white_eroded = detect_components(
    white_mask,
    "white"
)


# ============================================================
# SAVE ERODED WHITE MASK
# ============================================================

white_eroded_path = (
    OUTPUT_DIR /
    "white_mask_eroded.jpg"
)

cv2.imwrite(
    str(white_eroded_path),
    white_eroded
)


# ============================================================
# PRINT COUNTS
# ============================================================

print(
    f"\nGreen components detected: "
    f"{len(green_components)}"
)

print(
    f"White components detected: "
    f"{len(white_components)}"
)

print(
    f"Total components detected: "
    f"{len(green_components) + len(white_components)}"
)


# ============================================================
# SORT EACH COLOR
# ============================================================

green_components.sort(
    key=lambda item: (
        item["cy"],
        item["cx"]
    )
)

white_components.sort(
    key=lambda item: (
        item["cy"],
        item["cx"]
    )
)


# ============================================================
# COMBINE ALL COMPONENTS
# ============================================================

all_components = (
    green_components +
    white_components
)


# ============================================================
# SORT ALL 64 SQUARES
# ============================================================
#
# IMPORTANT:
#
# We do NOT simply number all green first and then white.
#
# Instead, all detected squares are sorted by their actual
# position on the board.
#
# This gives:
#
# 1  2  3  4  5  6  7  8
# 9 10 11 12 13 14 15 16
# ...
#
# regardless of whether a square is green or white.
#

all_components.sort(
    key=lambda item: (
        item["cy"],
        item["cx"]
    )
)


# ============================================================
# PRINT DETECTED SQUARES
# ============================================================

print("\nDetected squares:")

for index, component in enumerate(
    all_components,
    start=1
):

    print(
        f"{index:2d} | "
        f"{component['color']:5s} | "
        f"center=("
        f"{component['cx']:7.2f}, "
        f"{component['cy']:7.2f}) | "
        f"size=("
        f"{component['w']:4d} x "
        f"{component['h']:4d}) | "
        f"area="
        f"{component['area']:6d}"
    )


# ============================================================
# DEBUG IMAGE
# ============================================================

debug = image.copy()


# ============================================================
# DRAW ALL DETECTED SQUARES
# ============================================================

for index, component in enumerate(
    all_components,
    start=1
):

    x = component["x"]
    y = component["y"]

    w = component["w"]
    h = component["h"]

    cx = component["cx"]
    cy = component["cy"]

    # --------------------------------------------------------
    # Bounding box
    # --------------------------------------------------------

    cv2.rectangle(
        debug,
        (x, y),
        (x + w, y + h),
        (0, 255, 0),
        3
    )

    # --------------------------------------------------------
    # Center
    # --------------------------------------------------------

    cv2.circle(
        debug,
        (
            int(cx),
            int(cy)
        ),
        6,
        (0, 0, 255),
        -1
    )

    # --------------------------------------------------------
    # Number
    # --------------------------------------------------------

    cv2.putText(
        debug,
        str(index),
        (
            int(cx) - 10,
            int(cy) - 10
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 0, 0),
        2,
        cv2.LINE_AA
    )


# ============================================================
# SAVE DEBUG IMAGE
# ============================================================

debug_path = (
    OUTPUT_DIR /
    "all_squares_debug.jpg"
)

cv2.imwrite(
    str(debug_path),
    debug
)


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("CHESSBOARD SQUARE DETECTION RESULT")
print("=" * 70)


if len(green_components) == 32:

    print(
        "GREEN: SUCCESS - 32 green squares detected."
    )

else:

    print(
        f"GREEN: WARNING - "
        f"{len(green_components)} detected "
        f"(expected 32)."
    )


if len(white_components) == 32:

    print(
        "WHITE: SUCCESS - 32 white squares detected."
    )

else:

    print(
        f"WHITE: WARNING - "
        f"{len(white_components)} detected "
        f"(expected 32)."
    )


if len(all_components) == 64:

    print(
        "\nSUCCESS: Exactly 64 squares detected."
    )

else:

    print(
        f"\nWARNING: "
        f"{len(all_components)} total squares detected "
        f"(expected 64)."
    )


print(
    f"\nGreen raw mask:"
    f"\n{green_raw_path}"
)

print(
    f"\nGreen eroded mask:"
    f"\n{green_eroded_path}"
)

print(
    f"\nWhite raw mask:"
    f"\n{white_raw_path}"
)

print(
    f"\nWhite eroded mask:"
    f"\n{white_eroded_path}"
)

print(
    f"\nCombined debug image:"
    f"\n{debug_path}"
)

print("=" * 70)