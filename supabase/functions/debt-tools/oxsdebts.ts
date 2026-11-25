// OXS's own debt, into our charges (feature 24, 25 Nov 2026).
//
// The owner, on the Dialer page's amounts: "i need it to be accurate". Until now `charges` was our
// estimate from payment records (oxs_arrears.py), and 57 of the page's 201 flats matched OXS. Since
// OXS API rev 1.10 OXS works each flat's debt out itself, with its payments screen's rules, so we
// copy that: GET /debts names every flat that owes, GET /apartments/:id/debts gives it month by
// month (what is left on each month) and its open special payments. Migration 044 holds the rows.
//
// Pure on purpose, like route.ts and dialer.ts: Node runs scripts/check_oxs_debts.test.ts against
// it, because there is no local Deno. index.ts does the reading and the writing.

export const OXS_BASE = "https://api.oxs.co.il/api/external/v1";

/**
 * At most one OXS call every 1.5 s from the sync, about 40 a minute. OXS allows 60 a minute per key,
 * and the payment link a tenant waits for on the phone uses the same key (OXS_KEY_DEBTS).
 */
export const OXS_GAP_MS = 1500;

/** How long one run may keep calling OXS. Supabase stops a worker at 150 s on the free plan. */
export const RUN_BUDGET_MS = 95_000;

/** OXS's list has never been this short; a shorter one is a broken answer, and closes nothing. */
export function looksWhole(owing: number, lastOwing: number | null | undefined): boolean {
  if (owing <= 0) return false;
  if (!lastOwing || lastOwing <= 0) return true;
  return owing >= lastOwing * 0.5;
}

/** '050-123 4567', '972501234567', '+972 50…' -> '+972501234567'; null when it is not a number. */
export function e164(raw: unknown): string | null {
  if (raw === null || raw === undefined) return null;
  let d = String(raw).replace(/\D/g, "");
  if (d.startsWith("00972")) d = d.slice(5);
  else if (d.startsWith("972")) d = d.slice(3);
  d = d.replace(/^0+/, "");
  return d.length >= 8 && d.length <= 9 ? "+972" + d : null;
}

/** An Israeli mobile: 05X. The payment link goes to WhatsApp, so a mobile is the number to call. */
export function isMobile(phone: string): boolean {
  return /^\+9725\d{8}$/.test(phone);
}

/** 'יעקב דיין - דירה 1' -> 'יעקב דיין', as the residents import cleans OXS's names. */
export function cleanName(name: unknown): string {
  return String(name ?? "").replace(/\s*-\s*דירה\s*\S+\s*$/, "").replace(/\s+/g, " ").trim();
}

export type Payer = { phone: string; name: string; role: "renter" | "owner" };

/**
 * Every phone OXS gives for a flat's current payers: renters (the people living there) before
 * owners, and every mobile before any other number. An owner OXS marks inactive is left out.
 */
export function payersOf(row: any): Payer[] {
  const all: Array<Payer & { order: number }> = [];
  const seen = new Set<string>();
  let order = 0;
  const add = (p: any, role: Payer["role"]) => {
    if (!p || p.isActive === false) return;
    const cd = p.contactDetails ?? {};
    const raw: unknown[] = [cd.mobilePhone, cd.phone];
    if (Array.isArray(cd.phones)) {
      for (const x of cd.phones) raw.push(typeof x === "object" && x ? (x.number ?? x.numberOnly) : x);
    }
    for (const r of raw) {
      const phone = e164(r);
      if (!phone || seen.has(phone)) continue;
      seen.add(phone);
      all.push({ phone, name: cleanName(p.firstName), role, order: order++ });
    }
  };
  for (const p of Array.isArray(row?.renters) ? row.renters : []) add(p, "renter");
  for (const p of Array.isArray(row?.owners) ? row.owners : []) add(p, "owner");
  const rank = (p: Payer) => (isMobile(p.phone) ? 0 : 2) + (p.role === "renter" ? 0 : 1);
  return all.sort((a, b) => rank(a) - rank(b) || a.order - b.order)
    .map(({ phone, name, role }) => ({ phone, name, role }));
}

/**
 * Who the flat's debt is called on: the payer whose phone already holds it (`stored`), else the one
 * that held it under the old estimate (`legacy`), so staff keep calling the number they know; else
 * the first of payersOf's order. Only a phone OXS still lists for the flat is kept.
 */
export function choosePayer(payers: Payer[], stored?: string | null, legacy?: string | null): Payer | null {
  for (const want of [stored, legacy]) {
    const hit = want ? payers.find((p) => p.phone === want) : undefined;
    if (hit) return hit;
  }
  return payers[0] ?? null;
}

const num = (v: unknown): number => {
  const n = typeof v === "number" ? v : typeof v === "string" && v.trim() !== "" ? Number(v) : NaN;
  return Number.isFinite(n) ? n : 0;
};
const round2 = (n: number) => Math.round(n * 100) / 100;

