import 'server-only';
import { serverClient } from '@/lib/supabase-server';
import {
  answerText, answererOf, e164, externalIdFor, inCallingHours, localForm, type Answerer,
} from '@/lib/dialer-rules';

// The dialer test page (feature 20): one number into Omni's dialer, so a test
// call no longer needs an Excel sheet uploaded into Tokomni.
//
// WHERE THE NUMBER GOES. Every API lead lands in Tokomni's "List 2" (Omni,
// 27 Oct), which stays on, so a new lead is rung at once. The answered call
// comes in on extension 208 and on to Vapi, where feature 18's router picks the
// agent from the number the dialer rang. Nothing here chooses an agent; the
// page only says, from the same list the router reads, who will be on the line.
//
// WHAT IT REFUSES, server-side, before anything is sent:
//   - TOKOMNI_TOKEN or TOKOMNI_CAMPAIGN_ID missing in Vercel;
//   - a number that is not Israeli;
//   - outside calling hours, because Omni's dialer has none of its own;
//   - a number on file for a tenant outside the test building. The page rings
//     testers and numbers that are no tenant's; a real tenant is called from
//     the Debts page, on purpose.

const INSERT = 'https://api.tokomni.cc/api/campaign/insert/';
export const TEST_BUILDING = 'בר כוכבא 23, תל אביב - יפו';

const QUEUE_COLUMNS = 'resident_id,phone,first_name,amount,attempt';

export function dialerConnected(): boolean {
  return Boolean(process.env.TOKOMNI_TOKEN?.trim() && process.env.TOKOMNI_CAMPAIGN_ID?.trim());
}

/** First three and last three digits, for the function log. */
const mask = (n: string) => `${n.slice(0, 3)}…${n.slice(-3)}`;

export type Tester = { name: string; unit: string; local: string; answerer: Answerer };

/**
 * The one-press rows: the people we put in the test building ourselves
 * (source 'agent', by debt_demo_person.py and the like), with an Israeli
 * number. The building's OXS rows are real people's phones, Yariv's among
 * them, so they get no button; any of them can still be typed.
 */
export async function testers(): Promise<Tester[]> {
  const db = serverClient();
  const { data: people } = await db.from('residents').select('full_name,unit,phone')
    .eq('building', TEST_BUILDING).eq('source', 'agent').order('unit');
  const ours = (people ?? []).flatMap((p: any) => {
    const local = localForm(String(p.phone ?? ''));
    return local ? [{ ...p, local }] : [];
  });
  if (!ours.length) return [];
  // By number, not by building: the router looks the number up wherever it is.
  const { data: queue } = await db.from('v_debt_call_queue_person').select(QUEUE_COLUMNS)
    .in('phone', ours.map((p) => p.phone));
  return ours.map((p) => ({
    name: String(p.full_name ?? ''),
    unit: String(p.unit ?? ''),
    local: p.local,
    answerer: answererOf((queue ?? []).filter((q: any) => q.phone === p.phone)),
  }));
}

/** Who answers, as URL parameters for the page to put back into words. */
function whoParams(a: Answerer): Record<string, string> {
  return a.agent === 'debt'
    ? { a: 'debt', f: a.firstName, m: String(a.amount), t: String(a.attempt) }
    : { a: 'intake', y: a.why };
}

/** One press. Never throws: the outcome goes back in the page's URL. */
export async function dial(typed: string): Promise<Record<string, string>> {
  if (!dialerConnected()) return { r: 'off' };
  const local = localForm(typed);
  if (!local) return { r: 'number', n: typed.trim().slice(0, 40) };
  const now = new Date();
  if (!inCallingHours(now)) return { r: 'hours', n: local };

  const phone = e164(local);
  const db = serverClient();
  const [people, queue] = await Promise.all([
    db.from('residents').select('id,building').eq('phone', phone),
    db.from('v_debt_call_queue_person').select(QUEUE_COLUMNS).eq('phone', phone).limit(2),
  ]);
  const failed = people.error ?? queue.error;
  if (failed) return { r: 'db', n: local, b: String(failed.message ?? '').slice(0, 200) };
  const elsewhere = (people.data ?? []).find((p: any) => p.building !== TEST_BUILDING);
  if (elsewhere) return { r: 'tenant', n: local, w: String(elsewhere.building ?? '') };

  const who = answererOf(queue.data ?? []);
  const ids = (people.data ?? []).map((p: any) => String(p.id));
  const externalId = externalIdFor(
    who.agent === 'debt' ? who.residentId : ids.length === 1 ? ids[0] : null, now);

  let status: number;
  let body: string;
  try {
    const token = new URLSearchParams({ token: process.env.TOKOMNI_TOKEN!.trim() });
    const res = await fetch(`${INSERT}?${token}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        external_id: externalId,
        campaign_id: process.env.TOKOMNI_CAMPAIGN_ID!.trim(),
        number: local,
      }),
      cache: 'no-store',
      // Under Vercel's ten seconds for the whole function, so a slow Tokomni
      // still comes back as "no answer" rather than as an error page.
      signal: AbortSignal.timeout(8000),
    });
    status = res.status;
    body = await res.text();
  } catch (e) {
    console.error('dialer: no answer from Tokomni', mask(local), String(e));
    return { r: 'net', n: local, b: String(e).slice(0, 200) };
  }
  console.log('dialer', mask(local), status, who.agent, externalId);
  return {
    r: status >= 200 && status < 300 ? 'ok' : 'http',
    n: local, s: String(status), b: answerText(body), x: externalId, ...whoParams(who),
  };
}
