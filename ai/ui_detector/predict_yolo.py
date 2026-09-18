from ultralytics import YOLO

model = YOLO(
    "runs/detect/ai/ui_detector/runs/netra_ui/weights/best.pt"
)

results = model(
    "ai/ui_detector/dataset/val/images/ui_025.png",
    save=True,
    conf=0.25
)

for result in results:
    print("\nDetected UI elements:")

    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])

        print(
            f"{result.names[class_id]} "
            f"confidence={confidence:.2f}"
        )

print("\nPrediction completed.")