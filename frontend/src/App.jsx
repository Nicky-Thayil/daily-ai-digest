import { useState, useEffect, useCallback, useRef } from 'react';
import { digestApi } from './api';
import Header from './components/Header';
import GenerateButton from './components/GenerateButton';
import DigestView from './components/DigestView';
import HistorySidebar from './components/HistorySidebar';
import styles from './App.module.css';

export default function App() {
  const [digest, setDigest] = useState(null);
  const [digests, setDigests] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [loadingLatest, setLoadingLatest] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [loadingDigest, setLoadingDigest] = useState(false);
  const completedResult = useRef(null);

  // Load history list
  const fetchHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const res = await digestApi.list();
      // Handle both {digests: [...]} and [...] response shapes
      const data = res.data;
      setDigests(Array.isArray(data) ? data : (data.digests || []));
    } catch {
      setDigests([]);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  // Load latest digest on mount
  useEffect(() => {
    const init = async () => {
      setLoadingLatest(true);
      try {
        const res = await digestApi.latest();
        setDigest(res.data);
        setCurrentId(res.data.id);
      } catch (err) {
        if (err.response?.status !== 404) {
          console.error('Failed to load latest digest:', err);
        }
      } finally {
        setLoadingLatest(false);
      }
    };
    init();
    fetchHistory();
  }, [fetchHistory]);

  // Load a specific digest when selected from history
  const handleSelectDigest = async (id) => {
    if (id === currentId) return;
    setLoadingDigest(true);
    try {
      const res = await digestApi.byId(id);
      setDigest(res.data);
      setCurrentId(id);
    } catch (err) {
      console.error('Failed to load digest:', err);
    } finally {
      setLoadingDigest(false);
    }
  };

  // Store the completed task result in a ref so we can fetch the new digest in an effect (no side effects during render).
  const handleGenComplete = useCallback((result) => {
    completedResult.current = result;
  }, []);

  useEffect(() => {
    if (!completedResult.current) return;
    const result = completedResult.current;
    completedResult.current = null;

    const load = async () => {
      try {
        const res = await digestApi.byId(result.digest_id);
        setDigest(res.data);
        setCurrentId(result.digest_id);
      } catch (err) {
        console.error('Failed to load new digest:', err);
      }
      fetchHistory();
    };
    load();
  }, [completedResult.current, fetchHistory]); 

  const isEmpty = !loadingLatest && !digest;

  return (
    <div className={styles.app}>
      <Header />

      <div className={styles.layout}>
        <HistorySidebar
          digests={digests}
          currentId={currentId}
          onSelect={handleSelectDigest}
          loading={loadingHistory}
        />

        <main className={styles.main}>
          <div className={styles.toolbar}>
            <div className={styles.toolbarLeft}>
              {digest && (
                <span className={styles.breadcrumb}>
                  <span className={styles.breadcrumbMuted}>digest</span>
                  <span className={styles.breadcrumbSep}>/</span>
                  <span className={styles.breadcrumbId}>#{currentId}</span>
                </span>
              )}
            </div>
            <GenerateButton onComplete={handleGenComplete} />
          </div>

          <div className={styles.content}>
            {loadingLatest && (
              <div className={styles.loading}>
                <div className={styles.loadingBar} />
                <span>loading latest digest...</span>
              </div>
            )}

            {loadingDigest && !loadingLatest && (
              <div className={styles.loading}>
                <div className={styles.loadingBar} />
                <span>loading digest #{currentId}...</span>
              </div>
            )}

            {isEmpty && (
              <div className={styles.empty}>
                <div className={styles.emptyTitle}>
                  <span className={styles.emptyBracket}>[</span>
                  NO DIGEST FOUND
                  <span className={styles.emptyBracket}>]</span>
                </div>
                <div className={styles.emptySubtitle}>
                  Generate your first digest to get started.
                </div>
                <div className={styles.emptyHint}>
                  <span className={styles.cursor}>_</span>
                </div>
              </div>
            )}

            {!loadingLatest && !loadingDigest && digest && (
              <DigestView digest={digest} />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
