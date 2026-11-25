// Feature 23: the dashboard dialer's tick rules, in debt-tools (supabase/functions/debt-tools/dialer.ts).
//   node --test scripts/check_dialer_queue.test.ts
//
// The tick keeps its own copies of the dialer test page's rules (calling hours, the external_id,
// reading Tokomni's answer), because the function cannot import the dashboard. These tests hold
// the two side by side, so neither can change alone.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as tick from "../supabase/functions/debt-tools/dialer.ts";
import * as page from "../dashboard/lib/dialer-rules.ts";

test("calling hours: the tick and the dialer test page agree, minute by minute over a week", () => {
  // Winter (UTC+2) from Sunday 1 Nov 2026, and a summer week (UTC+3) from Sunday 12 Jul 2026.
  for (const start of ["2026-11-01T00:00:00Z", "2026-07-12T00:00:00Z"]) {
    const t0 = Date.parse(start);
    for (let m = 0; m < 7 * 24 * 60; m += 7) {
      const at = new Date(t0 + m * 60_000);
      assert.equal(tick.inCallingHours(at), page.inCallingHours(at), at.toISOString());
    }
  }
});

test("calling hours: Sunday to Thursday 09-20, Friday until 13, never Saturday", () => {
  const at = (iso: string) => tick.inCallingHours(new Date(iso));
  assert.equal(at("2026-11-25T06:59:00Z"), false); // Wednesday 08:59
  assert.equal(at("2026-11-25T07:00:00Z"), true);  // 09:00
  assert.equal(at("2026-11-25T17:59:00Z"), true);  // 19:59
  assert.equal(at("2026-11-25T18:00:00Z"), false); // 20:00
  assert.equal(at("2026-11-27T10:59:00Z"), true);  // Friday 12:59
  assert.equal(at("2026-11-27T11:00:00Z"), false); // Friday 13:00
  assert.equal(at("2026-11-28T09:00:00Z"), false); // Saturday 11:00
});

test("localOf: residents.phone to Omni's local form, nothing else", () => {
  assert.equal(tick.localOf("+972541234567"), "0541234567");
  assert.equal(tick.localOf("+97231234567"), "031234567");
  for (const bad of ["0541234567", "+639171234567", "", "+9725412345678", "+972-54-1234567"]) {
    assert.equal(tick.localOf(bad), null, bad);
  }
  // The round trip with the test page's own helpers.
  assert.equal(page.e164(tick.localOf("+972541234567")!), "+972541234567");
});

test("externalIdFor, leadsAdded, answerText: the same as the dialer test page's", () => {
  const at = new Date("2026-11-25T09:30:05.123Z");
  for (const id of ["0b1f9a52-3c1e-4d2a-9a77-1f2e3d4c5b6a", null]) {
    assert.equal(tick.externalIdFor(id, at), page.externalIdFor(id, at));
  }
  assert.equal(tick.externalIdFor("r", at), "r-20261125T093005");
  const bodies = [
    '{"inserted_count":1}', '{"inserted_count":0,"blacklisted_items":[{"number":"0541234567"}]}',
    '{"failed_items":[{"reason":"campaign not found"}]}', '{"invalid":[{"error":"number"}]}',
    '{"error_msg":"404 Route Not Found"}', "<html><title>500 Internal Server Error</title></html>",
    "", "not json",
  ];
  for (const b of bodies) {
    assert.equal(tick.leadsAdded(b), page.leadsAdded(b), b);
    assert.equal(tick.answerText(b), page.answerText(b), b);
  }
});

test("sendResult: only a lead Tokomni took, or no answer at all, holds the line", () => {
  assert.equal(tick.sendResult(200, '{"inserted_count":1}'), "ringing");
  assert.equal(tick.sendResult(200, "{}"), "ringing"); // says nothing about the count: as the test page
  assert.equal(tick.sendResult(200, '{"inserted_count":0}'), "failed");
  for (const s of [207, 400, 401, 404, 500, 502]) assert.equal(tick.sendResult(s, "{}"), "failed", String(s));
  // No answer (a timeout): on 16 Nov such a lead rang anyway, so it is treated as sent.
  assert.equal(tick.sendResult(0, "TimeoutError"), "ringing");
});

