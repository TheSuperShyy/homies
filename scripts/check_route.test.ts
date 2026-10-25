// Feature 18: which agent answers a call on the 208 line.
//   node --test scripts/check_route.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import {
  debtVariables, FIXED_DEFAULTS, GENDER_FORMS, isDialerCall, routeOf,
} from "../supabase/functions/debt-tools/route.ts";

// The 21 Oct dialer call (01a15d92), with the number swapped for a test one.
const DIALER = { id: "c1", customer: {
  name: "dialer-0509902043", sipUri: "sip:0509902043@44.238.177.138:5060" } };
const PHONE = "+972509902043";
const ROW = {
  phone: PHONE, resident_id: "r-1", first_name: "עידו", gender: "m", card_last4: "",
  building: "בר כוכבא 23, תל אביב - יפו", unit: "1", amount: "2000",
  apartments_phrase: "דירה 1", breakdown_phrase: "", months_phrase: "שמונה חודשים",
  attempt: "1", charges: [{ charge_id: "ch-1", unit: "1", period: "2026-01", amount: 250 }],
};

test("isDialerCall: only Omni's dialer name counts", () => {
  assert.equal(isDialerCall(DIALER), true);
  assert.equal(isDialerCall({ customer: { name: "201", sipUri: "sip:972776687949@x" } }), false);
  assert.equal(isDialerCall({ customer: { sipUri: "sip:031234567@x" } }), false);
  assert.equal(isDialerCall({}), false);
  assert.equal(isDialerCall(undefined), false);
});

test("routeOf: a dialer call to one tenant on the list gets the debt agent", () => {
  const r = routeOf(DIALER, [ROW]);
  assert.equal(r.agent, "debt");
  assert.equal(r.agent === "debt" && r.phone, PHONE);
});

test("routeOf: every other call gets the incoming agent", () => {
  const why = (call: any, rows: unknown) => {
    const r = routeOf(call, rows);
    return r.agent === "intake" ? r.why : "debt";
  };
  // Pressed 9: the caller's own number, no dialer name.
  assert.equal(why({ customer: { sipUri: "sip:0509902043@x" } }, [ROW]), "not a dialer call");
  assert.equal(why(DIALER, []), "not on the debt call list");
  assert.equal(why(DIALER, null), "not on the debt call list");
  assert.equal(why(DIALER, [{ ...ROW, phone: "+972501111111" }]), "not on the debt call list");
  assert.equal(why(DIALER, [ROW, { ...ROW, resident_id: "r-2" }]), "more than one row on this number");
  assert.equal(why(DIALER, [{ ...ROW, amount: "0" }]), "nothing owed");
  assert.equal(why(DIALER, [{ ...ROW, amount: "" }]), "nothing owed");
  assert.equal(why({ customer: { name: "dialer-" } }, [ROW]), "no number on the call");
});

// --- The Call button's own composer, run beside ours -------------------------
const CALL_TS = readFileSync(new URL("../dashboard/lib/call.ts", import.meta.url), "utf8");

function literal(name: string, scope: Record<string, unknown> = {}): any {
  const m = new RegExp(`const ${name}(?:: [^=]+)? = (\\{\\n[\\s\\S]*?\\n\\});\\n`).exec(CALL_TS);
  assert.ok(m, `${name} not found in dashboard/lib/call.ts`);
  const keys = Object.keys(scope);
  return new Function(...keys, `return ${m[1]};`)(...keys.map((k) => scope[k]));
}

function dashboardComposer() {
  const m = /export function debtVariableValues[\s\S]*?\n\}\n/.exec(CALL_TS);
  assert.ok(m, "debtVariableValues not found in dashboard/lib/call.ts");
  const js = stripTypeScriptTypes(m[0].replace(/^export /, ""), { mode: "strip" });
  const FIXED = literal("FIXED", { process: { env: {} } });
  return new Function("GENDER_FORMS", "FIXED", `${js}\nreturn debtVariableValues;`)(
    literal("GENDER_FORMS"), FIXED);
}

test("the gender texts are the dashboard's, character for character", () => {
  assert.deepEqual(GENDER_FORMS, literal("GENDER_FORMS"));
});

test("the fixed lines are the dashboard's defaults", () => {
  assert.deepEqual(FIXED_DEFAULTS, literal("FIXED", { process: { env: {} } }));
});

test("a dialer call hands the debt agent what the Call button would", () => {
  const button = dashboardComposer();
  for (const row of [
    ROW,
    { ...ROW, gender: "f", first_name: "דנה", card_last4: "1234" },
    { ...ROW, gender: undefined, charges: undefined, attempt: undefined },
  ]) {
    assert.deepEqual(debtVariables(row, PHONE), button(row, PHONE));
  }
});
