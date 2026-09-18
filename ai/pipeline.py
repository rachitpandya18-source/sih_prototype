import json
import subprocess
import sys

from PIL import Image, ImageDraw
from pii.pii_rules import detect_pii


def run_ocr(image_path):
    result = subprocess.run(
        ["node", "ai/ocr/ocr.js", image_path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)

    return json.loads(result.stdout)


def normalize(text):
    return "".join(
        character.lower()
        for character in text
        if character.isalnum()
    )


def find_pii_boxes(pii_findings, words):
    boxes = []

    for finding in pii_findings:

        target = normalize(finding["text"])

        for i in range(len(words)):

            combined = ""

            for j in range(i, len(words)):

                combined += normalize(words[j]["text"])

                if combined == target:

                    selected_words = words[i:j + 1]

                    x0 = min(word["x0"] for word in selected_words)
                    y0 = min(word["y0"] for word in selected_words)
                    x1 = max(word["x1"] for word in selected_words)
                    y1 = max(word["y1"] for word in selected_words)

                    boxes.append({
                        "type": finding["type"],
                        "text": finding["text"],
                        "box": [x0, y0, x1, y1]
                    })

                    break

                if len(combined) > len(target):
                    break

    return boxes


def redact_image(image_path, output_path, boxes):

    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    for item in boxes:

        x0, y0, x1, y1 = item["box"]

        draw.rectangle(
            [x0, y0, x1, y1],
            fill="black"
        )

    image.save(output_path)


def main():

    if len(sys.argv) < 2:
        print("Usage: python ai/pipeline.py <image-path>")
        return

    image_path = sys.argv[1]

    print("Running OCR...")

    ocr_result = run_ocr(image_path)

    text = ocr_result["text"]
    words = ocr_result["words"]

    print("\nOCR completed.")

    findings = detect_pii(text)

    print("\nPII detected:")

    for finding in findings:
        print(
            finding["type"],
            "->",
            finding["text"]
        )

    boxes = find_pii_boxes(findings, words)

    print("\nRedaction boxes:")

    for box in boxes:
        print(box)

    output_path = "ai/redaction/redacted_page.png"

    redact_image(
        image_path,
        output_path,
        boxes
    )

    print("\nRedacted image saved:")
    print(output_path)


if __name__ == "__main__":
    main()