import json
import subprocess
import sys

from PIL import Image, ImageDraw
from pii.pii_rules import detect_pii
from ui_detector.predict_ui import detect_ui
from ui_detector.match_axtree import match_ui_to_axtree


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

def build_test_axtree(ui_elements):
    axtree = []

    for index, ui in enumerate(ui_elements):
        if ui["class"] == "button":
            role = "button"
        elif ui["class"] == "textbox":
            role = "textbox"
        elif ui["class"] == "checkbox":
            role = "checkbox"
        elif ui["class"] == "radio":
            role = "radio"
        elif ui["class"] == "select":
            role = "combobox"
        elif ui["class"] == "link":
            role = "link"
        elif ui["class"] == "heading":
            role = "heading"
        elif ui["class"] == "image":
            role = "img"
        else:
            role = "generic"

        axtree.append({
            "id": f"ax_{index + 1}",
            "role": role,
            "name": "",
            "text": "",
            "bbox": ui["bbox"],
            "disabled": False,
            "visible": True
        })

    return axtree

def main():

    if len(sys.argv) < 2:
        print("Usage: python ai/pipeline.py <image-path>")
        return

    image_path = sys.argv[1]

    print("Running UI detection...")

    ui_elements = detect_ui(image_path)

    print("\nUI elements detected:")

    for element in ui_elements:
        print(element)

    print("\nBuilding test AXTree...")
    axtree = build_test_axtree(ui_elements)

    print("\nMatching UI detections to AXTree...")
    matched_ui = match_ui_to_axtree(ui_elements, axtree)

    for element in matched_ui:
        print(element)
    print("\nRunning OCR...")

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

    sanitized_text = text

    for finding in findings:
        sanitized_text = sanitized_text.replace(
            finding["text"],
            "[REDACTED]"
        )

        sanitized_context = {
            "ui_elements": matched_ui,
            "sanitized_axtree": axtree,
            "ocr_text": sanitized_text,
            "pii_detected": [
                {"type": finding["type"]}
                for finding in findings
            ],
            "redaction_boxes": [
                {
                    "type": box["type"],
                    "box": box["box"]
                }
                for box in boxes
            ],
            "sanitized_image": output_path
        }

    print("\nSanitized context:")
    print(json.dumps(sanitized_context, indent=2))

    context_path = "ai/redaction/sanitized_context.json"

    with open(context_path, "w", encoding="utf-8") as file:
        json.dump(
            sanitized_context,
            file,
            indent=2
        )

    print("\nSanitized context saved:")
    print(context_path)


if __name__ == "__main__":
    main()