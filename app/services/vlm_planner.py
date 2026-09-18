from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import Settings
from app.models.schemas import Action, ActionType, PageSnapshot, Perception


class VLMPlannerError(RuntimeError):
    pass


SYSTEM_PROMPT = '''You are NETRA, a privacy-preserving browser automation agent.
You are given only sanitized browser context, local UI perception, and a masked_token_map.

CRITICAL PRIVACY RULES:
1. When generating a TYPE action, you MUST use ONLY an exact token key from the supplied masked_token_map, such as [NAME_1], [EMAIL_1], or [AADHAAR_1].
2. NEVER invent, guess, paraphrase, echo, or substitute raw personal data, dummy values, example values, or realistic-looking values.
3. If the target field requires user data and no matching masked token exists, emit REQUEST_CONFIRMATION or WAIT.
4. For TYPE, set value_ref to LOCAL_USER_VALUE and set value to the exact token key.
5. Never return raw values from the page, OCR, screenshot, or memory.
6. Only reference element refs that exist in the supplied sanitized page snapshot.

Return exactly one JSON object with these keys:
{"type":"click|type|select|scroll|navigate|wait|finish|request_confirmation|no_op","ref":null,"value":null,"value_ref":null,"direction":null,"amount":null,"url":null,"ms":null,"reason":"short externally safe decision rationale","confidence":0.0,"requires_human_confirmation":false}

Never return chain-of-thought or hidden reasoning. The reason field must be a short externally safe rationale.
'''


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{.*\}', text, re.S)
    if not match:
        raise VLMPlannerError('VLM did not return a JSON object')
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise VLMPlannerError('VLM JSON could not be parsed') from exc
    if not isinstance(value, dict):
        raise VLMPlannerError('VLM response was not an object')
    return value


class OpenAICompatibleVLMPlanner:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def plan(
        self,
        instruction: str,
        page: PageSnapshot,
        perception: Perception,
        image_base64: str | None,
        mime_type: str,
        masked_token_map: dict[str, str] | None = None,
        history: list[dict] | None = None,
    ) -> tuple[Action, str]:
        masked_token_map = masked_token_map or {}
        history = history or []
        content: list[dict[str, Any]] = [
            {
                'type': 'text',
                'text': (
                    f'Instruction: {instruction}\n'
                    f'Sanitized page: {page.model_dump_json()}\n'
                    f'Local perception: {perception.model_dump_json()}\n'
                    f'Exact masked_token_map keys allowed for TYPE: {json.dumps(list(masked_token_map.keys()))}\n'
                    f'Masked token labels: {json.dumps(masked_token_map)}\n'
                    f'Action history: {json.dumps(history[-20:])}\n'
                ),
            }
        ]
        if image_base64:
            content.append({'type': 'image_url', 'image_url': {'url': f'data:{mime_type};base64,{image_base64}'}})

        payload = {
            'model': self.settings.vlm_model,
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': content},
            ],
            'temperature': 0,
        }
        headers = {'Authorization': f'Bearer {self.settings.vlm_api_key}'} if self.settings.vlm_api_key else {}
        url = self.settings.vlm_base_url.rstrip('/') + '/chat/completions'
        try:
            timeout = httpx.Timeout(self.settings.vlm_timeout_s)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise VLMPlannerError(f'VLM request failed: {exc}') from exc

        try:
            content_text = data['choices'][0]['message']['content']
            if isinstance(content_text, list):
                content_text = ''.join(str(x.get('text', '')) for x in content_text if isinstance(x, dict))
        except Exception as exc:
            raise VLMPlannerError('VLM response did not contain choices[0].message.content') from exc

        action_data = _extract_json(str(content_text))
        try:
            action = Action(**action_data)
        except Exception as exc:
            raise VLMPlannerError(f'VLM action schema validation failed: {exc}') from exc

        # Programmatic token-vault integrity enforcement. The model may only emit
        # exact token keys supplied by the frontend; unknown placeholders or raw
        # strings are converted into a safe confirmation step and are never sent
        # back to the browser vault.
        if action.type == ActionType.type:
            token = action.value
            allowed_tokens = set(masked_token_map.keys())
            if action.value_ref != 'LOCAL_USER_VALUE' or token not in allowed_tokens:
                return (
                    Action(
                        type=ActionType.request_confirmation,
                        ref=action.ref,
                        confidence=min(action.confidence, 0.5),
                        reason='TYPE action requires an exact local masked token; no unrecognized value will be used',
                        requires_human_confirmation=True,
                    ),
                    'qwen-vl-token-guard',
                )
        return action, 'qwen-vl'
