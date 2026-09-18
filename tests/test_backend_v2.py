import base64
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def tiny_webp_b64():
    buf = io.BytesIO()
    Image.new('RGB', (32, 32), 'white').save(buf, format='WEBP', quality=55)
    return base64.b64encode(buf.getvalue()).decode()


def canonical_payload():
    return {
        'session_id': 'sess_12345',
        'step_number': 1,
        'task_instruction': 'Find the Learn more link',
        'sanitized_screenshot_base64': tiny_webp_b64(),
        'sanitized_screenshot_mime_type': 'image/webp',
        'current_url': 'https://example.com/',
        'page_title': 'Example Domain',
        'sanitized_axtree': [
            {
                'id': 'elem_1',
                'role': 'textbox',
                'name': 'Full Name',
                'value': '[NAME_1]',
                'bbox': [120, 240, 300, 280],
            },
            {
                'id': 'elem_2',
                'role': 'button',
                'name': 'Create Account',
                'bbox': [120, 500, 220, 540],
            },
            {
                'id': 'elem_3',
                'role': 'link',
                'name': 'Learn more',
                'bbox': [30, 210, 122, 232],
            },
        ],
        'detected_ui_elements': [
            {'class': 'input', 'bbox': [120, 240, 300, 280], 'confidence': 0.92, 'id': 'elem_1'},
            {'class': 'button', 'bbox': [120, 500, 220, 540], 'confidence': 0.95, 'id': 'elem_2'},
        ],
        'masked_token_map': {
            '[NAME_1]': 'NAME',
            '[EMAIL_1]': 'EMAIL',
        },
        'history': [
            {'action': 'CLICK', 'target_id': 'elem_0', 'status': 'SUCCESS'}
        ],
    }


def test_canonical_plan_action():
    response = client.post('/api/v1/plan_action', json=canonical_payload())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['action_type'] == 'CLICK'
    assert data['target_id'] == 'elem_3'
    assert data['target_bbox'] == [30.0, 210.0, 122.0, 232.0]
    assert data['requires_human_confirmation'] is False
    assert data['raw_pii_received'] is False


def test_raw_email_in_axtree_is_rejected_with_contract_code():
    body = canonical_payload()
    body['sanitized_axtree'][0]['value'] = 'person@example.com'
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 422
    detail = response.json()['detail']
    assert detail['code'] == 'PII_LEAKAGE_REJECTED'


def test_raw_aadhaar_in_axtree_is_rejected():
    body = canonical_payload()
    body['sanitized_axtree'][0]['value'] = '1234 5678 9012'
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'PII_LEAKAGE_REJECTED'


def test_masked_type_value_is_allowed_but_raw_value_is_not_returned():
    body = canonical_payload()
    body['task_instruction'] = 'Fill the full name field'
    body['sanitized_axtree'] = [body['sanitized_axtree'][0]]
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['action_type'] == 'TYPE'
    assert data['value'] == '[NAME_1]'
    assert data['value_ref'] == 'LOCAL_USER_VALUE'


def test_sensitive_button_requires_human_confirmation():
    body = canonical_payload()
    body['task_instruction'] = 'Click Pay Now'
    body['sanitized_axtree'] = [
        {
            'id': 'pay1',
            'role': 'button',
            'name': 'Pay Now',
            'bbox': [100, 100, 200, 140],
        }
    ]
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 200
    data = response.json()
    assert data['action_type'] == 'CLICK'
    assert data['requires_human_confirmation'] is True
    assert data['next_step'] == 'request_confirmation_before_execution'


def test_cross_origin_navigation_is_blocked():
    body = canonical_payload()
    body['task_instruction'] = 'go to https://evil.example/'
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 200
    data = response.json()
    assert data['action_type'] == 'NO_OP'
    assert data['fallback_used'] is True


def test_config_exposes_contract():
    response = client.get('/api/v1/config')
    assert response.status_code == 200
    data = response.json()
    assert 'SELECT' in data['action_types']
    assert data['privacy']['pii_rejection_code'] == 'PII_LEAKAGE_REJECTED'
    assert data['image_limits']['target_bytes'] <= 307200


