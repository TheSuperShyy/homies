import type { Metadata } from 'next';
import ReviewBoard from './ReviewBoard';
import { loadReviewSet } from './set';
import styles from './review.module.css';

// 22 Nov: the owner saw the 10 Nov set again after the new one went live ("look it goes back like this"), while
// the server was serving the new one. So nothing on the reviewers' page is cached: not the page, and not the
// set's fetch (supabase-js posts with an Authorization header, which Next may otherwise keep).
export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';

// The reviewers' page (owner, 10 Nov: "push it live to vercel make sure the data can be saved on a
// database so we can retrieve it add a send button"). It shows Michael's real replies, and each one is
// marked right or wrong, with a comment. "Send" stores the marks in reply_reviews (migration 040).
//
// It opens without a login (middleware.ts lets /review through), so it shows nothing without the key
// in its link (?k=...). The replies come from review_set(), the only way in for a visitor without a
// session. They are not in this repo, which is public: they quote a real flat's balance.
//
// Since 11 Nov the page has a second section, /review/yariv: Yariv's comments beside our answers. The key
// check moved to set.ts so both sections open on the same one.
export const metadata: Metadata = {
  title: 'בדיקת התשובות של מיכאל',
  robots: { index: false, follow: false },
};

export default async function ReviewPage({
  searchParams,
}: {
  searchParams: { k?: string | string[]; show?: string | string[] };
}) {
  const key = typeof searchParams.k === 'string' ? searchParams.k : '';
  const set = await loadReviewSet(key);
  if (!set) {
    return (
      <main className={styles.missing} dir="rtl" lang="he">
        <h1>הקישור לא תקין</h1>
        <p>כדי לבדוק את התשובות של מיכאל צריך את הקישור המלא שקיבלתם, עם המפתח שבסופו.</p>
      </main>
    );
  }
  // 22 Nov: `show` picks a batch of the set (the newest answers, or the 10 Nov ones); ReviewBoard checks it.
  const show = typeof searchParams.show === 'string' ? searchParams.show : undefined;
  return <ReviewBoard set={set} reviewKey={key} initialView={show} />;
}
