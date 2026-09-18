from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from app.core.config import get_settings
from app.models.schemas import Action, ActionType, ActionValidationResponse, PageSnapshot


HIGH_RISK_RE = re.compile(
    r'\b(pay|payment|purchase|buy|checkout|delete|remove|erase|close account|terminate account|transfer|submit kyc|kyc|confirm|confirm order|place order|send money|withdraw|publish|post|submit|register)\b',
    re.I,
)


def _find_ref(page: PageSnapshot, ref: str | None):
    if not ref:
        return None
    return next((n for n in page.nodes if n.ref == ref), None)


def _bbox(node) -> list[float]:
    return [node.rect.x, node.rect.y, node.rect.x + node.rect.width, node.rect.y + node.rect.height]


def _high_risk_target(node) -> bool:
    return bool(node and HIGH_RISK_RE.search(f'{node.role or ""} {node.name} {node.text}'))


def validate_action(action: Action, page: PageSnapshot, masked_token_map: dict[str, str] | None = None) -> ActionValidationResponse:
    reasons: list[str] = []
    masked_token_map = masked_token_map or {}
    requires_confirmation = bool(action.requires_human_confirmation)
    risk_level = 'low'
    node = None

    if action.type in {ActionType.click, ActionType.type, ActionType.select}:
        node = _find_ref(page, action.ref)
        if node is None:
            reasons.append('Referenced node does not exist in the current snapshot')
        else:
            if not node.visible or node.disabled:
                reasons.append('Referenced node is not currently actionable')
            if action.type == ActionType.click and node.role not in {
                'button', 'link', 'menuitem', 'tab', 'checkbox', 'radio', 'option', None
            }:
                reasons.append(f'Node role {node.role!r} is not a normal click target')
            if action.type == ActionType.type and node.role not in {'textbox', 'searchbox', 'combobox'}:
                reasons.append(f'Node role {node.role!r} is not a text-entry target')
            if action.type == ActionType.select and node.role not in {'combobox', 'listbox', 'option'}:
                reasons.append(f'Node role {node.role!r} is not a selection target')
            if action.type == ActionType.type:
                if action.value is not None and not (action.value.startswith('[') and action.value.endswith(']')):
                    reasons.append('Raw type values are not permitted; use value_ref or a masked token')
                if action.value_ref != 'LOCAL_USER_VALUE' and not (action.value and action.value.startswith('[')):
                    reasons.append('TYPE action requires a local value reference or masked token')
                if (
                    action.value_ref == 'LOCAL_USER_VALUE'
                    and action.value not in masked_token_map
                    and not (not masked_token_map and action.value is None)
                ):
                    reasons.append('TYPE action token is not present in masked_token_map')
            if action.type == ActionType.select and action.value is None:
                reasons.append('SELECT action requires the option value/label')

            if _high_risk_target(node):
                requires_confirmation = True
                risk_level = 'high'
                reasons.append('Sensitive/destructive target requires human confirmation before execution')

    if action.type == ActionType.scroll:
        if not action.direction or action.amount is None:
            reasons.append('Scroll action requires direction and amount')

    if action.type == ActionType.navigate:
        if not action.url:
            reasons.append('Navigate action requires a URL')
        else:
            parsed = urlparse(action.url)
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                reasons.append('Navigate URL must be an absolute http(s) URL')
            try:
                if parsed.hostname:
                    ipaddress.ip_address(parsed.hostname)
                    reasons.append('Direct IP navigation is disabled by default')
            except ValueError:
                pass
            if parsed.hostname and page.url and get_settings().same_origin_navigation:
                current = urlparse(page.url)
                if current.hostname and parsed.hostname.lower() != current.hostname.lower():
                    reasons.append('Cross-origin navigation is blocked by default')
                    requires_confirmation = True
                    risk_level = 'high'

    if action.type == ActionType.wait and action.ms is None:
        reasons.append('Wait action requires ms')

    if action.type == ActionType.request_confirmation:
        requires_confirmation = True
        risk_level = 'high'

    if action.type == ActionType.finish:
        risk_level = 'low'

    if action.type == ActionType.no_op:
        risk_level = 'low'

    token_violation = any('TYPE action token is not present in masked_token_map' in r for r in reasons)
    if token_violation:
        requires_confirmation = True
        risk_level = 'high'
        normalized = Action(
            type=ActionType.request_confirmation,
            ref=action.ref,
            confidence=min(action.confidence, 0.5),
            reason='TYPE action requires an exact local token; human confirmation is required before any value is used',
            requires_human_confirmation=True,
        )
    else:
        normalized = action.model_copy(update={'requires_human_confirmation': requires_confirmation})

    hard_invalid = any(
        'does not exist' in r
        or 'not currently actionable' in r
        or 'blocked by default' in r
        for r in reasons
    )
    confirmable_only = all('requires human confirmation' in r.lower() for r in reasons)
    return ActionValidationResponse(
        valid=(not hard_invalid and (not reasons or confirmable_only or token_violation)),
        reasons=reasons,
        normalized_action=None if hard_invalid else normalized,
        requires_human_confirmation=requires_confirmation,
        risk_level=risk_level,
    )
