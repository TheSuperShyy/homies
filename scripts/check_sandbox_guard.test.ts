// Feature 19: the sandbox's network guard (supabase/functions/debt-tools-sandbox/guard.ts).
//   node --test scripts/check_sandbox_guard.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { decide, fakeWrite, install } from "../supabase/functions/debt-tools-sandbox/guard.ts";

const SB = "https://nmxlhlmcnnggnnuxyelt.supabase.co";

test("Supabase reads pass", () => {
  assert.equal(decide("GET", SB + "/rest/v1/residents?phone=eq.%2B1", SB), "pass");
  assert.equal(decide("HEAD", SB + "/rest/v1/requests", SB), "pass");
  assert.equal(decide("GET", SB + "/storage/v1/object/ticket-media/a.jpg", SB), "pass");
});

test("Supabase writes and every RPC are faked", () => {
  for (const m of ["POST", "PATCH", "PUT", "DELETE"]) assert.equal(decide(m, SB + "/rest/v1/requests", SB), "fake");
  assert.equal(decide("POST", SB + "/rest/v1/rpc/bump_charge_attempt", SB), "fake");
  assert.equal(decide("GET", SB + "/rest/v1/rpc/anything", SB), "fake");
  assert.equal(decide("POST", SB + "/storage/v1/object/ticket-media/x.jpg", SB), "fake");
});

test("every other host, and other Supabase paths, are refused", () => {
  for (const u of [
    "https://api.oxs.co.il/api/external/v1/service-calls",
    "https://chat.srv1879140.hstgr.cloud/api/v1/accounts/2/contacts/search?q=1",
    "https://graph.facebook.com/v23.0/1207299225801644/messages",
    "https://openrouter.ai/api/v1/chat/completions",
    "https://api.vapi.ai/call",
    "https://n8n-zqvb.srv1879140.hstgr.cloud/webhook/homies-voice-note",
  ]) assert.equal(decide("GET", u, SB), "refuse");
  assert.equal(decide("POST", SB + "/functions/v1/debt-tools", SB), "refuse");
});

test("a ticket insert that asks for its row gets an SBX reference", () => {
  const out = fakeWrite("POST", SB + "/rest/v1/requests?select=id%2Creference",
    JSON.stringify({ description: "x" }), "application/vnd.pgrst.object+json", "return=representation");
  const row = JSON.parse(out.body!);
  assert.equal(out.status, 201);
  assert.match(row.reference, /^SBX-\d+$/);
  assert.equal(row.description, "x");
  assert.ok(row.id);
});

test("a minimal insert returns 201 and no body; an update 204", () => {
  assert.deepEqual(fakeWrite("POST", SB + "/rest/v1/payment_links", "{}", "application/json", "return=minimal"),
    { status: 201, body: null });
  assert.deepEqual(fakeWrite("PATCH", SB + "/rest/v1/requests?id=eq.1", "{}", "application/json", ""),
    { status: 204, body: null });
});

test("an array insert returns an array", () => {
  const out = fakeWrite("POST", SB + "/rest/v1/call_outcomes", JSON.stringify([{ a: 1 }, { a: 2 }]),
    "application/json", "return=representation");
  assert.equal(JSON.parse(out.body!).length, 2);
});

test("the installed fetch lets only reads through", async () => {
  const seen: string[] = [];
  const real = (async (r: Request) => {
    seen.push(r.method + " " + r.url);
    return new Response("[]", { status: 200 });
  }) as unknown as typeof fetch;
  const f = install(real, SB, () => {});
  await f(SB + "/rest/v1/residents?select=id");
  const w = await f(SB + "/rest/v1/requests", {
    method: "POST", body: "{}",
    headers: { prefer: "return=representation", accept: "application/vnd.pgrst.object+json" },
  });
  const o = await f("https://api.oxs.co.il/x");
  assert.deepEqual(seen, ["GET " + SB + "/rest/v1/residents?select=id"]);
  assert.equal(w.status, 201);
  assert.equal(o.status, 503);
});
