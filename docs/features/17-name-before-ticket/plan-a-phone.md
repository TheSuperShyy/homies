# Name and number before a ticket — Plan A: the backend and the phone line

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No ticket from the incoming phone agent opens without the reporter's name and a number to call back, outside callers' numbers are kept, and all of it is proven offline before anything goes live.

**Architecture:** The pure rules (which number a call came from, what a ticket still needs) live in a new module, `identity.ts`. The Edge Function imports it and Node tests run against it. The function refuses a ticket with `need_name` or `need_phone` only on channels listed in `NAME_REQUIRED_CHANNELS`, so the backend can ship before an agent learns to send a name. The voice agent's prompt and tool texts change in the repo. Claude-played calls, scored by a checker, prove the behaviour. Live changes wait for the owner.

**Tech Stack:** Supabase Edge Function (Deno; deployed through the Management API, no local Deno), Node 24 (`node --test`, TypeScript type stripping), Python 3.12 scripts, Vapi.

**Spec:** [feature.md](feature.md), [context.md](context.md).

## Global Constraints

- Nothing is deployed, synced or switched on before Task 7. Task 7 starts only on the owner's go: *"Nothing changes live until you've seen the test results"* (22 Oct).
- No OpenRouter spend. Played tests use Claude subagents, never `voice_qa.py play` or `say`.
- Keys are never printed. Scripts read `.env`.
- Hebrew added to a prompt describes what to do. It never quotes a line for the model to recite.
- Refusal order in `open_request`: a named building that does not resolve, then `need_name`, then `need_phone` (phone calls only), then `need_building`.
- `NAME_REQUIRED_CHANNELS` unset or `off` means the tool behaves as before, except that a name sent is stored.
- A call we placed (the debt agent, `dialled(ctx)`) is never refused for a name or number.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Stage only this plan's files.
- WhatsApp is Plan B. Nothing in this plan touches n8n.
- Deploy with `--oxs-mirror`. A plain `--apply` deletes the OXS write key and switches off the test number's ticket copy.
- `<scratchpad>` means the session's scratch directory, outside the repo. Played-call runs go there; only the final transcripts are copied into `docs/`.

## File structure

| File | Change | Responsibility |
|---|---|---|
| `supabase/functions/debt-tools/identity.ts` | create | Pure rules: phone parsing (moved), the call's number, the name, the gate, the OXS line |
| `scripts/check_identity.test.ts` | create | Node tests for `identity.ts` |
| `scripts/check_function_syntax.mjs` | create | Strips types and syntax-checks the function's files, since there is no local Deno |
| `supabase/functions/debt-tools/index.ts` | modify | Import the module; the caller's number; the gate in `open_request`; store the name; the OXS line; the name on the voice note |
| `scripts/supabase_functions.py` | modify | Upload `identity.ts` beside `index.ts`; push `NAME_REQUIRED_CHANNELS` |
| `scripts/vapi_tools.py` | modify | The inbound `open_request` fields and text; `notify_team.caller_name` |
| `docs/assistant/demo-inbound.md` | modify | Two sentences of the incoming agent's system prompt |
| `dashboard/app/(app)/tickets/page.tsx` | modify | The caller column shows the name above the number |
| `scripts/voice_qa.py` | modify | `bundle --candidate`: the working tree's prompt and tools |
| `scripts/voice_qa_name.json` | create | Ten caller cards with expectations |
| `scripts/check_name_flow.py` | create | Scores played transcripts against the acceptance rules |
| `scripts/check_name_flow_test.py` | create | Tests for the checker |

---

### Task 1: The rules module and its tests

**Files:**
- Create: `supabase/functions/debt-tools/identity.ts`
- Test: `scripts/check_identity.test.ts`

**Interfaces:**
- Produces:
  - `phoneOf(value: unknown): string | null` (moved from index.ts, unchanged)
  - `sipUserOf(uri: unknown): string`
  - `callNumberOf(call: any): string | null`
  - `reporterNameOf(value: unknown): string | null`
  - `flagOf(value: unknown): boolean`
  - `requiredChannels(raw: unknown): Set<string>`
  - `ticketGate(g: GateInput): "need_name" | "need_phone" | null`
  - `reporterLine(name: string | null, phone: string | null): string`
  - `HOMIES_LINES: Set<string>`

- [ ] **Step 1: Write the failing test**

Create `scripts/check_identity.test.ts`:

```ts
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
```

- [ ] **Step 2: Run the test to make sure it fails**

Run: `node --test scripts/check_identity.test.ts`
Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `identity.ts`.

- [ ] **Step 3: Write the module**

Create `supabase/functions/debt-tools/identity.ts`. `phoneOf` and `e164` are moved here from `index.ts` with their comment, unchanged (Task 2 deletes the old copy):

```ts
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
```

- [ ] **Step 4: Run the test to make sure it passes**

Run: `node --test scripts/check_identity.test.ts`
Expected: `ℹ pass 18`, `ℹ fail 0`.

- [ ] **Step 5: Commit**

```bash
git add supabase/functions/debt-tools/identity.ts scripts/check_identity.test.ts
git commit -m "Feature 17: identity.ts, the pure rules for the caller's number and the ticket gate, with Node tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Wire the rules into the function

**Files:**
- Create: `scripts/check_function_syntax.mjs`
- Modify: `supabase/functions/debt-tools/index.ts` (the import at line 46; `context()` at line 174; `phoneOf`/`e164` at lines 1126-1157; `dialled()` at line 1008; `oxsMirror()` at line 938; `open_request` at lines 2923-3225; `transfer_to_human`'s voice note at lines 3637-3650; `endOfCall()` at line 4010)

**Interfaces:**
- Consumes: everything Task 1 produces.
- Produces: `open_request` accepts `reporter_name`, `name_declined`, `reporter_phone`, `phone_declined` and may answer `{ok: true, opened: false, reason: "need_name" | "need_phone"}`. `notify_team` accepts `caller_name`. `requests.reported_by_name` is written. `oxsMirror(…, reporterName, callback)`.

- [ ] **Step 1: Write the syntax check and run it on today's file**

Create `scripts/check_function_syntax.mjs`:

```js
// There is no Deno on this machine, so a typo in the Edge Function would only
// show at deploy. This strips the TypeScript (Node's own parser, which throws
// on a syntax error) and asks Node to parse the result as a module.
//   node scripts/check_function_syntax.mjs
import { stripTypeScriptTypes } from "node:module";
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";

