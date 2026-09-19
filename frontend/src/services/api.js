/**
 * NETRA API Client
 * Communicates with the backend at POST /api/v1/plan_action.
 * Also supports GET /health, GET /api/v1/config, and GET /api/v1/audit.
 * Includes intelligent multi-port discovery (8000, 8001).
 */

const CANDIDATE_URLS = [
  import.meta.env.VITE_NETRA_API_URL,
  'http://127.0.0.1:8000',
  'http://localhost:8000',
  'http://127.0.0.1:8001',
  'http://localhost:8001',
].filter(Boolean);

let activeBaseUrl = localStorage.getItem('netra_api_url') || CANDIDATE_URLS[0];

export function getBaseUrl() {
  return activeBaseUrl;
}

export function setBaseUrl(url) {
  if (!url) return;
  activeBaseUrl = url.replace(/\/+$/, '');
  localStorage.setItem('netra_api_url', activeBaseUrl);
}

/**
 * Custom error class for NETRA API errors.
 */
export class NetraApiError extends Error {
  constructor(message, status, code, detail) {
    super(message);
    this.name = 'NetraApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

/**
 * Internal fetch wrapper with error handling.
 */
async function request(path, options = {}) {
  const url = `${activeBaseUrl}${path}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      let detail = null;
      try {
        detail = await response.json();
      } catch {
        // Response body might not be JSON
      }

      // PII leakage rejection (Zero-trust gate)
      if (response.status === 422 && detail?.detail?.code === 'PII_LEAKAGE_REJECTED') {
        throw new NetraApiError(
          'Privacy violation: PII leakage detected by backend zero-trust gate',
          422,
          'PII_LEAKAGE_REJECTED',
          detail.detail
        );
      }

      // Validation errors
      if (response.status === 422) {
        const msg = detail?.detail?.message || (Array.isArray(detail?.detail) ? detail.detail.map(d => d.msg).join(', ') : 'Validation error');
        throw new NetraApiError(
          `Validation error: ${msg}`,
          422,
          detail?.detail?.code || 'VALIDATION_ERROR',
          detail?.detail
        );
      }

      throw new NetraApiError(
        `API error: ${response.status} ${response.statusText}`,
        response.status,
        'API_ERROR',
        detail
      );
    }

    return await response.json();
  } catch (err) {
    if (err instanceof NetraApiError) throw err;

    // Network / connection errors
    throw new NetraApiError(
      `Connection error: ${err.message}`,
      0,
      'CONNECTION_ERROR',
      null
    );
  }
}

/**
 * Check backend health with fallback discovery across 8000 / 8001.
 * GET /health
 */
export async function checkHealth() {
  // First try active URL
  try {
    const data = await request('/health');
    if (data && data.service?.includes('NETRA')) {
      return data;
    }
  } catch {
    // try discovery fallback
  }

  // Attempt discovery across candidates
  for (const candidate of CANDIDATE_URLS) {
    if (candidate === activeBaseUrl) continue;
    try {
      const res = await fetch(`${candidate}/health`, { signal: AbortSignal.timeout(1500) });
      if (res.ok) {
        const data = await res.json();
        if (data && data.service?.includes('NETRA')) {
          setBaseUrl(candidate);
          return data;
        }
      }
    } catch {
      // continue searching
    }
  }

  // Final attempt with primary error
  return request('/health');
}

/**
 * Fetch backend configuration.
 * GET /api/v1/config
 */
export async function getConfig() {
  return request('/api/v1/config');
}

/**
 * Send a plan_action request to the backend.
 * POST /api/v1/plan_action
 *
 * @param {Object} payload - The AgentRequest payload
 * @returns {Object} PlanResponse from backend
 */
export async function planAction(payload) {
  return request('/api/v1/plan_action', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Fetch audit trail.
 * GET /api/v1/audit
 */
export async function getAudit() {
  return request('/api/v1/audit');
}
