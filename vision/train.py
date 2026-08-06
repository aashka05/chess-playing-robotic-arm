from ultralytics import YOLO

def main():
    model = YOLO("runs/detect/vision/runs/piece_detector/weights/last.pt")

    model.train(
        data="vision/data/chess_dataset_piece/data.yaml",
        epochs=20,
        imgsz=640,
        batch=8,
        workers=2,
        cache=False,
        device=0,
        project="vision/runs",
        name="piece_detector",
        exist_ok=True,
        pretrained=False,
        patience=15,
        verbose=True,
    )

if __name__ == "__main__":
    main()