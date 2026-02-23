import { useState, useEffect, useRef, useCallback } from 'react';
import { digestApi } from '../api';

const POLL_INTERVAL_MS = 2000;

/**
 * Polls the backend task status endpoint every 2 seconds until completion.
 * Returns { status, progress, result, error, isPolling }
 */
export function useTaskPoller(taskId) {
  const [status, setStatus] = useState(null);    // PENDING | STARTED | PROGRESS | SUCCESS | FAILURE
  const [progress, setProgress] = useState(null); // custom meta from PROGRESS state
  const [result, setResult] = useState(null);     // SUCCESS result payload
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!taskId) return;

    // Reset on new taskId
    setStatus('PENDING');
    setProgress(null);
    setResult(null);
    setError(null);

    const poll = async () => {
      try {
        const res = await digestApi.status(taskId);
        const data = res.data;

        setStatus(data.status);

        if (data.status === 'PROGRESS') {
          setProgress(data.info);
        }

        if (data.status === 'SUCCESS') {
          setResult(data.result);
          stop();
        }

        if (data.status === 'FAILURE') {
          setError(data.error || 'Task failed');
          stop();
        }
      } catch (err) {
        setError(err.message || 'Network error');
        stop();
      }
    };

    poll(); // immediate first call
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return stop;
  }, [taskId, stop]);

  return {
    status,
    progress,
    result,
    error,
    isPolling: intervalRef.current !== null,
  };
}
