import 'server-only';
import { serverClient } from '@/lib/supabase-server';

// Place one outbound debt call to one resident, because a person pressed Call.
//
// This is the whole of "outbound" for now, and on purpose: there is no runner,
// no queue iteration, no schedule. The PRD's release-2 machinery — no-repeat
// rule, do-not-call, calling windows, daily report — is a follow-up the owner
// deferred on 25 Aug. What exists is a person choosing one resident by name
// and pressing a button, which is the decision `handed_over` was always
// waiting for.
//
// THREE GATES, ALL SERVER-SIDE
//   1. CALL_PIN. The dashboard has had no login wall since 9 Aug (demo mode),
//      so a bare button on a public page would let anyone with the URL ring a
//      resident on Homies' number and Homies' bill. The PIN lives in Vercel
//      and is typed next to the button; without it configured the button is
//      not rendered at all.
//   2. press_call() in Postgres (migration 024): flips handed_over for that
//      one resident and returns their composed call — or NULL if they owe
//      nothing, are on do-not-call, or have had four attempts.
//   3. VAPI_PHONE_NUMBER_ID. No number, no call. The Israeli number is being
//      ordered (Omnitelecom); until its Vapi id is set here the page says so
//      instead of pretending.
//
// The variables handed to the agent are the same set the browser demo composes
// (web/index.html variablesFor), so the prompt sees nothing new: the SQL view
// does the Hebrew phrases, and gender_forms / has_card are finished here for
// the same reason they are finished there — a model handed a code and a rule
// two hundred lines apart does not carry the branch through the sentence.

const VAPI = 'https://api.vapi.ai';
const DEBT_HE = '93c7f5e5-4024-49a3-9ab6-141f2b423649'; // Homies — Debt Follow-up (he), the August account

// The office number and email are Homies' own, from docs/reference/homies-faq.txt;
// the bank-transfer line is still the demo's until Homies confirms one. Overridable without a deploy.
// verification_email is the SPOKEN form — the TTS reads it letter by letter —
// which is why it is not an address.
const FIXED = {
  callback_number: process.env.HOMIES_CALLBACK_NUMBER ?? '077-6687949',
  verification_email:
    process.env.HOMIES_VERIFICATION_EMAIL_SAY
    ?? 'אופיס, שטרודל, הומיז, מקף, מנג\'מנט, נקודה, סי, או, נקודה, איי, אל',
  alt_payment: process.env.HOMIES_ALT_PAYMENT ?? 'none',
};

const GENDER_FORMS: Record<string, string> = {
  f: 'הנמענת אישה. פנה אליה בנקבה לאורך כל השיחה: את, שלָךְ, לָךְ, איתָּךְ, תגידי, תשלחי, תבדקי, תסגרי, תוכלי, תרצי.',
  m: 'הנמען גבר. פנה אליו בזכר לאורך כל השיחה: אתה, שלְךָ, לְךָ, איתְּךָ, תגיד, תשלח, תבדוק, תסגור, תוכל, תרצה.',
  unknown:
    'מין הנמען לא ידוע. דבר בניסוחים נייטרליים בלבד ואל תנחש: צריך, אפשר, בואו נראה, מה תרצו, אשמח לדעת. '
    + 'אם הוא או היא חושפים מין בדיבור על עצמם — אני צריכה מול אני צריך — עבור מיד להטיה הזאת.',
};

export function callButtonEnabled(): boolean {
  return Boolean(process.env.CALL_PIN);
}

export function phoneNumberConnected(): boolean {
  return Boolean(process.env.VAPI_PHONE_NUMBER_ID);
}

/** Returns 'ok:<call id>' or 'err:<reason a person can read>'. Never throws. */
export async function callResident(phone: string, pin: string): Promise<string> {
  const PIN = process.env.CALL_PIN;
  if (!PIN) return 'err:Calling is switched off (CALL_PIN is not set in Vercel).';
  if (!pin || pin !== PIN) return 'err:Wrong PIN.';
  if (!/^\+972\d{8,9}$/.test(phone)) return 'err:That is not an Israeli mobile number.';

  const key = process.env.VAPI_PRIVATE_KEY;
  const phoneNumberId = process.env.VAPI_PHONE_NUMBER_ID;
  const assistantId = process.env.VAPI_DEBT_ASSISTANT_ID ?? DEBT_HE;
  if (!key) return 'err:VAPI_PRIVATE_KEY is not set in Vercel.';
  if (!phoneNumberId) {
    return 'err:No phone number is connected yet. Order the Israeli number, then set VAPI_PHONE_NUMBER_ID.';
  }

  // Gate 2: the database decides eligibility and composes the call.
  const { data, error } = await serverClient().rpc('press_call', { p_phone: phone });
  if (error) return `err:${error.message}`;
  if (!data) return 'err:Not eligible: nothing unpaid, on do-not-call, or already called four times.';
  const p = data as Record<string, any>;

  const gender = String(p.gender ?? 'unknown');
  const variableValues: Record<string, string> = {
    phone,
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
    // The whitelist the end-of-call writer resolves every tool call against.
    // Sent as JSON text: variableValues are template substitutions.
    charges: JSON.stringify(p.charges ?? []),
    ...FIXED,
  };

  const res = await fetch(`${VAPI}/call`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      assistantId,
      phoneNumberId,
      customer: { number: phone, name: variableValues.first_name || undefined },
      assistantOverrides: { variableValues },
    }),
    cache: 'no-store',
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = Array.isArray(body?.message) ? body.message.join('; ') : (body?.message ?? res.statusText);
    return `err:Vapi ${res.status}: ${String(msg).slice(0, 160)}`;
  }
  return `ok:${body?.id ?? ''}`;
}