const dir = new URL("../supabase/functions/debt-tools/", import.meta.url);
const out = mkdtempSync(join(tmpdir(), "debt-tools-"));
let bad = 0;
for (const name of ["identity.ts", "index.ts"]) {
  try {
    const js = stripTypeScriptTypes(readFileSync(new URL(name, dir), "utf8"), { mode: "transform" });
    const path = join(out, name.replace(/\.ts$/, ".mjs"));
    writeFileSync(path, js);
    execFileSync(process.execPath, ["--check", path], { stdio: "pipe" });
    console.log("ok   ", name);
  } catch (e) {
    bad++;
    console.log("FAIL ", name, String(e.stderr ?? e.message).split("\n").slice(0, 6).join("\n"));
  }
}
process.exit(bad ? 1 : 0);
```

Run: `node scripts/check_function_syntax.mjs`
Expected: `ok    identity.ts` and `ok    index.ts`. If `index.ts` fails on today's code, read the message: `mode: "transform"` covers enums and namespaces. Fix the checker until today's file passes, so its later failures mean your edit.

- [ ] **Step 2: Import the module and delete the moved functions**

In `index.ts`, after line 46 (`import { createClient } from "https://esm.sh/@supabase/supabase-js@2";`) add:

```ts
// Who is calling and what a ticket still needs (feature 17, 22 Oct). Pure, so
// Node can test it: scripts/check_identity.test.ts.
import {
  callNumberOf, flagOf, phoneOf, reporterLine, reporterNameOf, requiredChannels, ticketGate,
} from "./identity.ts";
```

Delete the block that starts at the `/**` above ` * A phone number as it is stored, or nothing.` and ends with the closing `}` of `function e164(national: string)` (lines 1126-1157 today), and put in its place:

```ts
// phoneOf() and e164() moved to ./identity.ts on 22 Oct (feature 17), unchanged.
```

Run: `grep -nE "^function (phoneOf|e164)" supabase/functions/debt-tools/index.ts`
Expected: no output.

- [ ] **Step 3: Read the caller's number through `callNumberOf`**

In `context()`, replace:

```ts
    callerPhone: phoneOf(call?.customer?.number) ?? phoneOf(v.caller_phone) ?? phoneOf(v.phone),
```

with:

```ts
    // 22 Oct (feature 17): callNumberOf() also reads the SIP URI, where Omni
    // puts an outside caller in local form that Vapi leaves out of
    // customer.number, and returns nothing for a Homies internal extension.
    callerPhone: phoneOf(callNumberOf(call)) ?? phoneOf(v.caller_phone) ?? phoneOf(v.phone),
```

In `endOfCall()`, replace:

```ts
    caller_phone: call?.customer?.number ?? null,
```

with:

```ts
    caller_phone: callNumberOf(call),
```

- [ ] **Step 4: Add `residentName()` after `dialled()`**

After the closing `}` of `function dialled(ctx: CallContext): boolean`, add:

```ts

/** The name on the resident row of a call we placed (feature 17): the debt
 *  agent's ticket carries the person it rang, and nobody is asked. */
