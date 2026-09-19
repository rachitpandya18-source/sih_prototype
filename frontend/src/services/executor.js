/**
 * NETRA Browser Action Executor
 *
 * Executes actions returned by the backend locally in the browser.
 * Works seamlessly in both:
 * 1. React Dashboard Interactive Sandbox (visual highlighting & execution)
 * 2. Chrome/Edge Extension Content Script (direct DOM automation)
 */

/**
 * Execute an action returned by the backend.
 *
 * @param {Object} action - The action from PlanResponse
 * @param {Object} options - Execution options
 * @param {import('./privacy').TokenVault} options.tokenVault - For resolving masked tokens
 * @returns {Promise<{success: boolean, error?: string, message?: string}>}
 */
export async function executeAction(action, { tokenVault } = {}) {
  const { action_type, target_id, value, value_ref, direction, amount, url, ms } = action;

  switch (action_type) {
    case 'CLICK':
      return executeClick(target_id, action.target_coords);

    case 'TYPE':
      return executeType(target_id, value, value_ref, tokenVault);

    case 'SELECT':
      return executeSelect(target_id, value);

    case 'SCROLL':
      return executeScroll(direction, amount);

    case 'WAIT':
      return executeWait(ms);

    case 'NAVIGATE':
      return executeNavigate(url);

    case 'FINISH':
      return { success: true, message: 'Task completed successfully by NETRA' };

    case 'REQUEST_CONFIRMATION':
      return { success: true, message: 'Action paused pending user confirmation' };

    case 'NO_OP':
      return { success: true, message: 'No safe action taken' };

    default:
      return { success: false, error: `Unknown action type: ${action_type}` };
  }
}

/**
 * Execute CLICK with visual pulse and click dispatch.
 */
function executeClick(targetId, coords) {
  const el = resolveElement(targetId);
  if (el) {
    highlightElement(el);
    el.click();
    return { success: true, message: `Clicked element [${targetId}]` };
  }

  // Fallback to coordinates
  if (coords) {
    const cssX = coords.x / (window.devicePixelRatio || 1);
    const cssY = coords.y / (window.devicePixelRatio || 1);
    const el2 = document.elementFromPoint(cssX, cssY);
    if (el2) {
      highlightElement(el2);
      el2.click();
      return { success: true, message: `Clicked at coordinates (${coords.x}, ${coords.y})` };
    }
  }

  return { success: true, message: `Simulated CLICK on [${targetId || 'target'}]` };
}

/**
 * Execute TYPE using local Token Vault resolution (Zero-Trust).
 */
function executeType(targetId, maskedValue, valueRef, tokenVault) {
  if (valueRef !== 'LOCAL_USER_VALUE') {
    return { success: false, error: 'Security violation: value_ref must be LOCAL_USER_VALUE' };
  }

  if (!maskedValue || !tokenVault) {
    return { success: false, error: 'Missing token vault or masked token key' };
  }

  const realValue = tokenVault.resolve(maskedValue);
  if (!realValue) {
    return { success: false, error: `Token [${maskedValue}] not found in local vault` };
  }

  const el = resolveElement(targetId);
  if (el) {
    highlightElement(el);
    el.focus();
    el.value = realValue;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return {
      success: true,
      message: `Resolved ${maskedValue} on-device → typed into [${targetId}]`,
    };
  }

  return {
    success: true,
    message: `Resolved ${maskedValue} on-device → simulated TYPE into [${targetId}]`,
  };
}

/**
 * Execute SELECT option.
 */
function executeSelect(targetId, value) {
  const el = resolveElement(targetId);
  if (el && el.tagName === 'SELECT') {
    highlightElement(el);
    el.value = value;
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return { success: true, message: `Selected "${value}" in [${targetId}]` };
  }

  return { success: true, message: `Simulated SELECT "${value}" on [${targetId}]` };
}

/**
 * Execute SCROLL.
 */
function executeScroll(direction, amount) {
  const scrollAmount = amount || 300;
  const scrollMap = {
    up: [0, -scrollAmount],
    down: [0, scrollAmount],
    left: [-scrollAmount, 0],
    right: [scrollAmount, 0],
  };
  const [x, y] = scrollMap[direction] || [0, 0];

  const targetBox = document.querySelector('#netra-sandbox-target') || window;
  targetBox.scrollBy({ left: x, top: y, behavior: 'smooth' });

  return { success: true, message: `Scrolled ${direction} by ${scrollAmount}px` };
}

/**
 * Execute WAIT.
 */
async function executeWait(ms) {
  const duration = ms || 1000;
  await new Promise(resolve => setTimeout(resolve, duration));
  return { success: true, message: `Waited ${duration}ms for DOM update` };
}

/**
 * Execute NAVIGATE.
 */
function executeNavigate(url) {
  if (isExtensionContext()) {
    window.location.href = url;
    return { success: true, message: `Navigated to ${url}` };
  }
  return { success: true, message: `Simulated NAVIGATE to ${url}` };
}

/**
 * Resolve target_id against DOM or sandbox elements.
 */
function resolveElement(targetId) {
  if (!targetId) return null;
  return (
    document.querySelector(`[data-netra-id="${targetId}"]`) ||
    document.getElementById(targetId) ||
    document.querySelector(`[name="${targetId}"]`) ||
    document.querySelector(`[aria-label="${targetId}"]`)
  );
}

/**
 * Visual highlight pulse on interacted elements.
 */
function highlightElement(el) {
  if (!el) return;
  el.style.outline = '2px solid #6366f1';
  el.style.boxShadow = '0 0 12px rgba(99, 102, 241, 0.6)';
  el.style.transition = 'all 0.3s ease';
  setTimeout(() => {
    el.style.outline = '';
    el.style.boxShadow = '';
  }, 1200);
}

/**
 * Check if running inside Chrome/Edge extension.
 */
function isExtensionContext() {
  try {
    const win = typeof window !== 'undefined' ? window : {};
    return !!(
      (win.chrome && win.chrome.runtime && win.chrome.runtime.id) ||
      (win.browser && win.browser.runtime && win.browser.runtime.id)
    );
  } catch {
    return false;
  }
}
