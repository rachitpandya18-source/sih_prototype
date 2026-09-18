from PIL import Image, ImageDraw


def redact_image(image_path, output_path, boxes):
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    for box in boxes:
        x1, y1, x2, y2 = box
        draw.rectangle([x1, y1, x2, y2], fill="black")

    image.save(output_path)


if __name__ == "__main__":

    image_path = "ai/ocr/test_page.png"
    output_path = "ai/redaction/redacted_page.png"

    # Temporary test boxes.
    # We'll replace these with actual OCR/UI coordinates later.
    boxes = [
        (100, 100, 500, 130),
        (100, 140, 500, 170)
    ]

    redact_image(image_path, output_path, boxes)

    print("Redacted image saved:", output_path)