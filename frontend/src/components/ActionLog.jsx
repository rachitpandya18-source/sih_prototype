import { ACTION_ICONS, ACTION_LABELS, formatTime, getConfidenceLevel } from '../utils/helpers.js';
import './ActionLog.css';

export default function ActionLog({ history }) {
  if (!history || history.length === 0) {
    return (
      <div className="action-log-container animate-fade-in">
        <div className="log-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="log-header-icon">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
          <h3 className="log-title">Action History</h3>
        </div>
        <div className="log-empty">
          <p>No actions yet. Start a task to see the agent&apos;s action history.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="action-log-container animate-fade-in">
      <div className="log-header">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="log-header-icon">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
        <h3 className="log-title">Action History</h3>
        <span className="log-count">{history.length} step{history.length !== 1 ? 's' : ''}</span>
      </div>

      <div className="log-timeline">
        {history.map((entry, index) => {
          const icon = ACTION_ICONS[entry.action] || '●';
          const label = ACTION_LABELS[entry.action] || entry.action;
          const statusClass = entry.status === 'SUCCESS' ? 'entry-success'
            : entry.status === 'REJECTED_BY_USER' ? 'entry-rejected'
            : 'entry-failed';
          const conf = entry.confidence != null ? getConfidenceLevel(entry.confidence) : null;

          return (
            <div key={index} className={`log-entry ${statusClass}`} style={{ animationDelay: `${index * 50}ms` }}>
              <div className="entry-timeline">
                <span className="entry-dot" />
                {index < history.length - 1 && <span className="entry-line" />}
              </div>
              <div className="entry-content">
                <div className="entry-header">
                  <span className="entry-icon">{icon}</span>
                  <span className="entry-label">{label}</span>
                  <span className={`entry-status ${statusClass}`}>{entry.status}</span>
                  <span className="entry-step">Step {entry.step_number || index + 1}</span>
                  {entry.timestamp && (
                    <span className="entry-time">{formatTime(entry.timestamp)}</span>
                  )}
                </div>

                <div className="entry-details">
                  {entry.target_id && (
                    <span className="entry-detail">
                      <span className="detail-key">target:</span>
                      <code>{entry.target_id}</code>
                    </span>
                  )}
                  {conf && (
                    <span className="entry-detail">
                      <span className="detail-key">confidence:</span>
                      <span style={{ color: conf.color }}>{(entry.confidence * 100).toFixed(0)}%</span>
                    </span>
                  )}
                  {entry.confirmed_by_human && (
                    <span className="entry-human-tag">✓ Confirmed by user</span>
                  )}
                  {entry.error && (
                    <span className="entry-error">{entry.error}</span>
                  )}
                  {entry.message && (
                    <span className="entry-message">{entry.message}</span>
                  )}
                </div>

                {entry.rationale && (
                  <p className="entry-rationale">{entry.rationale}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
