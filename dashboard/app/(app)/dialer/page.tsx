import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getLocale, translator, when, type Key, type Locale, type T } from '@/lib/i18n';
import { shekels } from '@/lib/money';
import { inCallingHours } from '@/lib/dialer-rules';
import { board, callNumber, queueCalls, resumeCalls, stopCalls, type OxsSync } from '@/lib/dialer-queue';
import {
  ACTIVE_STATUSES, MAX_TRIES, RANG_STATUSES, blockOf, israelDate, matches, monthRange, parseSummary,
  todayByPhone, type DialerCall, type Owing,
} from '@/lib/dialer-board';
import { Pager, pageFrom, pageSlice, perParam, sizeFrom } from '@/components/pager';
import { PendingButton } from '@/components/pending-button';
import { SelectAll } from '@/components/select-all';
import { CallSelected } from '@/components/call-selected';
import { AutoRefresh } from '@/components/auto-refresh';
import { IconAlert, IconCheck, IconInbox, IconInfo, IconOpenLink, IconPhoneOut } from '@/components/icons';

// Feature 23 (25 Nov), the dialer. The owner: "in the dashboard we need to have an actual dialer
// section there not just the dialer test".
//
// Everyone who owes is listed, one row per phone. A person ticks tenants and presses Call; they go
// into the queue (lib/dialer-queue.ts, migration 043), and debt-tools sends them to Omni's dialer
// one at a time: only in calling hours, only once the bot's line is quiet, at most once a day per
// tenant and four tries per debt. The tenant who picks up gets the debt agent with their figures
// (feature 18's router). Nothing here rings anybody directly, and nothing rings that a signed-in
// person did not choose: the queue runs with the page closed, and Stop empties it.
//
// The page reads top to bottom as the job does: what the line is doing, then who owes (the list
// you call from), then today's calls. Each list row is four facts and a button, two short lines
// at most, so a page of fifty reads at a glance (the owner, 25 Nov: "the design is not good").
//
// 26 Nov: the "Test calls" tab is gone (the owner: "remove the test calls its not relevant"). Its page
// (feature 20) is still in the code at /dialer/test, and lib/sections.ts sends a visitor there to the Dialer.

type Q = Partial<Record<'month' | 'q' | 'page' | 'per' | 'r' | 'n' | 'k' | 'w' | 'b' | 'p', string>>;

const OUTCOME_PARAMS = ['r', 'n', 'k', 'w', 'b', 'p'] as const;

