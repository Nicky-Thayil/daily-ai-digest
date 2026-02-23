import { useState, useEffect } from 'react';
import styles from './Header.module.css';

export default function Header() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const fmt = (d) => d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <span className={styles.logo}>
          <span className={styles.bracket}>[</span>
          <span className={styles.logoText}>FLASH</span>
          <span className={styles.bracket}>]</span>
        </span>
        <span className={styles.tagline}>AI Topic Digest</span>
      </div>
      <div className={styles.right}>
        <span className={styles.clock}>{fmt(time)}</span>
        <span className={styles.dot} />
        <span className={styles.live}>LIVE</span>
      </div>
    </header>
  );
}
