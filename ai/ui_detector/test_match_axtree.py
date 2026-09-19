from match_axtree import match_ui_to_axtree


ui_elements = [
    {
        "class": "button",
        "bbox": [100, 100, 250, 150],
        "confidence": 0.95,
        "id": "ui_1"
    }
]

axtree = [
    {
        "id": "continue_button",
        "role": "button",
        "name": "Continue",
        "text": "Continue",
        "bbox": [102, 101, 249, 149],
        "disabled": False,
        "visible": True
    }
]

matches = match_ui_to_axtree(ui_elements, axtree)

print(matches)