/** The totals GET /debts gives a flat, as one string: when it changes, the months are read again. */
export function fingerprint(row: any): string {
  const years = (Array.isArray(row?.regularPaymentsDebt) ? row.regularPaymentsDebt : [])
    .map((y: any) => [num(y?.year), round2(num(y?.debt))]);
  const specials = (Array.isArray(row?.specialPayments) ? row.specialPayments : [])
    .map((s: any) => [String(s?._id ?? ""), round2(num(s?.debt ?? s?.amount))])
    .sort((a: any[], b: any[]) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  return JSON.stringify([
    round2(num(row?.totalDebt)), round2(num(row?.regularPaymentsDebtTotal)),
    round2(num(row?.specialPaymentsDebt)), years, specials,
  ]);
}

/** The year and month in Israel, which is what "this month" means to OXS's payments screen. */
export function israelMonth(at: Date): { y: number; m: number } {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Jerusalem", year: "numeric", month: "2-digit",
  }).formatToParts(at);
  const get = (t: string) => Number(parts.find((p) => p.type === t)?.value ?? 0);
  return { y: get("year"), m: get("month") };
}

export type Item =
  | { kind: "monthly"; period: string; amount: number }
  | { kind: "special"; ref: string; label: string; amount: number };

/**
 * One flat's overdue debt from its month-by-month detail (GET /apartments/:id/debts?lean=true):
 * each month owed before this one, from every year (`regularPayments[].yearlyVector`, January first,
 * the amount left on that month), and each open special payment (`debt` when partly paid, else
 * `amount`). This month and later ("future") are not overdue, which is OXS's `totalDebt`. A null
 * detail is a flat that owes nothing. `oxs` is what the detail itself totals, where it says: the
 * lean answer carries no monthly total, so the sync checks the sum against GET /debts' `totalDebt`
 * (agrees(), below).
 */
export function itemsOf(detail: any, at: Date): {
  items: Item[]; monthly: number; special: number;
  oxs: { monthly: number | null; special: number | null } | null;
} {
  if (!detail || typeof detail !== "object") return { items: [], monthly: 0, special: 0, oxs: null };
  const { y, m } = israelMonth(at);
  const items: Item[] = [];
  let monthly = 0;
  let special = 0;
  for (const yr of Array.isArray(detail.regularPayments) ? detail.regularPayments : []) {
    const year = Math.trunc(num(yr?.year));
    const vec = Array.isArray(yr?.yearlyVector) ? yr.yearlyVector : [];
    if (!year) continue;
    for (let i = 0; i < 12 && i < vec.length; i++) {
      const v = vec[i];
      if (v === null || v === undefined || v === "future") continue;
      const amount = round2(num(v));
      if (!(amount > 0)) continue;
      const month = i + 1;
      if (year > y || (year === y && month >= m)) continue;
      items.push({ kind: "monthly", period: `${year}-${String(month).padStart(2, "0")}-01`, amount });
      monthly += amount;
    }
  }
  for (const s of Array.isArray(detail.specialPayments) ? detail.specialPayments : []) {
    const ref = String(s?._id ?? "").trim();
    const amount = round2(num(s?.debt ?? s?.amount));
    if (!ref || !(amount > 0)) continue;
    items.push({ kind: "special", ref, label: String(s?.description ?? "").replace(/\s+/g, " ").trim(), amount });
    special += amount;
  }
  const has = (k: string) => detail[k] !== undefined && detail[k] !== null;
  return {
    items,
    monthly: round2(monthly),
    special: round2(special),
    oxs: {
      monthly: has("regularPaymentsDebtTotal") ? round2(num(detail.regularPaymentsDebtTotal)) : null,
      special: has("specialPaymentsDebt") ? round2(num(detail.specialPaymentsDebt)) : null,
    },
  };
}

/** The months and special payments written add up to what OXS's list says is overdue (to the shekel). */
export function agrees(got: { monthly: number; special: number }, totalDebt: number): boolean {
  return Math.abs(got.monthly + got.special - totalDebt) <= 1;
}

export type Flat = {
  ref: string;
  building_ref: string;
  address: string;
  number: string;
  phones: string[];
  payers: Payer[];
  overdue: number;
  with_month: number;
  fp: string;
};

/** One GET /debts row as oxs_debt_seen takes it. `addressOf` is our buildings.address by OXS id. */
export function flatOf(row: any, addressOf: (buildingRef: string) => string | undefined): Flat | null {
  const ref = String(row?.apartmentId ?? row?.apartment?._id ?? "").trim();
  if (!ref) return null;
  const building_ref = String(row?.buildingId ?? "").trim();
  const payers = payersOf(row);
  return {
    ref,
    building_ref,
    address: addressOf(building_ref) ?? String(row?.address ?? "").replace(/\s+/g, " ").trim(),
    number: String(row?.apartment?.number ?? "").trim(),
    phones: payers.map((p) => p.phone),
    payers,
    overdue: round2(num(row?.totalDebt)),
    with_month: round2(num(row?.totalDebtWithCurrentMonth)),
    fp: fingerprint(row),
  };
}

/**
 * Each phone's own flat: the one it owes most on. Its building and number become the resident's,
 * where the payment link and the balance lookup look. `phoneOf` is the phone each flat is on.
 */
export function homeFlats(flats: Flat[], phoneOf: (f: Flat) => string | null): Map<string, string> {
  const best = new Map<string, Flat>();
  for (const f of flats) {
    const phone = phoneOf(f);
    if (!phone || !(f.overdue > 0)) continue;
    const have = best.get(phone);
    if (!have || f.overdue > have.overdue || (f.overdue === have.overdue && f.ref < have.ref)) best.set(phone, f);
  }
  return new Map([...best].map(([phone, f]) => [phone, f.ref]));
}
