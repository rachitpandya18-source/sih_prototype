import { useState } from 'react';
import './InteractiveSandbox.css';

export default function InteractiveSandbox({ axtree }) {
  const [activeTab, setActiveTab] = useState('browser'); // 'browser' | 'axtree'

  return (
    <div className="sandbox-card animate-fade-in">
      <div className="sandbox-header">
        <div className="browser-chrome">
          <div className="browser-dots">
            <span className="dot red" />
            <span className="dot yellow" />
            <span className="dot green" />
          </div>
          <div className="browser-url-bar">
            <span className="url-lock">🔒</span>
            <span className="url-text">https://portal.citizen-services.gov.in/registration</span>
            <span className="url-badge">Sandbox Target</span>
          </div>
        </div>

        <div className="sandbox-tabs">
          <button
            type="button"
            className={`tab-btn ${activeTab === 'browser' ? 'active' : ''}`}
            onClick={() => setActiveTab('browser')}
          >
            Live Target Page
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'axtree' ? 'active' : ''}`}
            onClick={() => setActiveTab('axtree')}
          >
            Sanitized AXTree ({axtree?.length || 0})
          </button>
        </div>
      </div>

      <div className="sandbox-body">
        {activeTab === 'browser' ? (
          <div id="netra-sandbox-target" className="portal-page">
            <div className="portal-hero">
              <div className="portal-badge">National Citizen Services • Mock Portal</div>
              <h2 className="portal-title">Citizen Verification & Benefit Application</h2>
              <p className="portal-subtitle">
                Fill the form below to register. NETRA guarantees that sensitive credentials remain strictly on your local device.
              </p>
            </div>

            <form className="portal-form" onSubmit={(e) => e.preventDefault()}>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="fullname-input">Full Legal Name</label>
                  <input
                    id="fullname-input"
                    data-netra-id="fullname-input"
                    type="text"
                    placeholder="Enter full name"
                    defaultValue=""
                  />
                  <span className="field-hint">Tokenized as [NAME_1]</span>
                </div>
                <div className="form-group">
                  <label htmlFor="email-input">Official Email</label>
                  <input
                    id="email-input"
                    data-netra-id="email-input"
                    type="email"
                    placeholder="name@example.gov.in"
                    defaultValue=""
                  />
                  <span className="field-hint">Tokenized as [EMAIL_1]</span>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="phone-input">Mobile Number</label>
                  <input
                    id="phone-input"
                    data-netra-id="phone-input"
                    type="tel"
                    placeholder="+91 98765 43210"
                    defaultValue=""
                  />
                  <span className="field-hint">Tokenized as [PHONE_1]</span>
                </div>
                <div className="form-group">
                  <label htmlFor="kyc-input">Government ID (Aadhaar / PAN)</label>
                  <input
                    id="kyc-input"
                    data-netra-id="kyc-input"
                    type="text"
                    placeholder="XXXX XXXX XXXX"
                    defaultValue=""
                  />
                  <span className="field-hint">Tokenized as [AADHAAR_1]</span>
                </div>
              </div>

              <div className="form-actions-bar">
                <button
                  id="submit-app-btn"
                  data-netra-id="submit-app-btn"
                  type="button"
                  className="portal-btn portal-btn-primary"
                  onClick={() => alert('Application Submitted in Demo Sandbox!')}
                >
                  Submit Application
                </button>

                <button
                  id="transfer-btn"
                  data-netra-id="transfer-btn"
                  type="button"
                  className="portal-btn portal-btn-warning"
                  onClick={() => alert('Transfer Action Clicked!')}
                >
                  Transfer ₹5,000 (Sensitive)
                </button>

                <button
                  id="delete-account-btn"
                  data-netra-id="delete-account-btn"
                  type="button"
                  className="portal-btn portal-btn-danger"
                  onClick={() => alert('Delete Profile Action Clicked!')}
                >
                  Delete Account
                </button>

                <a
                  id="learn-more-link"
                  data-netra-id="learn-more-link"
                  href="#documentation"
                  className="portal-link"
                  onClick={(e) => { e.preventDefault(); alert('Learn More Link Clicked!'); }}
                >
                  Learn more &amp; Guidelines
                </a>
              </div>
            </form>
          </div>
        ) : (
          <div className="axtree-inspector">
            <div className="inspector-bar">
              <span className="inspector-title">Zero-Trust Sanitized Representation Sent to AI</span>
              <span className="inspector-badge">PII Free Verified</span>
            </div>
            <pre className="axtree-code">
              {JSON.stringify(axtree || [], null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
