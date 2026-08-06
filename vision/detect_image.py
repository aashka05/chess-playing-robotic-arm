from ultralytics import YOLO
import cv2
import os

# ==========================================
# Paths
# ==========================================
MODEL_PATH = "runs/detect/vision/runs/piece_detector/weights/best.pt"
IMAGE_PATH = "vision/test_images/chess6.jpg"
OUTPUT_PATH = "vision/outputs/detected.jpg"

# ==========================================
# Load model
# ==========================================
model = YOLO(MODEL_PATH)

# ==========================================
# Read image
# ==========================================
image = cv2.imread(IMAGE_PATH)

if image is None:
    raise FileNotFoundError(f"Image not found: {IMAGE_PATH}")

# ==========================================
# Run Detection
# ==========================================
results = model.predict(
    image,
    conf=0.25,
    iou=0.45
)

result = results[0]

# ==========================================
# Class name mapping
# ==========================================
label_map = {
    "white-pawn": "wp",
    "white-rook": "wr",
    "white-knight": "wn",
    "white-bishop": "wb",
    "white-queen": "wq",
    "white-king": "wk",
    "black-pawn": "bp",
    "black-rook": "br",
    "black-knight": "bn",
    "black-bishop": "bb",
    "black-queen": "bq",
    "black-king": "bk",
}

print("\nDetected Pieces")
print("-" * 45)

# ==========================================
# Draw detections
# ==========================================
for box in result.boxes:

    cls = int(box.cls[0])
    confidence = float(box.conf[0])

    x1, y1, x2, y2 = map(int, box.xyxy[0])

    class_name = model.names[cls]
    label = label_map.get(class_name, class_name)

    print(f"{label:2s}   {confidence:.2f}")

    # -----------------------
    # Bounding Box
    # -----------------------
    cv2.rectangle(
        image,
        (x1, y1),
        (x2, y2),
        (0, 255, 0),
        2
    )

    # -----------------------
    # BIG LABEL
    # -----------------------
    # font = cv2.FONT_HERSHEY_SIMPLEX
    # font_scale = 1.3       # Increase to 1.3 or 1.5 if needed
    # thickness = 3

    # (tw, th), _ = cv2.getTextSize(
    #     label,
    #     font,
    #     font_scale,
    #     thickness
    # )

    # # Put label INSIDE bounding box if possible
    # tx = x1 + 5
    # ty = y1 + th + 8

    # # If text would go outside box, move it above
    # if ty > y2:
    #     ty = y1 - 8

    # # Keep inside image
    # if ty - th < 0:
    #     ty = th + 5

    # # Black background
    # cv2.rectangle(
    #     image,
    #     (tx - 4, ty - th - 4),
    #     (tx + tw + 4, ty + 4),
    #     (0, 0, 0),
    #     -1
    # )

    # # Yellow text
    # cv2.putText(
    #     image,
    #     label,
    #     (tx, ty),
    #     font,
    #     font_scale,
    #     (0, 255, 255),
    #     thickness,
    #     cv2.LINE_AA
    # )

# ==========================================
# Save output
# ==========================================
os.makedirs("vision/outputs", exist_ok=True)
cv2.imwrite(OUTPUT_PATH, image)

print("\nOutput saved to:")
print(OUTPUT_PATH)

# ==========================================
# Display (Resizable Window)
# ==========================================
window_name = "Chess Piece Detection"

cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

# Initial window size
cv2.resizeWindow(window_name, 1400, 1000)

cv2.imshow(window_name, image)

cv2.waitKey(0)
cv2.destroyAllWindows()