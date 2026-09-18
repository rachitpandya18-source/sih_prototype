from __future__ import annotations

import secrets
import time
from collections import deque
from typing import Any
from uuid import uuid4

from app.core.config import Settings
from app.core.privacy import (
    PrivacyViolation,
    assert_masked_token_map,
    assert_privacy_request,
    assert_sanitized_axtree,
    assert_sanitized_detections,
    validate_sanitized_image,
)
from app.models.schemas import (
    Action,
    ActionType,
    AgentRequest,
    AgentRunRequest,
    AgentRunResponse,
    PageSnapshot,
    PlanRequest,
    PlanResponse,
    RedactionAuditRequest,
    RedactionAuditResponse,
    Rect,
)
from app.services.action_validator import validate_action
from app.services.deterministic_planner import plan as deterministic_plan
from app.services.vlm_planner import OpenAICompatibleVLMPlanner, VLMPlannerError


class AuditLog:
    def __init__(self, max_items: int = 500):
        self.items = deque(maxlen=max_items)

    def add(self, event: dict[str, Any]) -> None:
        self.items.append(event)

    def latest(self) -> list[dict[str, Any]]:
        return list(self.items)


ACTION_LOOP_IGNORE = {'wait', 'finish', 'request_confirmation', 'no_op'}

def detect_repetition(history: list[dict[str, Any]], current_action: Action) -> Action:
    """Convert an immediate repeated action into WAIT to allow DOM/UI updates."""
    if current_action.type.value in ACTION_LOOP_IGNORE or len(history) < 2:
        return current_action
    last_actions = history[-2:]
    current_type = current_action.type.value.upper()
    current_target = current_action.ref
    if all(
        str(h.get('action', '')).upper() == current_type
        and h.get('target_id') == current_target
        for h in last_actions
    ):
        return Action(
            type=ActionType.wait,
            ref=None,
            ms=750,
            confidence=min(current_action.confidence, 0.7),
            reason='Repeated action loop detected; waiting for DOM updates before retrying',
        )
    return current_action


