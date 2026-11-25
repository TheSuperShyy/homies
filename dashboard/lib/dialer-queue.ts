import 'server-only';
import { serverClient } from '@/lib/supabase-server';
import { inCallingHours } from '@/lib/dialer-rules';
import {
  ACTIVE_STATUSES, groupOwing, skipSummary, type Charge, type DialerCall, type Outcome, type Owing,
} from '@/lib/dialer-board';

// The real dialer (feature 23, 25 Nov): the page's reads, and the three things a person can do.
//
// A press does not ring anybody from here. It puts the chosen tenants in `dialer_calls` (migration
// 043, `dialer_queue`), and debt-tools sends them to Omni's dialer one at a time, every 15 s while
// the queue has work, only in calling hours and only when the bot's line is quiet. So the page
// never holds a Tokomni token and never waits on Tokomni: what it shows is the queue's own record.
//
// Every write goes through a SECURITY DEFINER function that reads the signed-in email itself
// (auth.jwt()), so "who pressed" cannot be typed in, and the anon key can do none of it.

/** PostgREST hands back at most 1,000 rows a request; the debt list is read whole, a page at a time. */
async function everyRow<Row>(page: (from: number, to: number) => PromiseLike<{ data: Row[] | null; error: any }>) {
  const out: Row[] = [];
  for (let from = 0; from < 20_000; from += 1000) {
    const { data, error } = await page(from, from + 999);
    if (error) throw new Error(String(error.message ?? error));
    out.push(...(data ?? []));
    if (!data || data.length < 1000) break;
  }
  return out;
}

export type Board = {
  owing: Owing[];
  calls: DialerCall[];
  state: { paused_at: string | null; paused_why: string | null; last_tick_at: string | null; last_error: string | null } | null;
  error: string | null;
};

/** Everything the page shows: who owes, the last day and a half of dialer calls, and the pause. */
export async function board(): Promise<Board> {
  const db = serverClient();
  try {
    const since = new Date(Date.now() - 36 * 3600_000).toISOString();
    const [charges, outcomes, recent, active, state] = await Promise.all([
      everyRow<Charge>((from, to) => db.from('charges')
        .select('resident_id,period,amount,attempts,unit,residents(full_name,building,phone,do_not_call)')
        .eq('status', 'unpaid').gt('amount', 0)
        .order('id', { ascending: true }).range(from, to) as any),
      db.from('call_outcomes').select('resident_id,outcome,created_at')
        .order('created_at', { ascending: false }).limit(1000),
      db.from('dialer_calls').select('*').gte('pressed_at', since)
        .order('pressed_at', { ascending: false }).limit(500),
      db.from('dialer_calls').select('*').in('status', [...ACTIVE_STATUSES])
        .order('pressed_at', { ascending: false }).limit(500),
      db.from('dialer_state').select('paused_at,paused_why,last_tick_at,last_error').eq('id', 1).maybeSingle(),
    ]);
    const failed = outcomes.error ?? recent.error ?? active.error ?? state.error;
    if (failed) throw new Error(String(failed.message ?? failed));
    // Active rows are normally today's too; an old one stuck on the line must still show.
    const byId = new Map<string, DialerCall>();
    for (const c of [...((recent.data ?? []) as DialerCall[]), ...((active.data ?? []) as DialerCall[])]) {
      byId.set(c.id, c);
    }
    const calls = [...byId.values()].sort((a, b) => (a.pressed_at < b.pressed_at ? 1 : -1));
    return {
      owing: groupOwing(charges, (outcomes.data ?? []) as Outcome[]),
      calls,
      state: (state.data as Board['state']) ?? null,
      error: null,
    };
  } catch (e) {
    return { owing: [], calls: [], state: null, error: String((e as Error)?.message ?? e).slice(0, 200) };
  }
}

/** A press: these phones into the queue. The outcome goes back in the page's URL. Never throws. */
export async function queueCalls(phones: string[]): Promise<Record<string, string>> {
  const list = [...new Set(phones.map((p) => String(p ?? '').trim()).filter(Boolean))].slice(0, 300);
  if (!list.length) return { r: 'none' };
  // The tick cancels anything outside the hours anyway; refusing here says so at the press.
  if (!inCallingHours(new Date())) return { r: 'hours' };
  try {
    const { data, error } = await serverClient().rpc('dialer_queue', { p_phones: list });
    if (error) return { r: 'db', b: String(error.message ?? '').slice(0, 200) };
    if (data?.error) return { r: 'db', b: String(data.error).slice(0, 200) };
    const skipped = Array.isArray(data?.skipped) ? data.skipped : [];
    return { r: 'queued', n: String(Number(data?.queued ?? 0)), k: String(skipped.length), w: skipSummary(skipped) };
  } catch (e) {
    return { r: 'db', b: String(e).slice(0, 200) };
  }
}

/** Stop: everyone still waiting is cancelled. Never throws. */
export async function stopCalls(): Promise<Record<string, string>> {
  try {
    const { data, error } = await serverClient().rpc('dialer_stop');
    if (error) return { r: 'db', b: String(error.message ?? '').slice(0, 200) };
    return { r: 'stopped', n: String(Number(data ?? 0)) };
  } catch (e) {
    return { r: 'db', b: String(e).slice(0, 200) };
  }
}

/** Resume after the five-in-a-row pause. Never throws. */
export async function resumeCalls(): Promise<Record<string, string>> {
  try {
    const { error } = await serverClient().rpc('dialer_resume');
    if (error) return { r: 'db', b: String(error.message ?? '').slice(0, 200) };
    return { r: 'resumed' };
  } catch (e) {
    return { r: 'db', b: String(e).slice(0, 200) };
  }
}
