from __future__ import annotations

import re
from typing import Iterable

from app.models.schemas import Action, ActionType, PageNode, PageSnapshot, Perception


def _norm(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip().lower()


def _node_text(node: PageNode) -> str:
    return _norm(f'{node.role or ""} {node.name} {node.text}')


def _keywords(instruction: str) -> list[str]:
    stop = {
        'the', 'a', 'an', 'to', 'on', 'in', 'at', 'for', 'and', 'of', 'please',
        'find', 'show', 'locate', 'where', 'this', 'that', 'with', 'my', 'without',
    }
    toks = re.findall(r'[a-z0-9]{2,}', _norm(instruction))
    return [t for t in toks if t not in stop]


def _score(node: PageNode, keys: Iterable[str], preferred_roles: set[str]) -> float:
    text = _node_text(node)
    score = 0.0
    for key in keys:
        if key in text:
            score += 1.0
            if key == _norm(node.name):
                score += 1.5
    if node.role in preferred_roles:
        score += 1.5
    if node.visible and not node.disabled:
        score += 0.4
    return score


def _best(nodes: list[PageNode], keys: list[str], roles: set[str]) -> PageNode | None:
    candidates = [n for n in nodes if n.visible and not n.disabled]
    ranked = sorted(candidates, key=lambda n: _score(n, keys, roles), reverse=True)
    if not ranked:
        return None
    best = ranked[0]
    return best if _score(best, keys, roles) >= 1.4 else None


def _token_for_target(target: PageNode, masked_token_map: dict[str, str]) -> str | None:
    label = _norm(f'{target.role} {target.name} {target.text}')
    preferred = []
    if 'email' in label:
        preferred = ['email']
    elif any(x in label for x in ('full name', 'name', 'username')):
        preferred = ['name', 'username']
    elif any(x in label for x in ('phone', 'mobile')):
        preferred = ['phone', 'mobile']
    elif any(x in label for x in ('aadhaar', 'government id', 'id number', 'kyc')):
        preferred = ['aadhaar', 'id_gov', 'id']
    elif 'address' in label:
        preferred = ['address']
    for wanted in preferred:
        for token, kind in masked_token_map.items():
            if wanted in _norm(kind):
                return token
    return next(iter(masked_token_map), '[LOCAL_USER_VALUE]') if masked_token_map else None


def _repeat_failure(history: list[dict], current_target: str | None = None) -> bool:
    tail = history[-3:]
    if len(tail) < 3:
        return False
    target_ids = [x.get('target_id') for x in tail]
    statuses = [str(x.get('status', '')).upper() for x in tail]
    return len(set(target_ids)) == 1 and statuses == ['FAIL', 'FAIL', 'FAIL'] and (current_target is None or target_ids[-1] == current_target)


def plan(
    instruction: str,
    page: PageSnapshot,
    perception: Perception,
    masked_token_map: dict[str, str] | None = None,
    history: list[dict] | None = None,
) -> tuple[Action, float, str, bool]:
    masked_token_map = masked_token_map or {}
    history = history or []
    text = _norm(instruction)
    keys = _keywords(instruction)

    if any(w in text for w in ('finish', 'complete task', 'done', 'stop')):
        return Action(type=ActionType.finish, confidence=0.99, reason='Explicit task completion instruction'), 0.99, 'deterministic', False

    url_match = re.search(r'https?://[^\s]+', instruction)
    if url_match and any(w in text for w in ('open', 'go to', 'navigate', 'visit')):
        return Action(type=ActionType.navigate, url=url_match.group(0), confidence=0.97, reason='Explicit URL navigation request'), 0.97, 'deterministic', False

    if any(w in text for w in ('scroll', 'page down', 'page up')):
        direction = 'up' if any(w in text for w in ('up', 'top')) else 'down'
        amount = 700 if 'page' in text else 500
        return Action(type=ActionType.scroll, direction=direction, amount=amount, confidence=0.92, reason='Explicit scroll instruction'), 0.92, 'deterministic', False

    if any(w in text for w in ('wait', 'pause')):
        return Action(type=ActionType.wait, ms=1000, confidence=0.9, reason='Explicit wait instruction'), 0.9, 'deterministic', False

    wants_type = any(w in text for w in ('type', 'enter', 'write', 'search for', 'fill'))
    wants_select = any(w in text for w in ('select', 'choose'))
    wants_click = any(w in text for w in ('click', 'tap', 'press', 'open', 'find', 'locate'))

    if wants_type:
        target = _best(page.nodes, keys, {'textbox', 'searchbox', 'combobox'})
        if target:
            if len(history) == 1 and str(history[-1].get('status', '')).upper() == 'SUCCESS' and history[-1].get('target_id') == target.ref and ' and ' not in text:
                return Action(type=ActionType.finish, confidence=0.96, reason='Previous requested browser action succeeded; task is complete'), 0.96, 'deterministic-completion', False
            token = _token_for_target(target, masked_token_map)
            return Action(
                type=ActionType.type,
                ref=target.ref,
                value=token,
                value_ref='LOCAL_USER_VALUE',
                confidence=0.88,
                reason='Text entry uses a local masked value; raw user data stays on-device',
            ), 0.88, 'deterministic', _repeat_failure(history, target.ref)

    if wants_select:
        target = _best(page.nodes, keys, {'combobox', 'listbox', 'option'})
        if target:
            if len(history) == 1 and str(history[-1].get('status', '')).upper() == 'SUCCESS' and history[-1].get('target_id') == target.ref and ' and ' not in text:
                return Action(type=ActionType.finish, confidence=0.96, reason='Previous requested browser action succeeded; task is complete'), 0.96, 'deterministic-completion', False
            option = next((k for k in keys if k not in {'select', 'choose'}), '')
            return Action(
                type=ActionType.select,
                ref=target.ref,
                value=f'[{option.upper()}]' if option else '[SELECTED_OPTION]',
                confidence=0.82,
                reason='Selected the best semantic option target from the sanitized AXTree',
            ), 0.82, 'deterministic', _repeat_failure(history, target.ref)

    if wants_click:
        target = _best(page.nodes, keys, {'button', 'link', 'menuitem', 'tab', 'checkbox', 'radio', 'option'})
        if target:
            if len(history) == 1 and str(history[-1].get('status', '')).upper() == 'SUCCESS' and history[-1].get('target_id') == target.ref and ' and ' not in text:
                return Action(type=ActionType.finish, confidence=0.96, reason='Previous requested browser action succeeded; task is complete'), 0.96, 'deterministic-completion', False
            action = Action(type=ActionType.click, ref=target.ref, confidence=0.93, reason=f'Best semantic match: {target.role or "element"}')
            if _repeat_failure(history, target.ref):
                return Action(type=ActionType.request_confirmation, ref=target.ref, confidence=0.5, reason='The same target has failed three consecutive times; human confirmation required'), 0.5, 'deterministic-loop-guard', True
            return action, 0.93, 'deterministic', False

    if perception.ui_detections:
        dets = [d for d in perception.ui_detections if d.confidence >= 0.6]
        if dets:
            d = max(dets, key=lambda x: x.confidence)
            return Action(type=ActionType.click, ref=d.ref, confidence=min(0.78, d.confidence), reason=f'Perception fallback: {d.label}'), min(0.78, d.confidence), 'deterministic-perception', False

    return Action(type=ActionType.no_op, confidence=0.15, reason='No safe matching action found'), 0.15, 'deterministic', False
