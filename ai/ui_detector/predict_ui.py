from ultralytics import YOLO
import json
import sys
from pathlib import Path


MODEL_PATH = "runs/detect/runs/netra_ui_v1/weights/best.pt"

CLASS_NAMES = [
    "button",
    "textbox",
    "checkbox",
    "radio",
    "select",
    "link",
    "tab",
    "menu",
    "heading",
    "image",
]


def detect_ui(image_path, confidence=0.5):

    model = YOLO(MODEL_PATH)

    results = model.predict(
        source=image_path,
        conf=confidence,
        verbose=False
    )

    result = results[0]

    detections = []

    if result.boxes is None:
        return detections

    for box in result.boxes:

        cls_id = int(box.cls[0])
        conf = float(box.conf[0])

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        detection = {
            "class": CLASS_NAMES[cls_id],
            "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
            "confidence": round(conf, 4),
            "id": f"ui_{len(detections) + 1}"
        }

        detections.append(detection)

        return detections


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python ai/ui_detector/predict_ui.py <image>")
        sys.exit(1)

    image_path = sys.argv[1]

    detections = detect_ui(image_path)

    print(json.dumps(detections, indent=2))