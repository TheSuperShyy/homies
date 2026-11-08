// Feature 20: the dialer test page's rules.
//   node --test scripts/check_dialer.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  answererOf, answerText, e164, externalIdFor, inCallingHours, israelClock, leadsAdded, localForm,
} from "../dashboard/lib/dialer-rules.ts";
import { routeOf } from "../supabase/functions/debt-tools/route.ts";

test("localForm: an Israeli number however it is typed, in Omni's local form", () => {
  for (const typed of ["054-123-4567", "0541234567", "+972541234567", "972541234567",
                       "00972541234567", "+972 054 123 4567", " 054 1234567 "]) {
    assert.equal(localForm(typed), "0541234567", typed);
  }
  assert.equal(localForm("(03) 123-4567"), "031234567");
  assert.equal(localForm("077-6687949"), "0776687949");
});

test("localForm: anything else is refused", () => {
  for (const typed of ["+639171234567", "0917 123 4567", "12345", "", "0123456789",
                       "05412345678", "abc"]) {
    assert.equal(localForm(typed), null, typed);
  }
});

test("e164: the form residents.phone holds", () => {
  assert.equal(e164("0541234567"), "+972541234567");
  assert.equal(e164("031234567"), "+97231234567");
});

test("calling hours: Sunday to Thursday 09-20, Friday until 13, never Saturday (Israel time)", () => {
  const at = (iso: string) => inCallingHours(new Date(iso));
  // Winter, UTC+2 since 25 Oct 2026. 28 Oct is a Wednesday.
  assert.deepEqual(israelClock(new Date("2026-10-28T08:00:00Z")), { day: 3, hour: 10, minute: 0 });
  assert.equal(at("2026-10-28T06:59:00Z"), false); // 08:59
  assert.equal(at("2026-10-28T07:00:00Z"), true);  // 09:00
  assert.equal(at("2026-10-28T17:59:00Z"), true);  // 19:59
  assert.equal(at("2026-10-28T18:00:00Z"), false); // 20:00
  assert.equal(at("2026-10-30T10:59:00Z"), true);  // Friday 12:59
  assert.equal(at("2026-10-30T11:00:00Z"), false); // Friday 13:00
  assert.equal(at("2026-10-31T10:00:00Z"), false); // Saturday noon
  assert.equal(at("2026-11-01T07:00:00Z"), true);  // Sunday 09:00
  assert.equal(at("2026-10-28T22:30:00Z"), false); // 00:30 Thursday
  // Summer, UTC+3. 15 Jul 2026 is a Wednesday.
  assert.equal(at("2026-07-15T05:59:00Z"), false); // 08:59
  assert.equal(at("2026-07-15T06:00:00Z"), true);  // 09:00
});

test("answererOf: says what feature 18's router will do with the same rows", () => {
  const call = { customer: { name: "dialer-0541234567", sipUri: "sip:0541234567@44.238.177.138:5060" } };
  const row = { phone: "+972541234567", resident_id: "r-1", first_name: "עידו", amount: "2000", attempt: "2" };
  const cases: Array<[string, Array<Record<string, any>>]> = [
    ["one row, owes", [row]],
    ["no row", []],
    ["two rows", [row, { ...row, resident_id: "r-2" }]],
    ["owes nothing", [{ ...row, amount: "0" }]],
    ["amount not a number", [{ ...row, amount: "אלפיים" }]],
  ];
  const WHY: Record<string, string> = {
    "not on the debt call list": "notListed",
    "more than one row on this number": "twoRows",
    "nothing owed": "nothingOwed",
  };
  for (const [name, rows] of cases) {
    const router = routeOf(call, rows);
    const page = answererOf(rows);
    assert.equal(page.agent, router.agent === "debt" ? "debt" : "intake", name);
    if (router.agent === "intake" && page.agent === "intake") assert.equal(page.why, WHY[router.why], name);
  }
  assert.deepEqual(answererOf([row]),
                   { agent: "debt", residentId: "r-1", firstName: "עידו", amount: 2000, attempt: 2 });
});

test("externalIdFor: the resident id first, then the press, so a second press is a new lead", () => {
  const at = new Date("2026-10-28T08:05:09.123Z");
  const id = "00000000-0000-4000-8000-000000000001";
  assert.equal(externalIdFor(id, at), `${id}-20261028T080509`);
  assert.equal(externalIdFor(id, at).slice(0, 36), id);
  assert.equal(externalIdFor(null, at), "test-20261028T080509");
  assert.notEqual(externalIdFor(id, at), externalIdFor(id, new Date("2026-10-28T08:05:10Z")));
});

test("answerText: Tokomni's answer as one short line", () => {
  assert.equal(answerText('{"error_msg":"404 Route Not Found"}\n'), "404 Route Not Found");
  assert.equal(answerText('{"ok":true}'), '{"ok":true}');
  assert.equal(answerText("<html><head><title>Attention Required! | Cloudflare</title></head></html>"),
               "Attention Required! | Cloudflare");
  assert.equal(answerText("added"), "added");
  assert.equal(answerText("x".repeat(500)).length, 200);
  assert.equal(answerText(""), "");
});

// Omni, 8 Nov: the v1 lead API answers with how many went in and why any did not.
test("answerText: Omni's v1 answer says what went in and what did not", () => {
  assert.equal(answerText('{"inserted_count":1}'), "inserted 1");
  assert.equal(answerText('{"inserted_count":0,"blacklisted_items":["05XXXXXXXX"]}'), "inserted 0, blacklisted 1");
  assert.equal(answerText('{"inserted_count":0,"failed_items":[{"number":"05XXXXXXXX","reason":"campaign not found"}]}'),
               "inserted 0, failed: campaign not found");
  assert.equal(answerText('{"invalid":[{"error":"number must be digits"}]}'), "invalid: number must be digits");
  assert.equal(answerText('{"failed_items":[{"number":"05XXXXXXXX"}]}'), 'failed: {"number":"05XXXXXXXX"}');
});

test("leadsAdded: inserted_count when Tokomni gives it, else null", () => {
  assert.equal(leadsAdded('{"inserted_count":1}'), 1);
  assert.equal(leadsAdded('{"inserted_count":0,"blacklisted_items":["05XXXXXXXX"]}'), 0);
  assert.equal(leadsAdded('{"ok":true}'), null);
  assert.equal(leadsAdded("<html></html>"), null);
  assert.equal(leadsAdded(""), null);
});
