import { useState, useEffect, useRef, useCallback } from 'react';
import { checkHealth, getConfig } from '../services/api.js';

/**
 * useBackendStatus — Polls backend health and config.
 * Updates connection status for the UI.
 */
export function useBackendStatus(intervalMs = 8000) {
  const [connected, setConnected] = useState(false);
  const [health, setHealth] = useState(null);
  const [config, setConfig] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);
  const [checking, setChecking] = useState(false);
  const intervalRef = useRef(null);

  const check = useCallback(async () => {
    setChecking(true);
    try {
      const [h, c] = await Promise.all([checkHealth(), getConfig()]);
      setHealth(h);
      setConfig(c);
      setConnected(true);
    } catch {
      setConnected(false);
      setHealth(null);
      setConfig(null);
    } finally {
      setLastChecked(new Date());
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      check();
    }, 0);
    intervalRef.current = setInterval(check, intervalMs);
    return () => {
      clearTimeout(timer);
      clearInterval(intervalRef.current);
    };
  }, [check, intervalMs]);

  return { connected, health, config, lastChecked, checking, recheckNow: check };
}
