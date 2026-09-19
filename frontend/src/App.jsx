import { useState, useEffect } from 'react';
import Header from './components/Header.jsx';
import TaskInput from './components/TaskInput.jsx';
import AgentStatus from './components/AgentStatus.jsx';
import ActionLog from './components/ActionLog.jsx';
import ConfirmationModal from './components/ConfirmationModal.jsx';
import InteractiveSandbox from './components/InteractiveSandbox.jsx';
import VaultManager from './components/VaultManager.jsx';
import { useAgent } from './hooks/useAgent.js';
import { useBackendStatus } from './hooks/useBackendStatus.js';
import { getBaseUrl, setBaseUrl, planAction, NetraApiError } from './services/api.js';
import { extractPagePerception } from './services/dom.js';
import './App.css';

export default function App() {
  const [apiUrl, setApiUrlState] = useState(getBaseUrl());
  const { connected, health, recheckNow } = useBackendStatus(6000);
  const [activeAxtree, setActiveAxtree] = useState([]);
  const [leakageAlert, setLeakageAlert] = useState(null);

  const {
    state,
    currentStep,
    sessionId,
    taskInstruction,
    history,
    currentAction,
    currentResponse,
    error,
    isRunning,
    privacyBlocked,
    pendingConfirmation,
    vaultSize,
    vaultEntries,
    startTask,
    stopAgent,
    confirmAction,
    rejectAction,
    resetAgent,
    addToVault,
    seedDemoVault,
    clearVault,
  } = useAgent();

  // Auto-seed demo vault once on first mount so judges have instant tokens
  useEffect(() => {
    seedDemoVault();
  }, [seedDemoVault]);

  // Periodically refresh extracted AXTree representation for the inspector
  useEffect(() => {
    const updateAXTree = () => {
      const { sanitized_axtree } = extractPagePerception();
      setActiveAxtree(sanitized_axtree);
    };

    updateAXTree();
    const interval = setInterval(updateAXTree, 2500);
    return () => clearInterval(interval);
  }, []);

  const handleUpdateApiUrl = (newUrl) => {
    setBaseUrl(newUrl);
    setApiUrlState(newUrl);
  };

  // Test intentionally sending raw unredacted PII to test the backend zero-trust gate
  const handleTestLeakage = async () => {
    setLeakageAlert(null);
    try {
      await planAction({
        session_id: `leak_test_${Date.now()}`,
        step_number: 1,
        task_instruction: 'Simulate raw data leakage attempt',
        sanitized_screenshot_base64: null,
        sanitized_screenshot_mime_type: 'image/webp',
        current_url: window.location.href,
        page_title: document.title,
        sanitized_axtree: [
          {
            id: 'unredacted_field',
            role: 'textbox',
            name: 'Raw PII Element',
            value: 'victim_aadhaar_5432_9876_1234@leak.com', // Raw PII!
            bbox: [100, 100, 250, 140],
          },
        ],
        detected_ui_elements: [],
        masked_token_map: {},
        history: [],
      });
      setLeakageAlert({
        type: 'warning',
        text: 'Warning: Backend did not reject raw PII.',
      });
    } catch (err) {
      if (err instanceof NetraApiError && err.code === 'PII_LEAKAGE_REJECTED') {
        setLeakageAlert({
          type: 'success',
          title: '🛡️ Zero-Trust Gate Triggered Successfully (HTTP 422)',
          text: 'Backend caught unmasked PII in the payload and immediately rejected it with PII_LEAKAGE_REJECTED. No data was accepted or logged.',
        });
      } else {
        setLeakageAlert({
          type: 'error',
          title: 'Error testing leakage gate',
          text: err.message,
        });
      }
    }
  };

  return (
    <div className="netra-app">
      <Header
        connected={connected}
        health={health}
        apiUrl={apiUrl}
        onUpdateApiUrl={handleUpdateApiUrl}
        recheckNow={recheckNow}
      />

      <main className="netra-main">
        {/* Leakage Test Feedback Banner */}
        {leakageAlert && (
          <div className={`leakage-banner ${leakageAlert.type} animate-slide-down`}>
            <div className="leakage-banner-content">
              <strong>{leakageAlert.title}</strong>
              <p>{leakageAlert.text}</p>
            </div>
            <button
              type="button"
              className="leakage-banner-close"
              onClick={() => setLeakageAlert(null)}
            >
              ✕
            </button>
          </div>
        )}

        <div className="dashboard-grid">
          {/* Left Column: Mission Control & Vault */}
          <div className="dashboard-col left-col">
            <TaskInput
              onStart={startTask}
              isRunning={isRunning}
              onStop={stopAgent}
              onReset={resetAgent}
              connected={connected}
            />

            <VaultManager
              vaultEntries={vaultEntries}
              onAddToken={addToVault}
              onSeedDemo={seedDemoVault}
              onClear={clearVault}
              onTestLeakage={handleTestLeakage}
            />

            <AgentStatus
              state={state}
              currentStep={currentStep}
              sessionId={sessionId}
              taskInstruction={taskInstruction}
              currentAction={currentAction}
              currentResponse={currentResponse}
              error={error}
              privacyBlocked={privacyBlocked}
              vaultSize={vaultSize}
            />
          </div>

          {/* Right Column: Sandbox Target & Action Stream */}
          <div className="dashboard-col right-col">
            <InteractiveSandbox
              axtree={activeAxtree}
            />

            <ActionLog
              history={history}
            />
          </div>
        </div>
      </main>

      {/* Human-in-the-loop Confirmation Modal */}
      <ConfirmationModal
        pending={pendingConfirmation}
        onConfirm={confirmAction}
        onReject={rejectAction}
      />
    </div>
  );
}
