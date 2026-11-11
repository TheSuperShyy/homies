import type { Metadata } from 'next';
import ReviewTabs from '../Tabs';
import { loadReviewSet } from '../set';
import base from '../review.module.css';
import styles from './yariv.module.css';
import { REPLIES, STATUSES, countByStatus, type Reply } from './replies';
import { paragraphs, runs } from './whole';

// The reviewers' page, second section (owner, 11 Nov: "create a new section ... on the right its yariv
// comment and on the left that answer", then "ok push live"). One row for each of Yariv's twelve comments
// of 9 Nov: the comment as written on the right, our answer on the left, with the check's number and a
// status word. Hebrew only.
//
// It opens with the same key as Michael's replies (middleware.ts lets /review/yariv through), so one link
// from the owner reaches both sections and a visitor without it sees neither. The content is in
// replies.ts: nothing in it is a tenant's.
export const metadata: Metadata = {
  title: REPLIES.title,
  robots: { index: false, follow: false },
};

const L = REPLIES.labels;
const WORD: Record<Reply['status'], string> = { done: L.done, same: L.same, answered: L.answered };
const COUNT: Record<Reply['status'], string> = { done: L.countDone, same: L.countSame, answered: L.countAnswered };

function Text({ text }: { text: string }) {
  return (
    <>
      {paragraphs(text).map((p, i) => (
        <p key={i}>
          {runs(p).map((r, j) => (r.whole ? <span key={j} className={styles.whole}>{r.text}</span> : r.text))}
        </p>
      ))}
    </>
  );
}

export default async function YarivPage({ searchParams }: { searchParams: { k?: string | string[] } }) {
  const key = typeof searchParams.k === 'string' ? searchParams.k : '';
  const set = await loadReviewSet(key);
  if (!set) {
    return (
      <main className={base.missing} dir="rtl" lang="he">
        <h1>הקישור לא תקין</h1>
        <p>כדי לפתוח את הדף צריך את הקישור המלא שקיבלתם, עם המפתח שבסופו.</p>
      </main>
    );
  }
  const n = countByStatus(REPLIES.items);
  return (
    <div className={`${base.page} ${styles.section}`} dir="rtl" lang="he">
      <ReviewTabs reviewKey={key} current="yariv" />
      <main className={styles.wide}>
        <header className={base.intro}>
          <h1>{REPLIES.title}</h1>
          <p className={base.lede}>{REPLIES.lede}</p>
          <ul className={styles.counts}>
            {STATUSES.filter((s) => n[s] > 0).map((s) => (
              <li key={s}>
                <span className={`${styles.pill} ${styles[s]}`}>
                  {n[s]} {COUNT[s]}
                </span>
              </li>
            ))}
          </ul>
        </header>

        <div className={styles.heads} aria-hidden="true">
          <div>{L.comment}</div>
          <div>{L.answer}</div>
        </div>

        <ol className={styles.rows}>
          {REPLIES.items.map((i) => (
            <li key={i.id} className={styles.row} id={`c-${i.id.replace('.', '-')}`}>
              <div className={styles.rowTop}>
                <h2 className={styles.check}>
                  {L.check} <span className={styles.num}>{i.id}</span>
                </h2>
                <span className={`${styles.pill} ${styles[i.status]}`}>
                  {WORD[i.status]}
                  {i.statusNote && <span className={styles.sub}> · {i.statusNote}</span>}
                </span>
              </div>
              <div className={styles.cols}>
                <div className={styles.comment}>
                  <div className={styles.label}>{L.comment}</div>
                  <div className={styles.text}>
                    <Text text={i.comment} />
                  </div>
                </div>
                <div className={styles.answer}>
                  <div className={styles.label}>{L.answer}</div>
                  <div className={styles.text}>
                    <Text text={i.answer} />
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ol>

        <p className={styles.foot}>{REPLIES.updated}</p>
      </main>
    </div>
  );
}
