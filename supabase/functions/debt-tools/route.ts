// Which agent answers a call on the 208 line (feature 18, 25 Oct 2026).
//
// Omni's extension 208 takes two kinds of call, by Yariv's choice with Omni
// (12 Oct): a caller who pressed 9 in the main number's menu, and a tenant
// Omni's dialer rang who picked up. The address names no agent of its own, so
// Vapi asks this function at the start of every call (`assistant-request`). A
// dialer call to exactly one tenant on the debt call list gets the debt agent
// with that tenant's figures; everything else gets the incoming agent, which is
// what every call got before.
//
// Pure on purpose, like identity.ts: Node runs scripts/check_route.test.ts
// against it, because there is no local Deno.

import { callNumberOf } from "./identity.ts";

/**
 * Omni's dialer names its call "dialer-<the number it rang>" (21 Oct, call
 * 01a15d92). A press-9 caller arrives under their own number and staff under
 * an extension. Nothing else marks a dialer call yet: Omni's external_id is
 * "still under review" (25 Oct), and the INVITE carries none.
 */
export function isDialerCall(call: any): boolean {
  return /^dialer-/i.test(String(call?.customer?.name ?? "").trim());
}

export type Route =
  | { agent: "debt"; phone: string; row: Record<string, any> }
  | { agent: "intake"; why: string };

/**
 * The agent for one call, given the debt call list's rows on the number the
 * dialer rang.
 *
 * `v_debt_call_queue_person` holds only people a person already put on the
 * list: unpaid, handed over, not on do-not-call, under four attempts. So a
 * number typed into Tokomni by hand reaches the debt agent only when it is on
 * that list too; the dialer never starts a debt conversation our side did not
 * choose. Anything but exactly one row is the incoming agent, because the
 * agent never guesses whose debt it is talking about.
 */
export function routeOf(call: any, rows: unknown): Route {
  if (!isDialerCall(call)) return { agent: "intake", why: "not a dialer call" };
  const phone = callNumberOf(call);
  if (!phone) return { agent: "intake", why: "no number on the call" };
  const list = Array.isArray(rows)
    ? rows.filter((r: any) => r && String(r.phone ?? "") === phone)
    : [];
  if (!list.length) return { agent: "intake", why: "not on the debt call list" };
  if (list.length > 1) return { agent: "intake", why: "more than one row on this number" };
  const amount = Number((list[0] as any).amount);
  if (!Number.isFinite(amount) || amount <= 0) return { agent: "intake", why: "nothing owed" };
  return { agent: "debt", phone, row: list[0] as Record<string, any> };
}

// The texts below are the Call button's (dashboard/lib/call.ts), byte for byte,
// so a dialer call and a button call hand the debt agent the same template.
// scripts/check_route.test.ts compares them with the dashboard's own.

/** The office's fixed lines; the Call button lets Vercel override each one. */
export const FIXED_DEFAULTS: Record<string, string> = {
  callback_number: '077-6687949',
  verification_email:
    'אופיס, שטרודל, הומיז, מקף, מנג\'מנט, נקודה, סי, או, נקודה, איי, אל',
  alt_payment: 'none',
};

export const GENDER_FORMS: Record<string, string> = {
  f: 'הנמענת אישה. פנה אליה בנקבה לאורך כל השיחה: את, שלָךְ, לָךְ, איתָּךְ, תגידי, תשלחי, תבדקי, תסגרי, תוכלי, תרצי. '
    + 'וכשאתה מדבר עליה עם מישהו אחר, גם אז בנקבה: היא, שלה, שתחזור.',
  m: 'הנמען גבר. פנה אליו בזכר לאורך כל השיחה: אתה, שלְךָ, לְךָ, איתְּךָ, תגיד, תשלח, תבדוק, תסגור, תוכל, תרצה. '
    + 'וכשאתה מדבר עליו עם מישהו אחר, גם אז בזכר: הוא, שלו, שיחזור.',
  unknown:
    'השם לא מכריע אם זה גבר או אישה. פנה בזכר, ביחיד: אתה, שלְךָ, לְךָ, איתְּךָ, תגיד, תשלח, תבדוק, תסגור, תוכל, תרצה.',
};

/** The debt agent's variables for one queue row, as the Call button composes them. */
export function debtVariables(
  p: Record<string, any>,
  phone: string,
  fixed: Record<string, string> = FIXED_DEFAULTS,
): Record<string, string> {
  const gender = String(p.gender ?? 'unknown');
  return {
    phone,
    resident_id: String(p.resident_id ?? ''),
    first_name: String(p.first_name ?? ''),
    gender,
    gender_forms: GENDER_FORMS[gender] ?? GENDER_FORMS.unknown,
    card_last4: String(p.card_last4 ?? ''),
    has_card: String(p.card_last4 ?? '').trim() ? 'yes' : 'no',
    building: String(p.building ?? ''),
    unit: String(p.unit ?? ''),
    amount: String(p.amount ?? ''),
    apartments_phrase: String(p.apartments_phrase ?? ''),
    breakdown_phrase: String(p.breakdown_phrase ?? ''),
    months_phrase: String(p.months_phrase ?? ''),
    attempt: String(p.attempt ?? '1'),
    charges: JSON.stringify(p.charges ?? []),
    ...fixed,
  };
}
