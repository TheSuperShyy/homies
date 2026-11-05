// Who is reporting, and whether a ticket may open yet (feature 17, 22 Oct 2026).
//
// Pure on purpose: no Deno, no database, no network. index.ts imports it, and
// Node runs scripts/check_identity.test.ts against it, because there is no
// local Deno to test the function with.

/**
 * Homies' own lines. A call FROM one of these with an extension as the
 * caller's name is staff dialling from inside the office: on 21 Oct
 * extensions 200, 201 and 202 rang 208 and all three showed this number.
 * That is not the person a ticket should call back.
 */
export const HOMIES_LINES = new Set(["+972776687949"]);

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
export function phoneOf(value: unknown): string | null {
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

/** The user part of a SIP URI: "sip:031234567@1.2.3.4:5060" is "031234567". */
export function sipUserOf(uri: unknown): string {
  const m = /^sips?:([^@;>]+)@/i.exec(String(uri ?? "").trim());
  return m ? m[1] : "";
}

/**
 * The number a phone call came from, or null.
 *
 * Vapi fills `customer.number` only when the caller arrives in E.164. Omni
 * sends outside callers in local form (031234567, 0509902043, and
 * "dialer-<number>" as the name on a dialer call), which Vapi leaves out of
 * `customer.number`, so two outside calls on 21 Oct stored no number at all.
 * The SIP URI still carries it.
 *
 * A Homies line with an extension (2 to 4 digits) as the caller's name is
 * staff calling from inside the office, and returns null so the agent asks
 * whom to call back. A foreign number Vapi already formatted is kept as it
 * came; phoneOf() reads Israeli numbers only.
 */
export function callNumberOf(call: any): string | null {
  const customer = call?.customer ?? {};
  const raw = String(customer?.number ?? "").trim();
  const number = raw
    ? (phoneOf(raw) ?? (/^\+[1-9]\d{7,14}$/.test(raw) ? raw : null))
    : phoneOf(sipUserOf(customer?.sipUri));
  const extension = /^\d{2,4}$/.test(String(customer?.name ?? "").trim());
  if (number && extension && HOMIES_LINES.has(number)) return null;
  return number;
}

/** A name as the person said it, tidied, or null when nothing usable was said. */
export function reporterNameOf(value: unknown): string | null {
  const name = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!name || name.length > 80) return null;
  // Digits or punctuation alone are not a name.
  if (!/\p{L}/u.test(name)) return null;
  return name;
}

/** A yes from a tool argument. n8n's $fromAI and some models send "true". */
export function flagOf(value: unknown): boolean {
  return value === true || String(value ?? "").trim().toLowerCase() === "true";
}

/** NAME_REQUIRED_CHANNELS ("voice", "voice,whatsapp", "off") as a set. */
export function requiredChannels(raw: unknown): Set<string> {
  return new Set(String(raw ?? "").split(",")
    .map((s) => s.trim().toLowerCase()).filter(Boolean));
}

export type GateInput = {
  /** "voice" or "whatsapp", as channel(ctx) says. */
  channel: string;
  /** A call we placed: the debt agent already knows who it rang. */
  dialled: boolean;
  /** requiredChannels(NAME_REQUIRED_CHANNELS). */
  enforced: Set<string>;
  /** reporterNameOf(args.reporter_name), or the dialled resident's name. */
  name: string | null;
  nameDeclined: boolean;
  /** A number to call back: the call's, the WhatsApp sender's, or the one they gave. */
  phone: string | null;
  phoneDeclined: boolean;
};

/**
 * What a ticket still needs before it may open, or null when nothing.
 *
 * The name before the number, because Homies' spec lists them in that order
 * (22 Oct, section 1). The number is asked on a phone call only: on WhatsApp
 * the sender's number IS the number. Someone who refuses after being told
 * why gets the ticket anyway (the flag); a refusal never blocks service.
 */
export function ticketGate(g: GateInput): "need_name" | "need_phone" | null {
  if (g.dialled || !g.enforced.has(g.channel)) return null;
  if (!g.name && !g.nameDeclined) return "need_name";
  if (g.channel === "voice" && !g.phone && !g.phoneDeclined) return "need_phone";
  return null;
}

/**
 * Who reported it, as text on the OXS copy of a ticket. `reportedBy` stays
 * OXS's own tenant for the flat (the owner's rule of 24 Sep: a wrong name in a
 * client's system is not recoverable), so the person who actually reported it
 * goes where staff read it: the description.
 */
export function reporterLine(name: string | null, phone: string | null): string {
  const parts = [name, phone].filter(Boolean);
  return parts.length ? ` [דיווח: ${parts.join(", ")}]` : "";
}
