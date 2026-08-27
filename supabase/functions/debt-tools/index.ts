// Homies — the eight tools of the outbound debt agent (feature 10).
//
// One function, eight tools, because they share one hard rule and it is easier
// to keep true in one file than in eight: the model does not get to say which
// debt it is collecting.
//
// Deploy:
//   supabase functions deploy debt-tools --no-verify-jwt
// Then set the secrets it reads:
//   supabase secrets set TOOL_SECRET=...           # 32+ random chars
//
// --no-verify-jwt is deliberate. Vapi is not a Supabase user and cannot present
// a Supabase JWT. The shared secret in the X-Homies-Secret header is what
// stands in front of this instead. Unlike the Apps Script endpoint, an Edge
// Function can read request headers — so the secret does not have to travel in
// the query string where it lands in logs.
//
// THE RULE THIS FILE EXISTS TO ENFORCE
// The agent never supplies charge_id, resident_id, amount or period. Those come
// from the variableValues the campaign runner attached to the call, which the
// model can read but cannot change. A model that hallucinates an amount, or is
// talked into collecting a different debt, still writes the right row — because
// the row is not built from anything it said. This is the same principle as
// verify_identity being server-side: never the agent's own claim.
//
// ONE CALL, SEVERAL APARTMENTS (feature 14, 11 Aug)
// A call is now about a PERSON, not a charge: v_debt_call_queue_person hands the
// runner one row per resident carrying every apartment of theirs that owes. So
// `ctx.charges` is the list, and every write below runs over it.
//
// THE AGENT SELECTS; IT NEVER SUPPLIES. A tool that can act on one apartment
// takes an optional `unit` — the apartment the resident said out loud, which is
// a thing they told us and not an identifier a model could invent. `targets()`
// maps it to charge ids against the call's own list and refuses anything absent
// from it. So the rule above still holds exactly: the model can point at a debt
// already in front of it, and cannot reach one that is not.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const db = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

const SECRET = Deno.env.get("TOOL_SECRET") ?? "";

/** One open charge on this call: an apartment, a month, a sum. */
type Charge = {
  charge_id: string;
  unit: string;
  period: string | null; // first of the month, e.g. 2026-07-01
  amount: number | null;
};

/** What the campaign runner attached to the call. Set once, never from the model. */
type CallContext = {
  callId: string;
  chargeId: string | null;
  residentId: string | null;
  amount: number | null;
  period: string | null; // first of the month, e.g. 2026-07-01
  cardLast4: string | null;
  building: string | null;
  unit: string | null;
  /**
   * The number the call came from, and the only thing about an inbound caller
   * we know before they say a word. Nobody asks for it and the agent never says
   * it aloud: it is on the call, so it goes on the row.
   */
  callerPhone: string | null;
  /** Every open charge this call covers. The whitelist. Never empty on a real call. */
  charges: Charge[];
};

/**
 * The charges array as it survives the trip through Vapi.
 *
 * variableValues are template substitutions, so anything that is not a string
 * arrives as one on some versions and as itself on others. Both are read rather
 * than picking one and being wrong on a version bump — the same reason
 * `context()` reads four places for variableValues.
 *
 * A malformed array is treated as no array at all, which falls back to the
 * single-charge shape below. Losing the split is survivable; throwing here
 * would take down every tool on the call.
 */
function parseCharges(raw: unknown): Charge[] {
  let v: any = raw;
  if (typeof v === "string") {
    try { v = JSON.parse(v); } catch { return []; }
  }
  if (!Array.isArray(v)) return [];
  return v
    .map((c: any) => ({
      charge_id: String(c?.charge_id ?? c?.id ?? "").trim(),
      unit: String(c?.unit ?? "").trim(),
      period: c?.period ?? null,
      amount: Number.isFinite(Number(c?.amount)) ? Number(c.amount) : null,
    }))
    .filter((c) => c.charge_id);
}

/**
 * Vapi nests the call one or two levels deep depending on the event, and
 * variableValues can sit on the assistant or on the override. Read all the
 * places it is known to appear rather than picking one and being wrong on a
 * version bump.
 */
function context(message: any): CallContext {
  const call = message?.call ?? {};
  const v =
    call?.assistantOverrides?.variableValues ??
    message?.assistant?.variableValues ??
    call?.assistant?.variableValues ??
    {};

  const num = (x: unknown) => {
    const n = Number(x);
    return Number.isFinite(n) && n > 0 ? n : null;
  };

  // A person call carries `charges`. A single-charge call — WhatsApp, a stale
  // assistant, anything started before feature 14 — carries charge_id and the
  // loose amount/period/unit, and is folded into the same one-element list here
  // so every tool below has exactly one code path. There is no "does this call
  // have several apartments" branch anywhere in this file.
  const charges = parseCharges(v.charges);
  const chargeId = v.charge_id ?? null;
  if (!charges.length && chargeId) {
    charges.push({
      charge_id: String(chargeId),
      unit: String(v.unit ?? "").trim(),
      period: v.period ?? null,
      amount: num(v.amount),
    });
  }

  return {
    callId: call?.id ?? message?.callId ?? "",
    chargeId,
    residentId: v.resident_id ?? null,
    amount: num(v.amount),
    period: v.period ?? null,
    cardLast4: v.card_last4 ? String(v.card_last4) : null,
    building: v.building ?? null,
    unit: v.unit ?? null,
    // Vapi puts the far end on `customer.number` for a real phone call and
    // leaves it absent on a web call, which is correct in both cases: a browser
    // has no number. The demo sends one in variableValues so the path is
    // testable, and it is read LAST so a real call can never be overridden by a
    // variable — the one direction of precedence this file got wrong before.
    // `v.phone` last, and it is what CHAT sends. The WhatsApp tool body puts
    // the sender's number there (n8n_whatsapp.py TOOL_BODY) and the call id is
    // `wa:<number>`, so the number was always present — but nothing read it
    // here, and `reported_by_phone` on a ticket is `ctx.callerPhone`. Result:
    // every ticket ever opened on WhatsApp stored a null phone while the
    // interaction beside it stored the right one, and the dashboard's Caller
    // column was empty on the whole channel. Found 25 Aug, the hour complaints
    // became tickets — a complaint nobody can ring back is half a complaint.
    callerPhone: phoneOf(call?.customer?.number) ?? phoneOf(v.caller_phone) ?? phoneOf(v.phone),
    charges,
  };
}

/**
 * Which charges a write lands on.
 *
 * No `unit` argument means the whole call, which is the common case and the one
 * the agent reaches by saying nothing. A `unit` narrows it to one apartment, and
 * only to an apartment already on the call: a unit the runner did not attach is
 * refused, not created, not guessed and not silently widened back to everything.
 *
 * Widening on a bad unit is the failure worth naming, because it is the tempting
 * one. A resident says "I already paid for four", the model hears "arba" as
 * something else, and a lenient fallback would dispute both flats on a claim
 * about one. Refusing gives the agent an error it can act on; guessing gives
 * the office a dispute nobody made.
 */
type Targets = { ok: true; charges: Charge[] } | { ok: false; error: string };

function targets(ctx: CallContext, args: any): Targets {
  if (!ctx.charges.length) return { ok: false, error: "no charge on this call" };

  const asked = String(args?.unit ?? "").trim();
  if (!asked) return { ok: true, charges: ctx.charges };

  const hit = ctx.charges.filter((c) => c.unit === asked);
  if (!hit.length) {
    return {
      ok: false,
      error: `apartment ${asked} is not on this call — apartments on this call: ` +
        [...new Set(ctx.charges.map((c) => c.unit))].join(", "),
    };
  }
  return { ok: true, charges: hit };
}

/** Move a set of charges to a status. Used by dispute and by the ownership pause. */
async function setStatus(charges: Charge[], status: string) {
  if (!charges.length) return;
  await db.from("charges").update({ status }).in("id", charges.map((c) => c.charge_id));
}

/**
 * payment_tickets has a CHECK that a captured authorisation must carry the call
 * it came from, because the recording IS the authorisation and a ticket nobody
 * can listen to must never be charged. But interactions is normally written by
 * the end-of-call report, which has not fired yet while the agent is still
 * talking. So the first tool call of any call creates the stub row, and the
 * end-of-call report fills in the transcript and audio later.
 */
async function interactionId(ctx: CallContext): Promise<string | null> {
  if (!ctx.callId) return null;

  // Read before write, rather than upsert. An upsert updates on conflict, which
  // would push started_at forward on every tool call until it recorded the last
  // one instead of the first — and started_at is what call duration is measured
  // from. A row that already exists is left exactly as it is.
  const found = await db
    .from("interactions")
    .select("id")
    .eq("external_call_id", ctx.callId)
    .maybeSingle();
  if (found.data?.id) return found.data.id;

  // Both of these were hardcoded — "voice" and "outbound" — from when Vapi was
  // the only caller, and both were already wrong: every WhatsApp interaction
  // written on 8 Aug is filed as an outbound voice call. The dashboard would
  // have reported those as calls that were placed, which is not a display bug
  // but a false statement about what happened.
  //
  // A chat is inbound by definition here: the resident writes first, always.
  const wa = channel(ctx) === "whatsapp";
  const { data } = await db
    .from("interactions")
    .insert({
      external_call_id: ctx.callId,
      channel: wa ? "whatsapp" : "voice",
      direction: wa ? "inbound" : "outbound",
      // The phone is on the call id as `wa:<number>` and nowhere else for chat,
      // so without this the row cannot be tied back to a person at all. On a
      // voice call it is `customer.number`, which until 19 Aug was read here and
      // nowhere else — recorded against the call and then dropped when the
      // ticket was written, which is exactly the number the office needs.
      caller_phone: wa ? ctx.callId.slice(3) : ctx.callerPhone,
      resident_id: ctx.residentId,
      started_at: new Date().toISOString(),
    })
    .select("id")
    .single();

  // Two tools firing at once both miss the select and one insert loses the
  // unique constraint. Re-read rather than fail: the row exists either way.
  if (data?.id) return data.id;
  const retry = await db
    .from("interactions")
    .select("id")
    .eq("external_call_id", ctx.callId)
    .maybeSingle();
  return retry.data?.id ?? null;
}

/**
 * Which front door this row came in through.
 *
 * Hardcoded "voice" at all three insert sites while Vapi was the only caller.
 * WhatsApp writes through this same function now, so every one of them was
 * about to start lying — and a channel column that lies is worse than one that
 * is absent, because every report broken down by channel would have been
 * quietly wrong rather than obviously empty.
 *
 * The `wa:` prefix is minted by the WhatsApp bot's tool nodes, which build a
 * call id of `wa:<phone>` precisely because this function was written for Vapi
 * and expects a call to exist.
 */
// The marker `request_standing_order` finds its own tickets by. Deliberately
// not a status or a type: a standing order is not a category of fault, and
// `requests.type` is constrained to Homies' eleven facility categories.
const STANDING_ORDER_REF = "standing_order";

function channel(ctx: { callId?: string | null }): string {
  return String(ctx?.callId ?? "").startsWith("wa:") ? "whatsapp" : "voice";
}

/**
 * An apartment number, or nothing.
 *
 * A lobby leak has no apartment, and the prompt says so — but on 8 Aug the
 * model complied with the idea and not the field: it filled `unit` with
 * "שטחים משותפים" ("common areas"). Nothing errors. The row reads correctly to
 * a person and is wrong to every query: `unit IS NULL` no longer finds
 * common-area faults, grouping by unit invents a flat called Common Areas, and
 * the duplicate guard below stops matching, because two lobby leaks phrased
 * differently get two different "units".
 *
 * A model asked to leave a field empty will often name the emptiness instead.
 * So the writer decides, not the prompt: a unit is a short thing with a digit
 * in it, and a label is not a unit.
 */
function unitOf(value: unknown): string | null {
  const v = String(value ?? "").trim();
  if (!v) return null;
  // Long enough to be a phrase, or carrying no digit at all — "קומה ב" and
  // "ground floor" are as wrong as "common areas", and none of them identify a
  // flat. Kept deliberately crude: the cost of dropping an odd real unit is one
  // ticket a human still reads, and the cost of keeping a label is silent.
  if (v.length > 12 || !/\d/.test(v)) return null;
  return v;
}

