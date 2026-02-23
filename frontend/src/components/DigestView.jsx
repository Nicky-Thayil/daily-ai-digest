import TopicCard from './TopicCard';
import styles from './DigestView.module.css';

export default function DigestView({ digest }) {
  if (!digest) return null;

  const generatedAt = new Date(digest.generated_at);
  const fmt = (d) => d.toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
  });

  return (
    <div className={styles.container}>
      <div className={styles.meta}>
        <div className={styles.metaLeft}>
          <span className={styles.label}>digest_id</span>
          <span className={styles.value}>{digest.id || '—'}</span>
          <span className={styles.sep}>/</span>
          <span className={styles.label}>generated</span>
          <span className={styles.value}>{fmt(generatedAt)}</span>
        </div>
        <div className={styles.metaRight}>
          <span className={styles.label}>articles_summarized</span>
          <span className={styles.value}>{digest.total_articles_summarized}</span>
          <span className={styles.sep}>/</span>
          <span className={styles.label}>topics</span>
          <span className={styles.value}>{digest.topics?.length}</span>
        </div>
      </div>

      <div className={styles.grid}>
        {digest.topics?.map((topic) => (
          <TopicCard key={topic.topic_id} topic={topic} />
        ))}
      </div>
    </div>
  );
}
