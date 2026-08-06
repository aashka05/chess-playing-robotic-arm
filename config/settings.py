from pathlib import Path
import torch

# =========================
# Project Paths
# =========================

ROOT = Path(__file__).resolve().parent.parent

VISION_DIR = ROOT / "vision"

MODEL_PATH = VISION_DIR / "models" / "best.pt"

DATASET_PATH = VISION_DIR / "data" / "data.yaml"

RUNS_PATH = VISION_DIR / "runs"

# =========================
# Training Settings
# =========================

IMAGE_SIZE = 640
EPOCHS = 100
BATCH_SIZE = 16
WORKERS = 4

# =========================
# Detection Settings
# =========================

CONFIDENCE = 0.5

# =========================
# Device Selection
# Works on:
# Windows (CUDA)
# macOS Apple Silicon (MPS)
# Intel Mac (CPU)
# Raspberry Pi (CPU)
# =========================

if torch.cuda.is_available():
    DEVICE = "cuda"
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"