from pathlib import Path
import torch
from ultralytics import YOLO

# -----------------------------
# Project Paths
# -----------------------------
ROOT = Path(__file__).resolve().parent.parent

# YOLO11 pretrained model
MODEL_PATH = ROOT / "yolo11n.pt"

# New 12-class dataset
DATASET_PATH = ROOT / "datasets" / "my_dataset_yolo11_converted" / "data.yaml"

# Where this model's training results will be stored
RUNS_PATH = ROOT / "models" / "detection" / "chess_pieces_yolo11"

# -----------------------------
# Training Parameters
# -----------------------------
IMAGE_SIZE = 640
EPOCHS = 100 
BATCH_SIZE = 8
WORKERS = 4

# -----------------------------
# Device Selection
# -----------------------------
if torch.cuda.is_available():
    DEVICE = "cuda"
else:
    DEVICE = "cpu"


def main():
    print("=" * 60)
    print("Chess Piece Detector - YOLO11 Training")
    print("=" * 60)
    print(f"Device   : {DEVICE}")
    print(f"Model    : {MODEL_PATH}")
    print(f"Dataset  : {DATASET_PATH}")
    print(f"Output   : {RUNS_PATH}")
    print("=" * 60)

    model = YOLO(str(MODEL_PATH))

    model.train(
        data=str(DATASET_PATH),
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        workers=WORKERS,
        device=DEVICE,
        project=str(RUNS_PATH),
        name="training",
        patience=20,
        cache=False,
    )

    print("\nTraining Complete!")
    print(
        RUNS_PATH
        / "training"
        / "weights"
        / "best.pt"
    )


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    main()