/** Only ever back to this page, whatever the form carries. */
function backTo(v: FormDataEntryValue | null): string {
  const s = String(v ?? '');
  return /^\/dialer(\?[^#\s]*)?$/.test(s) ? s : '/dialer';
}

/** The page the form came from, with the press's outcome in place of any earlier one. */
function withOutcome(back: string, outcome: Record<string, string>): string {
  const [path, query = ''] = back.split('?');
  const q = new URLSearchParams(query);
  for (const k of OUTCOME_PARAMS) q.delete(k);
  for (const [k, v] of Object.entries(outcome)) if (v) q.set(k, v);
  const s = q.toString();
  return s ? `${path}?${s}` : path;
}

// The forms come back to the page with the outcome in the URL, as on the Debts page, so a refresh
// cannot press again. The per-row Call button sends `one`; the button above the list sends the
// ticked boxes.
async function call(formData: FormData) {
  'use server';
  const one = String(formData.get('one') ?? '');
  const phones = one ? [one] : formData.getAll('phone').map(String);
  redirect(withOutcome(backTo(formData.get('back')), await queueCalls(phones)));
}

// Feature 24: a number typed above the list. Its debt is read from OXS now, then it is queued as a
// row's Call would be (lib/dialer-queue.ts, callNumber).
async function callTyped(formData: FormData) {
  'use server';
  redirect(withOutcome(backTo(formData.get('back')), await callNumber(String(formData.get('number') ?? ''))));
}

async function stop(formData: FormData) {
  'use server';
  redirect(withOutcome(backTo(formData.get('back')), await stopCalls()));
}

async function resume(formData: FormData) {
  'use server';
  redirect(withOutcome(backTo(formData.get('back')), await resumeCalls()));
}

/** A value set inside a sentence in its own direction: a number or a name in Hebrew. */
// In the tables, a name or a phone is a <bdi> inside a block that keeps the page's direction.
// A block with its own dir= aligns to its own start, so in English a Hebrew name sat at the far
// side of its cell (25 Nov), and Chrome has no text-align: match-parent to pull it back.
const iso = (s: string) => `⁨${s}⁩`;

// The words, by code. A code the page does not know is shown as it is rather than hidden.
const WHY: Record<string, Key> = {
  number: 'dial.why.number', queued: 'dial.why.queued', today: 'dial.why.today',
  unknown: 'dial.why.unknown', dnc: 'dial.why.dnc', paid: 'dial.why.paid', tries: 'dial.why.tries',
  eligible: 'dial.why.eligible', shared: 'dial.why.shared', hours: 'dial.why.hours',
  not_connected: 'dial.why.notConnected', lost: 'dial.why.lost', no_report: 'dial.why.noReport',
  stopped: 'dial.why.stopped', off: 'dial.why.off',
};
const OUTCOME: Record<string, Key> = {
  authorized: 'outcome.authorized', promised: 'outcome.promised', disputed: 'outcome.disputed',
  refused: 'outcome.refused', transferred: 'outcome.transferred', voicemail: 'outcome.voicemail',
  wrong_party: 'outcome.wrongParty', not_handed_over: 'outcome.notHandedOver',
  no_answer: 'outcome.noAnswer', office_to_contact: 'outcome.officeToContact',
};
const STATUS: Record<string, Key> = {
  waiting: 'dial.st.waiting', sending: 'dial.st.sending', ringing: 'dial.st.ringing',
  answered: 'dial.st.answered', done: 'dial.st.done', no_answer: 'dial.st.noAnswer',
  skipped: 'dial.st.skipped', failed: 'dial.st.failed', cancelled: 'dial.st.cancelled',
};
// The ticket pills' colours: under way, picked up, done, a problem, nothing happened.
const PILL: Record<string, string> = {
  waiting: '', sending: 'in_progress', ringing: 'in_progress', answered: 'open', done: 'resolved',
  no_answer: 'needs_review', failed: 'needs_review', skipped: 'cancelled', cancelled: 'cancelled',
};

function whyText(t: T, why: string | null | undefined): string {
  const w = String(why ?? '');
  const code = w.startsWith('stopped:') ? 'stopped' : w;
  return WHY[code] ? t(WHY[code]) : w;
}

function outcomeText(t: T, o: string | null | undefined): string {
  return o ? (OUTCOME[o] ? t(OUTCOME[o]) : o) : '';
}

/** What came of one dialer row, in words: the agent's outcome, or why it did not ring. */
function resultOf(t: T, c: DialerCall): { text: string; raw?: string } {
  if (c.status === 'done') {
    return { text: outcomeText(t, c.outcome) || t('dial.talkedNoOutcome'),
             raw: c.why === 'no_report' ? whyText(t, c.why) : undefined };
  }
  if (c.status === 'failed') {
    // Tokomni's own answer ("400: invalid: …") is kept for whoever has to chase it.
    return /^\d{3}:|^no answer/.test(String(c.why ?? ''))
      ? { text: t('dial.why.refused'), raw: String(c.why) }
      : { text: whyText(t, c.why) };
  }
  if (c.status === 'skipped' || c.status === 'cancelled') return { text: whyText(t, c.why) };
  return { text: '' };
}

const by = (email: string | null) => (email ? email.split('@')[0] : '—');

/** "4 months" / "4 חודשים", and Hebrew's own word for two. */
function monthsCount(t: T, n: number) {
  return n === 1 ? t('dial.months1') : n === 2 ? t('dial.months2') : t('dial.monthsN', { n });
}

/** The tick's last complaint, if it is recent enough to still be true. */
function tickError(t: T, state: { last_tick_at: string | null; last_error: string | null } | null) {
  const e = state?.last_error;
  if (!e || !state?.last_tick_at || Date.now() - Date.parse(state.last_tick_at) > 10 * 60_000) return null;
  if (e === 'not_connected') return t('dial.errNotConnected');
  if (e.startsWith('vapi')) return t('dial.errLine', { why: iso(e) });
  return t('dial.errTick', { why: iso(e) });
}

/**
 * Where the amounts come from, and how fresh they are (feature 24): OXS's own overdue debt, copied
 * every 10 minutes and read again just before each call. Before the first full copy, and when the
 * copy has not run for a while, the note says so.
 */
function OxsNote({ t, oxs, at }: { t: T; oxs: OxsSync | null; at: (iso: string | null) => string }) {
  if (!oxs?.last_ok_at) return <div className="notice info" role="status"><IconInfo /><span>{t('dial.oxsNever')}</span></div>;
  if (!oxs.complete_at && (oxs.backlog ?? 0) > 0) {
    return <div className="notice info" role="status"><IconInfo /><span>{t('dial.oxsLoading', { n: oxs.backlog ?? 0 })}</span></div>;
  }
  if (Date.now() - Date.parse(oxs.last_ok_at) > 45 * 60_000) {
    return (
      <div className="notice bad" role="status">
        <IconAlert /><span>{t('dial.oxsStale', { at: at(oxs.last_ok_at), why: iso(oxs.last_error || '—') })}</span>
      </div>
    );
  }
  return <p className="dialhint">{t('dial.oxsNote', { at: at(oxs.last_ok_at) })}</p>;
}

/** The pill for a dialer row, in the ticket pills' colours. */
function Pill({ t, status }: { t: T; status: string }) {
  return <span className={`pill ${PILL[status] ?? ''}`}>{STATUS[status] ? t(STATUS[status]) : status}</span>;
}

/**
 * Where a tenant stands, in one cell: today's call if there is one, else why they cannot be
 * called, else the last call's result, else nothing yet. The tries ride underneath.
 */
function Standing({ t, locale, row, today, block }: {
  t: T; locale: Locale; row: Owing; today?: DialerCall; block: string | null;
}) {
  const tries = row.tries > 0 ? t('dial.triesUsed', { n: row.tries, max: MAX_TRIES }) : '';
  if (today) {
    const res = resultOf(t, today);
    return (
      <>
        <Pill t={t} status={today.status} />
        {(res.text || tries) && <span className="sub">{res.text || tries}</span>}
      </>
    );
  }
  if (block === 'dnc' || block === 'tries') {
    return <span className="muted">{whyText(t, block)}</span>;
  }
  if (row.last) {
    return (
      <>
        <span>{outcomeText(t, row.last.outcome)}</span>
        <span className="sub">{[when(row.last.created_at, locale), tries].filter(Boolean).join(' · ')}</span>
      </>
    );
  }
  return (
    <>
      <span className="muted">{t(row.tries > 0 ? 'dial.calledBefore' : 'dial.never')}</span>
      {tries && <span className="sub">{tries}</span>}
    </>
  );
}

/** The outcome of the last press, from the URL the action came back with. */
function Outcome({ t, q }: { t: T; q: Q }) {
  const reasons = parseSummary(q.w)
    .map(([code, n]) => `${whyText(t, code)} (${n})`).join(' · ');
  const box = (kind: 'ok' | 'bad' | 'info', text: string, sub?: string) => (
    <div className={`notice ${kind}`} role={kind === 'bad' ? 'alert' : 'status'}>
      {kind === 'ok' ? <IconCheck /> : kind === 'bad' ? <IconAlert /> : <IconInfo />}
      <span>{text}{sub && <span className="sub">{sub}</span>}</span>
    </div>
  );
  const n = Number(q.n ?? 0);
  const k = Number(q.k ?? 0);
  switch (q.r) {
    case 'queued':
      return n > 0
        ? box('ok', t('dial.queued', { n }), k ? t('dial.notQueued', { n: k, why: reasons }) : undefined)
        : box('bad', t('dial.noneQueued', { why: reasons || '—' }));
    case 'none': return box('info', t('dial.noneTicked'));
    case 'hours': return box('bad', t('dial.hoursRefused'));
    case 'stopped': return box('ok', t('dial.stopped', { n }));
    case 'resumed': return box('ok', t('dial.resumed'));
    case 'db': return box('bad', t('dial.errDb', { why: iso(q.b ?? '') }));
    case 'badnumber': return box('bad', t('dial.typedBad'));
    case 'nodebt': return box('info', t('dial.typedNoDebt', { phone: iso(q.p ?? '') }));
    case 'oxs': return box('bad', t('dial.typedOxs', { why: iso(q.b ?? '') }));
    default: return null;
  }
}

export default async function Dialer({ searchParams }: { searchParams?: Q }) {
  const locale = getLocale();
  const t = translator(locale);
  const q = searchParams ?? {};
  const page = pageFrom(q);
  const size = sizeFrom(q);
  const search = (q.q ?? '').trim().slice(0, 80);

  const now = new Date();
  const open = inCallingHours(now);
  const day = israelDate(now);
  const nowText = new Intl.DateTimeFormat(locale === 'he' ? 'he-IL' : 'en-GB', {
    timeZone: 'Asia/Jerusalem', weekday: 'long', hour: '2-digit', minute: '2-digit',
  }).format(now);

  const { owing, calls, state, oxs, error } = await board();
  // Today's times as the time alone; anything older keeps its date.
  const clockFmt = new Intl.DateTimeFormat(locale === 'he' ? 'he-IL' : 'en-GB', {
    timeZone: 'Asia/Jerusalem', hour: '2-digit', minute: '2-digit',
  });
  const at = (iso: string | null) => (!iso ? '—'
    : israelDate(iso) === day ? clockFmt.format(new Date(iso)) : when(iso, locale));

  // ---- the line and today ------------------------------------------------
  const active = calls.filter((c) => (ACTIVE_STATUSES as readonly string[]).includes(c.status));
  const onLine = active.find((c) => c.status !== 'waiting') ?? null;
  const waiting = active.filter((c) => c.status === 'waiting').length;
  const sentToday = calls.filter((c) => c.sent_at && israelDate(c.sent_at) === day
    && (RANG_STATUSES as readonly string[]).includes(c.status));
  const answeredToday = sentToday.filter((c) => c.status === 'answered' || c.status === 'done').length;
  const noAnswerToday = sentToday.filter((c) => c.status === 'no_answer').length;
  const todays = calls.filter((c) => israelDate(c.pressed_at) === day || active.includes(c));
  const paused = Boolean(state?.paused_at);
  // Why it paused: five in a row that reached nobody, or Tokomni refusing (its answer is on the
  // newest refused row).
  const refusedBy = calls.find((c) => c.status === 'failed' && /^\d{3}:/.test(String(c.why ?? '')));
  const pausedText = state?.paused_why === 'tokomni'
    ? t('dial.pausedTokomni', { why: iso(String(refusedBy?.why ?? '—')) })
    : t('dial.paused');
  const problem = tickError(t, state);
  const busy = Boolean(onLine) || waiting > 0;

  // ---- the list ------------------------------------------------------------
  // The 12 newest months as filters. Since feature 24 a debt can reach back years, and a chip per
  // month would fill the bar; an older month is still in every row's tooltip, and under All.
  const months = [...new Set(owing.flatMap((r) => r.months))].sort().reverse().slice(0, 12);
  const month = q.month && months.includes(q.month) ? q.month : 'all';
  const rows = owing.filter((r) => (month === 'all' || r.months.includes(month)) && matches(r, search));
  const visible = pageSlice(rows, page, size);
  const today = todayByPhone(calls, day);
  const totalOwed = rows.reduce((s, r) => s + r.owed, 0);

  // Every link and form carries the filters it is not changing, as the Debts page's do.
  const params = (over: Partial<Record<'month' | 'q' | 'page', string>>) => {
    const p = new URLSearchParams();
    const m = over.month ?? month;
    if (m !== 'all') p.set('month', m);
    const s = over.q ?? search;
    if (s) p.set('q', s);
    const per = perParam(size);
    if (per) p.set('per', per);
    const pg = over.page ?? (page > 1 ? String(page) : '');
    if (pg && pg !== '1') p.set('page', pg);
    return p;
  };
  const href = (over: Partial<Record<'month' | 'q' | 'page', string>>) => {
    const s = params(over).toString();
    return s ? `/dialer?${s}` : '/dialer';
  };
  const back = href({});

  const nowLine = onLine
    ? t(onLine.status === 'answered' ? 'dial.nowTalking' : onLine.status === 'sending' ? 'dial.nowSending' : 'dial.nowRinging',
        { name: iso(onLine.name || onLine.phone),
          since: at(onLine.answered_at ?? onLine.sent_at ?? onLine.pressed_at) })
    : t('dial.nowIdle');

  return (
    <>
      {busy && <AutoRefresh seconds={10} />}
      <div className="pagehead">
        <h1>{t('dial.title')}</h1>
        <p>{t('dial.blurb')}</p>
      </div>

      <Outcome t={t} q={q} />
      {error && (
        <div className="notice bad" role="alert"><IconAlert /><span>{t('dial.errDb', { why: iso(error) })}</span></div>
      )}
      {!open && (
        <div className="notice info" role="status">
          <IconInfo /><span>{t('dial.closed', { now: nowText })}</span>
        </div>
      )}
      {paused && (
        <div className="notice bad dialnow" role="alert">
          <IconAlert />
          <span>{pausedText}</span>
          <form action={resume}>
            <input type="hidden" name="back" value={back} />
            <PendingButton className="btn-sm" busy={t('dial.working')}>{t('dial.resume')}</PendingButton>
          </form>
        </div>
      )}
      {problem && (
        <div className="notice bad" role="alert"><IconAlert /><span>{problem}</span></div>
      )}

      {/* The line, now. Stop is here because this is where someone looks when they want it to stop. */}
      <div className={`notice dialnow${onLine ? ' live' : ''}`} role="status" aria-live="polite">
        <IconPhoneOut />
        <span>
          <b>{nowLine}</b>
          <span className="sub">{waiting ? t('dial.waitingLine', { n: waiting }) : t('dial.noneWaiting')}</span>
        </span>
        {waiting > 0 && (
          <form action={stop}>
            <input type="hidden" name="back" value={back} />
            <PendingButton className="btn-sm dialstop" busy={t('dial.working')} title={t('dial.stopNote')}>
              {t('dial.stop')}
            </PendingButton>
          </form>
        )}
      </div>

      <div className="cards">
        {([
          ['is-open', t('dial.cardWaiting'), waiting],
          ['is-progress', t('dial.cardSent'), sentToday.length],
          ['is-done', t('dial.cardAnswered'), answeredToday],
          ['is-urgent', t('dial.cardNoAnswer'), noAnswerToday],
        ] as const).map(([tone, k, v]) => (
          <div className={`card ${tone}`} key={k}>
            <div className="n">{v}</div>
            <div className="k">{k}</div>
          </div>
        ))}
      </div>

      <h2>{t('dial.listHead')}</h2>
      <OxsNote t={t} oxs={oxs} at={at} />
      <form action={callTyped} className="search dialtyped">
        <input type="hidden" name="back" value={back} />
        <input name="number" type="tel" inputMode="tel" dir="ltr" autoComplete="off" required
               aria-label={t('dial.typedLabel')} aria-describedby="dial-typed-note"
               placeholder={t('dial.typedHint')} />
        <PendingButton busy={t('dial.adding')} disabled={!open || paused}>
          <IconPhoneOut />{t('dial.typedLabel')}
        </PendingButton>
      </form>
      <p id="dial-typed-note" className="dialhint">{t('dial.typedNote')}</p>
      <div className="filters">
        <nav className="seg" aria-label={t('col.period')}>
          {['all', ...months].map((m) => (
            <Link key={m} href={href({ month: m, page: '1' })} aria-current={month === m ? 'true' : undefined}>
              {m === 'all' ? t('status.all') : m}
            </Link>
          ))}
        </nav>
      </div>
      <form method="get" action="/dialer" className="search">
        {month !== 'all' && <input type="hidden" name="month" value={month} />}
        {perParam(size) && <input type="hidden" name="per" value={perParam(size)!} />}
        <input name="q" defaultValue={search} dir="auto" aria-label={t('dial.search')} placeholder={t('dial.search')} />
        <button type="submit">{t('calls.searchBtn')}</button>
        {search && <Link href={href({ q: '', page: '1' })} className="muted" style={{ fontSize: 13 }}>{t('calls.clear')}</Link>}
      </form>

      <Pager page={page} size={size} total={rows.length} basePath="/dialer"
             params={{ month: month === 'all' ? undefined : month, q: search || undefined }}
             unit={t('dial.unit')} t={t} />

      <form id="dialer-list" action={call} className="panel">
        <input type="hidden" name="back" value={back} />
        <div className="panelhead">
          <span>{t('dial.listCount', { n: rows.length, total: iso(shekels(totalOwed)) })}</span>
          <CallSelected form="dialer-list" name="phone" label={t('dial.callSelected')} busy={t('dial.adding')}
                        disabled={!open || paused} icon={<IconPhoneOut />} />
        </div>
        {visible.length ? (
          <div className="scrollx">
            <table className="dialtable">
              <thead><tr>
                <th>
                  <span className="dialwho">
                    <SelectAll form="dialer-list" name="phone" label={t('dial.selectAll')} />
                    <span>{t('col.resident')}</span>
                  </span>
                </th>
                <th>{t('col.building')}</th>
                <th className="num">{t('debts.owed')}</th>
                <th>{t('col.status')}</th>
                <th><span className="sr-only">{t('debts.call')}</span></th>
              </tr></thead>
              <tbody>
                {visible.map((r) => {
                  const mine = today.get(r.phone);
                  const block = blockOf(r, mine, day);
                  const can = open && !paused && !block;
                  const span = monthRange(r.months, locale);
                  return (
                    <tr key={r.phone}>
                      <td>
                        <label className="dialwho">
                          <input type="checkbox" className="dialcheck" name="phone" value={r.phone}
                                 disabled={!can} aria-label={t('dial.pick', { name: r.name || r.phone })} />
                          <span>
                            <b><bdi>{r.name || '—'}</bdi></b>
                            <span className="sub mono"><bdi dir="ltr">{r.phone}</bdi></span>
                          </span>
                        </label>
                      </td>
                      <td data-label={t('col.building')}>
                        <bdi>{r.buildings.join(' · ') || '—'}</bdi>
                        {r.units.length > 0 && (
                          <span className="sub">
                            {t(r.units.length > 1 ? 'dial.flatsMany' : 'dial.flats', { units: iso(r.units.join(', ')) })}
                          </span>
                        )}
                      </td>
                      <td className="num" data-label={t('debts.owed')}>
                        <span className="mono">{shekels(r.owed)}</span>
                        {r.months.length > 0 && (
                          <span className="sub" title={span.full}>{monthsCount(t, r.months.length)} · {span.range}</span>
                        )}
                        {r.special > 0 && (
                          <span className="sub" title={r.specials.join(' · ')}>
                            {t(r.specials.length > 1 ? 'dial.specialN' : 'dial.special1', { n: r.specials.length })}
                            {' · '}<bdi>{shekels(r.special)}</bdi>
                          </span>
                        )}
                      </td>
                      <td data-label={t('col.status')}>
                        <Standing t={t} locale={locale} row={r} today={mine} block={block} />
                      </td>
                      <td className="dialact">
                        {/* No button for a tenant who cannot be called: the Status cell says why.
                            Outside the hours or while paused every button stays, greyed, and
                            the notice above says why. */}
                        {!block && (
                          <PendingButton className="btn-sm" busy={t('dial.adding')} disabled={!can}
                                         name="one" value={r.phone}
                                         title={t('dial.callName', { name: r.name || r.phone })}>
                            <IconPhoneOut />{t('dial.call')}
                          </PendingButton>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">
            <IconInbox />
            <div>{search ? t('dial.emptySearch', { q: search }) : t('dial.empty')}</div>
          </div>
        )}
        <p className="setnote">{t('dial.rules')}</p>
      </form>

      {todays.length > 0 && (
        <>
          <h2>{t('dial.todayHead')}</h2>
          <div className="panel">
            <div className="scrollx">
              <table className="dialtable">
                <thead><tr>
                  <th>{t('col.resident')}</th><th>{t('col.status')}</th>
                  <th>{t('dial.colPressed')}</th><th>{t('dial.colBy')}</th>
                  <th><span className="sr-only">{t('dial.colCall')}</span></th>
                </tr></thead>
                <tbody>
                  {todays.slice(0, 100).map((c) => {
                    const res = resultOf(t, c);
                    return (
                      <tr key={c.id}>
                        <td>
                          <b><bdi>{c.name || '—'}</bdi></b>
                          <span className="sub mono"><bdi dir="ltr">{c.phone}</bdi></span>
                        </td>
                        <td data-label={t('col.status')}>
                          <Pill t={t} status={c.status} />
                          {res.text && <span className="sub">{res.text}</span>}
                          {res.raw && <span className="sub mono"><bdi dir="ltr">{res.raw}</bdi></span>}
                        </td>
                        <td data-label={t('dial.colPressed')}>
                          <span className="mono">{at(c.pressed_at)}</span>
                          {c.attempt ? <span className="sub">{t('dial.tryN', { n: c.attempt, max: MAX_TRIES })}</span> : null}
                        </td>
                        <td className="muted" data-label={t('dial.colBy')}><bdi>{by(c.pressed_by)}</bdi></td>
                        <td className="dialact">
                          {c.interaction_id && (
                            <Link className="btn-nav" href={`/calls/${c.interaction_id}`}>
                              <IconOpenLink />{t('dial.openCall')}
                            </Link>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}
