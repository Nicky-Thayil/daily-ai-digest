import styles from './HistorySidebar.module.css';

export default function HistorySidebar({ digests, currentId, onSelect, loading }) {
  const fmt = (iso) => {
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.title}>
        <span className={styles.titleLabel}>// history</span>
      </div>

      {loading && (
        <div className={styles.loading}>
          <span className={styles.loadingDot} />
          loading...
        </div>
      )}

      {!loading && digests.length === 0 && (
        <div className={styles.empty}>no digests yet</div>
      )}

      <div className={styles.list}>
        {digests.map((d) => (
          <button
            key={d.id}
            className={`${styles.item} ${d.id === currentId ? styles.active : ''}`}
            onClick={() => onSelect(d.id)}
          >
            <div className={styles.itemTop}>
              <span className={styles.itemId}>#{d.id}</span>
              <span className={styles.itemCount}>{d.total_articles_summarized} arts</span>
            </div>
            <div className={styles.itemDate}>{fmt(d.generated_at)}</div>
          </button>
        ))}
      </div>
    </aside>
  );
}
