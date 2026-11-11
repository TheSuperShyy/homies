import Link from 'next/link';
import styles from './review.module.css';

// The reviewers' page has two sections since 11 Nov: Michael's replies, and Yariv's comments beside our
// answers. Each opens only with the key in its link, so the key rides along in both tabs.
export default function ReviewTabs({ reviewKey, current }: { reviewKey: string; current: 'replies' | 'yariv' }) {
  const q = `?k=${encodeURIComponent(reviewKey)}`;
  return (
    <nav className={styles.tabs} aria-label="חלקי הדף">
      <div className={`${styles.wrap} ${styles.tabsInner}`}>
        <Link className={styles.tab} href={`/review${q}`} aria-current={current === 'replies' ? 'page' : undefined}>
          התשובות של מיכאל
        </Link>
        <Link className={styles.tab} href={`/review/yariv${q}`} aria-current={current === 'yariv' ? 'page' : undefined}>
          ההערות של יריב
        </Link>
      </div>
    </nav>
  );
}
