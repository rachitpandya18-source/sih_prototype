from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class ActionType(str, Enum):
    click = 'click'
    type = 'type'
    select = 'select'
    scroll = 'scroll'
    wait = 'wait'
    navigate = 'navigate'
    finish = 'finish'
    request_confirmation = 'request_confirmation'
    no_op = 'no_op'


class Rect(BaseModel):
    model_config = ConfigDict(extra='ignore')
    x: float
    y: float
    width: float
    height: float


class PageNode(BaseModel):
    model_config = ConfigDict(extra='ignore')
    ref: str = Field(min_length=1, max_length=128)
    role: Optional[str] = Field(default=None, max_length=64)
    name: str = Field(default='', max_length=500)
    text: str = Field(default='', max_length=500)
    rect: Rect
    disabled: bool = False
    visible: bool = True


class PageSnapshot(BaseModel):
    model_config = ConfigDict(extra='ignore')
    url: str = Field(default='', max_length=2048)
    title: str = Field(default='', max_length=500)
    nodes: List[PageNode] = Field(default_factory=list, max_length=3000)


class SanitizedScreenshot(BaseModel):
    model_config = ConfigDict(extra='ignore')
    redacted: Literal[True]
    mime_type: Literal['image/png', 'image/jpeg', 'image/webp'] = 'image/webp'
    data_base64: Optional[str] = None
    width: Optional[int] = Field(default=None, ge=1, le=10000)
    height: Optional[int] = Field(default=None, ge=1, le=10000)
    sha256: Optional[str] = Field(default=None, min_length=64, max_length=64)


class RedactionBox(BaseModel):
    model_config = ConfigDict(extra='ignore')
    entity_type: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0, le=1)
    box: Rect


class PrivacySummary(BaseModel):
    model_config = ConfigDict(extra='ignore')
    redaction_count: int = Field(default=0, ge=0)
    findings: List[RedactionBox] = Field(default_factory=list, max_length=1000)
    raw_values_sent: bool = False
    verified_local: bool = False
    leakage_check_passed: bool = False

    @field_validator('raw_values_sent')
    @classmethod
    def raw_values_must_be_false(cls, v: bool) -> bool:
        if v:
            raise ValueError('raw_values_sent must be false for NETRA privacy invariant')
        return v


