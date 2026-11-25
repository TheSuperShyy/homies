// The dialer's rules (feature 23, 25 Nov 2026), for debt-tools' `dialer-tick`.
//
// The dashboard's /dialer puts tenants who owe in a queue (migration 043); pg_cron posts
// `dialer-tick` here every 15 s while the queue has work, and each tick sends at most one tenant
// to Omni's dialer, only when the bot's line (208) is quiet, and only in calling hours.
//
// Pure on purpose, like route.ts: Node runs scripts/check_dialer_queue.test.ts against it, beside
// the dashboard's own copies in dashboard/lib/dialer-rules.ts, which the dialer test page uses.
// The two must agree; the test holds them side by side.

/** The bot's SIP address on Yariv's Vapi account (Omni's extension 208). A Vapi move changes it. */
export const LINE_208 = "e9f95429-3cbc-42cd-899f-7ac0d9adcd14";

/** Omni's lead API (8 Nov): a Bearer lead token, List 2's campaign id, our external_id, the number. */
export const TOKOMNI_INSERT = "https://api.tokomni.cc/api/v1/dialer/campaign/";

/** How long a tick waits for Tokomni. Under pg_net's 30 s for the tick itself. */
export const TOKOMNI_WAIT_MS = 20_000;

/** Day of the week (0 is Sunday) and the time, in Israel. */
export function israelClock(at: Date): { day: number; hour: number; minute: number } {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Jerusalem", weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(at);
  const part = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return {
    day: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(part("weekday")),
    hour: Number(part("hour")),
    minute: Number(part("minute")),
  };
}

/**
 * Omni's dialer rings a lead the moment it lands, at any hour (25 Oct), so this is the only
 * clock: Sunday to Thursday 09:00-20:00, Friday until 13:00, never Saturday. The dialer test
 * page and scripts/tokomni_lead.py keep the same hours.
 */
export function inCallingHours(at: Date): boolean {
  const { day, hour } = israelClock(at);
  if (day === 6) return false;
  if (day === 5 && hour >= 13) return false;
  return hour >= 9 && hour < 20;
}

/** "+972541234567" (residents.phone) in the local form Omni's dialer takes, "0541234567". */
export function localOf(phone: string): string | null {
  const m = /^\+972(\d{8,9})$/.exec(String(phone ?? "").trim());
  return m ? "0" + m[1] : null;
}

/**
 * The lead's external_id: the resident's id, then the moment (UTC, to the second), so a second
 * lead for the same tenant is a new lead to Tokomni. The same as the dialer test page's.
 */
export function externalIdFor(residentId: string | null, at: Date): string {
  const stamp = at.toISOString().replace(/[-:]/g, "").slice(0, 15);
  return `${residentId || "test"}-${stamp}`;
}

/** How many leads Tokomni says went in (`inserted_count`), or null when it does not say. */
export function leadsAdded(body: string): number | null {
  try {
    const j = JSON.parse(String(body ?? "").trim());
    return j && typeof j === "object" && typeof j.inserted_count === "number" ? j.inserted_count : null;
  } catch {
    return null;
  }
}

function firstReason(x: unknown): string {
  const first = Array.isArray(x) ? x[0] : x;
  if (first && typeof first === "object") {
    const o = first as Record<string, unknown>;
    const why = o.reason ?? o.error ?? o.message ?? o.msg;
    return typeof why === "string" ? why : JSON.stringify(first);
  }
  return String(first ?? "");
}

/** Tokomni's answer as one short line, as the dialer test page shows it. */
export function answerText(body: string): string {
  const text = String(body ?? "").trim();
  try {
    const j = JSON.parse(text);
    if (j && typeof j === "object") {
      const count = (x: unknown) => (Array.isArray(x) ? x.length : x ? 1 : 0);
      if (typeof j.inserted_count === "number" || count(j.failed_items) || count(j.blacklisted_items) || count(j.invalid)) {
        const parts: string[] = [];
        if (typeof j.inserted_count === "number") parts.push(`inserted ${j.inserted_count}`);
        if (count(j.blacklisted_items)) parts.push(`blacklisted ${count(j.blacklisted_items)}`);
        if (count(j.failed_items)) parts.push(`failed: ${firstReason(j.failed_items)}`);
        if (count(j.invalid)) parts.push(`invalid: ${firstReason(j.invalid)}`);
        return parts.join(", ").slice(0, 200);
      }
      const msg = j.error_msg ?? j.message ?? j.msg ?? j.error;
      return String(typeof msg === "string" ? msg : JSON.stringify(j)).slice(0, 200);
    }
  } catch {
    // not JSON
  }
  const title = text.match(/<title>([^<]*)<\/title>/i)?.[1];
  return (title ? title.trim() : text).slice(0, 200);
}

/**
 * What a send did, from Tokomni's status and answer. 200 that took the lead is ringing. No
 * answer at all (status 0: a timeout or a dropped connection) is ringing too, because on 16 Nov
 * a lead Tokomni never answered for rang anyway: treated as sent, it holds the line for its two
 * minutes instead of letting a second lead into List 2 behind it. Anything else took nothing.
 */
export function sendResult(status: number, body: string): "ringing" | "failed" {
  if (status === 0) return "ringing";
  return status === 200 && leadsAdded(body) !== 0 ? "ringing" : "failed";
}

/**
 * The bot's line from Vapi's newest calls on it (`GET /call?phoneNumberId=…`): busy while any
 * call has not ended, and otherwise quiet since the newest one ended. No calls at all: quiet
 * since the epoch. A lead still ringing is given up only 90 s after the line went quiet, because
 * while 208 talks to someone else Omni holds our lead and rings it once 208 is free.
 */
export function lineOf(calls: unknown): { busy: boolean; quietSince: string } {
  const list = Array.isArray(calls) ? calls : [];
  const busy = list.some((c: any) => c && String(c.status ?? "") !== "ended");
  let newest = 0;
  for (const c of list as any[]) {
    const at = Date.parse(String(c?.endedAt ?? c?.updatedAt ?? c?.createdAt ?? ""));
    if (Number.isFinite(at) && at > newest) newest = at;
  }
  return { busy, quietSince: new Date(newest).toISOString() };
}
