import { useState } from 'react';
import styles from './TopicCard.module.css';

const TOPIC_COLORS = {
  ai: '#00ff87',
  programming: '#4488ff',
  space: '#aa88ff',
  football: '#ffb800',
  cars: '#ff6644',
  food: '#ff88aa',
  physics: '#44ddff',
  mathematics: '#88ff44',
  biology: '#ff44dd',
};

export default function TopicCard({ topic }) {
  const [expanded, setExpanded] = useState(true);
  const accent = TOPIC_COLORS[topic.topic_id] || '#888888';

  return (
    <div className={styles.card} style={{ '--accent': accent }}>
      <button
        className={styles.header}
        onClick={() => setExpanded(e => !e)}
      >
        <div className={styles.headerLeft}>
          <span className={styles.indicator} />
          <span className={styles.topicId}>#{topic.topic_id}</span>
          <span className={styles.topicName}>{topic.topic_name}</span>
        </div>
        <div className={styles.headerRight}>
          <span className={styles.count}>{topic.article_count} articles</span>
          <span className={styles.chevron}>{expanded ? '−' : '+'}</span>
        </div>
      </button>

      {expanded && (
        <div className={styles.body}>
          {topic.bullets.map((bullet, i) => {
            // Strip leading "• " if present
            const text = bullet.replace(/^[•\-]\s*/, '');
            return (
              <div key={i} className={styles.bullet} style={{ animationDelay: `${i * 60}ms` }}>
                <span className={styles.bulletDot}>→</span>
                <span className={styles.bulletText}>{text}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
