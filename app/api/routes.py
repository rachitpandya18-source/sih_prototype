from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.privacy import PrivacyViolation
from app.models.schemas import (
    ActionValidationRequest,
    ActionValidationResponse,
    AgentRequest,
    AgentRunRequest,
    AgentRunResponse,
    HealthResponse,
    LegacyPlanRequest,
    PlanRequest,
    PlanResponse,
    RedactionAuditRequest,
    RedactionAuditResponse,
)
from app.services.agent import AgentService

router = APIRouter()
_agent_service = AgentService(get_settings())


def service() -> AgentService:
    return _agent_service


def _privacy_error(exc: PrivacyViolation) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            'code': exc.code,
            'message': str(exc),
            'hits': exc.hits,
        },
    )


@router.get('/health', response_model=HealthResponse)
async def health() -> HealthResponse:
    s = get_settings()
    return HealthResponse(
        ok=True,
        service=s.app_name,
        version=s.version,
        planner_mode=s.planner_mode,
        vlm_enabled=s.vlm_enabled,
        privacy_invariant='raw_pii_never_accepted_or_logged',
    )


@router.get('/api/v1/config')
async def config():
    s = get_settings()
    return {
        'api_version': 'v1',
        'planner_mode': s.planner_mode,
        'vlm_enabled': s.vlm_enabled,
        'supports': ['plan_action', 'agent_run', 'action_validate', 'redaction_audit'],
        'action_types': ['CLICK', 'TYPE', 'SELECT', 'SCROLL', 'WAIT', 'NAVIGATE', 'FINISH', 'REQUEST_CONFIRMATION'],
        'privacy': {
            'raw_pii_allowed': False,
            'raw_type_values_allowed': False,
            'screenshot_must_be_redacted': True,
            'pii_rejection_code': 'PII_LEAKAGE_REJECTED',
        },
        'image_limits': {
            'target_bytes': s.target_image_bytes,
            'hard_max_bytes': s.max_image_bytes,
        },
    }


async def _plan(req: PlanRequest) -> PlanResponse:
    try:
        return await service().plan(req)
    except PrivacyViolation as exc:
        raise _privacy_error(exc) from exc


@router.post('/api/v1/plan_action', response_model=PlanResponse)
async def plan_action(req: AgentRequest) -> PlanResponse:
    try:
        return await service().plan_canonical(req)
    except PrivacyViolation as exc:
        raise _privacy_error(exc) from exc


@router.post('/api/v1/plan', response_model=PlanResponse)
async def plan(req: PlanRequest) -> PlanResponse:
    return await _plan(req)


@router.post('/plan', response_model=PlanResponse)
async def legacy_plan(req: LegacyPlanRequest) -> PlanResponse:
    try:
        normalized = PlanRequest(
            instruction=req.instruction,
            page=req.page,
            screenshot=req.screenshot,
            pii=req.pii,
            perception=req.perception,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail={'code': 'invalid_payload', 'message': str(exc)}) from exc
    return await _plan(normalized)


@router.post('/api/v1/agent/run', response_model=AgentRunResponse)
async def agent_run(req: AgentRunRequest) -> AgentRunResponse:
    try:
        return await service().run(req)
    except PrivacyViolation as exc:
        raise _privacy_error(exc) from exc


@router.post('/api/v1/action/validate', response_model=ActionValidationResponse)
async def action_validate(req: ActionValidationRequest) -> ActionValidationResponse:
    from app.services.action_validator import validate_action

    return validate_action(req.action, req.page)


@router.post('/api/v1/redaction/audit', response_model=RedactionAuditResponse)
async def redaction_audit(req: RedactionAuditRequest) -> RedactionAuditResponse:
    return service().redaction_audit(req)


@router.get('/api/v1/audit')
async def audit():
    items = service().get_audit()
    return {'count': len(items), 'items': items}