class AgentService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.audit = AuditLog(settings.audit_keep)
        self.vlm = OpenAICompatibleVLMPlanner(settings)

    def _ids(self, request_id: str | None, session_id: str | None) -> tuple[str, str]:
        rid = request_id or str(uuid4())
        sid = session_id or f'netra-{secrets.token_hex(6)}'
        return rid, sid

    def _prepare(self, req: PlanRequest) -> tuple[str, str, dict[str, Any]]:
        rid, sid = self._ids(req.request_id, req.session_id)
        if len(req.page.nodes) > self.settings.max_nodes:
            raise PrivacyViolation('Page snapshot contains too many nodes')
        if len(req.instruction) > self.settings.max_instruction_chars:
            raise PrivacyViolation('Instruction is too long')
        assert_masked_token_map(req.masked_token_map)
        payload = req.model_dump()
        assert_privacy_request(payload, self.settings)
        # Field-specific zero-trust checks catch leaks even if future schemas change.
        assert_sanitized_axtree([
            {
                'id': n.ref,
                'role': n.role,
                'name': n.name,
                'text': n.text,
            }
            for n in req.page.nodes
        ])
        assert_sanitized_detections([d.model_dump() for d in req.perception.ui_detections])
        image_info = validate_sanitized_image(
            req.screenshot.data_base64,
            req.screenshot.mime_type,
            self.settings.max_image_bytes,
            self.settings.target_image_bytes,
        )
        if req.screenshot.sha256 and image_info.get('sha256') and req.screenshot.sha256 != image_info['sha256']:
            raise PrivacyViolation('Screenshot sha256 does not match received bytes')
        if req.pii.raw_values_sent:
            raise PrivacyViolation('raw_values_sent must be false')
        if not req.screenshot.redacted:
            raise PrivacyViolation('Only redacted screenshots are accepted')
        return rid, sid, image_info

    @staticmethod
    def _coordinates(action: Action, page: PageSnapshot) -> tuple[str | None, list[float] | None, dict[str, float] | None]:
        if not action.ref:
            return None, None, None
        node = next((n for n in page.nodes if n.ref == action.ref), None)
        if not node:
            return action.ref, None, None
        bbox = [node.rect.x, node.rect.y, node.rect.x + node.rect.width, node.rect.y + node.rect.height]
        return node.ref, bbox, {'x': round(node.rect.x + node.rect.width / 2, 2), 'y': round(node.rect.y + node.rect.height / 2, 2)}

    @staticmethod
    def _task_complete(action: Action, history: list[dict[str, Any]]) -> bool:
        if action.type.value == 'finish':
            return True
        # A successful prior action can mark a one-step task complete on the next observation.
        if history and str(history[-1].get('status', '')).upper() == 'SUCCESS':
            if any(w in action.reason.lower() if action.reason else False for w in ('best semantic match', 'explicit', 'selected')):
                return False
        return False

    async def plan(self, req: PlanRequest) -> PlanResponse:
        started = time.perf_counter()
        rid, sid, image_info = self._prepare(req)
        trace: list[dict[str, Any]] = [
            {'stage': 'privacy_gate', 'ok': True},
            {
                'stage': 'sanitized_image',
                'present': image_info['present'],
                'verified': image_info['verified'],
                'bytes': image_info['bytes'],
                'compression_target_met': image_info['compression_target_met'],
            },
            {
                'stage': 'context',
                'step_number': req.step_number,
                'history_items': len(req.history),
                'viewport_width': req.viewport_width,
                'viewport_height': req.viewport_height,
                'device_pixel_ratio': req.device_pixel_ratio,
            },
        ]
        fallback_used = False
        planner_name = 'deterministic'
        action: Action
        confidence: float
        use_vlm = self.settings.vlm_enabled and self.settings.planner_mode in {'hybrid', 'vlm'}

        if use_vlm:
            try:
                action, planner_name = await self.vlm.plan(
                    req.instruction,
                    req.page,
                    req.perception,
                    req.screenshot.data_base64,
                    req.screenshot.mime_type,
                    req.masked_token_map,
                    req.history,
                )
                confidence = action.confidence
                trace.append({'stage': 'vlm', 'ok': True, 'planner': planner_name})
            except VLMPlannerError as exc:
                trace.append({'stage': 'vlm', 'ok': False, 'error': str(exc)[:300]})
                if not self.settings.allow_fallback or self.settings.planner_mode == 'vlm':
                    raise
                action, confidence, planner_name, loop_guard = deterministic_plan(
                    req.instruction, req.page, req.perception, req.masked_token_map, req.history
                )
                fallback_used = True
                trace.append({'stage': 'fallback', 'planner': planner_name, 'loop_guard': loop_guard})
        elif self.settings.planner_mode == 'mock':
            action = Action(type='no_op', confidence=0.1, reason='Mock planner mode')
            confidence = action.confidence
            planner_name = 'mock'
            trace.append({'stage': 'mock', 'ok': True})
        else:
            action, confidence, planner_name, loop_guard = deterministic_plan(
                req.instruction, req.page, req.perception, req.masked_token_map, req.history
            )
            trace.append({'stage': 'deterministic', 'planner': planner_name, 'loop_guard': loop_guard})

        # Cross-planner loop guard: never repeat a target after three consecutive failures.
        failed_tail = req.history[-3:]
        if len(failed_tail) == 3 and all(str(x.get('status', '')).upper() == 'FAIL' for x in failed_tail):
            ids = [x.get('target_id') for x in failed_tail]
            if action.ref and len(set(ids)) == 1 and ids[0] == action.ref:
                action = Action(
                    type='request_confirmation',
                    ref=action.ref,
                    confidence=0.5,
                    reason='The same target failed three consecutive times; human confirmation is required',
                    requires_human_confirmation=True,
                )
                trace.append({'stage': 'loop_guard', 'triggered': True, 'target_id': action.ref})

        repeated_before_validation = action
        action = detect_repetition(req.history, action)
        if action.type != repeated_before_validation.type or action.ref != repeated_before_validation.ref:
            trace.append({
                'stage': 'loop_guard',
                'triggered': True,
                'mode': 'two_step_repetition',
                'previous_action_type': repeated_before_validation.type.value,
                'previous_target_id': repeated_before_validation.ref,
            })

        validation = validate_action(action, req.page, req.masked_token_map)
        trace.append({
            'stage': 'action_validation',
            'valid': validation.valid,
            'reasons': validation.reasons,
            'requires_human_confirmation': validation.requires_human_confirmation,
            'risk_level': validation.risk_level,
        })

        if validation.normalized_action is not None:
            action = validation.normalized_action
        elif not validation.valid:
            action = Action(type='no_op', confidence=0.05, reason='Generated action failed safety validation')
            confidence = action.confidence
            fallback_used = True

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        target_id, target_bbox, target_coords = self._coordinates(action, req.page)
        is_complete = self._task_complete(action, req.history)
        trace.append({'stage': 'complete', 'latency_ms': elapsed_ms, 'is_task_complete': is_complete})

        self.audit.add({
            'request_id': rid,
            'session_id': sid,
            'step_number': req.step_number,
            'planner': planner_name,
            'fallback_used': fallback_used,
            'raw_pii_received': False,
            'latency_ms': elapsed_ms,
            'action_type': action.type.value,
            'target_id': target_id,
            'requires_human_confirmation': action.requires_human_confirmation,
        })

        return PlanResponse(
            ok=True,
            request_id=rid,
            session_id=sid,
            step_number=req.step_number,
            planner=planner_name,
            fallback_used=fallback_used,
            action=action,
            action_type=action.type.value.upper(),
            target_id=target_id,
            target_bbox=target_bbox,
            target_coords=target_coords,
            value=action.value,
            value_ref=action.value_ref,
            requires_human_confirmation=action.requires_human_confirmation,
            direction=action.direction,
            amount=action.amount,
            url=action.url,
            ms=action.ms,
            decision_rationale=action.reason or '',
            is_task_complete=is_complete,
            sanitized=True,
            raw_pii_received=False,
            privacy={
                'raw_pii_received': False,
                'screenshot_redacted': req.screenshot.redacted,
                'local_redaction_count': req.pii.redaction_count,
                'local_leakage_check_passed': req.pii.leakage_check_passed,
                'viewport_width': req.viewport_width,
                'viewport_height': req.viewport_height,
                'device_pixel_ratio': req.device_pixel_ratio,
            },
            confidence=confidence,
            next_step='request_confirmation_before_execution' if action.requires_human_confirmation else 'execute_locally_then_reobserve',
            trace=trace,
        )

    async def plan_canonical(self, req: AgentRequest) -> PlanResponse:
        # Zero-trust checks run on the canonical payload before any normalization can drop fields.
        assert_masked_token_map(req.masked_token_map)
        assert_sanitized_axtree([item.model_dump(by_alias=True) for item in req.sanitized_axtree])
        assert_sanitized_detections([item.model_dump(by_alias=True) for item in req.detected_ui_elements])
        assert_privacy_request(req.model_dump(by_alias=True), self.settings)
        return await self.plan(req.to_internal())

    async def run(self, req: AgentRunRequest) -> AgentRunResponse:
        response = await self.plan(req)
        return AgentRunResponse(**response.model_dump(), closed_loop=True, requires_reobserve=True)

    def redaction_audit(self, req: RedactionAuditRequest) -> RedactionAuditResponse:
        reasons: list[str] = []
        try:
            image_info = validate_sanitized_image(
                req.screenshot.data_base64,
                req.screenshot.mime_type,
                self.settings.max_image_bytes,
                self.settings.target_image_bytes,
            )
            image_verified = image_info['verified'] or not image_info['present']
        except PrivacyViolation as exc:
            image_info = {'bytes': 0, 'compression_target_met': False}
            image_verified = False
            reasons.append(str(exc))
        metadata_verified = req.screenshot.redacted and not req.pii.raw_values_sent and req.pii.verified_local
        if not metadata_verified:
            reasons.append('Local redaction metadata is not fully verified')
        privacy_invariant = image_verified and metadata_verified
        if not req.pii.leakage_check_passed:
            reasons.append('Leakage check was not marked as passed')
            privacy_invariant = False
        return RedactionAuditResponse(
            valid=privacy_invariant,
            reasons=reasons,
            image_verified=image_verified,
            metadata_verified=metadata_verified,
            privacy_invariant=privacy_invariant,
            image_bytes=image_info['bytes'],
            compression_target_met=image_info['compression_target_met'],
        )

    def get_audit(self) -> list[dict[str, Any]]:
        return self.audit.latest()
