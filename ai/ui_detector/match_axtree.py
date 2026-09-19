def box_iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)

    intersection = iw * ih

    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)

    union = area_a + area_b - intersection

    if union == 0:
        return 0.0

    return intersection / union


def match_ui_to_axtree(ui_elements, axtree, threshold=0.5):
    matches = []

    for ui in ui_elements:
        best_node = None
        best_iou = 0.0

        for node in axtree:
            iou = box_iou(ui["bbox"], node["bbox"])

            if iou > best_iou:
                best_iou = iou
                best_node = node

        if best_node and best_iou >= threshold:
            matches.append({
                "class": ui["class"],
                "bbox": ui["bbox"],
                "confidence": ui["confidence"],
                "id": best_node["id"],
                "iou": round(best_iou, 4)
            })

    return matches