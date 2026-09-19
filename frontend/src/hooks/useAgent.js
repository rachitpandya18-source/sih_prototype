import { useState, useCallback, useRef, useEffect } from 'react';
import { planAction, NetraApiError } from '../services/api.js';
import { TokenVault } from '../services/privacy.js';
import { executeAction } from '../services/executor.js';
import { extractPagePerception } from '../services/dom.js';
import { generateSessionId, AGENT_STATES } from '../utils/helpers.js';

/**
 * useAgent — Core orchestrator hook for the NETRA agent loop.
 *
 * Manages:
 * - Session state
 * - observe → sanitize → plan → confirm → execute → re-observe loop
 * - Action history
 * - Token vault
 * - Error handling
 */
export function useAgent() {
  const [state, setState] = useState(AGENT_STATES.IDLE);
  const [currentStep, setCurrentStep] = useState(1);
  const [sessionId, setSessionId] = useState(() => generateSessionId());
  const [taskInstruction, setTaskInstruction] = useState('');
  const [history, setHistory] = useState([]);
  const [currentAction, setCurrentAction] = useState(null);
  const [currentResponse, setCurrentResponse] = useState(null);
  const [error, setError] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [privacyBlocked, setPrivacyBlocked] = useState(false);
  const [pendingConfirmation, setPendingConfirmation] = useState(null);
  const [vaultEntries, setVaultEntries] = useState([]);

  const stopRef = useRef(false);
  const vaultRef = useRef(new TokenVault());
  const runStepRef = useRef(null);

  const syncVaultEntries = useCallback(() => {
    const entries = [];
    for (const [token, realVal] of vaultRef.current._store) {
      const match = token.match(/^\[([A-Z][A-Z0-9_-]+)_\d+\]$/);
      entries.push({
        token,
        category: match ? match[1] : 'DATA',
        value: realVal,
      });
    }
    setVaultEntries(entries);
  }, []);

  /**
   * Execute a single step in the agent loop.
   */
  const runStep = useCallback(async (instruction, sid, step, hist) => {
    if (stopRef.current) {
      setState(AGENT_STATES.STOPPED);
      setIsRunning(false);
      return;
    }

    try {
      // Phase 1: Observe
      setState(AGENT_STATES.OBSERVING);
      await delay(250);

      // Phase 2: Sanitize & Redact
      setState(AGENT_STATES.SANITIZING);
      const { sanitized_axtree, detected_ui_elements } = extractPagePerception(null, vaultRef.current);
      await delay(200);

      const payload = {
        session_id: sid,
        step_number: step,
        task_instruction: instruction,
        current_url: window.location.href,
        page_title: document.title,
        sanitized_axtree,
        detected_ui_elements,
        masked_token_map: vaultRef.current.getMaskedTokenMap(),
        history: hist,
        viewport_width: window.innerWidth,
        viewport_height: window.innerHeight,
        device_pixel_ratio: window.devicePixelRatio || 1,
      };

      // Phase 3: Plan
      setState(AGENT_STATES.PLANNING);
      const response = await planAction(payload);
      setCurrentResponse(response);

      if (!response.ok) {
        throw new Error(response.decision_rationale || 'Backend returned ok=false');
      }

      const action = {
        action_type: response.action_type,
        target_id: response.target_id,
        target_bbox: response.target_bbox,
        target_coords: response.target_coords,
        value: response.value,
        value_ref: response.value_ref,
        direction: response.direction,
        amount: response.amount,
        url: response.url,
        ms: response.ms,
        requires_human_confirmation: response.requires_human_confirmation,
        decision_rationale: response.decision_rationale,
        is_task_complete: response.is_task_complete,
        confidence: response.confidence,
      };

      setCurrentAction(action);

      // Phase 4: Check for human confirmation
      if (action.requires_human_confirmation || action.action_type === 'REQUEST_CONFIRMATION') {
        setState(AGENT_STATES.AWAITING_CONFIRMATION);
        setPendingConfirmation({
          action,
          instruction,
          sessionId: sid,
          stepNumber: step,
          history: hist,
        });
        return; // Pauses here until user confirms or rejects
      }

      // Phase 5: Check for task completion
      if (action.is_task_complete || action.action_type === 'FINISH') {
        const completedEntry = {
          action: action.action_type,
          target_id: action.target_id || null,
          status: 'SUCCESS',
          step_number: step,
          rationale: action.decision_rationale,
          confidence: action.confidence,
          timestamp: new Date().toISOString(),
        };

        const newHist = [...hist, completedEntry];
        setHistory(newHist);
        setState(AGENT_STATES.COMPLETED);
        setIsRunning(false);
        return;
      }

      // Phase 6: Execute
      setState(AGENT_STATES.EXECUTING);
      const result = await executeAction(action, { tokenVault: vaultRef.current });

      const histEntry = {
        action: action.action_type,
        target_id: action.target_id || null,
        status: result.success ? 'SUCCESS' : 'FAILED',
        step_number: step,
        rationale: action.decision_rationale,
        confidence: action.confidence,
        timestamp: new Date().toISOString(),
        ...(result.error && { error: result.error }),
        ...(result.message && { message: result.message }),
      };

      const newHist = [...hist, histEntry];
      setHistory(newHist);

      if (!result.success) {
        setError(`Execution failed: ${result.error}`);
        setState(AGENT_STATES.ERROR);
        setIsRunning(false);
        return;
      }

      // Phase 7: Re-observe — next step
      const nextStep = step + 1;
      setCurrentStep(nextStep);

      // Small delay before re-observe
      await delay(500);

      // Continue the loop
      if (runStepRef.current) {
        await runStepRef.current(instruction, sid, nextStep, newHist);
      }
    } catch (err) {
      if (err instanceof NetraApiError && err.code === 'PII_LEAKAGE_REJECTED') {
        setPrivacyBlocked(true);
        setState(AGENT_STATES.PRIVACY_BLOCKED);
        setError('Privacy violation: The backend detected PII leakage in the request. Data was NOT processed.');
      } else if (err instanceof NetraApiError && err.code === 'CONNECTION_ERROR') {
        setError(`Cannot reach NETRA backend: ${err.message}`);
        setState(AGENT_STATES.ERROR);
      } else {
        setError(err.message || 'Unknown error');
        setState(AGENT_STATES.ERROR);
      }
      setIsRunning(false);
    }
  }, []);

  useEffect(() => {
    runStepRef.current = runStep;
  }, [runStep]);

  /**
   * Start a new agent task.
   */
  const startTask = useCallback(async (instruction) => {
    if (!instruction?.trim()) return;

    stopRef.current = false;
    setTaskInstruction(instruction);
    setIsRunning(true);
    setError(null);
    setPrivacyBlocked(false);
    setHistory([]);
    setCurrentAction(null);
    setCurrentResponse(null);
    setCurrentStep(1);

    const sid = generateSessionId();
    setSessionId(sid);

    if (runStepRef.current) {
      await runStepRef.current(instruction, sid, 1, []);
    }
  }, []);

  /**
   * Stop the agent loop.
   */
  const stopAgent = useCallback(() => {
    stopRef.current = true;
    setState(AGENT_STATES.STOPPED);
    setIsRunning(false);
    setPendingConfirmation(null);
  }, []);

  /**
   * Confirm a pending action (human-in-the-loop).
   */
  const confirmAction = useCallback(async () => {
    if (!pendingConfirmation) return;

    const { action, instruction, sessionId: sid, stepNumber, history: hist } = pendingConfirmation;
    setPendingConfirmation(null);

    // Execute the confirmed action
    setState(AGENT_STATES.EXECUTING);
    const result = await executeAction(action, { tokenVault: vaultRef.current });

    const histEntry = {
      action: action.action_type,
      target_id: action.target_id || null,
      status: result.success ? 'SUCCESS' : 'FAILED',
      step_number: stepNumber,
      rationale: action.decision_rationale,
      confidence: action.confidence,
      timestamp: new Date().toISOString(),
      confirmed_by_human: true,
    };

    const newHist = [...hist, histEntry];
    setHistory(newHist);

    if (action.is_task_complete || action.action_type === 'FINISH') {
      setState(AGENT_STATES.COMPLETED);
      setIsRunning(false);
      return;
    }

    const nextStep = stepNumber + 1;
    setCurrentStep(nextStep);

    await delay(500);
    if (runStepRef.current) {
      await runStepRef.current(instruction, sid, nextStep, newHist);
    }
  }, [pendingConfirmation]);

  /**
   * Reject a pending action.
   */
  const rejectAction = useCallback(() => {
    if (!pendingConfirmation) return;

    const { stepNumber, history: hist } = pendingConfirmation;

    const histEntry = {
      action: pendingConfirmation.action.action_type,
      target_id: pendingConfirmation.action.target_id || null,
      status: 'REJECTED_BY_USER',
      step_number: stepNumber,
      timestamp: new Date().toISOString(),
    };

    setHistory([...hist, histEntry]);
    setPendingConfirmation(null);
    setState(AGENT_STATES.STOPPED);
    setIsRunning(false);
  }, [pendingConfirmation]);

  /**
   * Reset agent to idle state.
   */
  const resetAgent = useCallback(() => {
    stopRef.current = true;
    setState(AGENT_STATES.IDLE);
    setCurrentStep(1);
    setTaskInstruction('');
    setHistory([]);
    setCurrentAction(null);
    setCurrentResponse(null);
    setError(null);
    setIsRunning(false);
    setPrivacyBlocked(false);
    setPendingConfirmation(null);
    vaultRef.current.clear();
    setVaultEntries([]);
    setSessionId(generateSessionId());
  }, []);

  /**
   * Add a value to the token vault.
   */
  const addToVault = useCallback((category, value) => {
    const token = vaultRef.current.store(category, value);
    syncVaultEntries();
    return token;
  }, [syncVaultEntries]);

  /**
   * Seed vault with demo PII data for quick testing.
   */
  const seedDemoVault = useCallback(() => {
    vaultRef.current.clear();
    vaultRef.current.store('NAME', 'Aditya Sharma');
    vaultRef.current.store('EMAIL', 'aditya.sharma@example.gov.in');
    vaultRef.current.store('PHONE', '+91 98765 43210');
    vaultRef.current.store('AADHAAR', '5432 9876 1234');
    syncVaultEntries();
  }, [syncVaultEntries]);

  /**
   * Clear all vault tokens.
   */
  const clearVault = useCallback(() => {
    vaultRef.current.clear();
    syncVaultEntries();
  }, [syncVaultEntries]);

  return {
    // State
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
    vaultSize: vaultEntries.length,
    vaultEntries,

    // Actions
    startTask,
    stopAgent,
    confirmAction,
    rejectAction,
    resetAgent,
    addToVault,
    seedDemoVault,
    clearVault,
  };
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