test("lineOf: busy while a call on 208 has not ended, else quiet since the newest end", () => {
  const ended = (endedAt: string) => ({ status: "ended", createdAt: "2026-11-25T08:00:00Z", endedAt });
  assert.deepEqual(tick.lineOf([]), { busy: false, quietSince: new Date(0).toISOString() });
  assert.deepEqual(tick.lineOf(null), { busy: false, quietSince: new Date(0).toISOString() });
  assert.deepEqual(
    tick.lineOf([ended("2026-11-25T08:01:00.000Z"), ended("2026-11-25T08:05:30.000Z")]),
    { busy: false, quietSince: "2026-11-25T08:05:30.000Z" });
  for (const status of ["queued", "ringing", "in-progress", "forwarding"]) {
    assert.equal(tick.lineOf([ended("2026-11-25T08:01:00Z"), { status, createdAt: "2026-11-25T08:06:00Z" }]).busy,
                 true, status);
  }
});

// ---- the page's list (dashboard/lib/dialer-board.ts) ------------------------------------------
import * as list from "../dashboard/lib/dialer-board.ts";

const person = (phone: string, name: string, extra: Record<string, unknown> = {}) =>
  ({ full_name: name, building: "בר כוכבא 23, תל אביב - יפו", phone, do_not_call: false, ...extra });

test("groupOwing: one row per phone, its flats and months, largest first", () => {
  const charges = [
    { resident_id: "a", period: "2026-09-01", amount: "500", attempts: 1, unit: "4", residents: person("+972541111111", "דנה לוי") },
    { resident_id: "a", period: "2026-10-01", amount: 500, attempts: 2, unit: "4", residents: person("+972541111111", "דנה לוי") },
    { resident_id: "a", period: "2026-10-01", amount: 700, attempts: 0, unit: "9", residents: person("+972541111111", "דנה לוי") },
    { resident_id: "b", period: "2026-10-01", amount: 3000, attempts: 0, unit: "2", residents: person("+972542222222", "משה כהן") },
    { resident_id: "c", period: "2026-10-01", amount: 0, attempts: 0, unit: "1", residents: person("+972543333333", "אפס") },
  ];
  const rows = list.groupOwing(charges as any, []);
  assert.deepEqual(rows.map((r) => [r.phone, r.owed]), [["+972542222222", 3000], ["+972541111111", 1700]]);
  const dana = rows[1];
  assert.deepEqual(dana.units, ["4", "9"]);
  assert.deepEqual(dana.months, ["2026-09", "2026-10"]);
  assert.equal(dana.tries, 2);
  assert.equal(dana.callable, true);
  assert.equal(dana.name, "דנה לוי");
});

test("groupOwing: a couple on one phone is one row, under the one who owes more; do-not-call from either", () => {
  const charges = [
    { resident_id: "h", period: "2026-10-01", amount: 200, attempts: 0, unit: "5", residents: person("+972544444444", "יוסי") },
    { resident_id: "w", period: "2026-10-01", amount: 900, attempts: 0, unit: "5", residents: person("+972544444444", "רחל", { do_not_call: true }) },
  ];
  const [row] = list.groupOwing(charges as any, []);
  assert.equal(row.owed, 1100);
  assert.equal(row.name, "רחל");
  assert.equal(row.dnc, true);
  assert.equal(list.blockOf(row, undefined, "2026-11-25"), "dnc");
});

test("groupOwing: four tries on every open month means the row cannot be ticked", () => {
  const charges = [
    { resident_id: "x", period: "2026-09-01", amount: 100, attempts: 4, unit: "1", residents: person("+972545555555", "x") },
  ];
  const [row] = list.groupOwing(charges as any, []);
  assert.equal(row.callable, false);
  assert.equal(list.blockOf(row, undefined, "2026-11-25"), "tries");
});

