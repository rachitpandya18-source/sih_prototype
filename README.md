# NETRA Backend — v1.2.0 Judge Hardening

This build adds five defensive layers requested for SIH PS 171 integration:

- strict masked-token reuse for Qwen-VL TYPE actions;
- programmatic high-risk action confirmation;
- Indian PII zero-trust detection for Aadhaar, PAN, email, phone, UPI and IFSC;
- viewport/DPR telemetry and CSS-pixel coordinate guidance;
- two-step repeated-action loop guard that converts immediate repeats into WAIT.

The canonical frontend endpoint remains `POST /api/v1/plan_action`. The older `/api/v1/plan` and `/plan` endpoints remain for compatibility.

# NETRA — Judge-Ready Backend v1.2 (SIH PS 171)

This is the hardened backend contract for **NETRA — Privacy-First Browser Agent**.
It is designed for the real multi-person prototype, not a throwaway mock server.

## Core architecture

```text
Chrome / Edge Extension
        |
        |  local perception + OCR + PII detection + redaction
        |  AXTree + masked tokens + redacted screenshot
        v
POST /api/v1/plan_action
        |
        +--> zero-trust PII leakage gate
        |
        +--> image verification / size check
        |
        +--> Qwen-VL (optional, local/OpenAI-compatible endpoint)
        |       |
        |       +--> 2.5 s timeout
        |       +--> deterministic fallback in hybrid mode
        |
        +--> action safety validator
        |       |
        |       +--> target/ref validation
        |       +--> same-origin navigation guard
        |       +--> destructive-action confirmation guard
        |       +--> loop/failure guard
        |
        v
structured action
        |
        +--> frontend resolves local secret/token values
        +--> frontend executes locally
        +--> frontend re-observes
        +--> next step uses session + history
```

## Canonical frontend contract

### Request

`POST /api/v1/plan_action`

```json
{
  "session_id": "sess_12345",
  "step_number": 1,
  "task_instruction": "Fill this registration form without leaking my personal details",
  "sanitized_screenshot_base64": "data:image/webp;base64,...",
  "sanitized_screenshot_mime_type": "image/webp",
  "current_url": "https://example.com/register",
  "page_title": "Registration",
  "sanitized_axtree": [
    {
      "id": "elem_1",
      "role": "textbox",
      "name": "Full Name",
      "value": "[NAME_1]",
      "bbox": [120, 240, 300, 280]
    },
    {
      "id": "elem_2",
      "role": "button",
      "name": "Create Account",
      "bbox": [120, 500, 220, 540]
    }
  ],
  "detected_ui_elements": [
    {"class": "input", "bbox": [120, 240, 300, 280], "confidence": 0.92, "id": "elem_1"},
    {"class": "button", "bbox": [120, 500, 220, 540], "confidence": 0.95, "id": "elem_2"}
  ],
  "masked_token_map": {
    "[NAME_1]": "NAME",
    "[EMAIL_1]": "EMAIL",
    "[AADHAAR_1]": "ID_GOV"
  },
  "history": [
    {"action": "CLICK", "target_id": "elem_0", "status": "SUCCESS"}
  ],
  "viewport_width": 1440,
  "viewport_height": 900,
  "device_pixel_ratio": 2
}
```

### Response

The response exposes both a nested `action` object and flattened frontend fields so the browser team cannot accidentally diverge on naming.

```json
{
  "ok": true,
  "session_id": "sess_12345",
  "step_number": 1,
  "planner": "deterministic",
  "fallback_used": false,
  "action_type": "CLICK",
  "target_id": "elem_2",
  "target_bbox": [120, 500, 220, 540],
  "target_coords": {"x": 170, "y": 520},
  "value": null,
  "value_ref": null,
  "requires_human_confirmation": true,
  "decision_rationale": "Sensitive/destructive target requires human confirmation before execution",
  "is_task_complete": false,
  "confidence": 0.93,
  "sanitized": true,
  "raw_pii_received": false,
  "next_step": "request_confirmation_before_execution"
}
```

> `decision_rationale` is intentionally a short, judge-safe explanation. The backend never exposes hidden chain-of-thought.

