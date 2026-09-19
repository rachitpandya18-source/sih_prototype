/**
 * NETRA DOM & AXTree Observation Engine
 *
 * Scans the active page or sandbox container to produce a clean, sanitized
 * Accessibility Tree (AXTree) and UI Element Detections conforming strictly to
 * shared_action_schema.json and app/models/schemas.py.
 */

import { detectPII } from './privacy.js';

/**
 * Scan target container (or document) and extract sanitized AXTree & detections.
 *
 * @param {HTMLElement|null} container - Root element to observe (defaults to sandbox or document.body)
 * @param {import('./privacy').TokenVault} tokenVault - Local vault for masking sensitive input values
 * @returns {{ sanitized_axtree: Array, detected_ui_elements: Array }}
 */
export function extractPagePerception(container = null, tokenVault = null) {
  const root = container || document.querySelector('#netra-sandbox-target') || document.body;
  if (!root) {
    return { sanitized_axtree: [], detected_ui_elements: [] };
  }

  // Find all interactive or semantic elements
  const candidates = root.querySelectorAll(
    'button, a, input, select, textarea, [role="button"], [role="link"], [role="textbox"], [data-netra-id]'
  );

  const axtree = [];
  const detections = [];
  let counter = 1;

  for (const el of candidates) {
    // Check visibility
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 && rect.height <= 0) continue;

    const computedStyle = window.getComputedStyle(el);
    if (computedStyle.display === 'none' || computedStyle.visibility === 'hidden') continue;

    const id = el.getAttribute('data-netra-id') || el.id || `elem_${counter++}`;
    const tagName = el.tagName.toLowerCase();

    // Determine semantic role
    let role = el.getAttribute('role');
    if (!role) {
      if (tagName === 'button') role = 'button';
      else if (tagName === 'a') role = 'link';
      else if (tagName === 'input') {
        const type = (el.type || 'text').toLowerCase();
        if (['button', 'submit', 'reset'].includes(type)) role = 'button';
        else if (['checkbox', 'radio'].includes(type)) role = type;
        else role = 'textbox';
      } else if (tagName === 'select') role = 'combobox';
      else if (tagName === 'textarea') role = 'textbox';
      else role = 'generic';
    }

    // Determine accessible name/label
    const labelEl = el.id ? root.querySelector(`label[for="${el.id}"]`) : null;
    let name = el.getAttribute('aria-label') ||
      el.getAttribute('title') ||
      el.getAttribute('placeholder') ||
      labelEl?.textContent?.trim() ||
      (tagName !== 'input' ? el.textContent?.trim() : '') ||
      el.getAttribute('name') ||
      '';

    // Sanitize label name if it contains sensitive patterns
    if (detectPII(name).length > 0) {
      name = '[REDACTED_LABEL]';
    }

    // Determine value (safely sanitized with token vault)
    let value = undefined;
    if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {
      const rawVal = el.value || '';
      if (rawVal) {
        // If raw value matches PII, tokenize or mask it
        const findings = detectPII(rawVal);
        if (findings.length > 0 && tokenVault) {
          const first = findings[0];
          value = tokenVault.store(first.type, first.value);
        } else if (rawVal.startsWith('[') && rawVal.endsWith(']')) {
          value = rawVal;
        } else if (tokenVault && tokenVault.size > 0) {
          // Check if it matches any stored value
          let matchedToken = null;
          for (const [tok] of tokenVault._store) {
            if (tokenVault.resolve(tok) === rawVal) {
              matchedToken = tok;
              break;
            }
          }
          value = matchedToken || undefined;
        }
      }
    }

    const bbox = [
      Math.round(rect.left),
      Math.round(rect.top),
      Math.round(rect.right),
      Math.round(rect.bottom),
    ];

    axtree.push({
      id,
      role,
      name: name.slice(0, 500),
      text: (el.textContent || '').trim().slice(0, 500),
      ...(value ? { value } : {}),
      bbox,
      disabled: !!el.disabled,
      visible: true,
    });

    detections.push({
      class: role === 'button' ? 'button' : role === 'link' ? 'link' : 'input',
      bbox,
      confidence: 0.95,
      id,
    });
  }

  return { sanitized_axtree: axtree, detected_ui_elements: detections };
}
