from __future__ import annotations

import base64
import binascii
import hashlib
import io
import re
from typing import Any, Iterable

from PIL import Image

from app.core.config import Settings


EMAIL_RE = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I)
PHONE_RE = re.compile(r'(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)')
CARD_RE = re.compile(r'(?<!\d)(?:\d[ -]?){13,19}(?!\d)')
AADHAAR_RE = re.compile(r'(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)')
PAN_RE = re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b', re.I)
UPI_RE = re.compile(r'\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b')
IFSC_RE = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', re.I)
SECRET_KEY_RE = re.compile(r'(api[_ -]?key|access[_ -]?token|password|secret)\s*[:=]\s*[^\s,]+', re.I)
MASKED_TOKEN_RE = re.compile(r'^\[[A-Z][A-Z0-9_-]{1,63}\]$')


class PrivacyViolation(ValueError):
    code = 'PII_LEAKAGE_REJECTED'

    def __init__(self, message: str, hits: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.hits = hits or []


def _strings(obj: Any, path: str = '') -> Iterable[tuple[str, str]]:
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f'{path}.{k}')
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _strings(v, f'{path}[{i}]')


def classify_sensitive(value: str) -> list[str]:
    hits: list[str] = []
    if EMAIL_RE.search(value):
        hits.append('email')
    if PHONE_RE.search(value):
        hits.append('phone')
    if AADHAAR_RE.search(value):
        hits.append('aadhaar_like')
    if PAN_RE.search(value):
        hits.append('pan_like')
    if UPI_RE.search(value):
        hits.append('upi_like')
    if IFSC_RE.search(value):
        hits.append('ifsc_like')
    if CARD_RE.search(value):
        hits.append('card_like')
    if SECRET_KEY_RE.search(value):
        hits.append('secret_like')
    return hits


def find_sensitive_literals(obj: Any, *, include_instruction: bool = False) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for path, value in _strings(obj):
        if not include_instruction and (path.endswith('.instruction') or path == 'instruction'):
            continue
        for kind in classify_sensitive(value):
            hits.append({'path': path, 'kind': kind})
    unique = {(x['path'], x['kind']): x for x in hits}
    return list(unique.values())


def assert_privacy_request(payload: Any, settings: Settings) -> None:
    if not settings.privacy_strict:
        return

    hits = find_sensitive_literals(payload, include_instruction=True)
    if hits:
        raise PrivacyViolation(
            'PII or secret-like literal detected in sanitized request. Send masked tokens and sanitized context only.',
            hits,
        )


def assert_masked_token_map(token_map: dict[str, str]) -> None:
    bad: list[dict[str, str]] = []
    for token, label in token_map.items():
        if not MASKED_TOKEN_RE.fullmatch(token):
            bad.append({'path': token, 'kind': 'invalid_masked_token'})
        kinds = classify_sensitive(label)
        if kinds:
            bad.append({'path': token, 'kind': f'raw_{kinds[0]}_in_token_map'})
    if bad:
        raise PrivacyViolation('masked_token_map contains unsafe or raw values', bad)


def assert_sanitized_axtree(axtree: list[dict[str, Any]]) -> None:
    hits: list[dict[str, str]] = []
    for idx, node in enumerate(axtree):
        for field in ('id', 'elem_id', 'ref', 'role', 'name', 'text', 'value'):
            value = node.get(field)
            if not isinstance(value, str) or not value:
                continue
            # IDs can be arbitrary DOM ids; only reject if they actually match a sensitive literal.
            for kind in classify_sensitive(value):
                hits.append({'path': f'sanitized_axtree[{idx}].{field}', 'kind': kind})
    if hits:
        raise PrivacyViolation('PII leakage detected in sanitized_axtree', hits)


def assert_sanitized_detections(detections: list[dict[str, Any]]) -> None:
    hits: list[dict[str, str]] = []
    for idx, det in enumerate(detections):
        for field in ('class', 'element_class', 'label', 'id', 'element_id', 'ref'):
            value = det.get(field)
            if not isinstance(value, str) or not value:
                continue
            for kind in classify_sensitive(value):
                hits.append({'path': f'detected_ui_elements[{idx}].{field}', 'kind': kind})
    if hits:
        raise PrivacyViolation('PII leakage detected in detected_ui_elements', hits)


def decode_image_data(encoded: str | None) -> tuple[bytes, str | None]:
    if not encoded:
        return b'', None
    if encoded.startswith('data:'):
        header, _, body = encoded.partition(',')
        mime = header[5:].split(';', 1)[0]
        encoded = body
    else:
        mime = None
    try:
        return base64.b64decode(encoded, validate=True), mime
    except (ValueError, binascii.Error) as exc:
        raise PrivacyViolation('Screenshot payload is not valid base64') from exc


def validate_sanitized_image(data_base64: str | None, mime_type: str, max_bytes: int, target_bytes: int) -> dict[str, Any]:
    if not data_base64:
        return {
            'present': False,
            'verified': False,
            'width': None,
            'height': None,
            'bytes': 0,
            'sha256': None,
            'compression_target_met': True,
            'mime_type': mime_type,
        }

    raw, data_mime = decode_image_data(data_base64)
    if len(raw) > max_bytes:
        raise PrivacyViolation(f'Screenshot exceeds the {max_bytes} byte hard limit')
    effective_mime = data_mime or mime_type
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.verify()
        with Image.open(io.BytesIO(raw)) as img:
            width, height = img.size
    except Exception as exc:
        raise PrivacyViolation('Sanitized screenshot is not a valid image') from exc
    digest = hashlib.sha256(raw).hexdigest()
    return {
        'present': True,
        'verified': True,
        'width': width,
        'height': height,
        'bytes': len(raw),
        'sha256': digest,
        'compression_target_met': len(raw) <= target_bytes,
        'mime_type': effective_mime,
    }