test("groupOwing: the last call is the newest outcome of anyone on the number", () => {
  const charges = [
    { resident_id: "h", period: "2026-10-01", amount: 200, attempts: 1, unit: "5", residents: person("+972544444444", "יוסי") },
    { resident_id: "w", period: "2026-10-01", amount: 900, attempts: 1, unit: "5", residents: person("+972544444444", "רחל") },
  ];
  const outcomes = [
    { resident_id: "w", outcome: "promised", created_at: "2026-11-24T10:00:00Z" },
    { resident_id: "h", outcome: "no_answer", created_at: "2026-11-20T10:00:00Z" },
    { resident_id: "w", outcome: "no_answer", created_at: "2026-11-19T10:00:00Z" },
  ];
  const [row] = list.groupOwing(charges as any, outcomes);
  assert.equal(row.last?.outcome, "promised");
});

test("blockOf and todayByPhone: queued or already rang today cannot be ticked again", () => {
  const [row] = list.groupOwing([
    { resident_id: "a", period: "2026-10-01", amount: 100, attempts: 0, unit: "1", residents: person("+972541111111", "a") },
  ] as any, []);
  const day = list.israelDate(new Date("2026-11-25T08:00:00Z"));
  assert.equal(day, "2026-11-25");
  const call = (status: string, pressed_at: string, sent_at: string | null = pressed_at) => ({
    id: status + pressed_at, phone: row.phone, name: "a", status, why: null, pressed_by: "x@y", pressed_at,
    sent_at, answered_at: null, ended_at: null, outcome: null, interaction_id: null, attempt: 1, amount: 100,
  });
  const at = (calls: any[]) => list.blockOf(row, list.todayByPhone(calls, day).get(row.phone), day);
  assert.equal(at([]), null);
  assert.equal(at([call("waiting", "2026-11-25T07:30:00Z", null)]), "queued");
  assert.equal(at([call("ringing", "2026-11-25T07:30:00Z")]), "queued");
  assert.equal(at([call("no_answer", "2026-11-25T07:30:00Z")]), "today");
  assert.equal(at([call("done", "2026-11-25T07:30:00Z")]), "today");
  // Skipped, refused or cancelled today never rang: it may be pressed again.
  for (const s of ["skipped", "failed", "cancelled"]) assert.equal(at([call(s, "2026-11-25T07:30:00Z")]), null, s);
  // Yesterday in Israel (22:30 UTC on the 24th is 00:30 on the 25th, so this one is the 24th).
  assert.equal(at([call("no_answer", "2026-11-24T21:30:00Z")]), null);
  assert.equal(at([call("no_answer", "2026-11-24T22:30:00Z")]), "today");
});

test("skipSummary and parseSummary: the press's reasons survive the URL", () => {
  const s = list.skipSummary([{ why: "today" }, { why: "paid" }, { why: "today" }, {}]);
  assert.equal(s, "today:2,paid:1,other:1");
  assert.deepEqual(list.parseSummary(s), [["today", 2], ["paid", 1], ["other", 1]]);
  assert.deepEqual(list.parseSummary(""), []);
  assert.deepEqual(list.parseSummary("junk,a:0,b:x"), []);
});

test("matches: a name, a building or a flat, or the phone however its digits are typed", () => {
  const [row] = list.groupOwing([
    { resident_id: "a", period: "2026-10-01", amount: 100, attempts: 0, unit: "12", residents: person("+972541234567", "עידו קליקס") },
  ] as any, []);
  for (const q of ["", "עידו", "קליקס", "כוכבא", "12", "054-123", "0541234567", "972541234567", "4567"]) {
    assert.equal(list.matches(row, q), true, q);
  }
  for (const q of ["משה", "0549999", "רוטשילד"]) assert.equal(list.matches(row, q), false, q);
});