async function residentName(id: string | null): Promise<string | null> {
  if (!id) return null;
  const { data } = await db.from("residents").select("full_name").eq("id", id).maybeSingle();
  return reporterNameOf(data?.full_name);
}
```

- [ ] **Step 5: Give `oxsMirror` the reporter's name and number**

Replace the signature:

```ts
async function oxsMirror(
  buildingOxsId: string, description: string, unit: string | null,
  reference: string, rowId: string, reporter: string | null,
  reporterUnit: string | null, building: string | null,
) {
```

with:

```ts
async function oxsMirror(
  buildingOxsId: string, description: string, unit: string | null,
  reference: string, rowId: string, reporter: string | null,
  reporterUnit: string | null, building: string | null,
  reporterName: string | null = null, callback: string | null = null,
) {
```

and in its body replace:

```ts
          + ` [בוט, סימוכין ${reference}]`,
```

with:

```ts
          + ` [בוט, סימוכין ${reference}]`
          + reporterLine(reporterName, callback),
```

- [ ] **Step 6: The gate in `open_request`**

Replace this block (from `const m = await matchBuilding(said);` through the line that defines `building`, lines 2923-2959 today):

```ts
    const m = await matchBuilding(said);
    if (!dialled(ctx) && m.status !== "found") {
```

…down to and including…

```ts
    const building = (m.status === "found" ? String(m.building.address) : "") || said;
```

with the block below. The long `AN INVENTED BUILDING` comment is kept word for word. The changes are that a missing building is held while the name is checked, and the gate in the middle.

```ts
    const m = await matchBuilding(said);
    // FEATURE 17 (22 Oct): a building nobody has named yet waits behind the
    // name, so the reporter is asked who they are before where they are
    // (Homies' spec, section 1). A building that WAS named and is not ours is
    // still said first: nobody is asked for a name for a ticket that cannot
    // open.
    let noBuildingYet: Record<string, unknown> | null = null;
    if (!dialled(ctx) && m.status !== "found") {
      // AN INVENTED BUILDING IS A MISSING ONE (27 Sep). The chat model called
      // this with `building: "בניין מגורים"` -- "residential building", a
      // placeholder it made up to have something to pass -- and got
      // `street_unknown`, which tells it the resident named a street we do not
      // manage. Nobody named anything. With no digit anywhere and not a Latin
      // street (that one keeps its own hint), nothing that could be an address
      // was given, and the honest reason is that we still need one. A managed
      // street typed without its number never gets here: matchBuilding answers
      // it with need_number.
      const invented = m.status === "street_unknown" && !/\d/.test(String(said))
        && !latinStreet(said);
      if (m.status === "street_unknown" || m.status === "empty") {
        const need = m.status === "empty" || invented;
        const refusal = {
          ok: true, opened: false, building_found: false,
          reason: need ? "need_building" : "street_unknown",
          ...(m.status === "street_unknown" && latinStreet(said) ? { hint: LATIN_HINT } : {}),
          ...(need && channel(ctx) === "whatsapp" ? { note: ASK_WHERE } : {}),
        };
        if (!need) return refusal;
        noBuildingYet = refusal;
      } else if (m.status === "need_number" || m.status === "number_off_street") {
        return {
          ok: true, opened: false, building_found: false,
          reason: m.status === "need_number" ? "need_number" : "number_not_on_street",
          street: m.street.street,
          numbers_we_manage: m.numbers,
          ...(m.status === "need_number" && channel(ctx) === "whatsapp" ? { note: ASK_WHERE } : {}),
        };
      } else {
        return {
          ok: true, opened: false, building_found: false, reason: "ambiguous",
          candidates: m.candidates.map((b: any) => b.address).slice(0, 5),
        };
      }
    }

    // WHO IS REPORTING (feature 17, 22 Oct). No ticket without the name of the
    // person reporting and a number to call them back (the owner: "before we
    // can open a ticket we should include the name"). The prompt asks; this
    // makes it true, because a rule a model must remember is a rule it drops
    // (23 Aug: five runs, zero chained calls). Switched per channel by
    // NAME_REQUIRED_CHANNELS, so an agent whose tool cannot send a name yet is
    // never refused forever. A call we placed already knows who it rang.
    const reporterName = reporterNameOf(args?.reporter_name)
      ?? (dialled(ctx) ? await residentName(ctx.residentId) : null);
    const givenPhone = phoneOf(args?.reporter_phone);
    const missing = ticketGate({
      channel: channel(ctx),
      dialled: dialled(ctx),
      enforced: requiredChannels(Deno.env.get("NAME_REQUIRED_CHANNELS")),
      name: reporterName,
      nameDeclined: flagOf(args?.name_declined),
      phone: reporterPhone(ctx) ?? givenPhone,
      phoneDeclined: flagOf(args?.phone_declined),
    });
    if (missing) return { ok: true, opened: false, reason: missing };
    if (noBuildingYet) return noBuildingYet;

    const building = (m.status === "found" ? String(m.building.address) : "") || said;
```

- [ ] **Step 7: Store the name and the given number**

In the emergency-stub update (the `.update({` inside `if (stub) {`), replace:

```ts
          reported_unit: reporterFlat,
          // Stays `emergency` however this call rates it. The urgency was set
```

with:

```ts
          reported_unit: reporterFlat,
          reported_by_name: reporterName,
          ...(givenPhone && !reporterPhone(ctx) ? { reported_by_phone: givenPhone } : {}),
          // Stays `emergency` however this call rates it. The urgency was set
```

In the same branch, replace:

```ts
        await oxsMirror(String(m.building.id), merged, unit, stub.reference, stub.id,
                        reporterPhone(ctx), reporterFlat, building);
```

with:

```ts
        await oxsMirror(String(m.building.id), merged, unit, stub.reference, stub.id,
                        reporterPhone(ctx), reporterFlat, building,
                        reporterName, reporterPhone(ctx) ?? givenPhone);
```

In the insert, replace:

```ts
        reported_by_phone: reporterPhone(ctx),
        urgency: urgency(args?.urgency),
```

with:

```ts
        reported_by_phone: reporterPhone(ctx) ?? givenPhone,
        reported_by_name: reporterName,
        urgency: urgency(args?.urgency),
```

and replace:

```ts
      await oxsMirror(String(m.building.id), String(args.description), unit,
                      data.reference, data.id, reporterPhone(ctx),
                      reporterFlat, building);
```

with:

```ts
      await oxsMirror(String(m.building.id), String(args.description), unit,
                      data.reference, data.id, reporterPhone(ctx),
                      reporterFlat, building,
                      reporterName, reporterPhone(ctx) ?? givenPhone);
```

- [ ] **Step 8: The caller's name on the voice team note**

In `transfer_to_human`, replace:

```ts
    if (isIntake(ctx)) {
      try {
        team_notified = await voiceNote({
```

with:

```ts
    if (isIntake(ctx)) {
      // Feature 17: the note opens with who called, when they said it.
      const who = reporterNameOf(args?.caller_name);
      try {
        team_notified = await voiceNote({
```

and in the same call replace:

```ts
          description: String(args?.description ?? "").trim().slice(0, 500),
          source: "tool",
```

with:

```ts
          description: ((who ? who + ": " : "") + String(args?.description ?? "").trim()).slice(0, 500),
          source: "tool",
```

- [ ] **Step 9: Check the files parse, and the rules still pass**

Run: `node scripts/check_function_syntax.mjs && node --test scripts/check_identity.test.ts`
Expected: `ok    identity.ts`, `ok    index.ts`, then `ℹ fail 0`.

Run: `grep -c "reported_by_name: reporterName" supabase/functions/debt-tools/index.ts`
Expected: `2`.

- [ ] **Step 10: Commit**

```bash
git add supabase/functions/debt-tools/index.ts scripts/check_function_syntax.mjs
git commit -m "Feature 17: open_request refuses without a name (and on calls, a number) behind NAME_REQUIRED_CHANNELS; the caller's number read from the SIP URI

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Deploy two files, and push the switch

**Files:**
- Modify: `scripts/supabase_functions.py` (line 55 `SRC`, line 136 `src = open(SRC…)`, the `to_push` list after `if or_key:`, the multipart list at line 232)
- Create: `scripts/check_name_gate.py` (the live probe Task 7 runs)

**Interfaces:**
- Consumes: `identity.ts` beside `index.ts`; `check_tools.post`, `check_tools.cleanup`, `check_tools.RUN`; `vapi_sync.load_env`, `vapi_sync.tool_server`.
- Produces: `--apply` uploads both files; `NAME_REQUIRED_CHANNELS` from `.env` is pushed when set; `python scripts/check_name_gate.py` exits 0 when the deployed function refuses a phone-call ticket without a name.

- [ ] **Step 1: Read both files**

After line 55 (`SRC = os.path.join(ROOT, "supabase", "functions", SLUG, "index.ts")`) add:

```python
# Feature 17 (22 Oct): the pure rules live beside index.ts, which imports them.
IDENTITY = os.path.join(ROOT, "supabase", "functions", SLUG, "identity.ts")
```

After line 136 (`    src = open(SRC, encoding="utf-8").read()`) add:

```python
    identity_src = open(IDENTITY, encoding="utf-8").read()
    print("files          index.ts %d chars, identity.ts %d chars" % (len(src), len(identity_src)))
```

- [ ] **Step 2: Push the switch when `.env` has it**

After the block:

```python
    if or_key:
        to_push.append({"name": "OPENROUTER_API_KEY", "value": or_key})
```

add:

```python
    # Feature 17 (22 Oct): which channels refuse a ticket without a name.
    # Unset here leaves the project's value as it is; "off" switches it off.
    name_channels = e.get("NAME_REQUIRED_CHANNELS", "").strip()
    if name_channels:
        to_push.append({"name": "NAME_REQUIRED_CHANNELS", "value": name_channels})
    print("name required  %s" % (name_channels or "unchanged (not in .env)"))
```

- [ ] **Step 3: Upload both files**

Replace:

```python
        ("file", "index.ts", src.encode("utf-8"), "application/typescript"),
```

with:

```python
        ("file", "index.ts", src.encode("utf-8"), "application/typescript"),
        ("file", "identity.ts", identity_src.encode("utf-8"), "application/typescript"),
```

- [ ] **Step 4: Dry run**

Run: `python scripts/supabase_functions.py`
Expected: a `files` line with both sizes, `name required  unchanged (not in .env)`, and `Dry run. Re-run with --apply.` Nothing is deployed.

- [ ] **Step 5: The live probe, for Task 7**

Create `scripts/check_name_gate.py`. It cannot pass until Task 7 Step 5, so it is only written here:

```python
# -*- coding: utf-8 -*-
"""Feature 17, live: the deployed function refuses a phone-call ticket without a name.

    N8N_BASE_URL= python scripts/check_name_gate.py

One open_request, as an incoming call with no name, on בר כוכבא 23 (the test
building). The refusal opens no ticket; any row the call id left is deleted the
way check_tools.py deletes its own probes.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_tools as T  # noqa: E402
from vapi_sync import load_env, tool_server  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    load_env()
    server = tool_server()
    if not server:
        sys.exit("No tool host configured in .env")
    url, secret, mode, label = server
    headers = {}
    if mode == "query":
        url = url + ("&" if "?" in url else "?") + "key=" + secret
    else:
        headers["x-homies-secret"] = secret
    body = {"message": {
        "call": {"id": "probe-%s-1" % T.RUN},
        "toolCalls": [{"id": "tc1", "function": {"name": "open_request", "arguments": {
            "description": "בדיקת מערכת, לא תקלה אמיתית",
            "building": "בר כוכבא 23", "type": "other"}}}],
    }}
    out = T.post(url, headers, body)
    try:
        result = json.loads((out.get("results") or [{}])[0].get("result") or "{}")
    except Exception:
        result = {"raw": out}
    T.cleanup(T.RUN)
    ok = result.get("opened") is False and result.get("reason") == "need_name"
    print("host: %s" % label)
    print("%s open_request with no name -> %s"
          % ("ok  " if ok else "FAIL", json.dumps(result, ensure_ascii=False)[:200]))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

Run: `python -X utf8 -c "import ast; ast.parse(open('scripts/check_name_gate.py',encoding='utf-8').read()); print('parses')"`
Expected: `parses`.

- [ ] **Step 6: Commit**

```bash
git add scripts/supabase_functions.py scripts/check_name_gate.py
git commit -m "Feature 17: the deploy uploads identity.ts and pushes NAME_REQUIRED_CHANNELS; a live probe for the name refusal

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: The incoming agent's tools and prompt

**Files:**
- Modify: `scripts/vapi_tools.py` (`_open_request`, the `location == "full"` branch and `lead`; `notify_team` in `INTAKE_TOOLS`)
- Modify: `docs/assistant/demo-inbound.md` (two sentences inside the `## System prompt` fence)

**Interfaces:**
- Consumes: the reasons and fields Task 2 defined.
- Produces: `vapi_tools.INTAKE_TOOLS`, whose `open_request` has `reporter_name`, `name_declined`, `reporter_phone` and `phone_declined`, and whose `notify_team` has `caller_name`.

- [ ] **Step 1: Write the failing check**

Run:

```bash
python -X utf8 -c "import sys; sys.path.insert(0,'scripts'); import vapi_tools as T; o=[t for t in T.INTAKE_TOOLS if t['function']['name']=='open_request'][0]['function']; n=[t for t in T.INTAKE_TOOLS if t['function']['name']=='notify_team'][0]['function']; p=o['parameters']['properties']; assert {'reporter_name','name_declined','reporter_phone','phone_declined'} <= set(p), sorted(p); assert 'caller_name' in n['parameters']['properties']; assert 'need_name' in o['description'] and 'need_phone' in o['description']; d=[t for t in T.DEBT_TOOLS if t['function']['name']=='open_request'][0]['function']['parameters']['properties']; assert 'reporter_name' not in d; print('ok')"
```

Expected: `AssertionError` listing today's fields.

- [ ] **Step 2: Add the fields (inbound only)**

In `_open_request`, inside `if location == "full":`, after the `props["type"] = {…}` assignment, add:

```python
        # 22 Oct, feature 17: no ticket without who reported it. The webhook
        # refuses with need_name / need_phone (NAME_REQUIRED_CHANNELS), so
        # none of these is `required` here: a required field the model cannot
        # fill yet is a field it invents.
        props["reporter_name"] = {
            "type": "string",
            "description": "The name of the person reporting, as they said it on "
                           "this call. Leave out rather than guess.",
        }
        props["name_declined"] = {
            "type": "boolean",
            "description": "true only when they were asked for their name, heard once "
                           "that it is so the team knows who to contact, and still "
                           "would not give it.",
        }
        props["reporter_phone"] = {
            "type": "string",
            "description": "Only after this tool answered need_phone: the number they "
                           "gave to reach them, in digits.",
        }
        props["phone_declined"] = {
            "type": "boolean",
            "description": "true only when they would not give a number after need_phone.",
        }
```

- [ ] **Step 3: Say what the new refusals mean**

In the same function, the `lead` string for `location == "full"` ends with:

```python
                "(a leak from above, water in a wall) is.\n")
```

Replace that line with:

```python
                "(a leak from above, water in a wall) is.\n"
                # 22 Oct, feature 17: the two new refusals.
                "It also needs who is reporting. Without reporter_name it opens "
                "nothing and answers need_name: ask for their name and call again. "
                "need_phone means this call came with no number of its own: ask for "
                "a number to reach them, read it back in words, and call again with "
                "it as reporter_phone. Someone who will not give a name or a number, "
                "after hearing once that it is so the team knows who to contact, "
                "still gets the ticket: name_declined or phone_declined true.\n")
```

- [ ] **Step 4: `notify_team` takes the caller's name**

In `INTAKE_TOOLS`, inside the `notify_team` `_fn(…)` properties dict, before the `"department": {` entry, add:

```python
            # 22 Oct, feature 17: the note opens with who called.
            "caller_name": {
                "type": "string",
                "description": "The caller's name, if they said it on this call. "
                               "Leave out rather than guess.",
            },
```

Run: `grep -c '"department": {' scripts/vapi_tools.py`. If it prints more than `1`, put the entry before the one inside the `notify_team` call (the one followed by `"enum": ["collections", "operations", "management", "service"]`).

- [ ] **Step 5: Run the check**

Run the command from Step 1 again.
Expected: `ok`.

- [ ] **Step 6: The two prompt sentences**

In `docs/assistant/demo-inbound.md`, inside the `## System prompt` fence, replace the sentence:

```
את הכתובת מבקשים רק כשכבר ברור שיש פנייה לפתוח.
```

with:

```
את הפרטים של מי שמדווח מבקשים רק כשכבר ברור שיש פנייה לפתוח, ופנייה לא נפתחת בלי שם: קודם השם, אם עוד לא נאמר בשיחה, ואחר כך הכתובת והדירה, כל אחד בשאלה קצרה משלו, כחלק מהשיחה ולא כמו טופס, ובלי להסביר למה. את המספר כבר יש לך מהשיחה; רק כשהכלי אומר שאין, אתה מבקש מספר שאפשר לחזור אליו ומקריא אותו בחזרה במילים. מי שלא רוצה לתת שם שומע ממך פעם אחת, במילים שלך, שזה כדי שהצוות יידע עם מי לדבר, ואם עדיין לא, הפנייה נפתחת בלי שם ולא שואלים שוב.
```

and the sentence:

```
כשמישהו בסכנה: פנייה בדחיפות חירום והצוות יודע, מיד, לפני כל שאלה שאפשר לדחות.
```

with:

```
כשמישהו בסכנה: הצוות יודע מיד, לפני כל שאלה שאפשר לדחות, ורק אחר כך השם והכתובת ופנייה בדחיפות חירום.
```

Run:

```bash
python -X utf8 -c "import sys; sys.path.insert(0,'scripts'); import vapi_sync as S; f,p=S.extract_fence(open('docs/assistant/demo-inbound.md',encoding='utf-8').read()); assert 'פנייה לא נפתחת בלי שם' in p and 'ורק אחר כך השם והכתובת' in p and 'את הכתובת מבקשים רק' not in p; print(len(p), 'ok')"
```

Expected: the new length (about 7,400) and `ok`.

- [ ] **Step 7: Commit**

```bash
git add scripts/vapi_tools.py docs/assistant/demo-inbound.md
git commit -m "Feature 17: the incoming agent asks the name (and a number when the call has none) before a ticket; emergency alert still first

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The name on the dashboard's tickets page

**Files:**
- Modify: `dashboard/app/(app)/tickets/page.tsx` (the select at line 92, the caller cell at line 232)

- [ ] **Step 1: Select the name**

In the `.select('reference,description,…')` string at line 92, replace `reported_by_phone,` with `reported_by_phone,reported_by_name,`.

- [ ] **Step 2: Show it above the number**

Replace:

```tsx
                  <td className="mono" data-label={t('col.caller')}>{r.reported_by_phone ?? <span className="muted">—</span>}</td>
```

with:

```tsx
                  <td className="mono" data-label={t('col.caller')}>
                    {/* Feature 17: who reported it, above the number to call back. */}
                    {r.reported_by_name && <div dir="auto" style={{ fontFamily: 'inherit' }}>{r.reported_by_name}</div>}
                    {r.reported_by_phone ?? <span className="muted">—</span>}
                  </td>
```

- [ ] **Step 3: Type-check**

Run: `cd dashboard && npx tsc --noEmit -p . ; cd ..`
Expected: exit code 0 and no output.

- [ ] **Step 4: Commit**

```bash
git add "dashboard/app/(app)/tickets/page.tsx"
git commit -m "Feature 17: the tickets page shows who reported a ticket above the number

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: The automatic test — played calls, scored

**Files:**
- Modify: `scripts/voice_qa.py` (`bundle()` and `main()`)
- Create: `scripts/check_name_flow_test.py`, `scripts/check_name_flow.py`, `scripts/voice_qa_name.json`

**Interfaces:**
- Consumes: the candidate prompt and tools from Task 4.
- Produces: `python scripts/voice_qa.py bundle --run DIR --deck scripts/voice_qa_name.json [--candidate]`; `python scripts/check_name_flow.py DIR` exits 0 when every transcript passes.

- [ ] **Step 1: `bundle --candidate`**

In `scripts/voice_qa.py`, change the signature `def bundle(run, deck_path=DECK):` to `def bundle(run, deck_path=DECK, candidate=False):`, and replace inside it:

```python
        prompt, first, tools = P.live_prompt(P.TARGETS[target])
        live[target] = (prompt, first, tools)
```

with:

```python
        prompt, first, tools = P.live_prompt(P.TARGETS[target])
        if candidate:
            # 22 Oct, feature 17: the working tree's prompt and tools, so a
            # change is played before it is synced. The live first message
            # stays; the candidate does not change it.
            prompt = P.file_prompt(P.TARGETS[target], os.path.join(ROOT, P.TARGETS[target]["doc"]))
            tools = P.repo_tools(P.TARGETS[target])
        live[target] = (prompt, first, tools)
```

In `main()`, replace `return bundle(argv[2], deck)` with `return bundle(argv[2], deck, candidate="--candidate" in argv)`, and add to the module docstring under the `bundle` line:

```
                                                   #   (--candidate: the repo's prompt and tools, not live)
```

- [ ] **Step 2: Write the checker's failing test**

Create `scripts/check_name_flow_test.py`:

```python
# -*- coding: utf-8 -*-
"""Tests for check_name_flow.py.   python scripts/check_name_flow_test.py"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_name_flow as C  # noqa: E402

OPENED = {"ok": True, "reference": "255-1600-26", "reference_spoken": "אחת שש אפס אפס"}


def turn_tool(name, args, result, agent):
    return {"rounds": [[{"tool": name, "arguments": args, "result": result}]], "agent": agent}


class Rules(unittest.TestCase):
    def check(self, card, turns):
        return C.score(card, {"scenario": card["id"], "turns": turns})

    def test_ticket_with_name_asked_first_passes(self):
        card = {"id": "a", "call_has_number": True, "expect": {"ticket": True}}
        turns = [{"agent": "היי, מדבר מיכאל"}, {"caller": "נשרפה נורה בחדר מדרגות"},
                 {"agent": "אוי. על איזה שם לרשום את הקריאה?"}, {"caller": "דני כהן"},
                 {"agent": "באיזה בניין, ומה מספר הדירה?"}, {"caller": "בר כוכבא 23 דירה 4"},
                 turn_tool("open_request", {"description": "נורה", "reporter_name": "דני כהן",
                                            "building": "בר כוכבא 23"}, OPENED, "פתחתי פנייה")]
        self.assertEqual(self.check(card, turns), [])

    def test_ticket_without_name_fails(self):
        card = {"id": "b", "call_has_number": True, "expect": {"ticket": True}}
        turns = [{"agent": "היי"}, {"caller": "נורה שרופה, בר כוכבא 23"},
                 turn_tool("open_request", {"description": "נורה", "building": "בר כוכבא 23"},
                           OPENED, "פתחתי")]
        fails = self.check(card, turns)
        self.assertIn("named", fails)
        self.assertIn("asked_first", fails)

    def test_name_said_up_front_must_not_be_asked(self):
        card = {"id": "c", "call_has_number": True, "expect": {"ticket": True, "name_given": True}}
        turns = [{"agent": "היי"}, {"caller": "זאת דנה לוי מבר כוכבא 23 דירה 4, יש נזילה"},
                 {"agent": "מה השם שלך?"}, {"caller": "אמרתי, דנה"},
                 turn_tool("open_request", {"description": "נזילה", "reporter_name": "דנה לוי"},
                           OPENED, "פתחתי")]
        self.assertIn("asked_once", self.check(card, turns))

    def test_emergency_alert_must_come_before_the_name(self):
        card = {"id": "d", "call_has_number": True, "expect": {"ticket": True, "emergency": True}}
        turns = [{"agent": "היי"}, {"caller": "יש ריח של גז חזק"},
                 {"agent": "מה השם שלך?"}, {"caller": "רון"},
                 turn_tool("notify_team", {"reason": "emergency", "description": "גז"},
                           {"ok": True}, "הצוות יודע"),
                 turn_tool("open_request", {"description": "גז", "reporter_name": "רון",
                                            "urgency": "emergency"}, OPENED, "פתחתי")]
        self.assertIn("emergency_first", self.check(card, turns))

    def test_phone_must_not_be_asked_when_the_call_has_one(self):
        card = {"id": "e", "call_has_number": True, "expect": {"ticket": True}}
        turns = [{"agent": "היי"}, {"caller": "שער שבור"}, {"agent": "על איזה שם לרשום?"},
                 {"caller": "מיכל"}, {"agent": "ומה מספר הטלפון שלך?"}, {"caller": "050..."},
                 turn_tool("open_request", {"description": "שער", "reporter_name": "מיכל"},
                           OPENED, "פתחתי")]
        self.assertIn("phone", self.check(card, turns))

    def test_no_ticket_expected(self):
        card = {"id": "f", "call_has_number": True, "expect": {"ticket": False}}
        turns = [{"agent": "היי"}, {"caller": "הכיור שלי סתום"},
                 {"agent": "כיור בתוך הדירה הוא באחריותך"}]
        self.assertEqual(self.check(card, turns), [])

    def test_refusal_gets_a_ticket_and_no_third_ask(self):
        card = {"id": "g", "call_has_number": True, "expect": {"ticket": True, "refuses_name": True}}
        turns = [{"agent": "היי"}, {"caller": "המעלית תקועה"}, {"agent": "על איזה שם לרשום?"},
                 {"caller": "לא משנה"}, {"agent": "זה רק כדי שהצוות יידע עם מי לדבר. מה השם?"},
                 {"caller": "לא רוצה"},
                 turn_tool("open_request", {"description": "מעלית", "name_declined": True},
                           OPENED, "פתחתי")]
        self.assertEqual(self.check(card, turns), [])


class Files(unittest.TestCase):
    def test_run_reads_the_source_deck_for_expectations(self):
        with tempfile.TemporaryDirectory() as d:
            deck = {"defaults": {}, "scenarios": [
                {"id": "a", "call_has_number": True, "expect": {"ticket": False}}]}
            src = os.path.join(d, "deck_src.json")
            json.dump(deck, open(src, "w", encoding="utf-8"), ensure_ascii=False)
            json.dump({"_source": src, "defaults": {}, "scenarios": [{"id": "a"}]},
                      open(os.path.join(d, "deck.json"), "w", encoding="utf-8"))
            os.makedirs(os.path.join(d, "transcripts"))
            json.dump({"scenario": "a", "turns": [{"agent": "היי"}]},
                      open(os.path.join(d, "transcripts", "a.json"), "w", encoding="utf-8"))
            self.assertEqual(C.run(d), {"a": []})


if __name__ == "__main__":
    unittest.main()
```

Run: `python -X utf8 scripts/check_name_flow_test.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'check_name_flow'`.

- [ ] **Step 3: Write the checker**

Create `scripts/check_name_flow.py`:

```python
# -*- coding: utf-8 -*-
"""Score played calls against feature 17: no ticket without the reporter's name.

    python scripts/check_name_flow.py RUN_DIR      # RUN_DIR/transcripts/*.json

RUN_DIR is a voice_qa.py bundle. Its deck.json names the source deck
(`_source`), which keeps each card's `expect` and `call_has_number`; the copy
the players read has them stripped. Exit 0 when every transcript passes.

Rules (docs/features/17-name-before-ticket/feature.md, Acceptance):
  named            every ticket that opened carries reporter_name or name_declined
  asked_first      a ticket was preceded by a question about the name, unless
                   the caller said it first
  asked_once       the name was asked at most once (twice when the caller refuses),
                   never when the caller said it first
  emergency_first  in an emergency the team alert came before any name question
  phone            no number asked on a call that has one; on a call without one,
                   the ticket carries reporter_phone or phone_declined
  ticket           a ticket opened exactly when the card expects one
"""
import glob
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# "מה השם" but not "מה השם של הרחוב": a street question is not a name question.
NAME_ASK = re.compile(r"(על איזה שם|על שם מי|מה השם(?!\s+של\s+ה)|מה שמך|איך קוראים ל|את שמך|"
                      r"השם שלך|השם המלא|שם מלא|עם מי (אני|יש לי))")
PHONE_WORD = re.compile(r"טלפון")
PHONE_ASK = re.compile(r"(מספר (טלפון|שאפשר|נייד|ליצירת קשר|לחזור)|לאיזה מספר|באיזה מספר)")


def asks_phone(text):
    return bool(PHONE_WORD.search(text) or PHONE_ASK.search(text))


def events(transcript):
    """The call as an ordered list: ('ask_name'|'ask_phone', i) and ('tool', name, args, result, i)."""
    out = []
    for i, turn in enumerate(transcript.get("turns", [])):
        for rnd in turn.get("rounds", []) or []:
            for call in rnd:
                out.append(("tool", call.get("tool"), call.get("arguments") or {},
                            call.get("result") or {}, i))
        text = turn.get("agent") or ""
        if text and NAME_ASK.search(text):
            out.append(("ask_name", i))
        if text and asks_phone(text):
            out.append(("ask_phone", i))
    return out


def yes(value):
    return value is True or str(value).strip().lower() == "true"


def score(card, transcript):
    """The names of the rules this transcript breaks; [] when it passes."""
    exp = card.get("expect") or {}
    ev = events(transcript)
    opened = [e for e in ev if e[0] == "tool" and e[1] == "open_request" and e[3].get("reference")]
    asks = [e for e in ev if e[0] == "ask_name"]
    fails = []
    if any(not str(e[2].get("reporter_name") or "").strip() and not yes(e[2].get("name_declined"))
           for e in opened):
        fails.append("named")
    if exp.get("ticket") and opened and not exp.get("name_given"):
        first = ev.index(opened[0])
        if not any(ev.index(a) < first for a in asks):
            fails.append("asked_first")
    if exp.get("name_given"):
        if asks:
            fails.append("asked_once")
    elif len(asks) > (2 if exp.get("refuses_name") else 1):
        fails.append("asked_once")
    if exp.get("emergency"):
        alert = [e for e in ev if e[0] == "tool" and e[1] == "notify_team"
                 and e[2].get("reason") == "emergency"]
        if not alert or (asks and ev.index(asks[0]) < ev.index(alert[0])):
            fails.append("emergency_first")
    phone_asks = [e for e in ev if e[0] == "ask_phone"]
    if card.get("call_has_number", True):
        if phone_asks:
            fails.append("phone")
    elif exp.get("ticket") and not any(str(e[2].get("reporter_phone") or "").strip()
                                       or yes(e[2].get("phone_declined")) for e in opened):
        fails.append("phone")
    if bool(exp.get("ticket")) != bool(opened):
        fails.append("ticket")
    return fails


def run(run_dir):
    bundled = json.load(open(os.path.join(run_dir, "deck.json"), encoding="utf-8"))
    src = bundled.get("_source", "")
    if src and not os.path.isabs(src):
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), src)
    deck = json.load(open(src, encoding="utf-8")) if src else bundled
    cards = {c["id"]: c for c in deck["scenarios"]}
    results = {}
    for path in sorted(glob.glob(os.path.join(run_dir, "transcripts", "*.json"))):
        t = json.load(open(path, encoding="utf-8"))
        sid = t.get("scenario") or os.path.splitext(os.path.basename(path))[0]
        results[sid] = score(cards[sid], t)
    return results


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    results = run(sys.argv[1])
    for sid, fails in results.items():
        print("%-4s %-24s %s" % ("ok" if not fails else "FAIL", sid, ", ".join(fails)))
    bad = sum(1 for f in results.values() if f)
    print("\n%d of %d passed" % (len(results) - bad, len(results)))
    sys.exit(1 if bad or not results else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the checker's test**

Run: `python -X utf8 scripts/check_name_flow_test.py`
Expected: `Ran 8 tests` … `OK`.

- [ ] **Step 5: The deck**

Create `scripts/voice_qa_name.json`. `defaults` is the `defaults` object of `scripts/voice_qa_inbound_4.json`, copied, with its `open_request` entry replaced by the one below. Copy the file, then replace that one entry. The scenarios follow it.

```json
{
 "_about": "Feature 17 (22 Oct): no ticket without the reporter's name, and on a call with no number of its own, a number. Ten incoming calls in בר כוכבא 23, the one building opened for tests. Claude plays each caller as a real person and the agent from the candidate prompt and tools. Scored by scripts/check_name_flow.py against each card's expect.",
 "defaults": {
  "open_request": {
   "_rule": "Apply these in order. (1) The building, exactly as before: Bar Kochba (בר כוכבא, any spelling) with another number: number_not_on_street; Bar Kochba with no number: need_number; any other street: street_unknown. (2) ONLY if open_request's parameters in the context include reporter_name: no reporter_name and no name_declined true: need_name. (3) Only then, ONLY if the card's call_has_number is false: no reporter_phone and no phone_declined true: need_phone. (4) No building at all: need_building. Otherwise opened. A second call with the same building and type inside 30 minutes returns the first reference with duplicate: true.",
   "opened": {"ok": true, "reference": "<ticket>", "reference_spoken": "<spoken>"},
   "need_name": {"ok": true, "opened": false, "reason": "need_name"},
   "need_phone": {"ok": true, "opened": false, "reason": "need_phone"},
   "need_building": {"ok": true, "opened": false, "building_found": false, "reason": "need_building"},
   "need_number": {"ok": true, "opened": false, "building_found": false, "reason": "need_number", "street": "בר כוכבא", "numbers_we_manage": ["23"]},
   "number_not_on_street": {"ok": true, "opened": false, "building_found": false, "reason": "number_not_on_street", "street": "בר כוכבא", "numbers_we_manage": ["23"]},
   "street_unknown": {"ok": true, "opened": false, "building_found": false, "reason": "street_unknown"}
  }
 },
 "scenarios": [
  {"id": "nm_light_noname", "agent": "inbound", "title": "A stairwell light is out; he never offers his name", "time": "10:20", "weekday_he": "שני", "ticket": "255-1601-26", "call_has_number": true,
   "caller": {"persona": "אבי, 45, in a hurry, polite, short answers. Speaks about himself in the masculine.", "knows": "Lives at בר כוכבא 23, apartment 5. The light on the third-floor landing has been out for two days; it is dark on the stairs in the evening.", "wants": "Someone to change the light.", "tendencies": "Starts with the problem, not a greeting. Answers only what he is asked. Does not volunteer his name or flat."},
   "expect": {"ticket": true}},
  {"id": "nm_name_upfront", "agent": "inbound", "title": "She says her name, building and flat in the first breath", "time": "09:05", "weekday_he": "שלישי", "ticket": "255-1602-26", "call_has_number": true,
   "caller": {"persona": "דנה לוי, 38, organised and direct. Speaks about herself in the feminine.", "knows": "Lives at בר כוכבא 23, apartment 4. Water is dripping from the ceiling of the ground-floor lobby near the mailboxes since this morning.", "wants": "A ticket for the leak.", "tendencies": "Opens with: her name, building and flat, then the leak, all in one sentence. Gets a little impatient if asked for something she already said."},
   "expect": {"ticket": true, "name_given": true}},
  {"id": "nm_refuses", "agent": "inbound", "title": "Will not give a name: 'why does it matter, just fix it'", "time": "18:40", "weekday_he": "רביעי", "ticket": "255-1603-26", "call_has_number": true,
   "caller": {"persona": "A man in his 60s, suspicious of giving details on the phone, gruff but not rude.", "knows": "Lives at בר כוכבא 23, apartment 7. The lift has been stuck on the second floor since the afternoon; nobody is inside.", "wants": "The lift fixed.", "tendencies": "When asked his name, says it does not matter. If asked again, refuses again and says just open it. Gives the building and flat when asked."},
   "expect": {"ticket": true, "refuses_name": true}},
  {"id": "nm_gas", "agent": "inbound", "title": "A strong smell of gas in the stairwell, frightened", "time": "21:10", "weekday_he": "חמישי", "ticket": "255-1604-26", "call_has_number": true,
   "caller": {"persona": "רונית, 52, frightened and talking fast. Speaks about herself in the feminine.", "knows": "Lives at בר כוכבא 23, apartment 2. A strong smell of gas on the stairwell between the first and second floors, started ten minutes ago.", "wants": "Help now; asks what she should do.", "tendencies": "Starts with the smell, before any greeting. Asks whether to open windows. Gives her name and building when asked, quickly."},
   "expect": {"ticket": true, "emergency": true}},
  {"id": "nm_payment", "agent": "inbound", "title": "Wants to arrange paying the building fee in instalments", "time": "11:30", "weekday_he": "ראשון", "ticket": "255-1605-26", "call_has_number": true,
   "caller": {"persona": "יוסי, 41, friendly, a bit embarrassed about being behind.", "knows": "Lives at בר כוכבא 23, apartment 1. Knows he owes a few months of the building fee.", "wants": "To pay it off in instalments.", "tendencies": "Says he wants to pay but in parts. Does not ask how much he owes. Gives details when asked."},
   "expect": {"ticket": true}},
  {"id": "nm_private_sink", "agent": "inbound", "title": "Her kitchen sink is blocked: her own fixture", "time": "13:15", "weekday_he": "שני", "ticket": "255-1606-26", "call_has_number": true,
   "caller": {"persona": "מירב, 33, chatty. Speaks about herself in the feminine.", "knows": "Lives at בר כוכבא 23, apartment 3. Her kitchen sink drains very slowly since yesterday; nothing else in the building is affected.", "wants": "Someone to come and fix the sink.", "tendencies": "Explains the sink in detail. Accepts kindly when told it is hers to handle."},
   "expect": {"ticket": false}},
  {"id": "nm_unmanaged", "agent": "inbound", "title": "A building Homies does not manage", "time": "15:45", "weekday_he": "שלישי", "ticket": "255-1607-26", "call_has_number": true,
   "caller": {"persona": "אלי, 50, calm.", "knows": "Lives at הרצל 5, Ramat Gan. The entrance door of his building does not close.", "wants": "The door fixed.", "tendencies": "Says his address when asked, the same way twice if asked again."},
   "expect": {"ticket": false}},
  {"id": "nm_staff_no_number", "agent": "inbound", "title": "Homies staff calling from the office extension for a tenant: the call has no number", "time": "12:00", "weekday_he": "רביעי", "ticket": "255-1608-26", "call_has_number": false,
   "caller": {"persona": "שירן from Homies' office, calling on behalf of an elderly tenant. Speaks about herself in the feminine.", "knows": "The tenant is משה ברק, בר כוכבא 23, apartment 6. The building's front gate does not lock since this morning. The tenant's number is 052-4418823.", "wants": "A ticket for the gate, with the tenant's details.", "tendencies": "Says she is calling from the office for a tenant. Gives the tenant's name and number when asked."},
   "expect": {"ticket": true}},
  {"id": "nm_status", "agent": "inbound", "title": "Asks what is happening with yesterday's ticket", "time": "10:50", "weekday_he": "חמישי", "ticket": "255-1609-26", "call_has_number": true,
   "caller": {"persona": "גדי, 60, patient.", "knows": "Lives at בר כוכבא 23, apartment 8. Reported a broken intercom yesterday; does not remember the ticket number.", "wants": "To know if anything happened.", "tendencies": "Gives the building and flat when asked. Thanks and ends the call."},
   "fixtures": {"get_request_status": {"ok": true, "found": 1, "as_of": "live", "other_open": 0, "requests": [{"reference": "255-1590-26", "reference_spoken": "אחת חמש תשע אפס", "type": "maintenance", "status": "open", "description": "האינטרקום בכניסה לא עובד", "created": "yesterday"}]}},
   "expect": {"ticket": false}},
  {"id": "nm_two_issues", "agent": "inbound", "title": "Two problems in one call: the lift is noisy, and the mailbox door is broken", "time": "16:20", "weekday_he": "ראשון", "ticket": "255-1610-26", "call_has_number": true,
   "caller": {"persona": "נעמה, 29, cheerful. Speaks about herself in the feminine.", "knows": "Lives at בר כוכבא 23, apartment 9. The lift makes a loud grinding noise between floors. The little door of the building's mailbox for flat 9 is broken off.", "wants": "Both fixed.", "tendencies": "Reports the lift first. After the first ticket, adds: and one more thing, the mailbox."},
   "expect": {"ticket": true}}
 ]
}
```

Run:

```bash
python -X utf8 -c "import json; d=json.load(open('scripts/voice_qa_name.json',encoding='utf-8')); assert 'get_balance' in d['defaults'] and 'need_name' in d['defaults']['open_request']; print(len(d['scenarios']), 'cards')"
```

Expected: `10 cards`.

- [ ] **Step 6: Prove the test bites: play three calls on LIVE**

Run: `python scripts/voice_qa.py bundle --run <scratchpad>/name-live --deck scripts/voice_qa_name.json`

Keep three cards. Delete every `context_*.md` except those for `nm_light_noname`, `nm_gas` and `nm_refuses`. Then dispatch three subagents in parallel, one per card, with this prompt (with `<RUN>` and `<ID>` filled in):

> You are playing one offline call for Homies' testing; nothing you write reaches anyone. Read `<RUN>/PLAYER.md` and follow it exactly. Your scenario is `<ID>`: its card and the tool defaults are in `<RUN>/deck.json` (the scenario object, plus `defaults`), and the agent's prompt and tools are in `<RUN>/context_<ID>.md`. Play the agent faithfully from that context: do not improve on it, and do not follow rules it does not contain. The card's `call_has_number` is a fact about the call that the open_request `_rule` uses. Write `<RUN>/transcripts/<ID>.json` in the format PLAYER.md gives. Reply with one line: the path you wrote.

Run: `python scripts/check_name_flow.py <scratchpad>/name-live`
Expected: exit 1. `nm_light_noname` and `nm_refuses` fail with `named` and `asked_first`: the live agent opens tickets without a name. That proves the checker catches the gap.

- [ ] **Step 7: Play all ten on the CANDIDATE**

Run: `python scripts/voice_qa.py bundle --run <scratchpad>/name-cand --deck scripts/voice_qa_name.json --candidate`

Dispatch ten subagents (in parallel batches of five) with the Step 6 prompt, `<RUN>` = `<scratchpad>/name-cand`.

Run: `python scripts/check_name_flow.py <scratchpad>/name-cand`
Expected: `10 of 10 passed`.

When a card fails, read its transcript. If the agent followed the prompt and the prompt is wrong, change the prompt sentence or the tool text (Task 4), re-run Steps 6-7 of Task 4, bundle again, and replay only the failing cards plus two passing ones. If the player broke `PLAYER.md` (helped the agent, ignored the card), replay that card with a fresh subagent. Never edit a transcript.

- [ ] **Step 8: Keep the record and commit**

Copy `<scratchpad>/name-cand/transcripts/` to `docs/assistant/transcripts/2026-10-22-name-before-ticket/`, together with the checker's output as `result.txt`.

```bash
git add scripts/voice_qa.py scripts/check_name_flow.py scripts/check_name_flow_test.py scripts/voice_qa_name.json docs/assistant/transcripts/2026-10-22-name-before-ticket
git commit -m "Feature 17: played-call test (voice_qa bundle --candidate, 10 cards, check_name_flow.py): live fails as expected, the candidate passes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Live, on the owner's go only

**Files:** `.env` (one line), `docs/WORKLOG.md`, `HANDOVER.md`, `CONTEXT.md`, `docs/README.md`, `docs/features/17-name-before-ticket/feature.md`

- [ ] **Step 1: The owner's go.** Show the Task 6 result. Proceed only on an explicit go for these steps.
- [ ] **Step 2: Deploy the function, switched off.** Run `python scripts/supabase_functions.py --apply --oxs-mirror`. Expected: `deploy HTTP 201` (or 200), and `name required unchanged (not in .env)`. The function now stores names and real numbers but refuses nothing new.
- [ ] **Step 3: Probe it.** Run `python scripts/check_tools.py`. Expected: all pass except the five known `no charge on this call` money cases.
- [ ] **Step 4: Sync the incoming agent.** Run `N8N_BASE_URL= python scripts/vapi_sync.py inbound --keep-voice` (dry). Compare what it would send with live: only the prompt and the tools may differ. Then add `--apply`, and read back the agent's prompt (it contains `פנייה לא נפתחת בלי שם`) and the `open_request` fields.
- [ ] **Step 5: Switch on for phone calls.** Add `NAME_REQUIRED_CHANNELS=voice` to `.env`, then run `python scripts/supabase_functions.py --apply --oxs-mirror`. Expected: `name required voice`. Then run `N8N_BASE_URL= python scripts/check_name_gate.py`. Expected: `ok   open_request with no name -> {"ok": true, "opened": false, "reason": "need_name"}`.
- [ ] **Step 6: The owner's test call through 208.** The script for the owner, from an office extension: "the light on the third floor of בר כוכבא 23 is out". Give no name until asked, and give a number when asked. Then check, read-only:
  - Run `python scripts/vapi_latency.py --turns`. It shows the newest call's turns, so you can see the name asked before the ticket and a number asked (the extension call has none).
  - Run the query below. Expected: one row with the name and the number given, and `caller_phone` empty for the extension call.

```bash
python -X utf8 - <<'EOF'
import psycopg
env = dict(l.strip().split("=", 1) for l in open(".env", encoding="utf-8") if "=" in l and not l.startswith("#"))
with psycopg.connect(env["SUPABASE_DB_URL"].strip()) as c:
    c.read_only = True
    print(c.execute("""select r.reference, r.reported_by_name, r.reported_by_phone, i.caller_phone
                         from requests r join interactions i on i.id = r.interaction_id
                        where i.channel = 'voice' order by r.created_at desc limit 1""").fetchone())
EOF
```
- [ ] **Step 7: Record it.**
  - WORKLOG: the 22 Oct entry, with the results.
  - HANDOVER: the 208 bullet and the voice agent's state.
  - CONTEXT: the voice agent section.
  - Feature 17 status: "live on the phone line".
  - Commit.

---

## After this plan: Plan B, WhatsApp

Written once Task 7 is done, with the same shape:
- `prompt.md` line 578: name, building and flat in one message;
- `open_request`'s `$fromAI` fields (`reporter_name`, `name_declined`) and a WhatsApp `need_name` note;
- a carrier patcher (`--dump`, `--apply`, `--restore`, epoch 84 to 85);
- `check_whatsapp_rules.py --candidate --replay`, `check_patchers_idle.py`;
- Claude-played chats scored by the same checker (`call_has_number` true, phone never asked);
- then `NAME_REQUIRED_CHANNELS=voice,whatsapp`, and the owner's phone.
