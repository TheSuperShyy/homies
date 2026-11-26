// The debt call's payment link: the rules that decide how long the caller waits.
//   node --test scripts/check_paylink.test.ts
//
// 26 Oct, the first real debt call: send_payment_link took about 12 s, Vapi gave
// up at 10, and the tenant heard an improvised line with a wrong office number.
// The time went on steps run one after another: a model's line that the template
// then threw away, and one fixed 2 s wait before looking for WhatsApp's id.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DELIVERY_WAITS_MS, EMAIL_BODY, EMAIL_ON_ITS_WAY, ON_ITS_WAY, WINDOW_MS, claimOnce, emailMessage, freeTextAllowed,
  pollUntil, stopwatch, windowOpen,
} from "../supabase/functions/debt-tools/paylink.ts";

// 26 Nov, the owner's call to Ido: the link went as free text into a window shut for 14 days,
// Meta refused it, and the template followed. Chatwoot's can_reply says shut before anything is sent.
test("freeTextAllowed: only Chatwoot's explicit false shuts the window", () => {
  assert.equal(freeTextAllowed({ id: 94, can_reply: false }), false);
  assert.equal(freeTextAllowed({ id: 94, can_reply: true }), true);
  assert.equal(freeTextAllowed({ id: 94 }), true);   // an older Chatwoot: the old way
  assert.equal(freeTextAllowed(null), true);         // a read that failed: the old way
});

// 17 Nov: the tenant no longer waits on the line for WhatsApp (the owner's test
// call waited about 8 s here). The tool answers once the link exists, so what it
// tells the agent, and that one call sends one link, are the rules to hold.
test("ON_ITS_WAY: the agent says the link is on its way, never that it arrived", () => {
  assert.match(ON_ITS_WAY, /on its way/);
  assert.match(ON_ITS_WAY, /do not say it has already arrived/);
});

test("claimOnce: one send per call while it is going, free again once released", () => {
  const sending = new Set<string>();
  assert.equal(claimOnce(sending, "interaction-1"), true);
  assert.equal(claimOnce(sending, "interaction-1"), false);
  assert.equal(claimOnce(sending, "interaction-2"), true);
  sending.delete("interaction-1");
  assert.equal(claimOnce(sending, "interaction-1"), true);
});

test("claimOnce: without an interaction id there is nothing to hold", () => {
  const sending = new Set<string>();
  assert.equal(claimOnce(sending, null), true);
  assert.equal(claimOnce(sending, null), true);
  assert.equal(sending.size, 0);
});

const HOUR = 3600 * 1000;

test("windowOpen: free text goes only inside 24 hours of the tenant's last message", () => {
  const now = Date.parse("2026-11-10T12:00:00Z");
  assert.equal(windowOpen(now - 1 * HOUR, now), true);
  assert.equal(windowOpen(now - 23.9 * HOUR, now), true);
  assert.equal(windowOpen(now - WINDOW_MS, now), true);
  assert.equal(windowOpen(now - 24.1 * HOUR, now), false);
  // 3 Nov to 10 Nov: Ido's last message, the ordinary case on a debt call.
  assert.equal(windowOpen(Date.parse("2026-11-03T13:44:45Z"), now), false);
});

test("windowOpen: a tenant who never wrote has no window", () => {
  const now = Date.parse("2026-11-10T12:00:00Z");
  assert.equal(windowOpen(0, now), false);
  assert.equal(windowOpen(NaN, now), false);
});

test("pollUntil stops at the first yes and waits no longer", async () => {
  const slept: number[] = [];
  let asked = 0;
  const yes = await pollUntil(async () => ++asked >= 2, [700, 900, 1200],
    async (ms) => { slept.push(ms); });
  assert.equal(yes, true);
  assert.equal(asked, 2);
  assert.deepEqual(slept, [700, 900]);
});

test("pollUntil says no only after every wait was used", async () => {
  const slept: number[] = [];
  let asked = 0;
  const yes = await pollUntil(async () => { asked++; return false; }, [700, 900, 1200],
    async (ms) => { slept.push(ms); });
  assert.equal(yes, false);
  assert.equal(asked, 3);
  assert.deepEqual(slept, [700, 900, 1200]);
});

test("pollUntil: a read that fails counts as not yet, and the next one still runs", async () => {
  let asked = 0;
  const yes = await pollUntil(async () => {
    asked++;
    if (asked === 1) throw new Error("timeout");
    return true;
  }, [10, 10], async () => {});
  assert.equal(yes, true);
  assert.equal(asked, 2);
});

test("the delivery waits: a first look inside a second, and never more than 4 s of waiting", () => {
  assert.ok(DELIVERY_WAITS_MS.length >= 2);
  assert.ok(DELIVERY_WAITS_MS[0] <= 1000, "the first look comes inside a second");
  const total = DELIVERY_WAITS_MS.reduce((a, b) => a + b, 0);
  assert.ok(total >= 2000, "at least the 2 s the old single look waited");
  assert.ok(total <= 4000, "a refusal must still leave the call time to answer");
});

test("stopwatch gives each step's time and the total, for one log line", () => {
  let t = 1000;
  const sw = stopwatch(() => t);
  t += 412; sw.lap("lookups");
  t += 1530; sw.lap("template");
  t += 88;
  assert.equal(sw.text(), "lookups 412, template 1530, total 2030");
  assert.equal(sw.total(), 2030);
});

// 26 Nov, the owner, after the call to Ido: the office email goes to WhatsApp when the tenant asks.
// The free text and the template are the same words, so the body is the template's, filled in.
test("emailMessage: the address fills the template's one blank, which neither opens nor closes the body", () => {
  const address = "Office@homies-management.co.il";
  const text = emailMessage(address);
  assert.equal((EMAIL_BODY.match(/\{\{\d+\}\}/g) ?? []).join(), "{{1}}");
  assert.ok(!EMAIL_BODY.trim().startsWith("{{") && !EMAIL_BODY.trim().endsWith("}}"), "Meta refuses a blank at either end");
  assert.ok(text.includes(" " + address + " "), "the address stands alone, so WhatsApp links it");
  assert.ok(!text.includes("{{"), "nothing left unfilled");
  assert.ok(text.length < 1024, "under Meta's body limit");
});

test("EMAIL_ON_ITS_WAY never tells the tenant it already arrived", () => {
  assert.match(EMAIL_ON_ITS_WAY, /on its way/);
  assert.match(EMAIL_ON_ITS_WAY, /do not say it has already arrived/);
});
