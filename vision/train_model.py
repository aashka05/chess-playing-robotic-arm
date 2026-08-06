from pathlib import Path
import torch
from ultralytics import YOLO

# -----------------------------
# Project Paths
# -----------------------------
ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = ROOT / "vision" / "models" / "best.pt"
DATASET_PATH = ROOT / "vision" / "data" / "data.yaml"
RUNS_PATH = ROOT / "vision" / "runs"

# -----------------------------
# Training Parameters
# -----------------------------
IMAGE_SIZE = 640
EPOCHS = 100
BATCH_SIZE = 16
WORKERS = 4

# -----------------------------
# Device Selection
# -----------------------------
if torch.cuda.is_available():
    DEVICE = "cuda"
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"


def main():
    print("=" * 50)
    print("Chess Piece Detector Training")
    print("=" * 50)
    print(f"Device   : {DEVICE}")
    print(f"Model    : {MODEL_PATH}")
    print(f"Dataset  : {DATASET_PATH}")
    print("=" * 50)

    model = YOLO(str(MODEL_PATH))

    model.train(
        data=str(DATASET_PATH),
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        workers=WORKERS,
        device=DEVICE,
        project=str(RUNS_PATH),
        name="chess_finetuned",
    )

    print("\nTraining Complete!")
    print(RUNS_PATH / "chess_finetuned" / "weights" / "best.pt")


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    main()