class Detection(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    label: str = Field(min_length=1, max_length=128)
    confidence: float = Field(ge=0, le=1)
    box: Optional[Rect] = None
    ref: Optional[str] = None


class Perception(BaseModel):
    model_config = ConfigDict(extra='ignore')
    ui_detections: List[Detection] = Field(default_factory=list, max_length=2000)
    ocr_text_redacted: List[str] = Field(default_factory=list, max_length=2000)
    source: str = 'local'
    model: Optional[str] = None


class Action(BaseModel):
    model_config = ConfigDict(extra='ignore')
    type: ActionType
    ref: Optional[str] = None
    value: Optional[str] = None
    value_ref: Optional[str] = None
    direction: Optional[Literal['up', 'down', 'left', 'right']] = None
    amount: Optional[float] = Field(default=None, ge=0, le=100000)
    url: Optional[str] = None
    ms: Optional[int] = Field(default=None, ge=0, le=30000)
    reason: Optional[str] = Field(default=None, max_length=500)
    confidence: float = Field(default=0.8, ge=0, le=1)
    requires_human_confirmation: bool = False

    @field_validator('value')
    @classmethod
    def no_raw_value(cls, v: str | None) -> str | None:
        # Raw TYPE payloads must never be returned. Token placeholders are allowed.
        if v is None:
            return None
        if v.startswith('[') and v.endswith(']'):
            return v
        raise ValueError('Raw values are not permitted; use a masked token/value_ref')


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')
    instruction: str = Field(min_length=1, max_length=1000)
    page: PageSnapshot
    screenshot: SanitizedScreenshot
    pii: PrivacySummary
    perception: Perception = Field(default_factory=Perception)
    session_id: Optional[str] = Field(default=None, max_length=128)
    request_id: Optional[str] = Field(default=None, max_length=128)
    step_number: int = Field(default=1, ge=1, le=100000)
    masked_token_map: Dict[str, str] = Field(default_factory=dict, max_length=100)
    history: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    viewport_width: int = Field(default=1280, ge=320, le=10000)
    viewport_height: int = Field(default=720, ge=240, le=10000)
    device_pixel_ratio: float = Field(default=1.0, ge=0.1, le=8.0)


class LegacyPlanRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')
    instruction: str = Field(min_length=1, max_length=1000)
    page: Dict[str, Any]
    screenshot: Dict[str, Any]
    pii: Dict[str, Any]
    perception: Dict[str, Any] = Field(default_factory=dict)


class AXTreeElement(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    id: str = Field(validation_alias=AliasChoices('id', 'elem_id', 'ref'), serialization_alias='id', min_length=1, max_length=128)
    role: str = Field(default='generic', max_length=64)
    name: str = Field(default='', max_length=500)
    value: Optional[str] = Field(default=None, max_length=500)
    text: str = Field(default='', max_length=500)
    bbox: List[float] = Field(min_length=4, max_length=4)
    disabled: bool = False
    visible: bool = True

    @field_validator('bbox')
    @classmethod
    def bbox_numbers(cls, v: List[float]) -> List[float]:
        if len(v) != 4:
            raise ValueError('bbox must contain [x1, y1, x2, y2]')
        return [float(x) for x in v]


class UIElementDetection(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    element_class: str = Field(validation_alias=AliasChoices('class', 'element_class', 'label'), serialization_alias='class', min_length=1, max_length=128)
    bbox: List[float] = Field(min_length=4, max_length=4)
    confidence: float = Field(ge=0, le=1)
    element_id: Optional[str] = Field(default=None, validation_alias=AliasChoices('id', 'element_id', 'ref'), serialization_alias='id')

    @field_validator('bbox')
    @classmethod
    def bbox_numbers(cls, v: List[float]) -> List[float]:
        if len(v) != 4:
            raise ValueError('bbox must contain [x1, y1, x2, y2]')
        return [float(x) for x in v]


class HistoryItem(BaseModel):
    model_config = ConfigDict(extra='ignore')
    action: str = Field(min_length=1, max_length=64)
    target_id: Optional[str] = Field(default=None, max_length=128)
    status: str = Field(default='UNKNOWN', max_length=32)
    step_number: Optional[int] = Field(default=None, ge=1, le=100000)


class AgentRequest(BaseModel):
    """Canonical frontend contract. Supports both the SIH handoff fields and sensible aliases."""
    model_config = ConfigDict(extra='ignore', populate_by_name=True)

    session_id: str = Field(default='sess_unassigned', min_length=1, max_length=128)
    step_number: int = Field(default=1, ge=1, le=100000)
    task_instruction: str = Field(
        validation_alias=AliasChoices('task_instruction', 'instruction'),
        serialization_alias='task_instruction',
        min_length=1,
        max_length=1000,
    )
    sanitized_screenshot_base64: Optional[str] = Field(default=None, max_length=12_000_000)
    sanitized_screenshot_mime_type: Optional[Literal['image/png', 'image/jpeg', 'image/webp']] = None
    sanitized_axtree: List[AXTreeElement] = Field(default_factory=list, max_length=3000)
    detected_ui_elements: List[UIElementDetection] = Field(default_factory=list, max_length=2000)
    masked_token_map: Dict[str, str] = Field(default_factory=dict, max_length=100)
    history: List[HistoryItem] = Field(default_factory=list, max_length=100)
    current_url: str = Field(default='', max_length=2048)
    page_title: str = Field(default='', max_length=500)
    screenshot_sha256: Optional[str] = Field(default=None, min_length=64, max_length=64)
    execute_locally: bool = False
    viewport_width: int = Field(default=1280, ge=320, le=10000)
    viewport_height: int = Field(default=720, ge=240, le=10000)
    device_pixel_ratio: float = Field(default=1.0, ge=0.1, le=8.0)

    @field_validator('masked_token_map')
    @classmethod
    def token_keys_must_be_masked(cls, value: Dict[str, str]) -> Dict[str, str]:
        import re

        token_re = re.compile(r'^\[[A-Z][A-Z0-9_-]{1,63}\]$')
        for token, label in value.items():
            if not token_re.fullmatch(token):
                raise ValueError(f'Invalid masked token key: {token!r}')
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9 _-]{0,63}', label or ''):
                raise ValueError(f'Invalid masked token label for {token!r}')
        return value

    def to_internal(self) -> PlanRequest:
        nodes: list[PageNode] = []
        for item in self.sanitized_axtree:
            x1, y1, x2, y2 = item.bbox
            nodes.append(
                PageNode(
                    ref=item.id,
                    role=item.role,
                    name=item.name,
                    text=item.text,
                    rect=Rect(x=x1, y=y1, width=max(0.0, x2 - x1), height=max(0.0, y2 - y1)),
                    disabled=item.disabled,
                    visible=item.visible,
                )
            )

        detections = [
            Detection(
                label=d.element_class,
                confidence=d.confidence,
                ref=d.element_id,
                box=(Rect(x=d.bbox[0], y=d.bbox[1], width=max(0.0, d.bbox[2] - d.bbox[0]), height=max(0.0, d.bbox[3] - d.bbox[1]))),
            )
            for d in self.detected_ui_elements
        ]

        mime = self.sanitized_screenshot_mime_type or 'image/webp'
        encoded = self.sanitized_screenshot_base64
        if encoded and encoded.startswith('data:'):
            header, _, body = encoded.partition(',')
            if header.startswith('data:'):
                guessed = header[5:].split(';', 1)[0]
                if guessed in {'image/png', 'image/jpeg', 'image/webp'}:
                    mime = guessed
                encoded = body

        screenshot = SanitizedScreenshot(
            redacted=True,
            mime_type=mime,
            data_base64=encoded,
            sha256=self.screenshot_sha256,
        )
        pii = PrivacySummary(
            redaction_count=0,
            findings=[],
            raw_values_sent=False,
            verified_local=True,
            leakage_check_passed=True,
        )
        perception = Perception(
            ui_detections=detections,
            ocr_text_redacted=[],
            source='local',
            model='browser-local-perception',
        )
        history = [item.model_dump() for item in self.history]
        return PlanRequest(
            instruction=self.task_instruction,
            page=PageSnapshot(url=self.current_url, title=self.page_title, nodes=nodes),
            screenshot=screenshot,
            pii=pii,
            perception=perception,
            session_id=self.session_id,
            step_number=self.step_number,
            masked_token_map=self.masked_token_map,
            history=history,
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
            device_pixel_ratio=self.device_pixel_ratio,
        )


class CanonicalActionResponse(BaseModel):
    action_type: str
    target_id: Optional[str] = None
    target_bbox: Optional[List[float]] = None
    target_coords: Optional[Dict[str, float]] = None
    value: Optional[str] = None
    value_ref: Optional[str] = None
    direction: Optional[str] = None
    amount: Optional[float] = None
    url: Optional[str] = None
    ms: Optional[int] = None
    requires_human_confirmation: bool = False
    decision_rationale: str = ''
    is_task_complete: bool = False
    confidence: float = 0.0


class PlanResponse(BaseModel):
    ok: bool
    request_id: str
    session_id: str
    step_number: int = 1
    planner: str
    fallback_used: bool
    action: Action
    # Canonical frontend fields kept top-level to make the handoff unambiguous.
    action_type: str
    target_id: Optional[str] = None
    target_bbox: Optional[List[float]] = None
    target_coords: Optional[Dict[str, float]] = None
    value: Optional[str] = None
    value_ref: Optional[str] = None
    requires_human_confirmation: bool = False
    direction: Optional[str] = None
    amount: Optional[float] = None
    url: Optional[str] = None
    ms: Optional[int] = None
    decision_rationale: str = ''
    is_task_complete: bool = False
    sanitized: bool = True
    raw_pii_received: bool = False
    privacy: Dict[str, Any]
    confidence: float
    next_step: str
    trace: List[Dict[str, Any]] = Field(default_factory=list)


class AgentRunRequest(PlanRequest):
    execute_locally: bool = False


class AgentRunResponse(PlanResponse):
    closed_loop: bool = True
    requires_reobserve: bool = True


class ActionValidationRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')
    action: Action
    page: PageSnapshot


class ActionValidationResponse(BaseModel):
    valid: bool
    reasons: List[str] = Field(default_factory=list)
    normalized_action: Optional[Action] = None
    requires_human_confirmation: bool = False
    risk_level: Literal['low', 'medium', 'high'] = 'low'


class RedactionAuditRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')
    screenshot: SanitizedScreenshot
    pii: PrivacySummary
    perception: Perception = Field(default_factory=Perception)


class RedactionAuditResponse(BaseModel):
    valid: bool
    reasons: List[str]
    image_verified: bool
    metadata_verified: bool
    privacy_invariant: bool
    image_bytes: int = 0
    compression_target_met: bool = True


class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str
    planner_mode: str
    vlm_enabled: bool
    privacy_invariant: str
