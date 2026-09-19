import { AGENT_STATES, STATE_LABELS, getConfidenceLevel } from '../utils/helpers.js';
import './AgentStatus.css';

const STATE_CONFIG = {
  [AGENT_STATES.IDLE]: { icon: '○', className: 'status-idle' },
  [AGENT_STATES.OBSERVING]: { icon: '👁', className: 'status-active' },
  [AGENT_STATES.SANITIZING]: { icon: '🔒', className: 'status-active' },
  [AGENT_STATES.PLANNING]: { icon: '🧠', className: 'status-planning' },
  [AGENT_STATES.AWAITING_CONFIRMATION]: { icon: '⚠️', className: 'status-warning' },
  [AGENT_STATES.EXECUTING]: { icon: '⚡', className: 'status-active' },
  [AGENT_STATES.COMPLETED]: { icon: '✅', className: 'status-success' },
  [AGENT_STATES.ERROR]: { icon: '❌', className: 'status-error' },
  [AGENT_STATES.STOPPED]: { icon: '⏹', className: 'status-stopped' },
  [AGENT_STATES.PRIVACY_BLOCKED]: { icon: '🛡️', className: 'status-privacy' },
};

export default function AgentStatus({
  state,
  currentStep,
  sessionId,
  taskInstruction,
  currentAction,
  currentResponse,
  error,
  privacyBlocked,
  vaultSize,
}) {
  const stateConfig = STATE_CONFIG[state] || STATE_CONFIG[AGENT_STATES.IDLE];
  const isActive = [
    AGENT_STATES.OBSERVING,
    AGENT_STATES.SANITIZING,
    AGENT_STATES.PLANNING,
    AGENT_STATES.EXECUTING,
  ].includes(state);

  return (
    <div className="agent-status-container animate-fade-in">
      {/* Pipeline Visualization */}
      <div className="pipeline">
        <PipelineStep
          label="Observe"
          icon="👁"
          active={state === AGENT_STATES.OBSERVING}
          done={[AGENT_STATES.SANITIZING, AGENT_STATES.PLANNING, AGENT_STATES.EXECUTING, AGENT_STATES.AWAITING_CONFIRMATION, AGENT_STATES.COMPLETED].includes(state)}
        />
        <PipelineArrow />
        <PipelineStep
          label="Sanitize"
          icon="🔒"
          active={state === AGENT_STATES.SANITIZING}
          done={[AGENT_STATES.PLANNING, AGENT_STATES.EXECUTING, AGENT_STATES.AWAITING_CONFIRMATION, AGENT_STATES.COMPLETED].includes(state)}
        />
        <PipelineArrow />
        <PipelineStep
          label="AI Plan"
          icon="🧠"
          active={state === AGENT_STATES.PLANNING}
          done={[AGENT_STATES.EXECUTING, AGENT_STATES.AWAITING_CONFIRMATION, AGENT_STATES.COMPLETED].includes(state)}
        />
        <PipelineArrow />
        <PipelineStep
          label="Confirm"
          icon="⚠️"
          active={state === AGENT_STATES.AWAITING_CONFIRMATION}
          done={[AGENT_STATES.EXECUTING, AGENT_STATES.COMPLETED].includes(state)}
        />
        <PipelineArrow />
        <PipelineStep
          label="Execute"
          icon="⚡"
          active={state === AGENT_STATES.EXECUTING}
          done={state === AGENT_STATES.COMPLETED}
        />
      </div>

      {/* Status Panel */}
      <div className="status-grid">
        <div className={`status-badge ${stateConfig.className}`}>
          <span className="status-icon">{stateConfig.icon}</span>
          <span className="status-text">{STATE_LABELS[state]}</span>
          {isActive && <span className="status-spinner" />}
        </div>

        <div className="status-details">
          <StatusItem label="Session" value={sessionId} mono />
          <StatusItem label="Step" value={`#${currentStep}`} />
          <StatusItem label="Vault" value={`${vaultSize} tokens`} />
          {taskInstruction && (
            <StatusItem label="Task" value={taskInstruction} truncate />
          )}
        </div>
      </div>

      {/* Current Action Display */}
      {currentAction && state !== AGENT_STATES.IDLE && (
        <ActionDisplay action={currentAction} response={currentResponse} />
      )}

      {/* Privacy Blocked */}
      {privacyBlocked && (
        <div className="privacy-alert">
          <span className="privacy-icon">🛡️</span>
          <div className="privacy-content">
            <strong>Privacy Violation Detected</strong>
            <p>The backend rejected this request because PII was detected in the payload. Your data was NOT processed or stored.</p>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && !privacyBlocked && (
        <div className="error-alert">
          <span className="error-icon">⚠️</span>
          <span className="error-text">{error}</span>
        </div>
      )}
    </div>
  );
}

function PipelineStep({ label, icon, active, done }) {
  let className = 'pipeline-step';
  if (active) className += ' pipeline-active';
  else if (done) className += ' pipeline-done';

  return (
    <div className={className}>
      <span className="pipeline-icon">{done ? '✓' : icon}</span>
      <span className="pipeline-label">{label}</span>
    </div>
  );
}

function PipelineArrow() {
  return (
    <div className="pipeline-arrow">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M5 12h14M12 5l7 7-7 7"/>
      </svg>
    </div>
  );
}

function StatusItem({ label, value, mono, truncate: shouldTruncate }) {
  let displayValue = value || '—';
  if (shouldTruncate && displayValue.length > 60) {
    displayValue = displayValue.slice(0, 60) + '…';
  }

  return (
    <div className="status-item">
      <span className="status-label">{label}</span>
      <span className={`status-value ${mono ? 'mono' : ''}`}>{displayValue}</span>
    </div>
  );
}

function ActionDisplay({ action, response }) {
  const conf = getConfidenceLevel(action.confidence);

  return (
    <div className="action-display">
      <div className="action-display-header">
        <span className="action-type-badge">{action.action_type}</span>
        <span className="action-confidence" style={{ color: conf.color }}>
          {(action.confidence * 100).toFixed(0)}% {conf.label}
        </span>
        {response?.planner && (
          <span className="planner-badge">{response.planner}</span>
        )}
        {response?.fallback_used && (
          <span className="fallback-badge">Fallback</span>
        )}
      </div>

      {action.target_id && (
        <div className="action-field">
          <span className="field-label">Target</span>
          <code className="field-value">{action.target_id}</code>
        </div>
      )}

      {action.value && (
        <div className="action-field">
          <span className="field-label">Value</span>
          <code className="field-value">{action.value}</code>
          {action.value_ref === 'LOCAL_USER_VALUE' && (
            <span className="local-badge">🔒 Resolved locally</span>
          )}
        </div>
      )}

      {action.url && (
        <div className="action-field">
          <span className="field-label">URL</span>
          <code className="field-value">{action.url}</code>
        </div>
      )}

      {action.direction && (
        <div className="action-field">
          <span className="field-label">Direction</span>
          <span className="field-value">{action.direction} {action.amount && `(${action.amount}px)`}</span>
        </div>
      )}

      {action.decision_rationale && (
        <div className="action-rationale">
          <span className="field-label">Rationale</span>
          <p>{action.decision_rationale}</p>
        </div>
      )}

      {response?.sanitized !== undefined && (
        <div className="privacy-status-bar">
          <span className={`privacy-tag ${response.sanitized ? 'clean' : 'dirty'}`}>
            {response.sanitized ? '🔒 Sanitized' : '⚠️ Not sanitized'}
          </span>
          <span className={`privacy-tag ${!response.raw_pii_received ? 'clean' : 'dirty'}`}>
            {!response.raw_pii_received ? '✓ No PII received' : '⚠️ Raw PII received'}
          </span>
        </div>
      )}
    </div>
  );
}
