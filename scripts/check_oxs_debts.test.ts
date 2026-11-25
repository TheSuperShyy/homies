// Feature 24: OXS's own debt, into our charges.
//   node --test scripts/check_oxs_debts.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  agrees, choosePayer, cleanName, e164, fingerprint, flatOf, homeFlats, isMobile, israelMonth, itemsOf,
  looksWhole, payersOf,
} from "../supabase/functions/debt-tools/oxsdebts.ts";

// 25 Nov 2026, 12:00 in Israel: November is this month, so it is not overdue yet.
const NOV25 = new Date("2026-11-25T10:00:00Z");

test("a number in any form OXS writes it", () => {
  assert.equal(e164("050-123 4567"), "+972501234567");
  assert.equal(e164("972501234567"), "+972501234567");
  assert.equal(e164("+972 50-123-4567"), "+972501234567");
  assert.equal(e164("00972501234567"), "+972501234567");
  assert.equal(e164("03-6123456"), "+97236123456");
  assert.equal(e164("1234"), null);
  assert.equal(e164(""), null);
  assert.equal(e164(null), null);
  assert.equal(isMobile("+972501234567"), true);
  assert.equal(isMobile("+97236123456"), false);
});

test("a name without OXS's flat suffix", () => {
  assert.equal(cleanName("יעקב  דיין - דירה 1"), "יעקב דיין");
  assert.equal(cleanName(undefined), "");
});

test("payers: renters before owners, a mobile before any other number, inactive owners out", () => {
  const row = {
    owners: [
      { firstName: "בעלים", isActive: true, contactDetails: { mobilePhone: "0521111111", phone: "03-6000000" } },
      { firstName: "לשעבר", isActive: false, contactDetails: { mobilePhone: "0529999999" } },
    ],
    renters: [
      { firstName: "שוכרת", contactDetails: { phone: "04-8000000", phones: [{ number: "054-222 2222" }] } },
    ],
  };
  assert.deepEqual(payersOf(row), [
    { phone: "+972542222222", name: "שוכרת", role: "renter" },
    { phone: "+972521111111", name: "בעלים", role: "owner" },
    { phone: "+97248000000", name: "שוכרת", role: "renter" },
    { phone: "+97236000000", name: "בעלים", role: "owner" },
  ]);
  assert.deepEqual(payersOf({ owners: [], renters: [] }), []);
  assert.deepEqual(payersOf(null), []);
});

test("the same number for two payers is listed once", () => {
  const row = {
    owners: [{ firstName: "א", contactDetails: { mobilePhone: "0501234567" } }],
    renters: [{ firstName: "ב", contactDetails: { mobilePhone: "+972501234567" } }],
  };
  assert.equal(payersOf(row).length, 1);
  assert.equal(payersOf(row)[0].role, "renter");
});

test("the flat stays on the phone it is on, while OXS still lists that phone", () => {
  const payers = [
    { phone: "+972542222222", name: "שוכרת", role: "renter" as const },
    { phone: "+972521111111", name: "בעלים", role: "owner" as const },
  ];
  assert.equal(choosePayer(payers, "+972521111111", null)?.phone, "+972521111111");
  assert.equal(choosePayer(payers, null, "+972521111111")?.phone, "+972521111111");
  assert.equal(choosePayer(payers, "+972500000000", "+972521111111")?.phone, "+972521111111");
  assert.equal(choosePayer(payers, "+972500000000", null)?.phone, "+972542222222");
  assert.equal(choosePayer([], "+972521111111", null), null);
});

test("the fingerprint changes with the totals, not with the order OXS lists them in", () => {
  const a = { totalDebt: 900, regularPaymentsDebtTotal: 400, specialPaymentsDebt: 500,
    regularPaymentsDebt: [{ year: 2026, debt: 842 }],
    specialPayments: [{ _id: "s1", amount: 300, debt: null }, { _id: "s2", amount: 250, debt: 200 }] };
  const b = { ...a, specialPayments: [...a.specialPayments].reverse() };
  assert.equal(fingerprint(a), fingerprint(b));
  assert.notEqual(fingerprint(a), fingerprint({ ...a, totalDebt: 500 }));
  assert.notEqual(fingerprint(a), fingerprint({ ...a, specialPayments: [{ _id: "s1", amount: 300, debt: 100 }] }));
});

test("this month is Israel's: the first of December starts at 22:00 UTC", () => {
  assert.deepEqual(israelMonth(new Date("2026-11-30T21:59:00Z")), { y: 2026, m: 11 });
  assert.deepEqual(israelMonth(new Date("2026-11-30T22:00:00Z")), { y: 2026, m: 12 });
});

