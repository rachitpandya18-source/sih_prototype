import { useState } from 'react';
import './VaultManager.css';

export default function VaultManager({
  vaultEntries,
  onAddToken,
  onSeedDemo,
  onClear,
  onTestLeakage,
}) {
  const [category, setCategory] = useState('NAME');
  const [value, setValue] = useState('');
  const [revealValues, setRevealValues] = useState(false);

  const handleAdd = (e) => {
    e.preventDefault();
    if (!value.trim()) return;
    onAddToken(category, value.trim());
    setValue('');
  };

  return (
    <div className="vault-card animate-fade-in">
      <div className="vault-header">
        <div className="vault-title-wrap">
          <span className="vault-icon">🔐</span>
          <div>
            <h3 className="vault-title">On-Device Privacy Vault</h3>
            <span className="vault-subtitle">Local Token Storage • Zero Raw PII Transmitted</span>
          </div>
        </div>

        <div className="vault-actions-top">
          <button
            type="button"
            className="btn-vault-action"
            onClick={() => setRevealValues(!revealValues)}
            title="Toggle value visibility"
          >
            {revealValues ? '🙈 Hide Values' : '👁 Show Values'}
          </button>
          <button
            type="button"
            className="btn-vault-action btn-seed"
            onClick={onSeedDemo}
          >
            ⚡ Quick Seed Demo Data
          </button>
          {vaultEntries.length > 0 && (
            <button
              type="button"
              className="btn-vault-action btn-clear"
              onClick={onClear}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Vault List */}
      <div className="vault-list">
        {vaultEntries.length === 0 ? (
          <div className="vault-empty">
            <p>Vault is empty. Click <strong>Quick Seed Demo Data</strong> or add sensitive values below.</p>
          </div>
        ) : (
          <div className="tokens-grid">
            {vaultEntries.map((entry, idx) => (
              <div key={idx} className="token-chip">
                <span className="token-key">{entry.token}</span>
                <span className="token-category">{entry.category}</span>
                <span className="token-val">
                  {revealValues ? entry.value : '••••••••••••'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Token Form & Leakage Test Bar */}
      <div className="vault-footer">
        <form onSubmit={handleAdd} className="vault-add-form">
          <select
            className="vault-select"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="NAME">NAME</option>
            <option value="EMAIL">EMAIL</option>
            <option value="PHONE">PHONE</option>
            <option value="AADHAAR">AADHAAR</option>
            <option value="PAN">PAN</option>
            <option value="CARD">CARD</option>
          </select>

          <input
            type="text"
            className="vault-input"
            placeholder="Enter sensitive value to tokenize..."
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />

          <button type="submit" className="btn-add-token" disabled={!value.trim()}>
            + Add to Vault
          </button>
        </form>

        <button
          type="button"
          className="btn-leakage-test"
          onClick={onTestLeakage}
          title="Send raw unredacted PII to test the backend zero-trust gate"
        >
          🚨 Test Backend Leakage Gate (Expect 422)
        </button>
      </div>
    </div>
  );
}
