import { useState, useEffect } from 'react';
import { digestApi } from '../api';
import { useTaskPoller } from '../hooks/useTaskPoller';
import styles from './GenerateButton.module.css';

const STATUS_LABELS = {
  PENDING: 'Queued in worker...',
  STARTED: 'Worker started...',
  PROGRESS: 'Generating digest...',
  SUCCESS: 'Complete',
  FAILURE: 'Failed',
};

export default function GenerateButton({ onComplete }) {
  const [taskId, setTaskId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const { status, error, result } = useTaskPoller(taskId);

  const isRunning = taskId && status && !['SUCCESS', 'FAILURE', null].includes(status);

  const handleGenerate = async () => {
    if (isRunning || submitting) return;
    setSubmitting(true);
    setTaskId(null);
    try {
      const res = await digestApi.generate();
      setTaskId(res.data.task_id);
    } catch (err) {
      console.error('Failed to enqueue task:', err);
    } finally {
      setSubmitting(false);
    }
  };

  // Notify parent when task completes
  useEffect(() => {
    if (status === 'SUCCESS' && result && onComplete) {
      onComplete(result);
    }
  }, [status, result]); 

  const getButtonLabel = () => {
    if (submitting) return '> submitting...';
    if (isRunning) return `> ${STATUS_LABELS[status] || status.toLowerCase()}`;
    if (status === 'SUCCESS') return '> generate new digest';
    if (status === 'FAILURE') return '> retry';
    return '> generate digest';
  };

  return (
    <div className={styles.container}>
      <button
        className={`${styles.btn} ${isRunning || submitting ? styles.running : ''} ${status === 'FAILURE' ? styles.failed : ''}`}
        onClick={handleGenerate}
        disabled={isRunning || submitting}
      >
        {(isRunning || submitting) && <span className={styles.spinner} />}
        <span>{getButtonLabel()}</span>
      </button>

      {isRunning && (
        <div className={styles.progress}>
          <div className={styles.progressBar}>
            <div className={styles.progressFill} />
          </div>
          <span className={styles.progressLabel}>{STATUS_LABELS[status] || status}</span>
        </div>
      )}

      {status === 'FAILURE' && (
        <div className={styles.error}>
          <span className={styles.errorIcon}>✗</span>
          {error || 'Digest generation failed'}
        </div>
      )}

      {status === 'SUCCESS' && (
        <div className={styles.success}>
          <span className={styles.successIcon}>✓</span>
          Digest saved — digest_id: {result?.digest_id}
        </div>
      )}
    </div>
  );
}