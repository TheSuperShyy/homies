'use client';

import { useEffect, useMemo, useState } from 'react';
import { browserClient } from '@/lib/supabase-browser';
import ReviewTabs from './Tabs';
import { chatsFor, toBatchView, type Batch } from './batches';
import styles from './review.module.css';

// One review set: chats of steps, each step a message (or a button tap) and Michael's replies to it.
export type Step = {
  id: string;
  at: string;
  kind: 'text' | 'tap' | 'greeting';
  sent: string;
  replies: string[];
  buttons?: string[];
  note?: string;
};
export type Chat = { n: number; title: string; steps: Step[]; batch?: string };
export type ReviewSet = {
  id: string;
  title: string;
  data: { intro?: string; date?: string; chats: Chat[]; batches?: Batch[] };
};

type Mark = { m: 'pass' | 'fail' | null; n: string };
type Marks = Record<string, Mark>;
type Status = { kind: 'idle' | 'sending' | 'sent' | 'error'; text: string };

const FILTERS = [
  { id: 'all', label: 'הכול' },
  { id: 'open', label: 'עוד לא נבדקו' },
  { id: 'fail', label: 'לא נכון' },
] as const;
type Filter = (typeof FILTERS)[number]['id'];

const EMPTY: Mark = { m: null, n: '' };
const latin = (s: string) => /^[A-Za-z]/.test(s.trim());

