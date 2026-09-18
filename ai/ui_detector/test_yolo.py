from ultralytics import YOLO

model = YOLO("yolo11n.pt")

results = model("ai/ocr/test_page.png")

for result in results:
    print("\nDetected objects:")

    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])

        print(
            f"{result.names[class_id]} "
            f"confidence={confidence:.2f}"
        )