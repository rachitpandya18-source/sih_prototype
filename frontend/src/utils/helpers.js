/**
 * Utility helpers for NETRA frontend.
 */

/**
 * Generate a unique session ID.
 */
export function generateSessionId() {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 8);
  return `sess_${ts}_${rand}`;
}

/**
 * Format a timestamp into a readable time string.
 */
export function formatTime(date) {
  if (!date) return '';
  const d = date instanceof Date ? date : new Date(date);
  return d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Format a duration in ms to a readable string.
 */
export function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

/**
 * Map action types to human-readable labels.
 */
export const ACTION_LABELS = {
  CLICK: 'Click',
  TYPE: 'Type',
  SELECT: 'Select',
  SCROLL: 'Scroll',
  WAIT: 'Wait',
  NAVIGATE: 'Navigate',
  FINISH: 'Task Complete',
  REQUEST_CONFIRMATION: 'Needs Confirmation',
};

/**
 * Map action types to icons (emoji for simplicity; avoids extra deps).
 */
export const ACTION_ICONS = {
  CLICK: '👆',
  TYPE: '⌨️',
  SELECT: '📋',
  SCROLL: '↕️',
  WAIT: '⏳',
  NAVIGATE: '🔗',
  FINISH: '✅',
  REQUEST_CONFIRMATION: '⚠️',
};

/**
 * Agent states for the UI.
 */
export const AGENT_STATES = {
  IDLE: 'idle',
  OBSERVING: 'observing',
  SANITIZING: 'sanitizing',
  PLANNING: 'planning',
  AWAITING_CONFIRMATION: 'awaiting_confirmation',
  EXECUTING: 'executing',
  COMPLETED: 'completed',
  ERROR: 'error',
  STOPPED: 'stopped',
  PRIVACY_BLOCKED: 'privacy_blocked',
};

/**
 * Human-readable labels for agent states.
 */
export const STATE_LABELS = {
  [AGENT_STATES.IDLE]: 'Ready',
  [AGENT_STATES.OBSERVING]: 'Observing Page',
  [AGENT_STATES.SANITIZING]: 'Sanitizing Data',
  [AGENT_STATES.PLANNING]: 'AI Planning…',
  [AGENT_STATES.AWAITING_CONFIRMATION]: 'Awaiting Confirmation',
  [AGENT_STATES.EXECUTING]: 'Executing Action',
  [AGENT_STATES.COMPLETED]: 'Task Complete',
  [AGENT_STATES.ERROR]: 'Error',
  [AGENT_STATES.STOPPED]: 'Stopped',
  [AGENT_STATES.PRIVACY_BLOCKED]: 'Privacy Blocked',
};

/**
 * Confidence level classification.
 */
export function getConfidenceLevel(confidence) {
  if (confidence >= 0.85) return { label: 'High', color: 'var(--status-success)' };
  if (confidence >= 0.6) return { label: 'Medium', color: 'var(--status-warning)' };
  return { label: 'Low', color: 'var(--status-error)' };
}

/**
 * Truncate text to a max length.
 */
export function truncate(text, max = 80) {
  if (!text || text.length <= max) return text;
  return text.slice(0, max) + '…';
}
