from ultralytics import YOLO

model = YOLO("yolo11n.pt")

model.train(
    data="ai/ui_detector/dataset/data.yaml",
    epochs=30,
    imgsz=640,
    batch=4,
    project="ai/ui_detector/runs",
    name="netra_ui_600"
)

print("Training completed.")