def test_qwen_timeout_falls_back_in_hybrid_mode(monkeypatch):
    from app.api.routes import service
    from app.services.vlm_planner import VLMPlannerError

    original = service().settings
    original_enabled = original.vlm_enabled
    original_mode = original.planner_mode
    original_fallback = original.allow_fallback
    original.vlm_enabled = True
    original.planner_mode = 'hybrid'
    original.allow_fallback = True

    async def fail_vlm(*args, **kwargs):
        raise VLMPlannerError('simulated 2.5s timeout')

    monkeypatch.setattr(service().vlm, 'plan', fail_vlm)
    try:
        response = client.post('/api/v1/plan_action', json=canonical_payload())
        assert response.status_code == 200
        data = response.json()
        assert data['fallback_used'] is True
        assert data['planner'] in {'deterministic', 'deterministic-perception'}
    finally:
        original.vlm_enabled = original_enabled
        original.planner_mode = original_mode
        original.allow_fallback = original_fallback


def test_completion_after_successful_previous_step():
    body = canonical_payload()
    body['step_number'] = 2
    body['history'] = [{'action': 'CLICK', 'target_id': 'elem_3', 'status': 'SUCCESS'}]
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 200
    data = response.json()
    assert data['action_type'] == 'FINISH'
    assert data['is_task_complete'] is True



def test_upi_and_ifsc_are_rejected_as_sensitive_literals():
    body = canonical_payload()
    body['sanitized_axtree'][0]['value'] = 'rudresh@okaxis'
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'PII_LEAKAGE_REJECTED'

    body = canonical_payload()
    body['sanitized_axtree'][0]['value'] = 'HDFC0ABC123'
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'PII_LEAKAGE_REJECTED'


def test_viewport_and_dpr_are_preserved_in_trace():
    body = canonical_payload()
    body['viewport_width'] = 1440
    body['viewport_height'] = 900
    body['device_pixel_ratio'] = 2
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 200
    trace_context = next(x for x in response.json()['trace'] if x['stage'] == 'context')
    assert trace_context['viewport_width'] == 1440
    assert trace_context['viewport_height'] == 900
    assert trace_context['device_pixel_ratio'] == 2


def test_type_action_uses_exact_token_from_map():
    body = canonical_payload()
    body['task_instruction'] = 'Fill the full name field'
    body['sanitized_axtree'] = [body['sanitized_axtree'][0]]
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 200
    data = response.json()
    assert data['action_type'] == 'TYPE'
    assert data['value'] == '[NAME_1]'
    assert data['value_ref'] == 'LOCAL_USER_VALUE'


def test_repeated_action_guard_converts_to_wait():
    body = canonical_payload()
    body['history'] = [
        {'action': 'CLICK', 'target_id': 'elem_3', 'status': 'SUCCESS', 'step_number': 1},
        {'action': 'CLICK', 'target_id': 'elem_3', 'status': 'SUCCESS', 'step_number': 2},
    ]
    response = client.post('/api/v1/plan_action', json=body)
    assert response.status_code == 200
    data = response.json()
    assert data['action_type'] == 'WAIT'
    assert data['ms'] == 750
    assert any(item.get('mode') == 'two_step_repetition' for item in data['trace'])


def test_vlm_unknown_token_is_programmatically_blocked(monkeypatch):
    from app.api.routes import service

    svc = service()
    original_enabled = svc.settings.vlm_enabled
    original_mode = svc.settings.planner_mode

    async def fake_vlm(*args, **kwargs):
        from app.models.schemas import Action, ActionType
        return Action(type=ActionType.type, ref='elem_1', value='[FAKE_1]', value_ref='LOCAL_USER_VALUE', confidence=0.99), 'qwen-vl'

    monkeypatch.setattr(svc.vlm, 'plan', fake_vlm)
    svc.settings.vlm_enabled = True
    svc.settings.planner_mode = 'vlm'
    try:
        response = client.post('/api/v1/plan_action', json=canonical_payload())
        assert response.status_code == 200
        data = response.json()
        assert data['action_type'] == 'REQUEST_CONFIRMATION'
        assert data['requires_human_confirmation'] is True
    finally:
        svc.settings.vlm_enabled = original_enabled
        svc.settings.planner_mode = original_mode



def test_action_validator_overrides_vlm_false_for_confirmation():
    from app.models.schemas import Action, ActionType, PageSnapshot, PageNode, Rect
    from app.services.action_validator import validate_action

    page = PageSnapshot(nodes=[
        PageNode(
            ref='pay1',
            role='button',
            name='Pay Now',
            text='',
            rect=Rect(x=10, y=10, width=100, height=40),
        )
    ])
    action = Action(type=ActionType.click, ref='pay1', requires_human_confirmation=False)
    result = validate_action(action, page, {})
    assert result.requires_human_confirmation is True
    assert result.normalized_action is not None
    assert result.normalized_action.requires_human_confirmation is True