test("a flat's overdue months: every year, this month and later left out, what is left on each", () => {
  const detail = {
    regularPaymentsDebtTotal: 2370,
    specialPaymentsDebt: 1709,
    regularPayments: [
      { year: 2025, yearlyVector: [null, null, null, null, null, null, null, null, null, 400, 400, 400] },
      { year: 2026, yearlyVector: [400, 170, null, null, null, null, null, null, null, 600, 442, "future"] },
    ],
    specialPayments: [
      { _id: "s1", description: " קרן  חירום ", amount: 1273, debt: null },
      { _id: "s2", description: "שיפוץ לובי", amount: 900, debt: 436 },
      { _id: "s3", description: "שולם", amount: 500, debt: 0 },
    ],
  };
  const got = itemsOf(detail, NOV25);
  assert.deepEqual(got.items, [
    { kind: "monthly", period: "2025-10-01", amount: 400 },
    { kind: "monthly", period: "2025-11-01", amount: 400 },
    { kind: "monthly", period: "2025-12-01", amount: 400 },
    { kind: "monthly", period: "2026-01-01", amount: 400 },
    { kind: "monthly", period: "2026-02-01", amount: 170 },
    { kind: "monthly", period: "2026-10-01", amount: 600 },
    { kind: "special", ref: "s1", label: "קרן חירום", amount: 1273 },
    { kind: "special", ref: "s2", label: "שיפוץ לובי", amount: 436 },
  ]);
  assert.equal(got.monthly, 2370);
  assert.equal(got.special, 1709);
  assert.deepEqual(got.oxs, { monthly: 2370, special: 1709 });
  assert.equal(agrees(got, 4079), true);
  assert.equal(agrees(got, 4200), false);
});

test("the lean answer has no monthly total, and that is not read as a zero", () => {
  const got = itemsOf({ regularPayments: [{ year: 2026, yearlyVector: [300, null] }], specialPaymentsDebt: 0,
    specialPayments: [] }, NOV25);
  assert.deepEqual(got.oxs, { monthly: null, special: 0 });
  assert.equal(agrees(got, 300), true);
});

test("a flat OXS says owes nothing has no items", () => {
  assert.deepEqual(itemsOf(null, NOV25), { items: [], monthly: 0, special: 0, oxs: null });
  assert.deepEqual(itemsOf({ regularPayments: [], specialPayments: [] }, NOV25).items, []);
});

test("amounts arrive as numbers or as strings, and are kept to the agora", () => {
  const got = itemsOf({ regularPayments: [{ year: 2026, yearlyVector: ["105.7", 105.75, null] }] }, NOV25);
  assert.deepEqual(got.items.map((i) => i.amount), [105.7, 105.75]);
  assert.equal(got.monthly, 211.45);
});

test("on the first of December, November is overdue", () => {
  const detail = { regularPayments: [{ year: 2026, yearlyVector: [null, null, null, null, null, null, null, null, null, null, 442, 442] }] };
  assert.deepEqual(itemsOf(detail, NOV25).items, []);
  assert.deepEqual(itemsOf(detail, new Date("2026-12-01T08:00:00Z")).items,
    [{ kind: "monthly", period: "2026-11-01", amount: 442 }]);
});

test("a GET /debts row as the sync keeps it", () => {
  const row = {
    apartmentId: "a1", buildingId: "b1", address: "החיל  3, רמת גן", apartment: { _id: "a1", number: "4" },
    owners: [{ firstName: "דנה - דירה 4", isActive: true, contactDetails: { mobilePhone: "0501234567" } }],
    renters: [], totalDebt: 1200, totalDebtWithCurrentMonth: 1642, regularPaymentsDebtTotal: 1200,
    specialPaymentsDebt: 0, regularPaymentsDebt: [{ year: 2026, debt: 1642 }], specialPayments: [],
  };
  const f = flatOf(row, (id) => (id === "b1" ? "החיל 3, רמת גן" : undefined));
  assert.equal(f?.ref, "a1");
  assert.equal(f?.address, "החיל 3, רמת גן");
  assert.equal(f?.number, "4");
  assert.deepEqual(f?.phones, ["+972501234567"]);
  assert.equal(f?.payers[0].name, "דנה");
  assert.equal(f?.overdue, 1200);
  assert.equal(f?.with_month, 1642);
  assert.equal(flatOf(row, () => undefined)?.address, "החיל 3, רמת גן");
  assert.equal(flatOf({}, () => undefined), null);
});

test("each phone's own flat is the one it owes most on", () => {
  const mk = (ref: string, overdue: number) => ({ ref, building_ref: "", address: "", number: "", phones: [],
    payers: [], overdue, with_month: overdue, fp: "" });
  const flats = [mk("a", 300), mk("b", 900), mk("c", 500), mk("d", 0)];
  const phone: Record<string, string> = { a: "+972501", b: "+972501", c: "+972502", d: "+972502" };
  const home = homeFlats(flats, (f) => phone[f.ref]);
  assert.equal(home.get("+972501"), "b");
  assert.equal(home.get("+972502"), "c");
});

test("a list far shorter than the last one is not read as everyone having paid", () => {
  assert.equal(looksWhole(874, 870), true);
  assert.equal(looksWhole(500, 874), true);
  assert.equal(looksWhole(300, 874), false);
  assert.equal(looksWhole(0, 874), false);
  assert.equal(looksWhole(874, null), true);
});
