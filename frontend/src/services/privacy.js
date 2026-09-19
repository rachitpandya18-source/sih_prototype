/**
 * NETRA Privacy Service
 *
 * Handles local PII detection, sanitization, and token vault management.
 * All sensitive data stays on-device; only masked tokens are sent to the backend.
 *
 * This module is designed to be usable both in the React dashboard
 * and in a future Chrome/Edge extension content script.
 */

// ── Indian PII patterns ──

const PII_PATTERNS = [
  { type: 'AADHAAR', pattern: /\b\d{4}\s?\d{4}\s?\d{4}\b/g },
  { type: 'PAN', pattern: /\b[A-Z]{5}\d{4}[A-Z]\b/g },
  { type: 'EMAIL', pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g },
  { type: 'PHONE', pattern: /\b(?:\+91[\s-]?)?[6-9]\d{9}\b/g },
  { type: 'UPI', pattern: /\b[a-zA-Z0-9._%+-]+@[a-zA-Z]{2,}\b/g },
  { type: 'IFSC', pattern: /\b[A-Z]{4}0[A-Z0-9]{6}\b/g },
  { type: 'CARD', pattern: /\b(?:\d{4}[\s-]?){3}\d{4}\b/g },
];

/**
 * Detect PII in a text string.
 * @param {string} text
 * @returns {Array<{type: string, value: string, index: number}>}
 */
export function detectPII(text) {
  if (!text) return [];
  const findings = [];

  for (const { type, pattern } of PII_PATTERNS) {
    const regex = new RegExp(pattern.source, pattern.flags);
    let match;
    while ((match = regex.exec(text)) !== null) {
      findings.push({
        type,
        value: match[0],
        index: match.index,
      });
    }
  }

  return findings;
}

/**
 * Token Vault — stores user-provided sensitive values locally.
 * Maps masked tokens like [NAME_1] → actual value.
 * Values NEVER leave the device.
 */
export class TokenVault {
  constructor() {
    this._store = new Map();
    this._counter = {};
  }

  /**
   * Store a value and return its masked token.
   * @param {string} category - e.g. 'NAME', 'EMAIL', 'AADHAAR'
   * @param {string} realValue - the actual sensitive value
   * @returns {string} masked token like [NAME_1]
   */
  store(category, realValue) {
    const cat = category.toUpperCase().replace(/[^A-Z0-9_-]/g, '_');
    this._counter[cat] = (this._counter[cat] || 0) + 1;
    const token = `[${cat}_${this._counter[cat]}]`;
    this._store.set(token, realValue);
    return token;
  }

  /**
   * Resolve a masked token to its real value.
   * @param {string} token - e.g. [NAME_1]
   * @returns {string|null}
   */
  resolve(token) {
    return this._store.get(token) || null;
  }

  /**
   * Check if a token exists.
   */
  has(token) {
    return this._store.has(token);
  }

  /**
   * Get the masked_token_map to send to the backend.
   * Only sends token → category, never the real value.
   */
  getMaskedTokenMap() {
    const map = {};
    for (const [token] of this._store) {
      // Extract category from token like [NAME_1] → NAME
      const match = token.match(/^\[([A-Z][A-Z0-9_-]+)_\d+\]$/);
      if (match) {
        map[token] = match[1];
      }
    }
    return map;
  }

  /**
   * Clear all stored values.
   */
  clear() {
    this._store.clear();
    this._counter = {};
  }

  get size() {
    return this._store.size;
  }
}

/**
 * Sanitize text by replacing detected PII with masked tokens.
 * @param {string} text
 * @param {TokenVault} vault
 * @returns {{ sanitized: string, tokenMap: Object }}
 */
export function sanitizeText(text, vault) {
  if (!text) return { sanitized: text, tokenMap: {} };

  let sanitized = text;
  const findings = detectPII(text);

  // Sort by index descending so replacements don't shift positions
  findings.sort((a, b) => b.index - a.index);

  for (const finding of findings) {
    const token = vault.store(finding.type, finding.value);
    sanitized = sanitized.slice(0, finding.index) + token + sanitized.slice(finding.index + finding.value.length);
  }

  return { sanitized, tokenMap: vault.getMaskedTokenMap() };
}
