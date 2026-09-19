import json
import requests

API_URL = "http://127.0.0.1:8000/api/v1/plan_action"

button_detection = {
    "class": "button",
    "bbox": [100, 100, 250, 150],
    "confidence": 0.95,
    "id": "continue_button"
}

axtree = [
    {
        "id": "continue_button",
        "role": "button",
        "name": "Continue",
        "text": "Continue",
        "bbox": [100, 100, 250, 150],
        "disabled": False,
        "visible": True
    }
]

payload = {
    "session_id": "netra_full_button_test",
    "step_number": 1,
    "task_instruction": "Click the Continue button.",
    "detected_ui_elements": [button_detection],
    "sanitized_axtree": axtree,
    "current_url": "http://localhost/test",
    "page_title": "NETRA Button Test",
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
print(json.dumps(response.json(), indent=2))