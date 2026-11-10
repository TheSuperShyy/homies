import type { Metadata } from 'next';
import { createClient } from '@supabase/supabase-js';
import ReviewBoard, { type ReviewSet } from './ReviewBoard';
import styles from './review.module.css';

// The reviewers' page (owner, 10 Nov: "push it live to vercel make sure the data can be saved on a
// database so we can retrieve it add a send button"). It shows Michael's real replies, and each one is
// marked right or wrong, with a comment. "Send" stores the marks in reply_reviews (migration 040).
//
// It opens without a login (middleware.ts lets /review through), so it shows nothing without the key
// in its link (?k=...). The replies come from review_set(), the only way in for a visitor without a
// session. They are not in this repo, which is public: they quote a real flat's balance.
export const metadata: Metadata = {
  title: 'בדיקת התשובות של מיכאל',
  robots: { index: false, follow: false },
};

async function load(key: string): Promise<ReviewSet | null> {
  if (key.length < 20 || key.length > 100) return null;
  const db = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error } = await db.rpc('review_set', { p_key: key });
  if (error || !data) return null;
  return data as ReviewSet;
}

export default async function ReviewPage({ searchParams }: { searchParams: { k?: string | string[] } }) {
  const key = typeof searchParams.k === 'string' ? searchParams.k : '';
  const set = await load(key);
  if (!set) {
    return (
      <main className={styles.missing} dir="rtl" lang="he">
        <h1>הקישור לא תקין</h1>
        <p>כדי לבדוק את התשובות של מיכאל צריך את הקישור המלא שקיבלתם, עם המפתח שבסופו.</p>
      </main>
    );
  }
  return <ReviewBoard set={set} reviewKey={key} />;
}
