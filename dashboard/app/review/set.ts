import { createClient } from '@supabase/supabase-js';
import type { ReviewSet } from './ReviewBoard';

// The one way in for a visitor without a session: the key in the link (?k=...), checked by review_set()
// (migration 040). Both sections of the reviewers' page open on it: Michael's replies, which it also
// returns, and Yariv's comments beside our answers, which only ask it whether the key is real.
export async function loadReviewSet(key: string): Promise<ReviewSet | null> {
  if (key.length < 20 || key.length > 100) return null;
  const db = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error } = await db.rpc('review_set', { p_key: key });
  if (error || !data) return null;
  return data as ReviewSet;
}
