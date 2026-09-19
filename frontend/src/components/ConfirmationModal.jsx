import './ConfirmationModal.css';

export default function ConfirmationModal({ pending, onConfirm, onReject }) {
  if (!pending) return null;

  const { action } = pending;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Human confirmation required">
      <div className="modal-container animate-fade-in">
        <div className="modal-header">
          <div className="modal-warning-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <h3 className="modal-title">Human Confirmation Required</h3>
          <p className="modal-subtitle">
            NETRA has identified a potentially sensitive or destructive action that requires your explicit approval before execution.
          </p>
        </div>

        <div className="modal-body">
          <div className="modal-action-card">
            <div className="modal-action-type">
              <span className="modal-type-badge">{action.action_type}</span>
              <span className="modal-confidence">
                Confidence: {(action.confidence * 100).toFixed(0)}%
              </span>
            </div>

            {action.target_id && (
              <div className="modal-detail">
                <span className="modal-detail-label">Target Element</span>
                <code>{action.target_id}</code>
              </div>
            )}

            {action.value && (
              <div className="modal-detail">
                <span className="modal-detail-label">Value</span>
                <code>{action.value}</code>
                {action.value_ref === 'LOCAL_USER_VALUE' && (
                  <span className="modal-local-tag">🔒 Resolved on-device</span>
                )}
              </div>
            )}

            {action.url && (
              <div className="modal-detail">
                <span className="modal-detail-label">Navigate To</span>
                <code>{action.url}</code>
              </div>
            )}

            {action.decision_rationale && (
              <div className="modal-rationale">
                <span className="modal-detail-label">Why confirmation is needed</span>
                <p>{action.decision_rationale}</p>
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button
            id="reject-action-btn"
            className="btn btn-ghost modal-btn"
            onClick={onReject}
          >
            Reject & Stop
          </button>
          <button
            id="confirm-action-btn"
            className="btn btn-confirm modal-btn"
            onClick={onConfirm}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="btn-icon">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            Confirm & Execute
          </button>
        </div>
      </div>
    </div>
  );
}