export default function ReviewBoard({
  set,
  reviewKey,
  initialView,
}: {
  set: ReviewSet;
  reviewKey: string;
  initialView?: string;
}) {
  const storeKey = `homies-review:${set.id}`;
  const batches = useMemo(() => set.data.batches ?? [], [set]);
  // Which batch is shown (22 Nov). The choice is `show` in the address, kept without a reload, so a view can
  // be linked to; the counts in the bar follow it, and "send" still sends every mark.
  const [view, setView] = useState(() => toBatchView(initialView, batches));
  const chats = useMemo(() => chatsFor(view, set.data.chats), [view, set]);
  const steps = useMemo(() => chats.flatMap((c) => c.steps), [chats]);
  const [marks, setMarks] = useState<Marks>({});
  const [notesOpen, setNotesOpen] = useState<Record<string, boolean>>({});
  const [filter, setFilter] = useState<Filter>('all');
  const [status, setStatus] = useState<Status>({ kind: 'idle', text: '' });
  const [loaded, setLoaded] = useState(false);

  // The marks are kept in this browser until they are sent, so a reload loses nothing. Sending again
  // after a change stores a new copy; every send is kept.
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storeKey);
      if (raw) setMarks(JSON.parse(raw) as Marks);
    } catch {
      /* storage blocked: the marks last for this visit */
    }
    setLoaded(true);
  }, [storeKey]);
  useEffect(() => {
    if (!loaded) return;
    try {
      window.localStorage.setItem(storeKey, JSON.stringify(marks));
    } catch {
      /* ignore */
    }
  }, [marks, loaded, storeKey]);

  const passed = steps.filter((s) => marks[s.id]?.m === 'pass').length;
  const failed = steps.filter((s) => marks[s.id]?.m === 'fail').length;
  const total = steps.length;

  function pickView(v: string) {
    setView(v);
    try {
      const u = new URL(window.location.href);
      if (v === 'all') u.searchParams.delete('show');
      else u.searchParams.set('show', v);
      window.history.replaceState(null, '', u.toString());
    } catch {
      /* the view still changes */
    }
  }

  function setMark(id: string, m: 'pass' | 'fail') {
    setMarks((prev) => {
      const cur = prev[id] ?? EMPTY;
      return { ...prev, [id]: { ...cur, m: cur.m === m ? null : m } };
    });
    if (m === 'fail') setNotesOpen((o) => ({ ...o, [id]: true }));
    setStatus({ kind: 'idle', text: '' });
  }

  function setNote(id: string, n: string) {
    setMarks((prev) => ({ ...prev, [id]: { ...(prev[id] ?? EMPTY), n } }));
    setStatus({ kind: 'idle', text: '' });
  }

  async function send() {
    if (status.kind === 'sending') return;
    if (!Object.values(marks).some((x) => x.m || x.n.trim())) {
      setStatus({ kind: 'error', text: 'עוד לא סימנת אף תשובה.' });
      return;
    }
    setStatus({ kind: 'sending', text: 'שולח…' });
    const { data, error } = await browserClient().rpc('submit_reply_review', { p_key: reviewKey, p_marks: marks });
    if (error) {
      setStatus({ kind: 'error', text: 'השליחה לא הצליחה. נסו שוב בעוד רגע.' });
      return;
    }
    const r = (data ?? {}) as { passed?: number; failed?: number };
    setStatus({ kind: 'sent', text: `נשלח, תודה! ${r.passed ?? passed} נכון, ${r.failed ?? failed} לא נכון.` });
  }

  const shown = (s: Step) => {
    const m = marks[s.id]?.m ?? null;
    return filter === 'all' || (filter === 'open' && !m) || (filter === 'fail' && m === 'fail');
  };
  const statusLine = status.text ? (
    <p className={status.kind === 'error' ? styles.statusBad : styles.status} role="status">
      {status.text}
    </p>
  ) : null;

  return (
    <div className={styles.page} dir="rtl" lang="he">
      <ReviewTabs reviewKey={reviewKey} current="replies" />
      <header className={styles.bar}>
        <div className={`${styles.wrap} ${styles.barInner}`}>
          <span className={styles.barTitle}>בדיקת התשובות של מיכאל</span>
          <span className={styles.counts}>
            נבדקו <b>{passed + failed}</b> מתוך <b>{total}</b> ·{' '}
            <span className={styles.cPass}>
              <b>{passed}</b> נכון
            </span>{' '}
            ·{' '}
            <span className={styles.cFail}>
              <b>{failed}</b> לא נכון
            </span>
          </span>
          <span className={styles.meter} aria-hidden="true">
            <span className={styles.mPass} style={{ width: `${(passed / total) * 100}%` }} />
            <span className={styles.mFail} style={{ width: `${(failed / total) * 100}%` }} />
          </span>
          <span className={styles.filters} role="group" aria-label="הצגה">
            {FILTERS.map((f) => (
              <button key={f.id} type="button" className={styles.chip} aria-pressed={filter === f.id}
                      onClick={() => setFilter(f.id)}>
                {f.label}
              </button>
            ))}
          </span>
          <button type="button" className={styles.send} onClick={send} disabled={status.kind === 'sending'}>
            שליחה
          </button>
        </div>
        {statusLine && <div className={styles.wrap}>{statusLine}</div>}
      </header>

      <main className={styles.wrap}>
        <section className={styles.intro}>
          <h1>{set.title}</h1>
          {set.data.date && <p className={styles.date}>{set.data.date}</p>}
          {set.data.intro && <p className={styles.lede}>{set.data.intro}</p>}
          {batches.length > 0 && (
            <label className={styles.view}>
              <span>להציג</span>
              <select value={view} onChange={(e) => pickView(e.target.value)}>
                <option value="all">
                  כל התשובות ({set.data.chats.reduce((k, c) => k + c.steps.length, 0)})
                </option>
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.label} ({chatsFor(b.id, set.data.chats).reduce((k, c) => k + c.steps.length, 0)})
                  </option>
                ))}
              </select>
            </label>
          )}
        </section>

        {chats.map((c) => (
          <section key={c.n} className={styles.chat}>
            <div className={styles.chatHead}>
              <h2>
                {c.n}. {c.title}
              </h2>
              <span className={styles.chatCount}>
                {c.steps.filter((s) => marks[s.id]?.m).length}/{c.steps.length}
              </span>
            </div>
            <ol className={styles.steps}>
              {c.steps.filter(shown).map((s) => {
                const mk = marks[s.id] ?? EMPTY;
                const noteOpen = notesOpen[s.id] || mk.n !== '';
                return (
                  <li key={s.id} className={styles.step} data-mark={mk.m ?? 'open'}>
                    <div className={styles.stepTop}>
                      <span className={styles.tag}>{s.id}</span>
                      <span className={styles.time}>{s.at}</span>
                      <span className={styles.state}>
                        {mk.m === 'pass' ? '✓ נכון' : mk.m === 'fail' ? '✗ לא נכון' : 'לא נבדק'}
                      </span>
                    </div>
                    <div className={styles.thread}>
                      <div className={s.kind === 'tap' ? styles.tap : styles.tenant} dir={latin(s.sent) ? 'ltr' : undefined}>
                        {s.kind === 'tap' ? `לחיצה על הכפתור: ${s.sent}` : s.sent}
                      </div>
                      {s.replies.map((r, i) => (
                        <div key={i} className={styles.michael}>
                          {r}
                        </div>
                      ))}
                      {s.buttons && (
                        <div className={styles.buttons}>
                          {s.buttons.map((b) => (
                            <span key={b} className={styles.button}>
                              {b}
                            </span>
                          ))}
                        </div>
                      )}
                      {s.note && <p className={styles.note}>{s.note}</p>}
                    </div>
                    <div className={styles.actions}>
                      <button type="button" className={`${styles.mark} ${styles.pass}`} aria-pressed={mk.m === 'pass'}
                              onClick={() => setMark(s.id, 'pass')}>
                        ✓ נכון
                      </button>
                      <button type="button" className={`${styles.mark} ${styles.fail}`} aria-pressed={mk.m === 'fail'}
                              onClick={() => setMark(s.id, 'fail')}>
                        ✗ לא נכון
                      </button>
                      {noteOpen ? (
                        <textarea className={styles.noteBox} value={mk.n} placeholder="מה לא נכון? מה היה צריך להיות?"
                                  aria-label={`הערה לתשובה ${s.id}`} onChange={(e) => setNote(s.id, e.target.value)} />
                      ) : (
                        <button type="button" className={styles.noteToggle}
                                onClick={() => setNotesOpen((o) => ({ ...o, [s.id]: true }))}>
                          הוספת הערה
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>
        ))}

        <section className={styles.foot}>
          <button type="button" className={styles.sendBig} onClick={send} disabled={status.kind === 'sending'}>
            שליחת הסימונים
          </button>
          {statusLine}
          <p className={styles.small}>
            הסימונים נשמרים בדפדפן הזה עד השליחה. אפשר לשנות ולשלוח שוב, וכל שליחה נשמרת.
          </p>
        </section>
      </main>
    </div>
  );
}
