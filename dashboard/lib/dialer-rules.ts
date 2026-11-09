// The dialer test page's rules (feature 20), with no imports, so
// scripts/check_dialer.test.ts runs them under plain Node beside feature 18's
// router.

/**
 * A typed Israeli number in the local form Omni's dialer takes ("0541234567",
 * their example is ten digits with no country code), or null.
 *
 * Takes what people actually type: dashes, spaces, brackets, "+972", "00972",
 * and "+972 054…" with the zero kept after the country code. A number from
 * anywhere else is null: Omni's dialer is not tried on those.
 */
export function localForm(typed: string): string | null {
  let d = String(typed ?? '').replace(/\D/g, '');
  if (d.startsWith('00')) d = d.slice(2);
  if (d.startsWith('972')) d = '0' + d.slice(3).replace(/^0/, '');
  return /^0[2-9]\d{7,8}$/.test(d) ? d : null;
}

/** The "+972…" form residents.phone and the debt call list hold. */
export function e164(local: string): string {
  return '+972' + local.slice(1);
}

/** Day of the week (0 is Sunday) and the time, in Israel. */
export function israelClock(at: Date): { day: number; hour: number; minute: number } {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Jerusalem', weekday: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(at);
  const part = (t: string) => parts.find((p) => p.type === t)?.value ?? '';
  return {
    day: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(part('weekday')),
    hour: Number(part('hour')),
    minute: Number(part('minute')),
  };
}

/**
 * Omni's dialer rings a lead the moment it lands, at any hour (25 Oct), so this
 * is the only clock: Sunday to Thursday 09:00-20:00, Friday until 13:00, never
 * Saturday. The same hours as scripts/tokomni_lead.py.
 */
export function inCallingHours(at: Date): boolean {
  const { day, hour } = israelClock(at);
  if (day === 6) return false;
  if (day === 5 && hour >= 13) return false;
  return hour >= 9 && hour < 20;
}

export type Answerer =
  | { agent: 'debt'; residentId: string; firstName: string; amount: number; attempt: number }
  | { agent: 'intake'; why: 'notListed' | 'twoRows' | 'nothingOwed' };

/**
 * Who picks up when the dialer's call is answered, from the debt call list's
 * rows on that number. The same decision as routeOf() in
 * supabase/functions/debt-tools/route.ts (feature 18): exactly one row with
 * something owed gets the debt agent, anything else the incoming agent.
 * check_dialer.test.ts holds the two side by side.
 */
export function answererOf(rows: Array<Record<string, any>>): Answerer {
  if (!rows.length) return { agent: 'intake', why: 'notListed' };
  if (rows.length > 1) return { agent: 'intake', why: 'twoRows' };
  const amount = Number(rows[0].amount);
  if (!Number.isFinite(amount) || amount <= 0) return { agent: 'intake', why: 'nothingOwed' };
  return {
    agent: 'debt',
    residentId: String(rows[0].resident_id ?? ''),
    firstName: String(rows[0].first_name ?? ''),
    amount,
    attempt: Number(rows[0].attempt ?? 1),
  };
}

/**
 * The lead's external_id: the resident's id when the number is one resident's,
 * else "test", then the time of the press (UTC, to the second).
 *
 * Tokomni adds a lead "if not already present", so a bare resident id could
 * make the second press for the same person a lead Tokomni already has, and
 * nobody rings. The id stays first, so whatever reads Omni's external_id header
 * later finds it in the first 36 characters.
 */
export function externalIdFor(residentId: string | null, at: Date): string {
  const stamp = at.toISOString().replace(/[-:]/g, '').slice(0, 15);
  return `${residentId || 'test'}-${stamp}`;
}

/** How many leads Tokomni says went in (`inserted_count`, Omni's v1 answer), or null when it does not say. */
export function leadsAdded(body: string): number | null {
  try {
    const j = JSON.parse(String(body ?? '').trim());
    return j && typeof j === 'object' && typeof j.inserted_count === 'number' ? j.inserted_count : null;
  } catch {
    return null;
  }
}

/** The first item of a list Tokomni returns, as its reason or as JSON. */
function firstReason(x: unknown): string {
  const first = Array.isArray(x) ? x[0] : x;
  if (first && typeof first === 'object') {
    const o = first as Record<string, unknown>;
    const why = o.reason ?? o.error ?? o.message ?? o.msg;
    return typeof why === 'string' ? why : JSON.stringify(first);
  }
  return String(first ?? '');
}

/**
 * Tokomni's answer as one short line. Omni's v1 answer (8 Nov) says how many went
 * in and why any did not: "inserted 1", "inserted 0, blacklisted 1", "failed: …",
 * "invalid: …". Otherwise the JSON's message, an HTML page's title, or the text.
 */
export function answerText(body: string): string {
  const text = String(body ?? '').trim();
  try {
    const j = JSON.parse(text);
    if (j && typeof j === 'object') {
      const count = (x: unknown) => (Array.isArray(x) ? x.length : x ? 1 : 0);
      if (typeof j.inserted_count === 'number' || count(j.failed_items) || count(j.blacklisted_items) || count(j.invalid)) {
        const parts: string[] = [];
        if (typeof j.inserted_count === 'number') parts.push(`inserted ${j.inserted_count}`);
        if (count(j.blacklisted_items)) parts.push(`blacklisted ${count(j.blacklisted_items)}`);
        if (count(j.failed_items)) parts.push(`failed: ${firstReason(j.failed_items)}`);
        if (count(j.invalid)) parts.push(`invalid: ${firstReason(j.invalid)}`);
        return parts.join(', ').slice(0, 200);
      }
      const msg = j.error_msg ?? j.message ?? j.msg ?? j.error;
      return String(typeof msg === 'string' ? msg : JSON.stringify(j)).slice(0, 200);
    }
  } catch {}
  const title = text.match(/<title>([^<]*)<\/title>/i)?.[1];
  return (title ? title.trim() : text).slice(0, 200);
}