/**
 * A street or a spoken address, flattened for comparison. Never for display.
 *
 * The quote marks are the point. ז'בוטינסקי arrives with U+05F3, with an ASCII
 * apostrophe, and with nothing at all, from the same person on different days;
 * a transcriber picks whichever it likes. None of those are a different street.
 * `רחוב` and `רח'` are dropped for the same reason — they are the word "street"
 * and carry no information, but they do stop a containment test from matching.
 *
 * Kept identical to `norm()` in scripts/oxs_buildings_sync.py, which writes
 * `buildings.street_norm`. If the two ever disagree the column stops matching
 * what is compared against it, and the symptom is a building that simply
 * cannot be found.
 */
function norm(value: unknown): string {
  return String(value ?? "")
    .replace(/["'`׳״]/g, "")
    .replace(/(^|\s)(רחוב|רח)(\s|$)/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * The one number inside a quoted ticket reference that identifies the ticket.
 *
 * Three shapes reach this, and the middle of one is the end of another:
 *
 *   255-1047-26     ours since 18 Aug   - OXS's shape, serial in the MIDDLE
 *   255-26277-26    theirs, imported    - same shape, five-digit serial
 *   HM-2026-1013    ours before 18 Aug  - serial at the END, 2026 is a year
 *
 * All three are `A-B-C`, so counting segments cannot tell them apart. What can
 * is that only the OXS shape has three NUMERIC segments: `HM` is a prefix we
 * invented and never was a number. So the three-number pattern is tried first
 * and yields its middle; what is left over is the old shape and yields its
 * tail. Reading `2026` out of the old one instead is the failure that matters -
 * it matches nothing, and the resident is told their own ticket does not exist.
 *
 * Matched anywhere in the string rather than against the whole of it, because
 * the model passes what the resident wrote and residents write sentences.
 * Anything with no such pattern is taken as the serial itself: what a resident
 * usually types is `1047`, or says into a phone for a transcriber to render as
 * digits. The four-digit floor is what stops an apartment number in that
 * argument from going looking for a ticket.
 */
// Digits as they are SPOKEN, in both languages.
//
// The agent reads a reference out one digit at a time — "1, 0, 6, 3" — and the
// resident reads it back the same way. What the transcriber then hands over is
// "one zero six three", and on 19 Aug the agent passed exactly that through and
// was told the reference does not exist. It did exist; 255-1063-26 was sitting
// in the table the whole call.
//
// Measured before the fix: "1063", "1, 0, 6, 3", "10 63", "255-1063-26" and
// "HM-2026-1063" all found it. "one zero six three" found nothing. The one form
// a person actually says out loud was the only one that failed.
//
// Hebrew carries both genders because a digit read aloud takes whichever the
// speaker reaches for, and "oh" for zero because English speakers say it more
// often than "zero".
const SPOKEN_DIGITS: Record<string, string> = {
  zero: "0", oh: "0", o: "0", nought: "0",
  one: "1", two: "2", three: "3", four: "4", five: "5",
  six: "6", seven: "7", eight: "8", nine: "9",
  "אפס": "0",
  "אחת": "1", "אחד": "1",
  "שתיים": "2", "שניים": "2", "שתי": "2", "שני": "2",
  "שלוש": "3", "שלושה": "3",
  "ארבע": "4", "ארבעה": "4",
  "חמש": "5", "חמישה": "5",
  "שש": "6", "שישה": "6",
  "שבע": "7", "שבעה": "7",
  "שמונה": "8",
  "תשע": "9", "תשעה": "9",
};

/** "one zero six three" -> "1063". Anything not a spoken digit is left alone. */
function digitsFromWords(raw: string): string {
  return raw
    .split(/[\s,.\-–—]+/)
    .map((w) => SPOKEN_DIGITS[w.toLowerCase()] ?? w)
    .join("");
}

// What each category sounds like when somebody says it, in both languages.
//
// A ticket's `type` is chosen by the agent that opened it and is wrong often
// enough to matter — `255-1063-26` reads "elevator issue" and is filed `other`.
// Filtering on the category alone therefore misses the caller's own request;
// dropping the filter instead hands back the whole building, which on 19 Aug
// read another resident's stolen parcel out to a stranger.
//
// Matching the words against the description as well as the category is what
// finds the caller's request without widening to everybody's.
const TYPE_WORDS: Record<string, string[]> = {
  elevator: ["elevator", "lift", "מעלית"],
  lighting: ["light", "lighting", "bulb", "נורה", "תאורה", "אור"],
  plumbing: ["leak", "water", "pipe", "drain", "נזילה", "מים", "צנרת", "ביוב"],
  electrical: ["electric", "power", "socket", "חשמל", "שקע"],
  cleaning: ["clean", "rubbish", "bin", "ניקיון", "אשפה", "זבל"],
  gardening: ["garden", "tree", "גינה", "עץ", "גינון"],
  pest_control: ["pest", "rat", "cockroach", "מזיקים", "ג'וקים", "עכבר"],
  locksmith: ["lock", "key", "door", "מנעול", "מפתח", "דלת"],
  fire_safety: ["fire", "smoke", "extinguisher", "אש", "עשן", "מטפה"],
  maintenance: ["maintenance", "תחזוקה"],
  // Ours, not OXS's (migration 025, 25 Aug): a complaint is a ticket on both
  // channels. The words are what a caller says when asking about one.
  complaint: ["complaint", "noise", "neighbour", "neighbor", "תלונה", "רעש", "שכן", "שכנים"],
};

/** Does this row look like the thing the caller named? */
function matchesType(row: any, type: string): boolean {
  if (!type) return true;
  if (String(row?.type ?? "") === type) return true;
  const words = TYPE_WORDS[type] ?? [type];
  const text = String(row?.description ?? "").toLowerCase();
  return words.some((w) => text.includes(w.toLowerCase()));
}

function serialOf(value: unknown): string | null {
  let raw = String(value ?? "").trim();

  // Only when the string does not already carry a serial's worth of digits, so
  // a well-formed reference is never touched by this. A half-and-half string —
  // "255, one zero six three, 26" — still fails, and is left failing on purpose:
  // the agent reads out the middle four and nothing else, so that is not a
  // shape anybody says.
  if (!/\d{4}/.test(raw)) {
    const spoken = digitsFromWords(raw);
    if (/\d{4}/.test(spoken)) raw = spoken;
  }

  const oxs = raw.match(/(\d{3})-(\d{4,6})-(\d{2})(?!\d)/);
  if (oxs) return oxs[2];

  const legacy = raw.match(/(\d{4})-(\d{3,6})(?!\d)/);
  if (legacy) return legacy[2];

  const bare = raw.replace(/\D/g, "");
  return bare.length >= 4 && bare.length <= 6 ? bare : null;
}

/**
 * The active building list, held between invocations.
 *
 * 173 rows of five short columns — about 25KB, and it changes when Homies takes
 * on or drops a building, which is not something that happens during a
 * conversation. Fetching it per tool call would add a round trip to a lookup
 * that sits in the middle of a resident waiting for an answer.
 *
 * Five minutes rather than forever, because an Edge Function instance can live
 * a long time and the failure of a stale list is invisible: a building imported
 * this morning is reported as one we do not manage, and nobody finds out until
 * a resident is turned away.
 */
let buildingCache: { at: number; rows: any[] } | null = null;

async function buildingList(): Promise<any[]> {
  if (buildingCache && Date.now() - buildingCache.at < 5 * 60 * 1000) {
    return buildingCache.rows;
  }
  const { data } = await db.from("buildings")
    .select("id,address,street,street_norm,number,city")
    .eq("active", true);
  // Longest street name first, so `אלתרמן נתן` is tested before a street
  // called `אלתרמן` would be. Containment matches both, and the more specific
  // one has to win — otherwise every address on the two-word street resolves
  // to the one-word one. Sorted here rather than in the query because this is
  // by LENGTH, and `.order()` would sort alphabetically.
  const rows = (data ?? []).sort(
    (a: any, b: any) => b.street_norm.length - a.street_norm.length,
  );
  // A failed fetch is not cached. Caching an empty list would answer "we do not
  // manage that building" for every caller for five minutes.
  if (rows.length) buildingCache = { at: Date.now(), rows };
  return rows;
}

/**
 * Which building a resident just named, if any.
 *
 * Shared by `verify_address`, which reports the outcome to the bot, and by
 * `open_request`, which uses it to file the ticket against the address as we
 * write it. One matcher, because two would drift and the direction they drift
 * is a ticket verified against one building and filed against another.
 *
 * Returns a discriminated outcome rather than a boolean, because the useful
 * answers are not found/not-found. `number_off_street` — the street is real,
 * that number is not — is what lets the caller be told something true instead
 * of being made to repeat themselves.
 */
type Match =
  | { status: "empty" }
  | { status: "found"; building: any }
  | { status: "street_unknown" }
  | { status: "ambiguous"; candidates: any[] }
  | { status: "need_number" | "number_off_street"; street: any; numbers: string[] };

async function matchBuilding(saidRaw: unknown): Promise<Match> {
  const said = norm(saidRaw);
  if (!said) return { status: "empty" };

  const all = await buildingList();
  // The house number is asked for as a standalone token, so `14` cannot match
  // inside another number and `6-8` matches as the single thing it is.
  const tokens = new Set(said.split(/[\s,.]+/).filter(Boolean));

  // Pass one: the sentence contains the registered street whole. Substring
  // rather than token overlap, because a street is one or two words said in
  // order, and overlap alone would match `נתן` against every building on a
  // street called אלתרמן נתן.
  let onStreet = all.filter((b: any) => said.includes(b.street_norm));
  let exact = onStreet.filter((b: any) => tokens.has(b.number));

  // Pass two: the street as registered is longer than the street as spoken.
  // `אלתרמן נתן 6-8` is a real address and nobody says the poet's first name —
  // they say אלתרמן. Pass one cannot match that, because the sentence does not
  // contain the whole registered name.
  //
  // Runs only when pass one found nothing, and only ever alongside an exact
  // house number: one shared word is weak evidence, and the number is what
  // makes the pair specific. Words of one or two letters are ignored, because a
  // Hebrew preposition glued to the next word is not a street name.
  if (!exact.length) {
    const partial = all.filter((b: any) =>
      tokens.has(b.number) &&
      b.street_norm.split(" ").some((w: string) => w.length > 2 && tokens.has(w))
    );
    if (partial.length) {
      onStreet = partial;
      exact = partial;
    }
  }

  if (!onStreet.length) return { status: "street_unknown" };

  if (!exact.length) {
    // The street is real. Either no number was said at all, or the one that was
    // said is not a building we manage — a different sentence in each case, so
    // a different answer. `onStreet[0]` is the longest matching street name,
    // because the list is sorted that way, and the numbers offered have to
    // belong to the most specific street the caller named.
    const street = onStreet[0].street_norm;
    const same = onStreet.filter((b: any) => b.street_norm === street);
    return {
      status: /\d/.test(said) ? "number_off_street" : "need_number",
      street: same[0],
      numbers: [...new Set(same.map((b: any) => String(b.number)))].slice(0, 12),
    };
  }

  // Measured 13 Aug: this cannot happen on today's data — street+number is
  // unique across all 173 buildings. Handled anyway, because that is a property
  // of the data and not a promise, and the failure it prevents is a confident
  // wrong answer. `oxs_buildings_sync.py` refuses to write if the uniqueness
  // ever breaks, so reaching here means the sync was bypassed.
  if (exact.length > 1) return { status: "ambiguous", candidates: exact };

  return { status: "found", building: exact[0] };
}

/**
 * Mirror a just-opened ticket into OXS, where Homies' staff actually work.
 *
 * Decided 26 Aug, reversing the read-only rule on this ONE endpoint: the
 * External API v1 grew POST/PUT/DELETE for service_calls (and only for
 * service_calls — finance and general keys cannot even be created with write
 * scope), the owner asked for tickets to land in Homies, and a live
 * create-read-delete round trip was run against the real API before this was
 * written. The rest of OXS stays read-only, forever.
 *
 * Best-effort BY DESIGN. The resident has already been promised the reference
 * by the time this runs, so an OXS outage must not unwrite that promise: any
 * failure here is logged and swallowed, and the ticket lives on in our table
 * exactly as before. The one thing a failure costs is staff seeing the ticket
 * only on the dashboard rather than in OXS.
 *
 * The created call's `_id` is written back to `requests.oxs_ref` — the same
 * column the importer keys on — which is how `oxs_requests_sync.py` recognises
 * this call as ours when it comes back in the feed, instead of minting a
 * duplicate row. The sync skips any oxs_ref held by a row it does not own.
 *
 * Created records carry no OXS user (the spec attributes them to the API key),
 * and `availableToTenants` defaults to false — the resident's own record is
 * OUR ticket; the OXS row is for staff.
 */
async function oxsMirror(
  buildingOxsId: string, description: string, unit: string | null,
  reference: string, rowId: string,
) {
  const key = Deno.env.get("OXS_KEY_REQUESTS") ?? "";
  if (!key) return; // not configured: the mirror is off, the ticket is fine
  try {
    const r = await fetch("https://api.oxs.co.il/api/external/v1/service-calls", {
      method: "POST",
      headers: { "x-api-key": key, "content-type": "application/json" },
      body: JSON.stringify({
        buildingId: buildingOxsId,
        // Staff-facing, so it carries what a dispatcher needs at a glance:
        // the fault, the flat when the fault is in one, and our reference so
        // the two systems can be joined by a human as well as by oxs_ref.
        description: description
          + (unit ? ` (דירה ${unit})` : "")
          + ` [בוט, סימוכין ${reference}]`,
      }),
    });
    const d = await r.json().catch(() => null);
    const oxsId = d?.data?._id;
    if (d?.status === 1 && oxsId) {
      await db.from("requests").update({ oxs_ref: String(oxsId) }).eq("id", rowId);
    } else {
      console.error("oxs mirror refused", r.status, JSON.stringify(d).slice(0, 200));
    }
  } catch (err) {
    console.error("oxs mirror failed", String(err).slice(0, 200));
  }
}

/** The address as we write it, or "" when what was said resolves to nothing. */
async function canonicalAddress(said: unknown): Promise<string> {
  const m = await matchBuilding(said);
  return m.status === "found" ? String(m.building.address) : "";
}

/**
 * Did we place this call, or did it come to us?
 *
 * It decides whether `ctx.building` and `ctx.unit` may be believed, and getting
 * it wrong is what put somebody else's address on a ticket on 19 Aug. Outbound,
 * the campaign runner attached the address and the model is not allowed to
 * overwrite it. Inbound, an address on the call did not come from the caller —
 * it came from whatever started the call, which on the demo page was a debt
 * campaign's file for an unrelated person. The caller who says "Herzo" and does
 * not know their apartment must not end up with a ticket reading Herzl 14,
 * flat 12.
 *
 * A dialled call always carries either the resident we dialled or the charges we
 * rang about; the runner cannot place one without them. An inbound call carries
 * neither, however much else is attached to it. So this is the test, rather than
 * "is `building` set" — the whole point is that `building` was set and wrong.
 */
function dialled(ctx: CallContext): boolean {
  return Boolean(ctx.residentId || ctx.charges.length);
}

/**
 * A phone number as it is stored, or nothing.
 *
 * `residents.phone` is E.164 (+972501234567) everywhere — the seed writes it
 * that way and every OXS importer normalises to it. A person typing their own
 * number into WhatsApp does not: they write 050-123-4567, or 0501234567, or
 * paste it back with the country code. Comparing those to the column as typed
 * fails on a number that is genuinely theirs, and a security check that rejects
 * the honest case is a security check nobody keeps.
 *
 * Deliberately conservative about what it accepts. Anything that does not land
 * on a plausible Israeli number returns null and is treated as *not given* —
 * the caller is asked again rather than matched loosely.
 */
function phoneOf(value: unknown): string | null {
  const digits = String(value ?? "").replace(/\D+/g, "");
  if (!digits) return null;
  // With the country code, however it was written: +972-50…, 00972 50…, 972…
  if (digits.startsWith("00972")) return e164(digits.slice(5));
  if (digits.startsWith("972")) return e164(digits.slice(3));
  // Local form, with the trunk zero.
  if (digits.startsWith("0")) return e164(digits.slice(1));
  // A mobile with the leading zero left off — 50 1234567.
  if (/^5\d{8}$/.test(digits)) return e164(digits);
  return null;
}

function e164(national: string): string | null {
  const n = national.replace(/^0+/, "");
  // Israeli national numbers are 8 (landline) or 9 (mobile) digits.
  return n.length === 8 || n.length === 9 ? "+972" + n : null;
}

/**
 * Is this the name on the record — said by someone who knows it, not guessed?
 *
 * Compared as a set of words rather than as a string, because `יוסי כהן` and
 * `כהן יוסי` are the same person and an exact-string test would reject the
 * second. Two distinct words are the floor: a surname on its own is shared by
 * a whole family and half a building, and it is exactly what a neighbour would
 * try.
 *
 * Containment rather than equality, so a record carrying a middle name still
 * matches the two words its owner actually says. The looseness is bounded — a
 * stranger still has to produce words that are all on the record — and the
 * phone is the other half of the check.
 */
function sameName(stored: unknown, given: unknown): boolean {
  const words = (v: unknown) =>
    String(v ?? "")
      .replace(/["'`׳״]/g, "")
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean);
  const on = new Set(words(stored));
  const said = new Set(words(given));
  if (on.size < 2 || said.size < 2) return false;
  return [...said].every((w) => on.has(w));
}

/**
 * requests.urgency has been constrained to these four since migration 001.
 *
 * The value used to be passed straight through, so an out-of-enum word was
 * caught by Postgres and came back as an English constraint message in the
 * middle of a Hebrew call — which the agent can neither read out nor act on.
 * `urgent` reached here that way on 8 Aug from the WhatsApp bot's own tool
 * schema. The synonyms below are the near-misses a model actually produces;
 * anything else lands on normal, because urgency is inferred rather than asked
 * for and a wrong-but-valid value costs less than a failed write.
 *
 * Deliberately not clamped to `low`: the failure that matters is an emergency
 * filed as routine, so unknown words go to the middle and not to the floor.
 */
function urgency(value: unknown): string {
  const v = String(value ?? "").trim().toLowerCase();
  const allowed = ["low", "normal", "high", "emergency"];
  if (allowed.includes(v)) return v;
  const synonyms: Record<string, string> = {
    urgent: "high",
    critical: "emergency",
    immediate: "emergency",
    routine: "normal",
    medium: "normal",
    "": "normal",
  };
  return synonyms[v] ?? "normal";
}

// ---------------------------------------------------------------------------
// The tools
// ---------------------------------------------------------------------------
// Each returns a short object the agent can read back. Keep the strings plain:
// they land in the model's context and anything florid there gets spoken.

const tools: Record<string, (args: any, ctx: CallContext) => Promise<unknown>> = {
  /**
   * They agreed to settle, so OXS sends them a link and they pay it themselves.
   *
   * This replaced open_payment_ticket on 4 Aug. Nothing here sends the link:
   * the row is the request and OXS is the sender, which is why the agent says a
   * link is on its way rather than that one has arrived. When the OXS API is
   * finally documented, the call to it goes here — the tool's contract with the
   * agent does not change.
   *
   * Deliberately does NOT touch charges.status. The old flow moved the charge to
   * `pending_charge` because a staff member was about to charge a card; a link
   * that has been sent is not a payment, and marking it as one would take the
   * resident out of the call queue for something they have not done yet.
   */
  async send_payment_link(args, ctx) {
    const t = targets(ctx, args);
    if (!t.ok) return { ok: false, error: t.error };
    const iid = await interactionId(ctx);

    // A row per charge, each carrying its OWN amount and period. Using ctx.amount
    // here would have written the call total against every apartment — two rows
    // of 1,230 for a resident who owes 450 and 780 — and the link the office
    // sends is built from this row.
    const { error } = await db.from("payment_links").insert(
      t.charges.map((c) => ({
        charge_id: c.charge_id,
        resident_id: ctx.residentId,
        interaction_id: iid,
        amount: c.amount,
        period: c.period,
        status: "requested",
        note: args?.note ?? null,
      })),
    );

    if (error) return { ok: false, error: error.message };
    return { ok: true, charges_written: t.charges.length };
  },

  /**
   * Retired 4 Aug — no longer offered to the agent, kept so a stale assistant
   * still gets an answer. authorization_captured was the difference between
   * "a person may charge the card on file" and "the office has to call them".
   */
  async open_payment_ticket(args, ctx) {
    if (!ctx.chargeId) return { ok: false, error: "no charge on this call" };
    const captured = args?.authorization_captured === true;
    const iid = await interactionId(ctx);

    // The constraint would reject this anyway; failing here says why.
    if (captured && !iid) {
      return { ok: false, error: "cannot capture authorisation without a call record" };
    }

    // No card, no authorisation — the claim cannot be true whatever the agent
    // believed. It believed it on 4 Aug: a resident with no card on file was
    // told there was one and a ticket was written claiming they had approved a
    // charge to it. The prompt is asked not to do this; here it cannot.
    if (captured && !ctx.cardLast4) {
      return {
        ok: false,
        error: "no card on file for this resident — authorisation cannot be captured",
      };
    }

    const { data, error } = await db
      .from("payment_tickets")
      .insert({
        charge_id: ctx.chargeId,
        resident_id: ctx.residentId,
        interaction_id: iid,
        authorization_captured: captured,
        amount: ctx.amount,
        period: ctx.period,
        card_last4: ctx.cardLast4,
        note: args?.note ?? null,
      })
      .select("id")
      .single();

    if (error) return { ok: false, error: error.message };

    // Stop the same debt being called about again while a person reviews it.
    await db.from("charges").update({ status: "pending_charge" }).eq("id", ctx.chargeId);

    return { ok: true, ticket_id: data.id, authorization_captured: captured };
  },

  /**
   * `said` is their own words and is required. Our parse of a spoken Hebrew date
   * is the thing most likely to be wrong later, so what they actually said is
   * kept beside it and outranks it when a promise is disputed.
   */
  async log_promise_to_pay(args, ctx) {
    if (!args?.said) return { ok: false, error: "said is required" };
    const t = targets(ctx, args);
    if (!t.ok) return { ok: false, error: t.error };

    const iid = await interactionId(ctx);
    const { error } = await db.from("promises_to_pay").insert(
      t.charges.map((c) => ({
        charge_id: c.charge_id,
        interaction_id: iid,
        promised_date: args?.promised_date ?? null,
        said: String(args.said),
      })),
    );

    return error
      ? { ok: false, error: error.message }
      : { ok: true, charges_written: t.charges.length };
  },

  /**
   * There is no standing_orders table and there should not be one — the agent
   * cannot set a standing order up, only record that they asked for one.
   *
   * IT WRITES TWO ROWS, AND THE SECOND ONE IS WHY THIS WORKS AT ALL.
   * Until 18 Aug it wrote only the `call_outcomes` flag, with a comment saying
   * that was "where a person will look for it". Nobody looks there: the Calls
   * page has five tabs and none of them filters on `standing_order_requested`
   * or `office_to_contact`. Two residents had agreed to set one up and were
   * waiting on an office that had never been told. So it now also opens a
   * request — the queue staff actually work from, with a reference the resident
   * can quote — and the flag stays, because the flag is what the collections
   * side reads off the call.
   *
   * The same silence still applies to `transfer_to_human`, which writes the
   * same table and is read by nobody. That one is open.
   */
  async request_standing_order(_args, ctx) {
    if (!ctx.charges.length) return { ok: false, error: "no charge on this call" };
    const iid = await interactionId(ctx);

    // Call-level, and takes no apartment. A standing order is an arrangement
    // with a person about their monthly payment; "a standing order for flat 4
    // only" is not a thing the office sets up, so offering the split here would
    // let the agent record a request nobody can act on.
    await db.from("call_outcomes").insert({
      charge_id: ctx.charges.length === 1 ? ctx.charges[0].charge_id : null,
      resident_id: ctx.residentId,
      interaction_id: iid,
      outcome: "office_to_contact",
      standing_order_requested: true,
    });

    // `requests.building` is NOT NULL, and an outbound call carries the building
    // in its variables — but a call started without them would otherwise fail
    // the insert and turn a resident who said yes into an error. Fall back to
    // what we hold on the resident, and if there is still nothing, keep the flag
    // and skip the ticket rather than failing the tool. A recorded yes with no
    // ticket is bad; a yes that errors out mid-call is worse.
    let building = ctx.building;
    if (!building && ctx.residentId) {
      const { data: r } = await db.from("residents").select("building")
        .eq("id", ctx.residentId).limit(1);
      building = r?.[0]?.building ?? null;
    }
    if (!building) return { ok: true, request_opened: false };

    // One open ticket per resident, with NO time window — unlike open_request's
    // 30-minute guard. A leak reported again next morning is a new fact; a
    // standing order asked for again next month is the same unmet request, and
    // stacking a second ticket on it tells the office there are two arrangements
    // to set up when there is one.
    const { data: already } = await db
      .from("requests")
      .select("reference")
      .eq("oxs_ref", STANDING_ORDER_REF)
      .eq("resident_id", ctx.residentId)
      .in("status", ["open", "in_progress", "needs_review"])
      .limit(1);
    if (already && already.length) {
      return { ok: true, reference: already[0].reference, duplicate: true };
    }

    const { data, error } = await db
      .from("requests")
      .insert({
        resident_id: ctx.residentId,
        interaction_id: iid,
        type: "other",
        description:
          "בקשה להוראת קבע. הדייר ביקש בשיחה להסדיר את התשלום החודשי " +
          "בהוראת קבע — יש ליצור איתו קשר להסדרה.",
        building,
        unit: ctx.unit,
        urgency: "normal",
        opened_via: channel(ctx),
        // Not an OXS id. Same use as save_partial_request's `partial:` sentinel:
        // a marker this handler can find its own rows by. The unique index on
        // this column is scoped to `opened_via = 'oxs'`, so repeating it here is
        // legal and deliberate.
        oxs_ref: STANDING_ORDER_REF,
      })
      .select("reference")
      .single();

    // The flag is already written and the resident already said yes. A failed
    // insert loses the ticket, not the outcome, so it is reported and not thrown.
    return error
      ? { ok: true, request_opened: false, error: error.message }
      : { ok: true, reference: data.reference };
  },

  /**
   * They say they already paid. The agent never asks when or how.
   *
   * Takes an apartment, and this is the tool the whole feature turns on. A
   * resident with two flats who says "I paid for four" has disputed four. Before
   * this, the only shape available was disputing the call — so the office
   * received a claim against both flats, one of which the resident never made,
   * and the honest one got buried in it.
   */
  async log_disputed_payment(args, ctx) {
    const t = targets(ctx, args);
    if (!t.ok) return { ok: false, error: t.error };

    const iid = await interactionId(ctx);
    const { error } = await db.from("payment_disputes").insert(
      t.charges.map((c) => ({
        charge_id: c.charge_id,
        interaction_id: iid,
        receipt_requested: true,
      })),
    );
    if (error) return { ok: false, error: error.message };

    await setStatus(t.charges, "disputed");
    return { ok: true, charges_written: t.charges.length };
  },

  /**
   * A resident asks what happened to a ticket. Read-only, and the answer is
   * live: these rows are the system of record for tickets opened here, so no
   * freshness caveat is owed — PRD §2.2's caveat is about OXS-side status,
   * which this deliberately does not touch.
   *
   * Lookup order mirrors open_request's asymmetry: an explicit reference wins,
   * then the resident on the call, then building+unit — context first,
   * arguments second. The reference matches on its serial alone - see
   * `serialOf` - because a caller says "אלף שלוש עשרה", not "255-1013-26", and
   * because tickets opened before 18 Aug still carry the old HM- shape.
   */
  /**
   * Is this a building we manage, and does that apartment exist in it.
   *
   * Asked for 13 Aug. The bot asks a resident which building and which
   * apartment they are reporting from, and until now there was nothing to
   * check the answer against: `residents.building` is a string composed at
   * import time and stored, which is enough to file a ticket and useless for
   * verifying one. A caller who named a street we do not manage, or apartment
   * 40 in a building with 25 flats, was recorded verbatim and the ticket went
   * to a person to puzzle out.
   *
   * The matching itself is `matchBuilding()` above, shared with
   * `open_request` so a ticket is filed against the same building that was
   * verified. This handler is the part that turns an outcome into something a
   * bot can say.
   *
   * THE THREE ANSWERS, AND WHY THE THIRD ONE MATTERS MOST
   * Found, not found, and *found the street but not that number* — which is
   * the one that lets the bot say something true and useful. "We manage הרצל
   * 12 and הרצל 16, not 14" ends the conversation correctly; "not found" makes
   * the resident repeat themselves at a machine that will fail again. Same for
   * apartments: the flat range comes back with the refusal, so the reply can
   * be "that building has flats 1 to 25".
   *
   * AMBIGUITY IS RETURNED, NEVER RESOLVED
   * Two candidates come back as two candidates for the bot to ask about. This
   * is feature 01's confidence floor: below it, unmatched beats guessed. A
   * ticket filed against a confidently wrong building reads correct to
   * everyone who sees it and sends a van to the wrong street.
   */
  async verify_address(args, ctx) {
    const unit = unitOf(args?.unit);
    const m = await matchBuilding(args?.building);

    if (m.status === "empty") {
      return { ok: true, building_found: false, reason: "need_building" };
    }
    if (m.status === "street_unknown") {
      return { ok: true, building_found: false, reason: "street_unknown" };
    }
    if (m.status === "need_number" || m.status === "number_off_street") {
      return {
        ok: true,
        building_found: false,
        // The bot says a different sentence for each, which is the whole point
        // of keeping them apart: nothing was said is not the wrong thing said.
        reason: m.status === "need_number" ? "need_number" : "number_not_on_street",
        street: m.street.street,
        numbers_we_manage: m.numbers,
      };
    }
    if (m.status === "ambiguous") {
      return {
        ok: true,
        building_found: false,
        reason: "ambiguous",
        candidates: m.candidates.map((b: any) => b.address).slice(0, 5),
      };
    }

    const b: any = m.building;
    const out: Record<string, unknown> = {
      ok: true,
      building_found: true,
      // The string the ticket should carry: the address as we write it, not as
      // the resident phrased it. `open_request` re-derives the same value
      // server-side, so a bot that ignores this cannot file a differently
      // spelled duplicate — but it is returned so the bot can read it back for
      // confirmation, which is the one place a wrong match gets caught.
      building: b.address,
      city: b.city,
    };

    const { data: flats } = await db.from("apartments")
      .select("number,order_index").eq("building_id", b.id)
      .order("order_index", { ascending: true });
    const numbers = (flats ?? []).map((f: any) => String(f.number).trim());
    // A building with no apartments imported is a gap in the sync, not a
    // building with no flats. Saying "that flat does not exist" off missing
    // data would be a confident lie, so the unit is left unchecked instead.
    const known = numbers.length > 0;
    if (known) {
      out.apartment_count = numbers.length;
      // The spoken range comes from the NUMERIC flats only. 138 of the 4,092
      // are labels rather than numbers — חנות, מסחר 2, מחסן, חניה 43,
      // דירת ועד — and they sort by `order_index` like anything else, so the
      // last row of a building is quite often a shop. Read straight off the
      // ends of the list, the helpful sentence becomes "this building has
      // apartments 1 to חנות".
      const digits = numbers.filter((n) => /^\d+$/.test(n)).map(Number);
      if (digits.length) {
        out.first_unit = String(Math.min(...digits));
        out.last_unit = String(Math.max(...digits));
      }
    }

    if (!unit) {
      // Not an error. A lift, a lobby or a stairwell has no apartment, and the
      // prompt has said so since 8 Aug — the tool must not push back on the one
      // case the prompt spent a section getting right.
      out.unit_checked = false;
      return out;
    }

    out.unit_checked = known;
    if (known) {
      // Compared through norm() on BOTH sides, for the same reason street names
      // are. `לואי מרשל 41` numbers its flats `1א'`, `1ב'`, `2א'` — number plus
      // a Hebrew letter plus a geresh — and nobody types the geresh. A raw
      // string compare tells a resident of 3א that their own flat does not
      // exist, which is the most insulting possible way for this feature to be
      // wrong.
      const want = norm(unit);
      out.unit_found = numbers.some((n) => norm(n) === want);
      out.unit = unit;
    }
    return out;
  },

  async get_request_status(args, ctx) {
    const fields =
      "reference,type,description,status,urgency,building,unit,created_at,updated_at";
    let rows: any[] | null = null;
    // How many recent requests in this building are NOT the one the caller
    // asked about. A count and nothing else — it is the most the agent is
    // allowed to say about somebody else's fault.
    let othersInBuilding = 0;
    // True when the caller named a building and nothing else, so their own
    // request cannot be told from a neighbour's.
    let namedNothing = false;

    const serial = serialOf(args?.reference);
    if (serial) {
      const { data, error } = await db
        .from("requests")
        .select(fields)
        .or(`reference.like.%-${serial}-%,reference.like.%-${serial}`)
        .order("created_at", { ascending: false })
        .limit(3);
      if (error) return { ok: false, error: error.message };
      rows = data;
    }

    // A REFERENCE ONE DIGIT SHORT IS A NEAR MISS, NOT A DEAD END.
    // On 19 Aug a caller said "one zero six three" and the agent passed "106" —
    // it dropped a digit somewhere between the transcriber and the tool call.
    // Three digits is below a serial's length, so this returned nothing and the
    // caller was told their reference does not exist. It did: 255-1063-26.
    //
    // Rather than fail, fill the missing digit with a wildcard and hand back the
    // handful that match. `partial_reference` is the agent's cue to read them
    // back and ask which — never to pick one, because picking is how somebody is
    // told about a stranger's fault.
    if (!rows?.length) {
      const short = String(args?.reference ?? "").replace(/\D/g, "");
      if (short.length === 3) {
        // Ten, because the missing digit has ten possible values and a limit
        // below that silently drops candidates. Measured at four: "106" came
        // back as 1064-1067 and cut off 1063, which was the one the caller
        // actually wanted — a near-miss recovery that confidently offers the
        // wrong four is worse than the dead end it replaced.
        const { data } = await db
          .from("requests")
          .select(fields)
          .like("reference", `%-${short}_-%`)
          .order("created_at", { ascending: false })
          .limit(10);

        // More than three is not a question anybody can answer out loud. Say
        // there are several and ask for the number again, rather than reading a
        // list of near-identical references down a phone.
        if (data && data.length > 3) {
          return { ok: true, found: 0, partial_reference: true,
                   too_many: data.length, requests: [] };
        }

        if (data?.length) {
          return {
            ok: true,
            found: data.length,
            partial_reference: true,
            as_of: "live",
            requests: data.map((r: any) => ({
              reference: r.reference,
              status: r.status,
              type: r.type,
              urgency: r.urgency,
              opened: String(r.created_at).slice(0, 10),
              last_update: String(r.updated_at).slice(0, 10),
              description: r.description ? String(r.description).slice(0, 200) : null,
            })),
          };
        }
      }
    }

    if (!rows?.length && ctx.residentId) {
      const { data, error } = await db
        .from("requests")
        .select(fields)
        .eq("resident_id", ctx.residentId)
        .order("created_at", { ascending: false })
        .limit(3);
      if (error) return { ok: false, error: error.message };
      rows = data;
    }

    // The building, and the apartment only if there is one.
    //
    // BOTH HALVES OF THIS CHANGED ON 19 AUG, AND BOTH WERE WRONG THE SAME WAY:
    // they assumed the caller would hand over a database value.
    //
    // 1. The match was `.eq`, so it wanted the building's name character for
    //    character — "סוקולוב 86, תל אביב - יפו", punctuation and city included.
    //    A caller says "Sokolov", or "Herzl", or "building one". Measured: an
    //    exact name matched, and the same name in lower case, the same name
    //    without its number, and anything a person would actually say all
    //    returned nothing. `ilike %…%` is what a caller can reach.
    //
    // 2. The apartment was REQUIRED, and for a shared fault that is the wrong
    //    question. A lift, a lobby light, a gate, a bin store — none of them are
    //    in a flat, and asking somebody which apartment their elevator is in is
    //    a question with no answer. The building alone is now a complete query.
    if (!rows?.length) {
      const building = ctx.building || args?.building || "";
      let unit = unitOf(ctx.unit || args?.unit);

      // A LIFT IS NOT IN A FLAT, AND THIS IS WHERE THAT STOPS BEING ADVICE.
      // The prompt tells the agent not to ask for an apartment when the fault is
      // a shared one, and on 19 Aug it asked anyway — twice in one call — then
      // passed the answers through: `{type: elevator, unit: "300"}`, and again
      // with "107". Both filtered the building's requests down to a flat that
      // has nothing to do with the lift, and both returned nothing while the
      // ticket sat there.
      //
      // An instruction the model can ignore is not a constraint. These five
      // categories cannot be inside anybody's apartment, so the apartment is
      // dropped here regardless of what arrived with it.
      if (unit && ["elevator", "lighting", "cleaning", "gardening",
                   "fire_safety"].includes(String(args?.type ?? ""))) {
        unit = null;
      }

      if (building) {
        let q = db.from("requests").select(fields).ilike("building", `%${building}%`);
        if (unit) q = q.eq("unit", unit);
        // The caller almost always names the thing — "the elevator", "the
        // lighting". Without it, a building with no apartment given returns
        // every recent request in the building and the agent reads out
        // somebody else's leak.
        //
        // BUT IT NARROWS AN ANSWER; IT NEVER CAUSES THERE TO BE NONE.
        // Added as a hard `.eq` on 19 Aug and wrong within the hour. A caller
        // asked about the lift and heard "I could not find any recent request
        // about the elevator" while `255-1063-26` — description "elevator
        // issue" — sat in the table. The row's `type` is `other`, because the
        // agent that opened it inferred the category and got it wrong, and the
        // filter then trusted that mistake over the caller.
        //
        // The type is written by an inference and the question is asked by a
        // person; where they disagree, the person is the one who knows. So it
        // is a soft filter: narrow with it, and if that empties the answer,
        // ask again without it. The cost is one extra query on the runs that
        // would otherwise have returned nothing.
        // One query, unfiltered by category, and the sorting happens here.
        //
        // The category filter used to run in the database and fall back to the
        // whole building when it matched nothing — which is how a caller asking
        // about the lift was read another resident's stolen parcel. Now
        // everything in the building comes back and `matchesType` splits it:
        // what the caller named is answered in full, and the rest is a NUMBER.
        // Never a description, never a reference, never a category.
        const type = String(args?.type ?? "").trim();
        const { data, error } = await q
          .order("created_at", { ascending: false })
          .limit(unit ? 5 : 12);
        if (error) return { ok: false, error: error.message };

        const all = data ?? [];
        const mine = type ? all.filter((r) => matchesType(r, type)) : all;
        othersInBuilding = all.length - mine.length;
        // Nothing was named to match on, so there is no way to tell the
        // caller's request from a neighbour's. The agent asks what it was
        // about; see `identify_needed` below.
        namedNothing = !type && all.length > 1;
        rows = mine.slice(0, unit ? 3 : 8);

        // A loose match can span two buildings — "Herzl" is Herzl 14 and
        // Herzl 22. Reading one building's requests to somebody standing in
        // the other is worse than asking which they meant, so this says so
        // rather than guessing. Named for the agent; the resident just gets
        // asked a question.
        const names = [...new Set((rows ?? []).map((r) => String(r.building)))];
        if (names.length > 1) {
          return { ok: true, found: 0, ambiguous_building: true, buildings: names };
        }
      }
    }

    return {
      ok: true,
      found: rows?.length ?? 0,
      as_of: "live", // our own system of record, not a nightly export
      // A count, deliberately. Decided 19 Aug: the agent may say how many
      // requests are open in a building and may not say what any of them is.
      // Somebody who names a street is not thereby entitled to their
      // neighbours' business.
      other_open: othersInBuilding,
      // The caller gave a building and named no fault, so nothing here can be
      // attributed to them. Descriptions are withheld and the agent asks what
      // it was about rather than reading the list.
      identify_needed: namedNothing || undefined,
      requests: (rows ?? []).map((r) => ({
        reference: r.reference,
        status: r.status, // open | in_progress | resolved | cancelled
        type: namedNothing ? undefined : r.type,
        urgency: namedNothing ? undefined : r.urgency,
        opened: String(r.created_at).slice(0, 10),
        last_update: String(r.updated_at).slice(0, 10),
        description: namedNothing
          ? undefined
          : (r.description ? String(r.description).slice(0, 200) : null),
      })),
    };
  },

  /**
   * How much does this apartment owe. Read-only: amounts and months, nothing
   * that moves money — payments, receipts and disputes stay with the team.
   *
   * IDENTITY, ON CHAT, IS TWO FACTS OR NOTHING (asked for 13 Aug)
   * PRD §13 #1 — prove who is asking before money is read out — was open until
   * now, and the demo posture was to answer whoever asked. On chat it no longer
   * is. A resident who wants a balance gives a full name *and* a phone number,
   * and the two have to land on the same record before a single shekel is read
   * back.
   *
   * What that closes: a name on its own, and a building with an apartment
   * number on its own, were both enough. Both are things a neighbour knows. So
   * were they enough for anyone who found the WhatsApp number — the bot would
   * read out a stranger's debt to whoever typed their name.
   *
   * The envelope number is no longer a shortcut past the question either. It
   * is a good signal and it is not proof: a handset gets lent, sold and shared,
   * and answering it silently means the bot never asks anybody anything. One
   * rule, no exception — an exception here is how the whole gate gets skipped.
   *
   * The two failures are told apart for the agent and not for the resident.
   * `need_identity` means it has not asked yet; `identity_failed` means the
   * pair did not match, and says nothing about *which* half was wrong. Telling
   * a caller their name was right but the number was not turns this into a
   * machine for testing guesses.
   *
   * On voice, nothing changes here. The debt agent dials a known resident and
   * `ctx.residentId` is already the answer; inbound identity is its own
   * problem and not this one.
   *
   * SINCE MIGRATION 012, DEBT BELONGS TO AN APARTMENT
   * How the caller was identified decides what they are told. Identified by
   * building+apartment, the answer covers that apartment only. Identified by
   * their phone or their name, it covers everything they own, with
   * `owed_apartments` splitting it — because an owner of three flats asking
   * "how much do I owe" means all three, and the same owner asking about 601
   * does not.
   */
  async get_balance(args, ctx) {
    const fields = "id,full_name,building,unit";
    let resident: any = null;
    // Set only when the caller identified themselves *by apartment*. Then the
    // answer is about that apartment and no other — an owner of three flats
    // asking about 601 must not be read the total for all three.
    let askedUnit: string | null = null;

    if (channel(ctx) === "whatsapp") {
      const given = String(args?.name ?? "").trim();
      const phone = phoneOf(args?.phone);
      if (!given || !phone) {
        return {
          ok: true,
          found: 0,
          need_identity: true,
          missing: [!given ? "name" : null, !phone ? "phone" : null].filter(Boolean),
        };
      }
      const { data } = await db.from("residents").select(fields)
        .eq("phone", phone).maybeSingle();
      // One flag for both halves. See the note above: a per-half answer is an
      // oracle, and an oracle plus a list of surnames is a search.
      if (!data || !sameName(data.full_name, given)) {
        return { ok: true, found: 0, identity_failed: true };
      }
      resident = data;
      // An apartment named alongside the identification still narrows the
      // answer, exactly as it did before — but now only among the flats this
      // verified resident actually owns, because the charge query is already
      // filtered by their id.
      askedUnit = unitOf(args?.unit);
    }
    if (!resident && ctx.residentId) {
      const { data } = await db.from("residents").select(fields)
        .eq("id", ctx.residentId).maybeSingle();
      resident = data;
    }
    if (!resident) {
      const building = String(args?.building ?? "").trim();
      const unit = String(args?.unit ?? "").trim();
      if (building && unit) {
        const { data } = await db.from("residents").select(fields)
          .eq("building", building).eq("unit", unit).limit(1);
        resident = data?.[0] ?? null;
        if (resident) askedUnit = unit;

        // `residents.unit` names only ONE of an owner's flats — since
        // migration 012 the apartment that owes lives on the charge. So a
        // caller from the second flat is absent from the lookup above and has
        // to be found through their debt instead. Without this, the owner of
        // 601 and 103 is reachable as 103 and invisible as 601.
        if (!resident) {
          const { data: viaCharge } = await db.from("charges")
            .select("unit,residents!inner(id,full_name,building,unit)")
            .eq("unit", unit).eq("residents.building", building).limit(1);
          const hit: any = viaCharge?.[0]?.residents ?? null;
          if (hit) {
            resident = hit;
            askedUnit = unit;
          }
        }
      }
    }
    if (!resident) {
      const name = String(args?.name ?? "").trim();
      if (name.length >= 2) {
        const { data } = await db.from("residents").select(fields)
          .ilike("full_name", "%" + name + "%").limit(2);
        if (data && data.length > 1) return { ok: true, found: 0, ambiguous_name: true };
        resident = data?.[0] ?? null;
      }
    }
    if (!resident) return { ok: true, found: 0 };

    let q = db
      .from("charges")
      .select("period,amount,status,unit")
      .eq("resident_id", resident.id);
    if (askedUnit !== null) q = q.eq("unit", askedUnit);
    const { data: charges, error } = await q.order("period", { ascending: true });
    if (error) return { ok: false, error: error.message };

    const owed = (charges ?? []).filter((c) => c.status === "unpaid");

    // Months are summed across apartments rather than listed twice. An owner of
    // two flats owing April on both owes April once, for the sum — "April, and
    // also April" is not a sentence anybody should hear read back to them.
    const byMonth = new Map<string, number>();
    for (const c of owed) {
      const p = String(c.period).slice(0, 7);
      byMonth.set(p, (byMonth.get(p) ?? 0) + Number(c.amount));
    }

    // The per-apartment split, and only when there is one to make. A single
    // apartment is the overwhelming majority — 117 of 119 — and an extra array
    // on every answer is one more thing for the model to read out unasked.
    const units = [...new Set(owed.map((c) => String(c.unit)))];
    const byApartment = units.length > 1
      ? units.map((u) => ({
        unit: u,
        total: owed.filter((c) => String(c.unit) === u)
          .reduce((s, c) => s + Number(c.amount), 0),
        months: owed.filter((c) => String(c.unit) === u)
          .map((c) => String(c.period).slice(0, 7)),
      }))
      : undefined;

    return {
      ok: true,
      found: 1,
      resident: resident.full_name,
      building: resident.building,
      // The apartment asked about; or the only one that owes; or null when
      // several do, which is the signal to use owed_apartments rather than
      // naming a flat the caller did not mention.
      unit: askedUnit ?? (units.length === 1 ? units[0] : null),
      owed_total: owed.reduce((s, c) => s + Number(c.amount), 0),
      owed_months: [...byMonth].map(([period, amount]) => ({ period, amount })),
      owed_apartments: byApartment,
      // Disputed and pending rows are facts the agent should not hide behind
      // a clean zero — "in review with the team" is the truthful phrasing.
      in_review: (charges ?? [])
        .filter((c) => c.status === "disputed" || c.status === "pending_charge")
        .map((c) => ({ period: String(c.period).slice(0, 7), status: c.status })),
    };
  },

  /**
   * A maintenance issue raised during a debt call, and the whole job of the
   * inbound intake agent. Acceptance criterion 7 is zero silent drops, so this
   * writes a real requests row and hands back the real reference — the agent is
   * forbidden from inventing one.
   */
  async open_request(args, ctx) {
    if (!args?.description) return { ok: false, error: "description is required" };

    // Context first, arguments second — the same order n8n uses, and the
    // asymmetry documented in vapi_tools.py LOCATION. Outbound, the building is
    // a fact attached to the call and the model may not overwrite it. Inbound
    // there is no caller ID and no lookup, so the only source is what the caller
    // just said, and these arguments are it.
    //
    // This read `ctx.building ?? ""` until 8 Aug, which is correct outbound and
    // silently wrong inbound: every intake ticket would have carried an empty
    // building while the agent read a reference number back to the caller.
    // 19 Aug: `ctx.building` now only counts on a call we placed — see
    // `dialled`. The comment above was right about the intent and the code did
    // not enforce it: nothing checked that the context belonged to this caller.
    const said = (dialled(ctx) ? ctx.building : "") || args?.building || "";
    const type = args?.type ?? "other";

    // The address as WE write it, when what was said resolves to a building we
    // manage. Added 13 Aug alongside `verify_address`.
    //
    // On VOICE this normalises and never refuses: voice agents were never
    // taught to verify first, and rejecting an unresolvable building would
    // silently drop inbound voice tickets — a worse failure than the one it
    // fixes. An unresolved voice building files as said, for a person to read.
    //
    // On WHATSAPP this refuses, since 23 Aug. The chat bot was taught a
    // two-step dance — verify_address, then open_request, then answer — and
    // the field test showed the model simply does not chain: five live runs,
    // zero second calls, three invented references read to residents.
    // Sequencing that must always happen belongs in code, not in a model's
    // discipline, so the verification now lives HERE: one tool call, nothing
    // to chain. An address that does not resolve returns the same refusal
    // vocabulary `verify_address` speaks — the prompt already knows how to
    // relay every reason — and no ticket is filed, because a ticket against a
    // building we do not manage is staff time spent on something that does
    // not exist.
    //
    // The canonical form matters even when it changes nothing else, because
    // the duplicate guard below matches on `building` as a string. Two
    // reports of one lobby leak written `יואב 14` and `רחוב יואב 14 רמת גן`
    // are two buildings to that guard and one building to everybody else, so
    // the second report would mint a second ticket and dispatch a second van.
    const m = await matchBuilding(said);
    if (channel(ctx) === "whatsapp" && m.status !== "found") {
      if (m.status === "street_unknown" || m.status === "empty") {
        return {
          ok: true, opened: false, building_found: false,
          reason: m.status === "empty" ? "need_building" : "street_unknown",
        };
      }
      if (m.status === "need_number" || m.status === "number_off_street") {
        return {
          ok: true, opened: false, building_found: false,
          reason: m.status === "need_number" ? "need_number" : "number_not_on_street",
          street: m.street.street,
          numbers_we_manage: m.numbers,
        };
      }
      return {
        ok: true, opened: false, building_found: false, reason: "ambiguous",
        candidates: m.candidates.map((b: any) => b.address).slice(0, 5),
      };
    }
    const building = (m.status === "found" ? String(m.building.address) : "") || said;

    // ctx first, argument second — outbound the apartment is a fact attached to
    // the call and the model may not overwrite it.
    //
    // Since feature 14 there is a third case: a call covering SEVERAL
    // apartments, where the view deliberately sends `unit` empty because no
    // single value is true. Then the only source is what the resident just said,
    // and it is checked against the apartments actually on the call — a flat
    // that is not one of theirs is dropped to null, which files the ticket for a
    // person to read rather than dispatching a technician to a guess.
    // 19 Aug, same gate as the building above: an apartment attached to a call
    // we did not place is not this caller's apartment.
    let unit = dialled(ctx) ? unitOf(ctx.unit) : null;
    if (!unit) {
      const said = unitOf(args?.unit);
      const known = new Set(ctx.charges.map((c) => c.unit).filter(Boolean));
      unit = said && (known.size === 0 || known.has(said)) ? said : null;
    }

    // WHERE THE PERSON LIVES, which is not where the fault is (13 Aug).
    //
    // The chat bot now asks for a building and an apartment on every report,
    // including a lobby leak, because it is asking WHO IS THIS — there is no
    // caller ID on chat and until now nothing ever looked the sender up, so a
    // WhatsApp ticket carried no resident at all.
    //
    // That is not a reversal of the lift rule from 8 Aug. `unit` still means
    // where the fault is and stays null for common property, so every query
    // that finds common-area faults with `unit is null` keeps working and the
    // duplicate guard still groups two reports of one lobby leak. The
    // reporter's flat goes in its own column.
    //
    // `fault_location` is the one distinction the model has to make, and it
    // already had to make it — it used to express it by omitting `unit`, which
    // is the kind of implicit branch this file has been burned by before. Said
    // out loud it can at least be checked: anything that is not the string
    // "apartment" is treated as common property, because a fault wrongly filed
    // as common gets read by a person, and one wrongly pinned to a flat sends a
    // technician to knock on a stranger's door.
    const reportedUnit = unitOf(args?.reporter_unit);
    if (reportedUnit && String(args?.fault_location ?? "") !== "apartment") {
      unit = null;
    } else if (reportedUnit && !unit) {
      unit = reportedUnit;
    }

    // --- The duplicate guard ------------------------------------------------
    //
    // Same place, same kind of fault, still open, opened in the last 30 minutes
    // → hand back the reference that already exists instead of minting a second
    // one. The resident is told about their ticket either way and cannot tell
    // the difference; the difference is that a technician is not dispatched
    // twice to one leak.
    //
    // Three ways this happens and none of them are the resident being careless:
    // Meta retries a webhook that was slow to answer, a caller repeats
    // themselves when the line is bad, and a resident who has heard nothing for
    // an hour reports the same thing again. Only the first is a true duplicate
    // in the technical sense; all three should produce one ticket.
    //
    // It is deliberately NOT keyed on the description. Two people describing
    // one lobby leak will not phrase it the same way, and a substring match on
    // free text is exactly the kind of clever that fails silently at 3am.
    // Place plus type is coarse, and coarse is the safe direction: the failure
    // mode is a second genuine fault of the same kind in the same lobby inside
    // half an hour getting attached to the first, which a human reading the
    // ticket will catch. The opposite failure — two tickets, two vans — costs
    // real money and looks incompetent to the resident.
    //
    // 30 minutes, not 24 hours, because "the leak is back" the next morning is
    // a new fact and deserves its own row.
    // A COMPLAINT IS NEVER A DUPLICATE, and this guard would eat it.
    //
    // Everything above is reasoning about a FAULT: one leak, one van, and a
    // second report of it is the same physical thing. A complaint is not a
    // thing in a building, it is a person's account of one — so two complaints
    // from one building inside half an hour are two people, not one event, and
    // "place plus type" collides on every single one of them (they share a
    // type by definition and a common-area complaint has no unit either).
    //
    // Caught within the hour of complaints becoming a ticket type on 25 Aug:
    // a cleaning complaint and a noise complaint, same building, minutes
    // apart. The second was swallowed into the first and its author was read
    // back a reference to somebody else's complaint, with their own never
    // written down. There is no cost on the other side to weigh against that
    // — nobody is dispatched twice for a complaint.
    if (type !== "complaint") {
    const since = new Date(Date.now() - 30 * 60 * 1000).toISOString();
    let dupeQuery = db
      .from("requests")
      .select("id,reference,description")
      .eq("building", building)
      .eq("type", type)
      .gte("created_at", since)
      .in("status", ["open", "in_progress", "needs_review"])
      .order("created_at", { ascending: false })
      .limit(1);
    // .eq() never matches NULL in Postgres, so a common-area fault — which has
    // no unit — has to be asked for with .is(), or the guard silently never
    // fires on exactly the tickets most likely to be reported twice.
    dupeQuery = unit === null ? dupeQuery.is("unit", null) : dupeQuery.eq("unit", unit);

    const { data: existing } = await dupeQuery;
    if (existing && existing.length) {
      // A second report of one fault inside the window often carries NEW
      // FACTS. 27 Aug, live: "תקלה במעלית" came back twenty minutes later as
      // "נתקעת בין קומות, כבר חודשיים, ביקשתי כמה פעמים" — and the guard
      // handed back the old reference and dropped all of it, leaving the
      // ticket as thin as its first phrasing. Same convention as
      // add_request_detail: append with " | ", never replace, and skip when
      // the second report carries the same words (a retried webhook does).
      const dupeRow = existing[0];
      const fresh = String(args.description).trim();
      const held = String(dupeRow.description ?? "");
      if (fresh && !held.includes(fresh)) {
        await db.from("requests")
          .update({ description: held ? held + " | " + fresh : fresh })
          .eq("id", dupeRow.id);
      }
      return { ok: true, reference: dupeRow.reference, duplicate: true };
    }
    }

    // Who this is, when the call did not already say. Outbound we dialled them
    // and `ctx.residentId` is the answer; on chat nothing has ever looked the
    // sender up, and now the verified building+flat can. Best-effort on purpose:
    // a flat with no phone number on file has no `residents` row at all, which
    // is exactly why `reported_unit` is stored separately rather than being
    // reduced to this lookup.
    let residentId = ctx.residentId;
    if (!residentId && reportedUnit && building) {
      const { data: who } = await db.from("residents").select("id")
        .eq("building", building).eq("unit", reportedUnit).limit(1);
      residentId = who?.[0]?.id ?? null;
    }

    const { data, error } = await db
      .from("requests")
      .insert({
        resident_id: residentId,
        interaction_id: await interactionId(ctx),
        type,
        description: String(args.description),
        building,
        unit,
        reported_unit: reportedUnit,
        reported_by_phone: ctx.callerPhone,
        urgency: urgency(args?.urgency),
        opened_via: channel(ctx),
      })
      .select("id,reference")
      .single();

    if (error) return { ok: false, error: error.message };

    // Into OXS as well, when the building resolved — an unresolved voice
    // building has no OXS id to file against and stays ours-only, for a
    // person to read. Awaited so the Deno runtime cannot cancel it at
    // response time; failures inside are logged and swallowed.
    if (m.status === "found") {
      await oxsMirror(String(m.building.id), String(args.description), unit,
                      data.reference, data.id);
    }

    return { ok: true, reference: data.reference };
  },

  /**
   * Add to a ticket that already exists.
   *
   * WHY THIS EXISTS AT ALL, GIVEN open_request TAKES A DESCRIPTION
   *
   * The line closes after three minutes with no warning, so the intake prompt
   * has always said: write the row the moment you have a fault and a place, and
   * tidy up afterwards. A perfect conversation with no row is a failed call.
   *
   * That was fine while every ticket was a fault. It is not fine for the ones
   * asked for on 19 Aug — a lost parcel, a CCTV review, a neighbour — where the
   * office cannot act on the first sentence alone and needs what it was, where
   * it was left, and when it was noticed. Asking that BEFORE writing puts the
   * whole ticket behind a question, which is the one ordering that loses calls.
   * So the agent writes, then asks, then adds. Nothing is ever at risk.
   *
   * APPENDS, NEVER REPLACES. The caller's first sentence is the one thing on
   * the row that came out of their mouth unprompted, and an answer to a follow-up
   * does not supersede it. A tool that could overwrite a description would, on a
   * mishearing, quietly delete the only account of the fault anybody has.
   */
  async add_request_detail(args, ctx) {
    const serial = serialOf(args?.reference);
    const detail = String(args?.detail ?? "").trim();
    if (!serial) return { ok: false, error: "no reference" };
    if (!detail) return { ok: false, error: "nothing to add" };

    // Same serial-only match as get_request_status, and for the same reason: a
    // caller says "one thousand and fifty six", not "255-1056-26".
    const { data: rows } = await db
      .from("requests")
      .select("id,reference,description")
      .or(`reference.like.%-${serial}-%,reference.like.%-${serial}`)
      .order("created_at", { ascending: false })
      .limit(1);

    const row = rows?.[0];
    if (!row) return { ok: false, error: "not found" };

    // Already there — a repeated tool call on a retried webhook, or an agent
    // that asked the same question twice. Appending it again gives the office a
    // ticket that stutters.
    const existing = String(row.description ?? "");
    if (existing.includes(detail)) return { ok: true, reference: row.reference };

    const { error } = await db
      .from("requests")
      .update({ description: existing ? existing + " | " + detail : detail })
      .eq("id", row.id);

    return error ? { ok: false, error: error.message }
                 : { ok: true, reference: row.reference };
  },

  /**
   * The net under the inbound agent: a call that is already failing still leaves
   * a row. Never refuses — a validation error here turns a salvaged call into a
   * lost one, and an empty description is a real answer, because it says the
   * audio was unusable, which is exactly what the row is for.
   *
   * `needs_review` is the status migration 003 added for this, and the reason
   * type/description/building are nullable on that status alone. Captured slots
   * are trustworthy; empty ones were never captured and are never guessed.
   *
   * Was missing from this file until 8 Aug while the live intake assistant
   * carried the tool, so pointing that assistant here would have answered
   * `unknown tool save_partial_request` at the exact moment it was salvaging a
   * call.
   */
  async save_partial_request(args, ctx) {
    const reasons = ["audio", "time_limit", "caller_left"];
    const reason = reasons.includes(args?.reason) ? args.reason : "audio";
    const description = args?.description ? String(args.description) : null;

    const { data, error } = await db
      .from("requests")
      .insert({
        resident_id: ctx.residentId,
        interaction_id: await interactionId(ctx),
        description,
        // WHAT THE CALLER SAID WINS. This read the other way round until 19 Aug
        // — context first, the agent's capture second — and on a web call that
        // meant the demo page's variables. A caller who said "Herzo" and did not
        // know their apartment got a ticket reading Herzl 14, flat 12: an
        // address they never gave, on a row that looks exactly like one they
        // confirmed. Context is right on an OUTBOUND call, where we dialled a
        // known person; it is never right about someone ringing in.
        building: args?.building || (dialled(ctx) ? ctx.building : null) || null,
        unit: unitOf(args?.unit || (dialled(ctx) ? ctx.unit : null)),
        reported_by_phone: ctx.callerPhone,
        urgency: "normal",
        status: "needs_review",
        opened_via: channel(ctx),
        oxs_ref: `partial:${reason}`,
      })
      .select("reference")
      .single();

    // Still ok:true on a failure. The agent is seconds from losing the call and
    // there is nothing useful it can do with the error; the end-of-call report
    // writes its own partial from the transcript regardless.
    return error ? { ok: true } : { ok: true, reference: data.reference };
  },

  /**
   * RETIRED 11 AUG, and no longer offered to the agent. Kept so a stale
   * assistant gets an answer rather than `unknown tool`, and DEFANGED so a stale
   * assistant cannot do what this used to do.
   *
   * It used to set `residents.handed_over = false` and waive the charge, on an
   * unverified verbal claim, made to an automated caller, by somebody with an
   * obvious incentive. That made "this flat was never mine" the sentence that
   * ends any call about money, and it is not a sentence anybody has to prove.
   *
   * Two further reasons it had to go, both structural rather than a judgement
   * about residents. `handed_over` lives on the RESIDENT, so setting it for one
   * flat stopped calls about every other flat that owner holds — the same
   * category error migration 012 fixed for charges. And who holds an apartment
   * is exactly the kind of change CONTEXT.md says becomes staff work rather than
   * an API call; an agent recording it unilaterally is the OXS write-back
   * mistake one layer down.
   *
   * So it now does what the ownership branch does: pauses the apartment and
   * routes it to a person. `pending_charge` is excluded from the queue, so the
   * resident is not rung again next week about something the office is checking,
   * and nothing about the ownership record has moved on their say-so.
   */
  async flag_not_handed_over(args, ctx) {
    if (!ctx.residentId) return { ok: false, error: "no resident on this call" };
    const t = targets(ctx, args);
    if (!t.ok) return { ok: false, error: t.error };

    await db.from("call_outcomes").insert({
      charge_id: t.charges.length === 1 ? t.charges[0].charge_id : null,
      resident_id: ctx.residentId,
      interaction_id: await interactionId(ctx),
      outcome: "transferred",
      transfer_reason: "ownership",
    });
    await setStatus(t.charges, "pending_charge");

    return { ok: true, charges_written: t.charges.length, paused: true };
  },

  /**
   * The transfer itself is Vapi's, configured on the assistant. This records why,
   * so the reason survives even when no rep is free and the transfer fails.
   */
  /**
   * Write the request the WhatsApp model SAID it opened and did not.
   *
   * WHY THIS EXISTS
   * On 20 Aug the bot was given three messages: a leak in the lobby, "yes please
   * open a request", and a building and apartment. It called `verify_address`,
   * got back a real building and a real flat, and then answered:
   *
   *     פתחתי קריאה על הנזילה בלובי, מספר 255-1048-26 — זה עובר לצוות התחזוקה
   *
   * `open_request` was never called. The reference was invented, digit for
   * digit, in the shape this system uses. Nothing was written anywhere.
   *
   * The reply guard in n8n catches the claim — it looks for a reference-shaped
   * string with no `open_request` run behind it — and until now it replaced the
   * message with "I am passing this to the team". That stops the lie and leaves
   * the resident with nothing: no ticket, and a handover that reaches nobody.
   *
   * By that point everything a ticket needs already exists. The address was
   * verified a moment ago, and the fault is sitting in `messages`, which is
   * written for every inbound message before the model ever runs. So this
   * assembles the row from what is on record instead of from what the model
   * claimed, and gives the resident a reference that is real.
   *
   * WHY IT IS `needs_review` AND NOT `open`
   * A normal ticket carries a `type` and a `fault_location` the model chose. A
   * rescued one has neither — nobody classified it — so it is marked for a
   * person rather than dressed up as something an inference produced. Same
   * reasoning as `salvage()` below, and the same status.
   *
   * The description is the resident's own inbound messages, oldest first,
   * joined. Not a summary: nothing here is smart enough to summarise, and this
   * runs precisely when the smart thing has failed.
   */
  async rescue_request(args, ctx) {
    const phone = phoneOf(args?.phone) ?? phoneOf(ctx.callerPhone);
    const rawPhone = String(args?.phone ?? "").trim();
    if (!phone && !rawPhone) return { ok: false, error: "phone is required" };

    const iid = await interactionId(ctx);

    // Never mint a second one. The guard can fire on consecutive turns of the
    // same conversation — a model that invents a reference once will usually do
    // it again on the next message — and a resident describing one leak must
    // not collect a ticket per message.
    const since = new Date(Date.now() - 30 * 60 * 1000).toISOString();
    let dupe = db.from("requests").select("reference")
      .gte("created_at", since)
      .in("status", ["open", "in_progress", "needs_review"])
      .order("created_at", { ascending: false }).limit(1);
    dupe = iid ? dupe.eq("interaction_id", iid) : dupe.eq("reported_by_phone", phone);
    const { data: already } = await dupe;
    if (already && already.length) {
      return { ok: true, reference: already[0].reference, duplicate: true };
    }

    // What they actually said. `messages` is written by "Log inbound" before the
    // model runs, so it is on record even on the turn the model went wrong.
    // Both phone spellings are tried: n8n stores what WhatsApp sends (972…),
    // and everything else in this file works in E.164 (+972…).
    const spellings = [...new Set([phone, rawPhone].filter(Boolean))];
    const { data: msgs } = await db.from("messages")
      .select("body,created_at")
      .in("phone", spellings)
      .eq("direction", "inbound")
      .order("created_at", { ascending: false })
      .limit(12);

    const said = (msgs ?? [])
      .map((m: any) => String(m?.body ?? "").trim())
      .filter(Boolean)
      .reverse();
    if (!said.length && !args?.description) {
      return { ok: false, error: "nothing on record to write" };
    }
    const description = String(args?.description ?? said.join(" / ")).slice(0, 4000);

    // The building as WE write it. `args.building` is what verify_address just
    // returned and is already canonical; the fallback re-derives it from what
    // was said, which is what happens when the guard fires before any address
    // was verified.
    let building = (await canonicalAddress(args?.building)) || "";
    if (!building) {
      for (const line of said) {
        const m = await matchBuilding(line);
        if (m.status === "ok") { building = (m.building as any)?.address ?? ""; break; }
      }
    }

    const { data, error } = await db.from("requests").insert({
      resident_id: ctx.residentId,
      interaction_id: iid,
      // Null, deliberately: nothing classified this. A guessed category on a
      // rescued row is the same failure that produced it.
      type: null,
      description,
      building: building || null,
      unit: null,
      reported_unit: unitOf(args?.unit),
      reported_by_phone: phone,
      urgency: urgency(args?.urgency),
      status: "needs_review",
      opened_via: channel(ctx),
      oxs_ref: "partial:model_claimed",
    }).select("reference").single();

    return error
      ? { ok: false, error: error.message }
      : { ok: true, reference: data.reference, rescued: true };
  },

  async transfer_to_human(args, ctx) {
    // BOTH agents' vocabularies, because both write to this one column.
    // Kept in step with TRANSFER_REASONS and INTAKE_TRANSFER_REASONS in
    // scripts/vapi_tools.py, and with the CHECK widened in migration 021.
    //
    // Until 20 Aug this list held the debt agent's six and nothing else. The
    // intake agent has been sending `emergency`, `out_of_scope` and
    // `repeated_failure` since the day it shipped; every one of them failed the
    // `includes` test below and was written as `caller_request`. The fallback
    // was there to stop an unstorable value hitting the CHECK constraint and
    // throwing — so it turned a loud failure into a quiet lie, which is the
    // worse of the two. A caller reporting black smoke from a window is on
    // record as somebody who asked to speak to a person.
    //
    // The fallback stays, for a genuinely unknown word. It is no longer load
    // bearing for values this system sends itself.
    const reasons = [
      "hardship", "dispute", "distress", "language", "not_understood",
      "caller_request", "ownership",
      "out_of_scope", "emergency", "repeated_failure",
    ];
    const reason = reasons.includes(args?.reason) ? args.reason : "caller_request";

    // `ownership` is the one reason that changes anything besides the record:
    // the resident says an apartment is not theirs, or was never handed over.
    // The claim is not acted on — the ownership record is untouched — but the
    // apartment is PAUSED, because the alternative is ringing them again next
    // week about the thing the office has not finished checking.
    //
    // Scoped to the apartment they actually named. A two-flat owner contesting
    // one of them keeps getting called about the other, which is correct: they
    // did not dispute it.
    let paused = 0;
    if (reason === "ownership") {
      const t = targets(ctx, args);
      if (!t.ok) return { ok: false, error: t.error };
      await setStatus(t.charges, "pending_charge");
      paused = t.charges.length;
    }

    const iid = await interactionId(ctx);

    // --- The emergency backstop ---------------------------------------------
    //
    // A TRANSFER IS A NOTE. IT IS NOT A TICKET.
    // Nothing searches call_outcomes, no dashboard lists it, and no technician
    // is dispatched off it. An emergency that produced a transfer and no
    // request has therefore left no record anybody will ever find.
    //
    // On 20 Aug a caller reported what they believed was a fire. The agent
    // behaved sensibly by its own lights — recognised the emergency, said it
    // was bringing in a person, transferred — and never called `open_request`.
    // The `requests` table ended that day empty. The prompt's Emergency section
    // has been rewritten to say write first, then transfer; this is the half
    // that does not depend on the model doing as it is told, which is a lesson
    // this file has now paid for three times.
    //
    // ONLY for `emergency`, deliberately. `out_of_scope` and `caller_request`
    // are cases where minting a ticket is often exactly the wrong move — the
    // office wanted a note, not a work item. Emergency is the one reason where
    // a missing record costs more than a spurious one.
    //
    // Written as `needs_review`, not `open`: nothing here came from a completed
    // intake, so a person reads it before it is treated as a well-formed
    // request. `urgency` is `emergency` so it sorts to the top of whatever they
    // are looking at.
    let emergency_reference: string | null = null;
    if (reason === "emergency" && iid) {
      const prior = await db.from("requests").select("id")
        .eq("interaction_id", iid).limit(1);
      if (!prior.data?.length) {
        // Same asymmetry as open_request: a building attached to a call counts
        // only on a call we placed. Inbound, the argument is the only source.
        const said = (dialled(ctx) ? ctx.building : "") || args?.building || "";
        const building = (await canonicalAddress(said)) || String(said).trim() || null;
        const { data: em } = await db.from("requests").insert({
          resident_id: ctx.residentId,
          interaction_id: iid,
          type: null,
          description: String(args?.description ?? "").trim() ||
            "Emergency transfer with no request opened. The agent did not " +
            "record what was reported; the call recording is the only account.",
          building,
          unit: null,
          reported_by_phone: ctx.callerPhone,
          urgency: "emergency",
          status: "needs_review",
          opened_via: channel(ctx),
        }).select("reference").single();
        emergency_reference = em?.reference ?? null;
      }
    }

    await db.from("call_outcomes").insert({
      charge_id: ctx.charges.length === 1 ? ctx.charges[0].charge_id : null,
      resident_id: ctx.residentId,
      interaction_id: iid,
      outcome: "transferred",
      transfer_reason: reason,
      posture_reached: args?.posture_reached ?? null,
    });

    // Matches the scoreboard query in 08-instrumentation.
    await db
      .from("interactions")
      .update({ disposition: `transfer:${reason}` })
      .eq("external_call_id", ctx.callId);

    // `emergency_reference` is returned so the agent can read it back if it has
    // not already given one. It is never an error that it exists — the caller
    // is told about their report either way.
    return { ok: true, reason, charges_paused: paused, emergency_reference };
  },

  /**
   * Every call, always — including voicemail, wrong party and no answer.
   * posture_reached is the number worth watching: hot is a floor, so the rate of
   * hot calls is the honest measure of whether the agent is damaging
   * relationships. Nothing else in the system records it.
   */
  async log_call_outcome(args, ctx) {
    const outcomes = [
      "authorized", "promised", "disputed", "refused", "transferred", "voicemail",
      "wrong_party", "not_handed_over", "no_answer", "office_to_contact",
    ];
    if (!outcomes.includes(args?.outcome)) {
      return { ok: false, error: `outcome must be one of: ${outcomes.join(", ")}` };
    }

    // ONE ROW, however many apartments the call covered. An outcome is a fact
    // about the call — it was answered, it went to voicemail, the wrong person
    // picked up — and writing it per charge would put a two-flat owner twice in
    // the dashboard's no-answer list off a single unanswered call. charge_id is
    // kept when there is exactly one it could mean and left null otherwise,
    // rather than pointing at whichever charge happened to sort first.
    const { error } = await db.from("call_outcomes").insert({
      charge_id: ctx.charges.length === 1 ? ctx.charges[0].charge_id : null,
      resident_id: ctx.residentId,
      interaction_id: await interactionId(ctx),
      outcome: args.outcome,
      posture_reached: args?.posture_reached ?? null,
      transfer_reason: args?.transfer_reason ?? null,
    });
    if (error) return { ok: false, error: error.message };

    // The attempt counter gates the queue at four, and it is per charge — so
    // EVERY charge on the call is bumped, not just one. Missing the others would
    // leave them at the same count forever: the person view takes the max
    // attempt across the row, so one un-bumped charge is enough to keep the
    // resident in the queue after the fourth call.
    //
    // Properly this belongs to the campaign runner, which knows a call was
    // placed even when the agent never reached this tool; doing it here too is
    // the backstop, not the design.
    await Promise.all(
      ctx.charges.map((c) =>
        db.rpc("bump_charge_attempt", { p_charge_id: c.charge_id }).then(
          () => {},
          () => {}, // the view still works without it; never fail a call over a counter
        )
      ),
    );

    return { ok: true, charges_bumped: ctx.charges.length };
  },
};

// ---------------------------------------------------------------------------
// The end-of-call report
// ---------------------------------------------------------------------------
// Vapi POSTs this to the assistant's server URL once the call is over, carrying
// everything that only exists after the fact: the transcript, the recording, the
// reason it ended, the duration, the cost, and the per-stage latency.
//
// Nothing consumed it until 8 Aug, so `interactions` had zero rows while eleven
// test calls happened — every transcript, every latency number and every ended
// reason lived in the Vapi dashboard and nowhere the CRM, the scoreboard in
// 08-instrumentation or a native Hebrew reviewer could reach. The tools wrote
// stub interaction rows during the call and nothing ever filled them in.
//
// It also closes the hole `maxDurationSeconds` opens. Vapi hangs up on the
// second the cap expires, mid-word, and never tells the model it is coming — so
// the agent cannot be relied on to call save_partial_request first. A server
// that sees endedReason `max-duration-exceeded` writes the partial itself, from
// the transcript, with no cooperation from the model at all. That is the version
// that cannot be talked out of.

/** Vapi's endedReason -> what a human reading the CRM needs to know. */
function disposition(reason: string): string {
  if (!reason) return "unknown";
  if (reason.includes("assistant-said-end-call-phrase")) return "completed";
  if (reason.includes("customer-ended-call")) return "caller_hung_up";
  if (reason.includes("max-duration")) return "cut_off_time_limit";
  if (reason.includes("silence-timed-out")) return "silence";
  if (reason.includes("voicemail")) return "voicemail";
  if (reason.includes("error") || reason.includes("failed")) return `error:${reason}`;
  return reason;
}

async function endOfCall(message: any, ctx: CallContext) {
  const call = message?.call ?? {};
  const artifact = message?.artifact ?? {};
  const endedReason = String(message?.endedReason ?? call?.endedReason ?? "");

  const startedAt = message?.startedAt ?? call?.startedAt ?? null;
  const endedAt = message?.endedAt ?? call?.endedAt ?? new Date().toISOString();
  const duration =
    message?.durationSeconds != null
      ? Math.round(Number(message.durationSeconds))
      : startedAt
      ? Math.round((Date.parse(endedAt) - Date.parse(startedAt)) / 1000)
      : null;

  // Vapi has moved this between message.performanceMetrics and the artifact
  // across versions, and reports it under two names. Read every known place: a
  // null here is indistinguishable from a fast call, which is the one number
  // this whole report was wired up to stop guessing at.
  const perf =
    message?.performanceMetrics ??
    artifact?.performanceMetrics ??
    call?.performanceMetrics ??
    {};
  const latency =
    perf?.turnLatency?.average ??
    perf?.modelLatencyAverage ??
    perf?.averageTurnLatency ??
    null;

  // The transcript, then the structured turns as a fallback. A call that ends in
  // the first second has neither, and an empty string is a truer record than a
  // null that reads as "we did not ask".
  const transcript =
    artifact?.transcript ??
    message?.transcript ??
    (Array.isArray(artifact?.messages)
      ? artifact.messages
          .filter((m: any) => m?.role && m?.role !== "system" && m?.message)
          .map((m: any) => `${m.role}: ${m.message}`)
          .join("\n")
      : null);

  const toolCalls = Array.isArray(artifact?.messages)
    ? artifact.messages
        .flatMap((m: any) => m?.toolCalls ?? [])
        .map((t: any) => ({ name: t?.function?.name, arguments: t?.function?.arguments }))
        .filter((t: any) => t.name)
    : [];

  const row = {
    channel: "voice",
    // Web calls have no phone number at either end. `type` is `webCall`,
    // `outboundPhoneCall` or `inboundPhoneCall`, and it is the only reliable
    // signal — the demo runs entirely on web calls, so direction cannot be
    // inferred from a customer number that is never there.
    direction: String(call?.type ?? "").toLowerCase().includes("inbound") ? "inbound" : "outbound",
    resident_id: ctx.residentId,
    caller_phone: call?.customer?.number ?? null,
    transcript,
    summary: message?.summary ?? artifact?.summary ?? null,
    audio_url: message?.recordingUrl ?? artifact?.recordingUrl ?? artifact?.recording?.stereoUrl ?? null,
    duration_seconds: duration,
    latency_ms: latency != null ? Math.round(Number(latency)) : null,
    tool_calls: toolCalls,
    started_at: startedAt,
    ended_at: endedAt,
  };

  // The tools create a stub row during the call, so update-then-insert rather
  // than insert. `disposition` is only written here if a tool has not already
  // set a more specific one — transfer:hardship says more than caller_hung_up,
  // and the transfer is the fact worth keeping.
  const existing = await db
    .from("interactions")
    .select("id, disposition, resident_id")
    .eq("external_call_id", ctx.callId)
    .maybeSingle();

  if (existing.data?.id) {
    await db
      .from("interactions")
      .update({
        ...row,
        resident_id: ctx.residentId ?? existing.data.resident_id,
        disposition: existing.data.disposition ?? disposition(endedReason),
      })
      .eq("id", existing.data.id);
    return { id: existing.data.id, endedReason };
  }

  const { data } = await db
    .from("interactions")
    .insert({ ...row, external_call_id: ctx.callId, disposition: disposition(endedReason) })
    .select("id")
    .single();
  return { id: data?.id ?? null, endedReason };
}

/**
 * The call was cut off by the duration cap and no row was written. Salvage one.
 *
 * Only fires when the call produced nothing — a completed request or a partial
 * the agent saved itself both count, and this stays out of the way. The
 * transcript goes in verbatim under `needs_review` because the alternative is
 * summarising it here, and a guessed building on a maintenance ticket sends
 * somebody to the wrong address.
 */
async function salvage(interactionId: string | null, ctx: CallContext, transcriptFrom: any) {
  if (!interactionId) return false;

  const already = await db
    .from("requests")
    .select("id")
    .eq("interaction_id", interactionId)
    .limit(1);
  if (already.data?.length) return false;

  const text = transcriptFrom ?? null;
  const { error } = await db.from("requests").insert({
    resident_id: ctx.residentId,
    interaction_id: interactionId,
    description: text ? String(text).slice(0, 4000) : null,
    building: ctx.building || null,
    unit: unitOf(ctx.unit),
    urgency: "normal",
    status: "needs_review",
    opened_via: channel(ctx),
    oxs_ref: "partial:cut_off",
  });
  return !error;
}

// ---------------------------------------------------------------------------
// Vapi's tool protocol
// ---------------------------------------------------------------------------
// It POSTs { message: { toolCalls: [ { id, function: { name, arguments } } ] } }
// and expects { results: [ { toolCallId, result } ] } where result is a string.
// `arguments` arrives as an object on some versions and a JSON string on others.

Deno.serve(async (req) => {
  if (req.headers.get("x-homies-secret") !== SECRET || !SECRET) {
    return new Response(JSON.stringify({ error: "unauthorised" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  let body: any;
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "bad json" }), { status: 400 });
  }

  const message = body?.message ?? {};
  const ctx = context(message);
  const calls = message?.toolCalls ?? [];

  // Server messages arrive on the same URL as tool calls and are told apart by
  // `type`. Everything that is not a tool call gets 200 and is ignored by name:
  // Vapi retries a non-2xx, and a status-update retried forever is noise that
  // looks like an outage. Adding a serverMessage to the assistant is therefore
  // safe here — an unhandled one costs nothing.
  const type = String(message?.type ?? "");
  if (type && !calls.length) {
    if (type !== "end-of-call-report") {
      return new Response(JSON.stringify({ ok: true, ignored: type }), {
        headers: { "content-type": "application/json" },
      });
    }
    try {
      const { id, endedReason } = await endOfCall(message, ctx);
      let salvaged = false;
      if (endedReason.includes("max-duration") || endedReason.includes("silence-timed-out")) {
        const artifact = message?.artifact ?? {};
        salvaged = await salvage(id, ctx, artifact?.transcript ?? message?.transcript ?? null);
      }
      return new Response(JSON.stringify({ ok: true, interaction: id, salvaged }), {
        headers: { "content-type": "application/json" },
      });
    } catch (e) {
      // 200 on failure, on purpose. The call is already over, so a retry storm
      // buys nothing, and the report is the only copy — losing it to a 500 that
      // Vapi replays six times is worse than losing it once, visibly.
      return new Response(JSON.stringify({ ok: false, error: String(e) }), {
        headers: { "content-type": "application/json" },
      });
    }
  }

  const results = await Promise.all(
    calls.map(async (c: any) => {
      const name = c?.function?.name;
      let args = c?.function?.arguments ?? {};
      if (typeof args === "string") {
        try { args = JSON.parse(args); } catch { args = {}; }
      }

      const fn = tools[name];
      if (!fn) return { toolCallId: c.id, result: JSON.stringify({ ok: false, error: `unknown tool ${name}` }) };

      try {
        return { toolCallId: c.id, result: JSON.stringify(await fn(args, ctx)) };
      } catch (e) {
        // Never throw at Vapi. A 500 mid-call is dead air; a failed result at
        // least lets the agent say it will check and come back to them.
        return { toolCallId: c.id, result: JSON.stringify({ ok: false, error: String(e) }) };
      }
    }),
  );

  return new Response(JSON.stringify({ results }), {
    headers: { "content-type": "application/json" },
  });
});