## Privacy guarantees

The backend is **zero-trust** even though redaction is supposed to happen on-device.

It rejects the request with HTTP **422** and code **`PII_LEAKAGE_REJECTED`** when sensitive literals are found in sanitized AXTree/detection context, including common:

- email addresses
- Indian phone numbers
- Aadhaar-like 12 digit values
- PAN-like values
- card-like numeric sequences
- secret/password/key patterns
- UPI identifiers (e.g. `handle@bank`)
- IFSC codes (e.g. `HDFC0ABC123`)

It also rejects:

- unredacted screenshots
- oversized screenshot payloads
- invalid base64/image data
- SHA-256 mismatches
- raw type values returned from the planner

For typing, the backend returns a masked token such as `[NAME_1]` and `value_ref="LOCAL_USER_VALUE"`. The real value stays in the extension's local vault/session storage and is inserted only on-device immediately before input.

## Safety guardrails

Supported public action types:

`CLICK`, `TYPE`, `SELECT`, `SCROLL`, `WAIT`, `NAVIGATE`, `FINISH`, `REQUEST_CONFIRMATION`.

The backend additionally supports internal `NO_OP` for safe failure handling.

The validator:

- validates the referenced element exists, is visible, and is not disabled;
- validates semantic roles for click/type/select;
- blocks cross-origin navigation by default;
- rejects direct-IP navigation;
- requires human confirmation for destructive/sensitive controls such as Pay, Delete, Purchase, Transfer, Submit KYC and similar high-risk labels;
- never returns raw typing values;
- raises a loop guard after repeated failed attempts against the same target.

## Qwen-VL integration

The Qwen adapter uses an OpenAI-compatible `/chat/completions` interface and receives only sanitized context:

```env
VLM_ENABLED=true
VLM_BASE_URL=http://localhost:11434/v1
VLM_API_KEY=local
VLM_MODEL=qwen-vl
PLANNER_MODE=hybrid
ALLOW_FALLBACK=true
VLM_TIMEOUT_S=2.5
```

The backend sends:

- task instruction
- sanitized AXTree/page context
- local UI detection results
- masked-token type map
- recent action history
- sanitized screenshot

The VLM must return structured JSON. The safety validator still gets the final say; the VLM cannot bypass privacy or execution rules.

## Performance / image contract

The browser should send compressed **JPEG/WebP** screenshots with a target of **<= 300 KB**. The backend hard limit is **600 KB** by default. The redaction audit reports whether the target was met.

## CORS

The backend permits normal development origins and browser-extension origins. Credentials are intentionally disabled because the API does not require cookie-based authentication for the local prototype.

## Endpoints

- `GET /health`
- `GET /api/v1/config`
- `POST /api/v1/plan_action` — canonical frontend contract
- `POST /api/v1/agent/run` — legacy/closed-loop request shape
- `POST /api/v1/plan` — structured legacy endpoint
- `POST /plan` — compatibility endpoint for the current 0.2 extension
- `POST /api/v1/action/validate`
- `POST /api/v1/redaction/audit`
- `GET /api/v1/audit`
- Swagger: `/docs`

## Run on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Judge verification

Before the event, run:

```powershell
python -m pytest -q tests
python -m compileall app
python scripts/run_smoke.py
```

The repository contains tests for:

- canonical frontend contract
- PII leakage rejection
- masked-token typing
- high-risk human confirmation
- cross-origin navigation guard
- image contract/config
- legacy extension compatibility

## Frontend handoff rule

The extension should use `/api/v1/plan_action` as the **single source of truth** for the judge build.
Keep `shared_action_schema.json` copied unchanged into the extension repository.

The browser remains responsible for:

1. local UI perception and redaction;
2. local token vault / secret resolution;
3. human confirmation UI;
4. local browser action execution;
5. re-observation and step/history updates.

The backend remains responsible for:

1. zero-trust privacy verification;
2. multimodal reasoning (Qwen-VL when enabled);
3. deterministic fallback;
4. action safety validation;
5. session/step-aware planning metadata;
6. non-sensitive audit trace.
