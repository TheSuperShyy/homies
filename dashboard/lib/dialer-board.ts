// The dialer page's list (feature 23), with no imports, so scripts/check_dialer_queue.test.ts runs
// it under plain Node.
//
// One row per phone number, because one ring reaches everyone on it: a couple on one phone is
// one call, and an owner of two flats hears both in it (the debt agent is given every flat the
// number owes on, feature 14). What the page shows is what the press is about; whether the call
// may still go out is decided again when it is sent (press_call, migration 024), so nothing here
// is the gate.

export const MAX_TRIES = 4;

/** The statuses that hold a place in the queue or on the line. */
export const ACTIVE_STATUSES = ['waiting', 'sending', 'ringing', 'answered'] as const;
/** The statuses that mean the phone rang (or was sent to ring) today. */
export const RANG_STATUSES = ['ringing', 'answered', 'done', 'no_answer'] as const;

export type Charge = {
  resident_id: string; period: string; amount: number | string; attempts: number | null; unit: string | null;
  residents: { full_name: string | null; building: string | null; phone: string | null; do_not_call: boolean | null } | null;
};

export type Outcome = { resident_id: string | null; outcome: string; created_at: string };

export type DialerCall = {
  id: string; phone: string; name: string | null; status: string; why: string | null;
  pressed_by: string | null; pressed_at: string; sent_at: string | null; answered_at: string | null;
  ended_at: string | null; outcome: string | null; interaction_id: string | null; attempt: number | null;
  amount: number | string | null;
};

export type Owing = {
  phone: string;
  name: string;
  buildings: string[];
  units: string[];
  owed: number;
  months: string[];
  /** The most tries any open month has had. */
  tries: number;
  /** Some open month has had fewer than four tries. */
  callable: boolean;
  dnc: boolean;
  last: Outcome | null;
};

/** The date in Israel, YYYY-MM-DD: what "today" means on this page and in migration 043. */
export function israelDate(at: Date | string): string {
  const d = typeof at === 'string' ? new Date(at) : at;
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Jerusalem', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(d);
}

/**
 * Everyone who owes, one row per phone, largest first. `charges` are unpaid ones with an amount;
 * `outcomes` are call_outcomes, newest first (the first per resident is their last call).
 */
export function groupOwing(charges: Charge[], outcomes: Outcome[] = []): Owing[] {
  const lastOf = new Map<string, Outcome>();
  for (const o of outcomes) if (o.resident_id && !lastOf.has(o.resident_id)) lastOf.set(o.resident_id, o);

  type Acc = Owing & { byResident: Map<string, number>; residents: Set<string> };
  const rows = new Map<string, Acc>();
  for (const c of charges) {
    const phone = String(c.residents?.phone ?? '').trim();
    const amount = Number(c.amount);
    if (!phone || !Number.isFinite(amount) || amount <= 0) continue;
    const row: Acc = rows.get(phone) ?? {
      phone, name: '', buildings: [], units: [], owed: 0, months: [], tries: 0, callable: false,
      dnc: false, last: null, byResident: new Map(), residents: new Set(),
    };
    row.owed += amount;
    row.byResident.set(c.resident_id, (row.byResident.get(c.resident_id) ?? 0) + amount);
    row.residents.add(c.resident_id);
    const m = String(c.period ?? '').slice(0, 7);
    if (m && !row.months.includes(m)) row.months.push(m);
    const unit = String(c.unit ?? '').trim();
    if (unit && !row.units.includes(unit)) row.units.push(unit);
    const building = String(c.residents?.building ?? '').trim();
    if (building && !row.buildings.includes(building)) row.buildings.push(building);
    const tries = Number(c.attempts ?? 0) || 0;
    row.tries = Math.max(row.tries, tries);
    if (tries < MAX_TRIES) row.callable = true;
    if (c.residents?.do_not_call) row.dnc = true;
    rows.set(phone, row);
    // The name is the one who owes the most on this number, as dialer_queue shows it.
    const top = [...row.byResident.entries()].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0]?.[0];
    if (top === c.resident_id) row.name = String(c.residents?.full_name ?? '').trim() || row.name;
  }

  const out: Owing[] = [];
  for (const row of rows.values()) {
    let last: Outcome | null = null;
    for (const id of row.residents) {
      const o = lastOf.get(id);
      if (o && (!last || o.created_at > last.created_at)) last = o;
    }
    const { byResident: _b, residents: _r, ...rest } = row;
    out.push({ ...rest, months: [...rest.months].sort(), last });
  }
  return out.sort((a, b) => b.owed - a.owed || (a.phone < b.phone ? -1 : 1));
}

