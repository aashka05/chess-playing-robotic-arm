from pathlib import Path
from datetime import datetime

import cv2
from ultralytics import YOLO


# ============================================================
# PATHS
# ============================================================

# Project root:
# C:\Users\veera\Desktop\chess-playing-robotic-arm
PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    PROJECT_ROOT
    / "runs"
    / "detect"
    / "train-3"
    / "weights"
    / "best.pt"
)

IMAGE_PATH = (
    PROJECT_ROOT
    / "datasets"
    / "board_image"
    / "test19.jpg"
)

OUTPUT_DIR = PROJECT_ROOT / "vision" / "outputs"


# ============================================================
# SETTINGS
# ============================================================

IMAGE_SIZE = 640
CONFIDENCE = 0.25


# ============================================================
# LOAD MODEL
# ============================================================

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Model not found:\n{MODEL_PATH}"
    )

if not IMAGE_PATH.exists():
    raise FileNotFoundError(
        f"Input image not found:\n{IMAGE_PATH}"
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

model = YOLO(str(MODEL_PATH))


# ============================================================
# RUN DETECTION
# ============================================================

results = model.predict(
    source=str(IMAGE_PATH),
    imgsz=IMAGE_SIZE,
    conf=CONFIDENCE,
    verbose=False,
)

result = results[0]


# ============================================================
# LOAD ORIGINAL IMAGE
# ============================================================

image = cv2.imread(str(IMAGE_PATH))

if image is None:
    raise RuntimeError(
        f"Could not read image:\n{IMAGE_PATH}"
    )


# ============================================================
# DRAW CLEAN W / B LABELS
# ============================================================

for box, class_id in zip(
    result.boxes.xyxy,
    result.boxes.cls
):

    x1, y1, x2, y2 = map(
        int,
        box.tolist()
    )

    class_id = int(class_id.item())

    # Our dataset:
    # 0 = white_piece
    # 1 = black_piece

    if class_id == 0:
        label = "w"
    elif class_id == 1:
        label = "b"
    else:
        continue

    # Draw bounding box
    cv2.rectangle(
        image,
        (x1, y1),
        (x2, y2),
        (0, 255, 0),
        2,
    )

    # Label size
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 2.0
    thickness = 2

    (text_width, text_height), baseline = cv2.getTextSize(
        label,
        font,
        font_scale,
        thickness,
    )

    # Keep label inside image boundaries
    label_top = max(
        0,
        y1 - text_height - baseline - 6
    )

    label_right = x1 + text_width + 8

    # White label background
    cv2.rectangle(
        image,
        (x1, label_top),
        (label_right, y1),
        (255, 255, 255),
        -1,
    )

    # Black text
    cv2.putText(
        image,
        label,
        (x1 + 4, y1 - 5),
        font,
        font_scale,
        (0, 0, 0),
        thickness,
        cv2.LINE_AA,
    )


# ============================================================
# SAVE RESULT
# ============================================================

timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

output_path = (
    OUTPUT_DIR
    / f"chess3_bw_{timestamp}.jpg"
)

success = cv2.imwrite(
    str(output_path),
    image,
)

if not success:
    raise RuntimeError(
        f"Failed to save output:\n{output_path}"
    )


# ============================================================
# SUMMARY
# ============================================================

print()
print("Detection completed successfully.")
print(f"Model: {MODEL_PATH}")
print(f"Input: {IMAGE_PATH}")
# print(f"Detections: {len(result.boxes)}")
print(f"Output: {output_path}")