// Feature 17: the pure rules behind "no ticket without a name and a number".
//   node --test scripts/check_identity.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  callNumberOf, flagOf, phoneOf, reporterLine, reporterNameOf, requiredChannels,
  sipUserOf, ticketGate,
} from "../supabase/functions/debt-tools/identity.ts";

test("phoneOf keeps its old behaviour", () => {
  assert.equal(phoneOf("0501234567"), "+972501234567");
  assert.equal(phoneOf("+972-50-123-4567"), "+972501234567");
  assert.equal(phoneOf("031234567"), "+97231234567");
  assert.equal(phoneOf("12"), null);
  assert.equal(phoneOf(undefined), null);
});

test("sipUserOf reads the user part of a SIP URI", () => {
  assert.equal(sipUserOf("sip:031234567@44.238.177.138:5060"), "031234567");
  assert.equal(sipUserOf("sip:0509902043@x"), "0509902043");
  assert.equal(sipUserOf(""), "");
  assert.equal(sipUserOf(undefined), "");
});

test("callNumberOf: staff on an internal extension have no number", () => {
  // 21 Oct, extension 201 calling 208 from inside the office.
  assert.equal(callNumberOf({ customer: {
    number: "+972776687949", name: "201", sipUri: "sip:972776687949@44.238.177.138:5060" } }), null);
});

test("callNumberOf: an outside caller in local form is kept", () => {
  // 21 Oct 07:09, a landline through Omni: Vapi left customer.number empty.
  assert.equal(callNumberOf({ customer: {
    name: "031234567", sipUri: "sip:031234567@44.238.177.138:5060" } }), "+97231234567");
});

test("callNumberOf: a dialer call carries the number it rang", () => {
  assert.equal(callNumberOf({ customer: {
    name: "dialer-0509902043", sipUri: "sip:0509902043@44.238.177.138:5060" } }), "+972509902043");
});

test("callNumberOf: a foreign number Vapi already formatted is kept", () => {
  assert.equal(callNumberOf({ customer: { number: "+639171234567" } }), "+639171234567");
});

test("callNumberOf: the office line without an extension is a real caller", () => {
  assert.equal(callNumberOf({ customer: { number: "+972776687949", name: "Homies" } }), "+972776687949");
});

test("callNumberOf: a web call has no number", () => {
  assert.equal(callNumberOf({}), null);
  assert.equal(callNumberOf(undefined), null);
});

test("reporterNameOf tidies a name and refuses non-names", () => {
  assert.equal(reporterNameOf("  יוסי   כהן "), "יוסי כהן");
  assert.equal(reporterNameOf(""), null);
  assert.equal(reporterNameOf("123"), null);
  assert.equal(reporterNameOf("א".repeat(81)), null);
  assert.equal(reporterNameOf(undefined), null);
});

test("flagOf accepts true and 'true' only", () => {
  assert.equal(flagOf(true), true);
  assert.equal(flagOf("true"), true);
  assert.equal(flagOf("TRUE"), true);
  assert.equal(flagOf("false"), false);
  assert.equal(flagOf("yes"), false);
  assert.equal(flagOf(undefined), false);
});

test("requiredChannels parses the switch", () => {
  assert.deepEqual([...requiredChannels(" voice, WhatsApp ")], ["voice", "whatsapp"]);
  assert.equal(requiredChannels(undefined).size, 0);
  assert.equal(requiredChannels("off").has("voice"), false);
});

const on = requiredChannels("voice,whatsapp");
const base = { channel: "voice", dialled: false, enforced: on, name: null,
  nameDeclined: false, phone: "+972501234567", phoneDeclined: false };

test("ticketGate: switched off, nothing is refused", () => {
  assert.equal(ticketGate({ ...base, enforced: requiredChannels("") }), null);
});

test("ticketGate: a call we placed is never refused", () => {
  assert.equal(ticketGate({ ...base, dialled: true, phone: null }), null);
});

test("ticketGate: the name comes first", () => {
  assert.equal(ticketGate({ ...base, phone: null }), "need_name");
});

test("ticketGate: a declined name still needs a number on a call with none", () => {
  assert.equal(ticketGate({ ...base, nameDeclined: true, phone: null }), "need_phone");
});

test("ticketGate: a declined number lets the ticket open", () => {
  assert.equal(ticketGate({ ...base, name: "דנה", phone: null, phoneDeclined: true }), null);
});

test("ticketGate: WhatsApp never needs a number", () => {
  assert.equal(ticketGate({ ...base, channel: "whatsapp", name: "דנה", phone: null }), null);
  assert.equal(ticketGate({ ...base, channel: "whatsapp", phone: null }), "need_name");
});

test("reporterLine names who reported for the OXS copy", () => {
  assert.equal(reporterLine("יוסי כהן", "+972501234567"), " [דיווח: יוסי כהן, +972501234567]");
  assert.equal(reporterLine(null, "+972501234567"), " [דיווח: +972501234567]");
  assert.equal(reporterLine(null, null), "");
});
