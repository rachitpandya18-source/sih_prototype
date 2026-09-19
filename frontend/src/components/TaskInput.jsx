import { useState } from 'react';
import './TaskInput.css';

const PRESETS = [
  { label: '📝 Fill Full Name', text: 'Fill the full name field with user name' },
  { label: '✉️ Fill Official Email', text: 'Fill the official email field' },
  { label: '🚀 Submit Application', text: 'Click Submit Application' },
  { label: '💳 Transfer ₹5,000 (Sensitive Gate)', text: 'Click Transfer ₹5,000' },
  { label: '⚠️ Delete Account (High Risk Gate)', text: 'Click Delete Account' },
  { label: '🔗 Navigate Learn More', text: 'Click Learn more' },
];

export default function TaskInput({ onStart, isRunning, onStop, onReset, connected }) {
  const [instruction, setInstruction] = useState('');

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!instruction.trim() || isRunning || !connected) return;
    onStart(instruction.trim());
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const selectPreset = (text) => {
    setInstruction(text);
  };

  return (
    <div className="task-input-container animate-fade-in">
      <div className="task-input-header">
        <div className="task-input-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <h2 className="task-input-title">Task &amp; Mission Controller</h2>
          <span className="task-input-hint">Instruct NETRA on the goal to execute on the observed page</span>
        </div>
      </div>

      {/* Quick Presets */}
      <div className="preset-bar">
        <span className="preset-label">Judge Presets:</span>
        <div className="preset-chips">
          {PRESETS.map((p, idx) => (
            <button
              key={idx}
              type="button"
              className="preset-chip"
              disabled={isRunning}
              onClick={() => selectPreset(p.text)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="task-form">
        <div className="textarea-wrapper">
          <textarea
            id="task-instruction-input"
            className="task-textarea"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. Fill the registration form using my on-device credentials..."
            disabled={isRunning}
            rows={2}
            maxLength={1000}
          />
          <span className="char-count">{instruction.length}/1000</span>
        </div>

        <div className="task-actions">
          {!isRunning ? (
            <button
              id="start-agent-btn"
              type="submit"
              className="btn btn-primary"
              disabled={!instruction.trim() || !connected}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="btn-icon">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              Start Agent Loop
            </button>
          ) : (
            <button
              id="stop-agent-btn"
              type="button"
              className="btn btn-danger"
              onClick={onStop}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="btn-icon">
                <rect x="6" y="6" width="12" height="12" rx="1"/>
              </svg>
              Stop Agent
            </button>
          )}

          <button
            id="reset-agent-btn"
            type="button"
            className="btn btn-ghost"
            onClick={() => { onReset(); setInstruction(''); }}
            disabled={isRunning}
          >
            Reset
          </button>

          {!connected && (
            <span className="connection-warning">
              ⚠ Backend offline — verify server on port 8000/8001
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
