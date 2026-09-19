import { useState } from 'react';
import './Header.css';

export default function Header({ connected, health, apiUrl, onUpdateApiUrl, recheckNow }) {
  const [editingUrl, setEditingUrl] = useState(false);
  const [tempUrl, setTempUrl] = useState(apiUrl || '');

  const handleSaveUrl = (e) => {
    e.preventDefault();
    if (tempUrl.trim()) {
      onUpdateApiUrl(tempUrl.trim());
      setEditingUrl(false);
      recheckNow?.();
    }
  };

  return (
    <header className="netra-header">
      <div className="header-brand">
        <div className="header-logo">
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="logo-svg">
            <defs>
              <linearGradient id="logo-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#6366f1"/>
                <stop offset="100%" stopColor="#06b6d4"/>
              </linearGradient>
            </defs>
            <circle cx="32" cy="32" r="30" stroke="url(#logo-grad)" strokeWidth="2.5" fill="none"/>
            <ellipse cx="32" cy="32" rx="18" ry="12" stroke="url(#logo-grad)" strokeWidth="2" fill="none"/>
            <circle cx="32" cy="32" r="5.5" fill="url(#logo-grad)"/>
            <circle cx="32" cy="32" r="2" fill="#0a0e1a"/>
            <path d="M24 44 L32 50 L40 44" stroke="url(#logo-grad)" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div className="header-titles">
          <div className="name-row">
            <h1 className="header-name">NETRA</h1>
            <span className="header-badge">SIH 2026 • PS 171</span>
          </div>
          <span className="header-tagline">Privacy-First Multimodal AI Browser Agent</span>
        </div>
      </div>

      <div className="header-meta">
        {editingUrl ? (
          <form onSubmit={handleSaveUrl} className="url-edit-form">
            <input
              type="text"
              className="url-edit-input"
              value={tempUrl}
              onChange={(e) => setTempUrl(e.target.value)}
              placeholder="http://localhost:8000"
            />
            <button type="submit" className="url-save-btn">Save</button>
            <button type="button" className="url-cancel-btn" onClick={() => setEditingUrl(false)}>✕</button>
          </form>
        ) : (
          <div
            className={`connection-indicator ${connected ? 'connected' : 'disconnected'}`}
            onClick={() => { setTempUrl(apiUrl); setEditingUrl(true); }}
            title="Click to change backend endpoint"
          >
            <span className="connection-dot" />
            <span className="connection-label">
              {connected ? 'Backend Online' : 'Backend Offline'}
            </span>
            <span className="url-pill">{apiUrl?.replace('http://', '')}</span>
          </div>
        )}

        {health && (
          <div className="health-badges">
            <span className="header-chip version-chip">v{health.version}</span>
            <span className="header-chip planner-chip">{health.planner_mode} mode</span>
            <span className="header-chip gate-chip">Zero-Trust Gate ✓</span>
          </div>
        )}
      </div>
    </header>
  );
}
