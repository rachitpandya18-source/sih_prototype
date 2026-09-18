# NETRA Frontend Handoff — Canonical Integration

## Use this endpoint in the judge build

`POST http://localhost:8000/api/v1/plan_action`

Do not create a second frontend-specific schema. Copy `shared_action_schema.json` unchanged.

## Request builder

```js
const payload = {
  session_id,
  step_number,
  task_instruction,
  sanitized_screenshot_base64, // data:image/webp;base64,... OR raw base64
  sanitized_screenshot_mime_type: "image/webp",
  current_url: location.href,
  page_title: document.title,
  sanitized_axtree,
  detected_ui_elements,
  masked_token_map,
  history
};

const res = await fetch("http://localhost:8000/api/v1/plan_action", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload)
});

const data = await res.json();
```

## Execute action locally

### CLICK

Resolve `target_id` against the current DOM/AXTree and click locally.

### TYPE

Never use a server-provided raw value. The backend returns:

```json
{
  "action_type": "TYPE",
  "target_id": "elem_1",
  "value": "[NAME_1]",
  "value_ref": "LOCAL_USER_VALUE"
}
```

The extension resolves `[NAME_1]` from its local session vault and types it locally.

### SELECT

Resolve `target_id`, then choose the option indicated by the masked token/label.

### SCROLL / WAIT / NAVIGATE

Use the structured `direction`, `amount`, `ms`, or `url` fields. Navigation is already safety-checked by the backend.

### Human confirmation

If:

```js
if (data.requires_human_confirmation) {
  // pause automation and show the NETRA confirmation modal
}
```

Examples include Pay Now, Delete Account, Purchase, Transfer, Submit KYC and similar high-risk controls.

### Re-observation loop

After a successful local action:

```js
history.push({
  action: data.action_type,
  target_id: data.target_id ?? null,
  status: "SUCCESS",
  step_number
});
step_number += 1;
```

Capture the page again and call `/api/v1/plan_action` with the same `session_id` and updated history.

## Privacy rule

The backend is a second safety gate. If the frontend accidentally sends raw PII, expect:

HTTP `422`

```json
{
  "detail": {
    "code": "PII_LEAKAGE_REJECTED"
  }
}
```

Do not hide or swallow this error in the UI. Show a privacy-blocked state.

## Judge UI telemetry

The response contains `planner`, `fallback_used`, `confidence`, `trace`, `requires_human_confirmation`, `sanitized`, and `raw_pii_received`. These fields can power the NETRA judge dashboard without fabricating metrics.


## Coordinate space / DPR rule

The canonical semantic target is always `target_id`. Resolve that element locally first. Treat `target_coords` as a visual fallback only. Browser screenshots can be larger than CSS viewport coordinates on high-DPI displays.

Use the request telemetry fields:
- `viewport_width`
- `viewport_height`
- `device_pixel_ratio`

When a visual coordinate is derived from screenshot pixels, convert to CSS pixels with:

```js
const cssX = pixelX / window.devicePixelRatio;
const cssY = pixelY / window.devicePixelRatio;
```

Do not click by coordinates when `target_id` resolves successfully.

## Token vault integrity

For `TYPE`, the only valid server-provided `value` is an exact key from `masked_token_map`, and `value_ref` must be `LOCAL_USER_VALUE`. The frontend must look up the real value locally and never send that real value back to the backend.

If the backend returns `REQUEST_CONFIRMATION` because a token is unavailable or invalid, pause and ask the user instead of inventing a value.