/** The newest dialer row per phone pressed on `day` (Israel date), for the list's "today" column. */
export function todayByPhone(calls: DialerCall[], day: string): Map<string, DialerCall> {
  const out = new Map<string, DialerCall>();
  for (const c of calls) {
    if (israelDate(c.pressed_at) !== day) continue;
    const have = out.get(c.phone);
    if (!have || c.pressed_at > have.pressed_at) out.set(c.phone, c);
  }
  return out;
}

/**
 * Whether a row's box can be ticked, and if not, why: the same reasons the press would be
 * refused for (dialer_queue), shown before anyone presses.
 */
export function blockOf(row: Owing, today: DialerCall | undefined, day: string): string | null {
  if (row.dnc) return 'dnc';
  if (!row.callable) return 'tries';
  if (today && (ACTIVE_STATUSES as readonly string[]).includes(today.status)) return 'queued';
  if (today && (RANG_STATUSES as readonly string[]).includes(today.status)
      && today.sent_at && israelDate(today.sent_at) === day) return 'today';
  return null;
}

/** "today:2,paid:1" from dialer_queue's skipped list, for the page's notice. */
export function skipSummary(skipped: Array<{ why?: string }>): string {
  const counts = new Map<string, number>();
  for (const s of skipped) {
    const k = String(s?.why ?? 'other');
    counts.set(k, (counts.get(k) ?? 0) + 1);
  }
  return [...counts.entries()].map(([k, n]) => `${k}:${n}`).join(',');
}

/** The reverse, for the notice: [["today", 2], ["paid", 1]]. Unknown words are kept as they are. */
export function parseSummary(s: string | undefined): Array<[string, number]> {
  return String(s ?? '').split(',').flatMap((part) => {
    const [k, n] = part.split(':');
    const count = Number(n);
    return k && Number.isFinite(count) && count > 0 ? [[k, count] as [string, number]] : [];
  });
}

/**
 * The months a row owes as a short range, "Jul–Oct 2026" or "יולי–אוקטובר 2026", and every month
 * for the tooltip. A list of ten "2026-01, 2026-02, …" set the whole table's width (25 Nov); the
 * count beside the range (the page's own words) still says when there are gaps in it.
 */
export function monthRange(months: string[], locale: 'he' | 'en'): { range: string; full: string } {
  const sorted = [...new Set(months)].filter((m) => /^\d{4}-\d{2}$/.test(m)).sort();
  if (!sorted.length) return { range: '', full: '' };
  const name = (m: string, withYear: boolean) => new Intl.DateTimeFormat(locale === 'he' ? 'he-IL' : 'en-GB', {
    month: locale === 'he' ? 'long' : 'short', ...(withYear ? { year: 'numeric' as const } : {}), timeZone: 'UTC',
  }).format(new Date(`${m}-01T00:00:00Z`));
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const range = first === last ? name(first, true)
    : first.slice(0, 4) === last.slice(0, 4) ? `${name(first, false)}–${name(last, false)} ${last.slice(0, 4)}`
    : `${name(first, true)} – ${name(last, true)}`;
  return { range, full: sorted.map((m) => name(m, true)).join(', ') };
}

/** Matches a search box against a row: name, building or flat, or the phone's digits. */
export function matches(row: Owing, q: string): boolean {
  const s = q.trim().toLowerCase();
  if (!s) return true;
  const digits = s.replace(/\D/g, '');
  if (digits.length >= 3) {
    const phone = row.phone.replace(/\D/g, '');
    const local = phone.startsWith('972') ? '0' + phone.slice(3) : phone;
    if (phone.includes(digits) || local.includes(digits)) return true;
  }
  return [row.name, ...row.buildings, ...row.units].some((v) => v.toLowerCase().includes(s));
}
