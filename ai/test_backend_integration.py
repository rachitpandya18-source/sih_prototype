import json
import requests

API_URL = "http://127.0.0.1:8000/api/v1/plan_action"

with open(
    "ai/redaction/sanitized_context.json",
    "r",
    encoding="utf-8"
) as file:
    context = json.load(file)

payload = {
    "session_id": "netra_pipeline_test",
    "step_number": 1,
    "task_instruction": "Identify the textbox on the page.",
    "detected_ui_elements": context["ui_elements"],
    "sanitized_axtree": context["sanitized_axtree"],
    "current_url": "http://localhost/test",
    "page_title": "Customer Registration",
    "execute_locally": False,
    "viewport_width": 1440,
    "viewport_height": 900,
    "device_pixel_ratio": 1.0
}

response = requests.post(
    API_URL,
    json=payload,
    timeout=60
)

print("Status:", response.status_code)
print("\nResponse:")
print(json.dumps(response.json(), indent=2))