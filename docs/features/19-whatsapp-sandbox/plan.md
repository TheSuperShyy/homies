# WhatsApp sandbox (feature 19) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent copy of the WhatsApp bot. It has its own Chatwoot account (in Hebrew), its own n8n workflows and its own backend function, and it runs Yariv's section 6 changes. Nothing live changes.

**Architecture:**
- **Backend:** the live `debt-tools/index.ts` runs unchanged as `debt-tools-sandbox`, behind a network guard that lets Supabase reads through, fakes every write and refuses every other host.
- **n8n:** pure transforms over GET copies of the live bot and handover produce the sandbox workflows. They are created with POST, never PUT on a live id.
- **Chatwoot:** a second account on the same server, with an API inbox, its own agent bot, its own admin user and its own tokens.
- **Channel:** a local page proxies Chatwoot's public API, so the owner can write as any tenant.

**Tech Stack:** Deno Edge Function (TypeScript), Node 24 `node --test` with type stripping, Python 3.12 stdlib scripts, n8n 2.33.3 public API, Chatwoot (latest) API, rails runner over SSH, Supabase Management API.

## Global Constraints

- **Production must not be affected; the sandbox is independent** (owner, 26 Oct). Nothing may PUT, PATCH, activate or deactivate these live n8n workflows: `u2JjrbcNPYyyh3yl`, `oB66atFlWwtkSGgN`, `lXofknAbE5wu5nwQ`, `IVNR5iNn7bQS8JgP`, `i3VMdCnXZGooI1Dj`, `pduAdXjX1EU7cA6E`, `pvMuradcJOASapF0`.
- **Never run `scripts/supabase_functions.py` for the sandbox.** It pushes and deletes project-wide secrets.
- **No call to Chatwoot account 2** except read-only GETs, which copy the attribute definitions and take fingerprints.
- **Real phone numbers live only in `.env`** (`SANDBOX_PERSONAS`), never in the repo.
- **Every OpenRouter-spending run needs the owner's go,** with the estimated price stated first. The live OpenRouter credential is shared (owner, 26 Oct).
- **`scripts/sandbox_fingerprint.py --compare` must pass** after each task that creates something.

---

### Task 1: The live fingerprint

**Files:**
- Create: `scripts/sandbox_fingerprint.py`
- Test: `scripts/check_sandbox_fingerprint.py`

**Interfaces:**
- Produces: `snapshot(since_iso) -> dict`, `compare(before, after) -> list[str]`, and the CLI `--save PATH`, `--compare PATH` (exit 1 on any difference).

- [ ] **Step 1: Write the failing test** (`scripts/check_sandbox_fingerprint.py`)

```python
"""Offline checks for compare() in sandbox_fingerprint.py (feature 19)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox_fingerprint import compare

BASE = {"since": "2026-10-26T00:00:00+00:00",
        "n8n": {"a": {"hash": "1", "updatedAt": "t", "active": True, "name": "x"}},
        "function": {"slug": "debt-tools", "version": 130, "updated_at": 1},
        "chatwoot": {"account": {"name": "CLIX", "locale": "en"}, "inboxes": [], "agent_bots": [],
                     "labels": [], "teams": [], "attributes": []},
        "persona_rows_since": {"עידו": {"requests": 0, "messages": 0, "interactions": 0}}}

def clone(**over):
    import copy
    d = copy.deepcopy(BASE); d.update(over); return d

assert compare(BASE, clone()) == [], "identical snapshots must compare clean"
assert compare(BASE, clone(function={"slug": "debt-tools", "version": 131, "updated_at": 2})), "a new live version is a change"
after = clone(); after["n8n"]["a"]["hash"] = "2"
assert compare(BASE, after), "an edited live workflow is a change"
after = clone(); after["persona_rows_since"]["עידו"]["requests"] = 1
assert any("requests" in d for d in compare(BASE, after)), "a persona row in a live table is a change"
print("check_sandbox_fingerprint: 4/4 ok")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python scripts/check_sandbox_fingerprint.py`
Expected: `ModuleNotFoundError: No module named 'sandbox_fingerprint'`

- [ ] **Step 3: Write `scripts/sandbox_fingerprint.py`**

```python
"""Prove the sandbox (feature 19) leaves the live system alone. Reads only.

    python scripts/sandbox_fingerprint.py --save    local/sandbox/before.json
    python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json

What is snapshotted is what the sandbox must never change:
- the 7 live n8n workflows: a hash of nodes, connections and settings, plus updatedAt and active;
- the live Edge Function `debt-tools`: its version and updated_at;
- Chatwoot account 2: name, locale, inboxes, agent bots, labels, teams and attribute definitions;
- rows written since the snapshot for the sandbox personas' phones, in `requests`, `messages` and
  `interactions`. The sandbox must add none. A persona using live WhatsApp in the window also shows
  up here, so testers stay off the live number during a round.

--compare prints every difference and exits 1 if there is one.
"""
import hashlib, json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_WORKFLOWS = ["u2JjrbcNPYyyh3yl", "oB66atFlWwtkSGgN", "lXofknAbE5wu5nwQ", "IVNR5iNn7bQS8JgP",
                  "i3VMdCnXZGooI1Dj", "pduAdXjX1EU7cA6E", "pvMuradcJOASapF0"]
LIVE_FUNCTION = "debt-tools"
LIVE_ACCOUNT = 2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def env():
    return dict(l.strip().split("=", 1) for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
                if l.strip() and not l.startswith("#") and "=" in l)


def fetch(url, headers):
    req = urllib.request.Request(url, headers={**headers, "User-Agent": "homies/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return dict(r.headers), r.read()


def getj(url, headers):
    return json.loads(fetch(url, headers)[1])


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def personas(e):
    """SANDBOX_PERSONAS='עידו:+972…,יריב:+972…' -> [(label, phone)]."""
    out = []
    for part in (e.get("SANDBOX_PERSONAS") or "").split(","):
        if ":" in part:
            label, phone = part.split(":", 1)
            out.append((label.strip(), phone.strip()))
    return out


def count(base, key, table, filters):
    q = "&".join(["select=id"] + ["%s=%s" % (k, urllib.parse.quote(v, safe=".:")) for k, v in filters])
    h, _ = fetch("%s/rest/v1/%s?%s" % (base, table, q),
                 {"apikey": key, "Authorization": "Bearer " + key, "Prefer": "count=exact", "Range": "0-0"})
    return int((h.get("Content-Range") or h.get("content-range") or "*/0").split("/")[-1])


def snapshot(since_iso):
    e = env()
    snap = {"taken_at": datetime.now(timezone.utc).isoformat(), "since": since_iso}
    n8 = e["N8N_BASE_URL"].strip().rstrip("/")
    nh = {"X-N8N-API-KEY": e["N8N_API_KEY"].strip(), "accept": "application/json"}
    snap["n8n"] = {}
    for wid in LIVE_WORKFLOWS:
        w = getj("%s/api/v1/workflows/%s" % (n8, wid), nh)
        snap["n8n"][wid] = {"name": w["name"], "active": w.get("active"), "updatedAt": w.get("updatedAt"),
                            "hash": digest({"nodes": w["nodes"], "connections": w["connections"],
                                            "settings": w.get("settings")})}
    ref = e["SUPABASE_URL"].strip().split("//")[1].split(".")[0]
    fx = getj("https://api.supabase.com/v1/projects/%s/functions" % ref,
              {"Authorization": "Bearer " + e["SUPABASE_ACCESS_TOKEN"].strip()})
    live = next(f for f in fx if f["slug"] == LIVE_FUNCTION)
    snap["function"] = {"slug": LIVE_FUNCTION, "version": live.get("version"), "updated_at": live.get("updated_at")}
    cw = e["CHATWOOT_URL"].strip().rstrip("/") + "/api/v1/accounts/%d" % LIVE_ACCOUNT
    ch = {"api_access_token": e["CHATWOOT_API_TOKEN"].strip()}
    acc = getj(cw, ch)
    snap["chatwoot"] = {
        "account": {"name": acc.get("name"), "locale": acc.get("locale")},
        "inboxes": sorted([i["id"], i["name"], i["channel_type"]] for i in getj(cw + "/inboxes", ch)["payload"]),
        "agent_bots": sorted([b["id"], b["name"], b.get("outgoing_url")] for b in getj(cw + "/agent_bots", ch)),
        "labels": sorted([l["title"], l.get("color"), l.get("description")] for l in getj(cw + "/labels", ch)["payload"]),
        "teams": sorted([t["id"], t["name"]] for t in getj(cw + "/teams", ch)),
        "attributes": sorted([a["attribute_key"], a["attribute_display_name"]]
                             for a in getj(cw + "/custom_attribute_definitions?attribute_model=0", ch)),
    }
    base, key = e["SUPABASE_URL"].strip().rstrip("/"), e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    snap["persona_rows_since"] = {
        label: {
            "requests": count(base, key, "requests", [("reported_by_phone", "eq." + phone), ("created_at", "gte." + since_iso)]),
            "messages": count(base, key, "messages", [("phone", "eq." + phone.lstrip("+")), ("created_at", "gte." + since_iso)]),
            "interactions": count(base, key, "interactions", [("caller_phone", "eq." + phone), ("started_at", "gte." + since_iso)]),
        } for label, phone in personas(e)}
    return snap


def compare(before, after):
    diffs = []
    for k in ("n8n", "function", "chatwoot"):
        if before[k] != after[k]:
            diffs.append("%s: %s -> %s" % (k, json.dumps(before[k], ensure_ascii=False)[:400],
                                          json.dumps(after[k], ensure_ascii=False)[:400]))
    for label, counts in after.get("persona_rows_since", {}).items():
        for table, n in counts.items():
            if n:
                diffs.append("%s: %d new %s row(s) since %s" % (label, n, table, before["since"]))
    return diffs


def main():
    if "--save" in sys.argv:
        path = sys.argv[sys.argv.index("--save") + 1]
        snap = snapshot(datetime.now(timezone.utc).isoformat())
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        json.dump(snap, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("saved %s | %d live workflows | debt-tools v%s | %d personas"
              % (path, len(snap["n8n"]), snap["function"]["version"], len(snap["persona_rows_since"])))
    elif "--compare" in sys.argv:
        before = json.load(open(sys.argv[sys.argv.index("--compare") + 1], encoding="utf-8"))
        diffs = compare(before, snapshot(before["since"]))
        print("live system unchanged" if not diffs else "\n".join(["CHANGED:"] + diffs))
        sys.exit(1 if diffs else 0)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test, then take the first real snapshot**

Run: `python scripts/check_sandbox_fingerprint.py`
Expected: `check_sandbox_fingerprint: 4/4 ok`

Add `SANDBOX_PERSONAS` to `.env`: עידו, יריב and אסף from `v_debt_call_queue_person`, plus `לא מוכר:+972500000001`, a test prefix the function already treats as a test number.

Run: `python scripts/sandbox_fingerprint.py --save local/sandbox/before.json`
Expected: `saved local/sandbox/before.json | 7 live workflows | debt-tools v130 | 4 personas`

Run: `python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json`
Expected: `live system unchanged`

- [ ] **Step 5: Commit**

```bash
git add scripts/sandbox_fingerprint.py scripts/check_sandbox_fingerprint.py
git commit -m "Feature 19: live fingerprint for the sandbox (read-only snapshot and compare)"
```

---

### Task 2: The network guard

**Files:**
- Create: `supabase/functions/debt-tools-sandbox/guard.ts`
- Create: `supabase/functions/debt-tools-sandbox/guard_install.ts`
- Create: `supabase/functions/debt-tools-sandbox/index.ts`
- Test: `scripts/check_sandbox_guard.test.ts`

**Interfaces:**
- Produces:
  - `decide(method, url, supabaseUrl): "pass" | "fake" | "refuse"`;
  - `fakeWrite(method, url, body, accept, prefer): { status: number; body: string | null }`;
  - `install(realFetch, supabaseUrl, log?) => typeof fetch`.
- The sandbox entry imports `./guard_install.ts`, then `./app.ts`. `app.ts` is uploaded by Task 3 as the live `debt-tools/index.ts`, byte for byte.

- [ ] **Step 1: Write the failing test** (`scripts/check_sandbox_guard.test.ts`)

```ts
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `node --test scripts/check_sandbox_guard.test.ts`
Expected: FAIL, `Cannot find module '…/debt-tools-sandbox/guard.ts'`

- [ ] **Step 3: Write `guard.ts`**

```ts
/**
 * The sandbox's network guard (feature 19, docs/features/19-whatsapp-sandbox).
 *
 * debt-tools-sandbox runs the LIVE debt-tools index.ts unchanged, uploaded as
 * app.ts. This module replaces globalThis.fetch before that code loads, so
 * every call the live code makes is decided here:
 *   - Supabase REST and Storage reads (GET, HEAD) go through. The sandbox
 *     reads real tenants, buildings, tickets and balances.
 *   - Supabase writes (POST, PATCH, PUT, DELETE) and every RPC are answered
 *     HERE with a fake success and never sent. An insert that asks for its row
 *     back gets the row it sent plus an id; a `requests` row gets SBX-<n>.
 *   - Every other host (OXS, Chatwoot, Meta, OpenRouter, Vapi, n8n) and every
 *     other Supabase path are refused with 503, which the live code already
 *     treats as "not available".
 * decide() and fakeWrite() are pure, so scripts/check_sandbox_guard.test.ts can check them.
 */
export type Decision = "pass" | "fake" | "refuse";

export function decide(method: string, url: string, supabaseUrl: string): Decision {
  const u = new URL(url);
  if (u.host !== new URL(supabaseUrl).host) return "refuse";
  const read = method.toUpperCase() === "GET" || method.toUpperCase() === "HEAD";
  if (u.pathname.startsWith("/rest/v1/rpc/")) return "fake";
  if (u.pathname.startsWith("/rest/v1/") || u.pathname.startsWith("/storage/v1/")) return read ? "pass" : "fake";
  return "refuse";
}

let serial = 0;

export function fakeWrite(
  method: string, url: string, body: string | null, accept: string, prefer: string,
): { status: number; body: string | null } {
  const path = new URL(url).pathname;
  const m = method.toUpperCase();
  if (path.startsWith("/storage/v1/")) return { status: 200, body: JSON.stringify({ Key: "sandbox" + path }) };
  if (path.startsWith("/rest/v1/rpc/")) return { status: 200, body: "null" };
  if (m === "DELETE") return { status: 204, body: null };
  if (!prefer.includes("return=representation")) return { status: m === "POST" ? 201 : 204, body: null };
  const table = path.slice("/rest/v1/".length);
  let sent: unknown = {};
  try { sent = body ? JSON.parse(body) : {}; } catch { sent = {}; }
  const list = (Array.isArray(sent) ? sent : [sent]) as Record<string, unknown>[];
  const now = new Date().toISOString();
  const rows = list.map((r) => {
    const row: Record<string, unknown> = { id: crypto.randomUUID(), created_at: now, ...r };
    if (table === "requests" && m === "POST") row.reference = `SBX-${++serial}`;
    return row;
  });
  const single = accept.includes("application/vnd.pgrst.object+json");
  return { status: m === "POST" ? 201 : 200, body: JSON.stringify(single ? rows[0] ?? null : rows) };
}

export function install(
  real: typeof fetch, supabaseUrl: string, log: (...a: unknown[]) => void = console.log,
): typeof fetch {
  return (async (input: RequestInfo | URL, init?: RequestInit) => {
    const req = new Request(input, init);
    const verdict = decide(req.method, req.url, supabaseUrl);
    const where = new URL(req.url);
    if (verdict === "pass") return real(req);
    if (verdict === "refuse") {
      log("SANDBOX refused", req.method, where.host + where.pathname);
      return new Response(JSON.stringify({ error: "sandbox: outside calls are off" }), {
        status: 503, headers: { "content-type": "application/json" },
      });
    }
    const out = fakeWrite(req.method, req.url, await req.text(),
      req.headers.get("accept") ?? "", req.headers.get("prefer") ?? "");
    log("SANDBOX faked", req.method, where.pathname, out.status);
    return new Response(out.body, { status: out.status, headers: { "content-type": "application/json" } });
  }) as typeof fetch;
}
```

- [ ] **Step 4: Write `guard_install.ts` and the entry `index.ts`**

`supabase/functions/debt-tools-sandbox/guard_install.ts`:

```ts
// Runs before app.ts (see index.ts): from here on every fetch passes the guard.
import { install } from "./guard.ts";

globalThis.fetch = install(globalThis.fetch.bind(globalThis), Deno.env.get("SUPABASE_URL") ?? "");
```

`supabase/functions/debt-tools-sandbox/index.ts`:

```ts
// The sandbox entry (feature 19). Order matters: the guard replaces fetch
// before app.ts creates its Supabase client and starts serving. app.ts is the
// live debt-tools index.ts byte for byte; scripts/sandbox_function.py uploads
// it under that name and checks the bytes.
import "./guard_install.ts";
import "./app.ts";
```

- [ ] **Step 5: Run the tests**

Run: `node --test scripts/check_sandbox_guard.test.ts`
Expected: `# pass 7`, `# fail 0`

- [ ] **Step 6: Commit**

```bash
git add supabase/functions/debt-tools-sandbox scripts/check_sandbox_guard.test.ts
git commit -m "Feature 19: network guard for debt-tools-sandbox (reads pass, writes faked, other hosts refused)"
```

---

### Task 3: Deploy the sandbox function, without secrets

**Files:**
- Create: `scripts/sandbox_function.py`

**Interfaces:**
- Consumes: `multipart(parts)`, `call(token, method, path, body=None, ctype=None)` and `env()` from `scripts/supabase_functions.py` (module-level helpers, imported, not run).
- Produces: the endpoint `<SUPABASE_URL>/functions/v1/debt-tools-sandbox`, which takes the same `x-homies-secret` and the same Vapi tool envelope as the live function.

- [ ] **Step 1: Write the script**

```python
"""Deploy debt-tools-sandbox (feature 19): the live debt-tools code, unchanged,
behind supabase/functions/debt-tools-sandbox/guard.ts.

    python scripts/sandbox_function.py           # dry run: the files and their hashes
    python scripts/sandbox_function.py --apply   # deploy (files only)
    python scripts/sandbox_function.py --probe   # three tool calls against the sandbox

It NEVER touches project secrets. scripts/supabase_functions.py pushes and
deletes project-wide secrets on every run (a plain run deletes OXS_KEY_REQUESTS
and so switches off the live mirror). This script only uploads files.
"""
import hashlib, json, os, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from supabase_functions import call, env, multipart  # helpers only; that script's main() is not run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "supabase", "functions", "debt-tools")
SBX = os.path.join(ROOT, "supabase", "functions", "debt-tools-sandbox")
SLUG = "debt-tools-sandbox"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def files():
    """(uploaded name, path). app.ts IS the live index.ts."""
    return [("index.ts", os.path.join(SBX, "index.ts")),
            ("guard_install.ts", os.path.join(SBX, "guard_install.ts")),
            ("guard.ts", os.path.join(SBX, "guard.ts")),
            ("app.ts", os.path.join(LIVE, "index.ts")),
            ("identity.ts", os.path.join(LIVE, "identity.ts")),
            ("route.ts", os.path.join(LIVE, "route.ts"))]


def deploy(e):
    token = e["SUPABASE_ACCESS_TOKEN"].strip()
    ref = e["SUPABASE_URL"].strip().split("//")[1].split(".")[0]
    parts = [("metadata", None, json.dumps({"name": SLUG, "entrypoint_path": "index.ts",
                                            "verify_jwt": False}).encode(), "application/json")]
    for name, path in files():
        parts.append(("file", name, open(path, "rb").read(), "application/typescript"))
    body, ctype = multipart(parts)
    code, out = call(token, "POST", "/v1/projects/%s/functions/deploy?slug=%s" % (ref, SLUG), body, ctype)
    print("deploy HTTP %s | version %s | status %s" % (code, (out or {}).get("version"), (out or {}).get("status")))
    if code >= 300:
        print(out); sys.exit(1)


def tool(e, phone, name, args):
    bare = phone.lstrip("+")
    envelope = {"message": {"call": {"id": "wa:" + bare, "assistantOverrides": {"variableValues": {"phone": bare}}},
                            "toolCalls": [{"id": "wa", "function": {"name": name, "arguments": args}}]}}
    req = urllib.request.Request(e["SUPABASE_URL"].strip().rstrip("/") + "/functions/v1/" + SLUG, method="POST",
                                 data=json.dumps(envelope).encode(),
                                 headers={"x-homies-secret": e["TOOL_SECRET"].strip(),
                                          "content-type": "application/json", "User-Agent": "homies/1.0"})
    out = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return json.loads(out["results"][0]["result"])


def probe(e):
    label, phone = [p.split(":", 1) for p in e["SANDBOX_PERSONAS"].split(",")][0]
    print("as", label, phone[:4] + "…" + phone[-3:])
    status = tool(e, phone, "get_request_status", {"reference": "", "building": ""})
    print("get_request_status ->", json.dumps(status, ensure_ascii=False)[:200])
    opened = tool(e, phone, "open_request", {"description": "בדיקת סביבת ניסוי: נורה שרופה בלובי", "type": "electrical",
                                             "building": "בר כוכבא 23", "reporter_unit": "1",
                                             "fault_location": "common", "urgency": "normal"})
    print("open_request ->", json.dumps(opened, ensure_ascii=False)[:300])
    ref = str(opened.get("reference", ""))
    assert ref.startswith("SBX-"), "open_request did not come back with an SBX reference"
    link = tool(e, phone, "get_payment_link", {})
    print("get_payment_link ->", json.dumps(link, ensure_ascii=False)[:200])
    assert "link" not in link or not str(link.get("link", "")).startswith("http"), "a real payment link came back"
    k = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    q = e["SUPABASE_URL"].strip().rstrip("/") + "/rest/v1/requests?select=id&reference=eq." + urllib.parse.quote(ref)
    rows = json.loads(urllib.request.urlopen(urllib.request.Request(q, headers={"apikey": k, "Authorization": "Bearer " + k}), timeout=60).read())
    assert rows == [], "a sandbox ticket reached the live requests table"
    print("probe ok: reads work, the ticket was faked (%s, no row), no payment link" % ref)


def main():
    e = env()
    for name, path in files():
        print("%-17s %6d bytes  sha %s" % (name, os.path.getsize(path), hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]))
    assert open(os.path.join(LIVE, "index.ts"), "rb").read() == open(files()[3][1], "rb").read()
    if "--apply" in sys.argv:
        deploy(e)
    elif "--probe" in sys.argv:
        probe(e)
    else:
        print("\nDry run. --apply deploys the files (no secrets); --probe calls the deployed sandbox.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry run**

Run: `python scripts/sandbox_function.py`
Expected: six lines (`index.ts`, `guard_install.ts`, `guard.ts`, `app.ts`, `identity.ts`, `route.ts`) and `Dry run.`

- [ ] **Step 3: Deploy, then check the live system is unchanged**

Run: `python scripts/sandbox_function.py --apply`
Expected: `deploy HTTP 201 | version 1 | status ACTIVE`

Run: `python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json`
Expected: `live system unchanged`. `debt-tools` is still v130; the new slug is not in the snapshot.

- [ ] **Step 4: Probe**

Run: `python scripts/sandbox_function.py --probe`
Expected: `probe ok: reads work, the ticket was faked (SBX-1, no row), no payment link`

- [ ] **Step 5: Commit**

```bash
git add scripts/sandbox_function.py
git commit -m "Feature 19: deploy debt-tools-sandbox with files only (no project secrets); probe proves reads pass and writes are faked"
```

---

### Task 4: The sandbox Chatwoot account, in Hebrew

**Files:**
- Create: `scripts/chatwoot_sandbox.py`

**Interfaces:**
- Produces these `.env` keys:
  - `SANDBOX_CW_ACCOUNT_ID`, `SANDBOX_CW_ADMIN_USER_ID`, `SANDBOX_CW_ADMIN_TOKEN`, `SANDBOX_CW_BOT_TOKEN`;
  - `SANDBOX_CW_INBOX_ID`, `SANDBOX_CW_INBOX_IDENTIFIER`;
  - `SANDBOX_WEBHOOK_SECRET`;
  - `SANDBOX_CW_TEAMS`, as JSON `{"collections": id, "operations": id, "management": id, "service": id}`.

- [ ] **Step 1: Write the script.** All API calls use the sandbox admin token; the one exception is the read-only GET of account 2's attribute definitions.

```python
"""Create and set up the sandbox Chatwoot account (feature 19). Idempotent.

    python scripts/chatwoot_sandbox.py           # what it would create
    python scripts/chatwoot_sandbox.py --apply   # create, then read back

1. rails runner over SSH: Account "Homies — Sandbox", a sandbox admin user
   (owner of the sandbox tokens), and the owner's own login as an administrator
   of the sandbox only, so he can open it in the UI. Account 2 is not touched.
2. API, with the sandbox admin token:
   - Hebrew name and locale;
   - an API inbox;
   - the agent bot "מיכאל — ניסוי", pointed at n8n /webhook/homies-whatsapp-sandbox?s=<secret>;
   - four Hebrew teams with both users;
   - the eight labels, with their English titles kept (the bot depends on them),
     Hebrew descriptions and colours by urgency;
   - the conversation attributes, copied by key with Hebrew display names.
"""
import json, os, secrets, subprocess, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from supabase_functions import env, set_env

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SSH = ["ssh", "-i", os.path.join(os.path.expanduser("~"), ".ssh", "homies_vps"), "-o", "BatchMode=yes",
       "-o", "ConnectTimeout=15", "root@186.240.147.235"]
ACCOUNT_NAME = "Homies — Sandbox"
HEBREW_NAME = "הומי'ז — סביבת ניסוי"
INBOX_NAME = "צ'אט ניסוי"
BOT_NAME = "מיכאל — ניסוי"
TEAMS = {"collections": ("גבייה", "תשלומים, חובות והסדרים"),
         "operations": ("תפעול ותקלות", "תקלות ובקשות תחזוקה בבניין"),
         "management": ("הנהלה", "ועד, חוזים והסלמות"),
         "service": ("שירות לדיירים", "פניות כלליות של דיירים")}
LABELS = [("after-hours", "#7F8C8D", "הגיע מחוץ לשעות הפעילות; ההתראה תצא ב-09:00"),
          ("bot-off", "#2563EB", "הבוט כבוי בשיחה הזו, נציג מטפל"),
          ("escalated", "#C0392B", "לא נענה בזמן, הועבר גם להנהלה"),
          ("handover", "#E67E22", "הועבר לנציג"),
          ("handover-collections", "#E67E22", "הועבר לגבייה"),
          ("handover-management", "#E67E22", "הועבר להנהלה"),
          ("handover-operations", "#E67E22", "הועבר לתפעול ותקלות"),
          ("handover-service", "#E67E22", "הועבר לשירות לדיירים")]
ATTR_HE = {"handover_at": "הועבר לנציג ב", "handover_reason": "סיבת ההעברה",
           "handover_department": "מחלקה", "handover_source": "מקור ההעברה",
           "handover_paged_at": "התראה נשלחה ב", "handover_escalation": "רמת הסלמה",
           "handover_answered_at": "נענה ב", "handover_channel": "ערוץ",
           "handover_reasons": "סיבות ההעברה"}

RUBY = r'''
require "securerandom"
acc = Account.find_by(name: "Homies — Sandbox") || Account.create!(name: "Homies — Sandbox", locale: "he")
email = "sandbox-admin@homies-sandbox.test"
u = User.find_by(email: email)
unless u
  u = User.new(name: "Sandbox Admin", email: email, password: SecureRandom.hex(12) + "Aa1!")
  u.skip_confirmation!
  u.save!
end
AccountUser.find_or_create_by!(account_id: acc.id, user_id: u.id) { |au| au.role = :administrator }
owner = User.find_by(email: ENV.fetch("OWNER_EMAIL", ""))
AccountUser.find_or_create_by!(account_id: acc.id, user_id: owner.id) { |au| au.role = :administrator } if owner
token = (u.access_token || u.create_access_token).token
puts "SANDBOX_JSON=" + { account_id: acc.id, admin_user_id: u.id, owner_user_id: owner&.id, admin_token: token }.to_json
'''


def rails(owner_email):
    remote = ("cat > /tmp/sbx.rb && docker cp /tmp/sbx.rb chatwoot-rails-1:/tmp/sbx.rb && "
              "docker exec -e OWNER_EMAIL=%s chatwoot-rails-1 bundle exec rails runner /tmp/sbx.rb" % owner_email)
    out = subprocess.run(SSH + [remote], input=RUBY.encode(), capture_output=True, timeout=300).stdout.decode()
    line = next(l for l in out.splitlines() if l.startswith("SANDBOX_JSON="))
    return json.loads(line.split("=", 1)[1])


def api(base, token, method, path, body=None):
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                                 headers={"api_access_token": token, "Content-Type": "application/json",
                                          "User-Agent": "homies/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def main():
    e = env()
    apply = "--apply" in sys.argv
    cw = e["CHATWOOT_URL"].strip().rstrip("/")
    secret = e.get("SANDBOX_WEBHOOK_SECRET", "").strip() or secrets.token_urlsafe(24)
    hook = e["N8N_BASE_URL"].strip().rstrip("/") + "/webhook/homies-whatsapp-sandbox?s=" + secret
    print("account %s (%s) | inbox %s | bot %s -> …/homies-whatsapp-sandbox | %d teams | %d labels"
          % (ACCOUNT_NAME, HEBREW_NAME, INBOX_NAME, BOT_NAME, len(TEAMS), len(LABELS)))
    if not apply:
        print("Dry run. --apply creates it."); return
    made = rails(e["CHATWOOT_ADMIN_EMAIL"].strip())
    acc, tok = made["account_id"], made["admin_token"]
    base = cw + "/api/v1/accounts/%d" % acc
    users = [u for u in (made["admin_user_id"], made.get("owner_user_id")) if u]
    api(base, tok, "PATCH", "", {"name": HEBREW_NAME, "locale": "he"})
    inbox = next((i for i in api(base, tok, "GET", "/inboxes")["payload"] if i["name"] == INBOX_NAME), None) \
        or api(base, tok, "POST", "/inboxes", {"name": INBOX_NAME, "channel": {"type": "api", "webhook_url": ""}})
    bot = next((b for b in api(base, tok, "GET", "/agent_bots") if b["name"] == BOT_NAME), None)
    if bot:
        bot = api(base, tok, "PATCH", "/agent_bots/%d" % bot["id"], {"outgoing_url": hook})
    else:
        bot = api(base, tok, "POST", "/agent_bots", {"name": BOT_NAME, "description": "Feature 19 sandbox", "outgoing_url": hook})
    api(base, tok, "POST", "/inboxes/%d/set_agent_bot" % inbox["id"], {"agent_bot": bot["id"]})
    have = {t["name"]: t["id"] for t in api(base, tok, "GET", "/teams")}
    team_ids = {}
    for key, (name, desc) in TEAMS.items():
        tid = have.get(name) or api(base, tok, "POST", "/teams", {"name": name, "description": desc})["id"]
        api(base, tok, "POST", "/teams/%d/team_members" % tid, {"user_ids": users})
        team_ids[key] = tid
    have = {l["title"] for l in api(base, tok, "GET", "/labels")["payload"]}
    for title, color, desc in LABELS:
        if title not in have:
            api(base, tok, "POST", "/labels", {"title": title, "description": desc, "color": color, "show_on_sidebar": True})
    live = api(cw + "/api/v1/accounts/2", e["CHATWOOT_API_TOKEN"].strip(), "GET",
               "/custom_attribute_definitions?attribute_model=0")
    have = {a["attribute_key"] for a in api(base, tok, "GET", "/custom_attribute_definitions?attribute_model=0")}
    for a in live:
        if a["attribute_key"] not in have:
            api(base, tok, "POST", "/custom_attribute_definitions", {
                "attribute_display_name": ATTR_HE.get(a["attribute_key"], a["attribute_display_name"]),
                "attribute_display_type": a["attribute_display_type"], "attribute_description": a.get("attribute_description") or "",
                "attribute_key": a["attribute_key"], "attribute_model": 0})
    for k, v in {"SANDBOX_CW_ACCOUNT_ID": acc, "SANDBOX_CW_ADMIN_USER_ID": made["admin_user_id"],
                 "SANDBOX_CW_ADMIN_TOKEN": tok, "SANDBOX_CW_BOT_TOKEN": bot["access_token"],
                 "SANDBOX_CW_INBOX_ID": inbox["id"], "SANDBOX_CW_INBOX_IDENTIFIER": inbox["inbox_identifier"],
                 "SANDBOX_WEBHOOK_SECRET": secret, "SANDBOX_CW_TEAMS": json.dumps(team_ids)}.items():
        set_env(k, str(v))
    back = api(base, tok, "GET", "")
    print("account %d: %s, locale %s | inbox %d | bot %d | teams %s"
          % (acc, back["name"], back["locale"], inbox["id"], bot["id"], team_ids))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry run, then apply**

Run: `python scripts/chatwoot_sandbox.py`
Expected: one summary line and `Dry run.`

Run: `python scripts/chatwoot_sandbox.py --apply`
Expected: `account <N>: הומי'ז — סביבת ניסוי, locale he | inbox <i> | bot <b> | teams {...}`. N is not 2.

- [ ] **Step 3: Check the live account is unchanged**

Run: `python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json`
Expected: `live system unchanged`. Account 2's name, locale, inboxes, bots, labels, teams and attributes are identical.

- [ ] **Step 4: Commit**

```bash
git add scripts/chatwoot_sandbox.py
git commit -m "Feature 19: sandbox Chatwoot account (own admin, API inbox, bot, Hebrew teams, labels, attributes); account 2 untouched"
```

---

### Task 5: The sandbox n8n workflows, a faithful copy

**Files:**
- Create: `scripts/n8n_sandbox.py`
- Test: `scripts/check_n8n_sandbox.py`

**Interfaces:**
- Consumes the `.env` keys from Task 4, plus `N8N_BASE_URL`, `N8N_API_KEY` and `SUPABASE_URL`.
- Produces:
  - `sandboxify_handover(wf, cfg) -> dict` and `sandboxify_bot(wf, cfg) -> dict` (pure);
  - the `.env` keys `SANDBOX_N8N_CRED_ADMIN`, `SANDBOX_N8N_CRED_BOT`, `SANDBOX_N8N_HANDOVER_ID`, `SANDBOX_N8N_BOT_ID`.
- `cfg` is a dict with:
  - `account_id` (int), `chatwoot_url`, `supabase_url`, `sandbox_secret`;
  - `cred_admin` and `cred_bot` (`{"id", "name"}`);
  - `handover_id`;
  - `teams` (dict `department -> id`).

- [ ] **Step 1: Write the failing offline test** (`scripts/check_n8n_sandbox.py`)

```python
"""Offline checks of the feature 19 transforms on fresh GET copies of the live workflows."""
import copy, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n8n_sandbox import LIVE_IDS, load, sandboxify_bot, sandboxify_handover

CFG = {"account_id": 99, "chatwoot_url": "https://chat.srv1879140.hstgr.cloud",
       "supabase_url": "https://nmxlhlmcnnggnnuxyelt.supabase.co", "sandbox_secret": "SANDBOX-SECRET",
       "cred_admin": {"id": "A", "name": "SANDBOX Chatwoot admin"}, "cred_bot": {"id": "B", "name": "SANDBOX Chatwoot bot"},
       "handover_id": "HANDOVER-SBX", "teams": {"collections": 11, "operations": 12, "management": 13, "service": 14}}

live_bot, live_h = load("u2JjrbcNPYyyh3yl"), load("oB66atFlWwtkSGgN")
keep_bot, keep_h = copy.deepcopy(live_bot), copy.deepcopy(live_h)
bot, h = sandboxify_bot(live_bot, CFG), sandboxify_handover(live_h, CFG)
assert live_bot == keep_bot and live_h == keep_h, "the transforms must not mutate the live copies"

text = json.dumps({"bot": bot, "h": h}, ensure_ascii=False)
for bad in ("/api/v1/accounts/2/", "graph.facebook.com", "/webhook/homies-debt-tools", "/rest/v1/messages",
            "Chatwoot admin (api_access_token)", "Chatwoot bot (api_access_token)", "Homies WhatsApp typing (Meta)"):
    assert bad not in text, "live reference left in the sandbox: " + bad
assert not re.search(r"/functions/v1/debt-tools(?![-\w])", text), "the live function is still called"
for wid in LIVE_IDS:
    assert wid not in text, "a live workflow id is still referenced: " + wid
by = {n["name"]: n for n in bot["nodes"]}
assert by["WhatsApp"]["parameters"]["path"] == "homies-whatsapp-sandbox"
assert 'const SHARED = "SANDBOX-SECRET"' in by["Sort"]["parameters"]["jsCode"]
assert by["Anything newer?"]["type"] == "n8n-nodes-base.code"
assert bot["connections"]["Anything newer? (fetch)"]["main"][0][0]["node"] == "Anything newer?"
for name in ("Show typing", "Show typing again", "Log inbound", "Log reply"):
    assert by[name]["type"] == "n8n-nodes-base.noOp", name
assert all(n["parameters"]["workflowId"]["value"] == "HANDOVER-SBX"
           for n in bot["nodes"] if n["type"] == "n8n-nodes-base.executeWorkflow")
code = next(n for n in h["nodes"] if n["name"] == "Decide the routing")["parameters"]["jsCode"]
assert "const TEAMS = { collections: 11, operations: 12, management: 13, service: 14 };" in code
assert bot["name"].startswith("SANDBOX — ") and h["name"].startswith("SANDBOX — ")
print("check_n8n_sandbox: copy ok")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python scripts/check_n8n_sandbox.py`
Expected: `ModuleNotFoundError: No module named 'n8n_sandbox'`

- [ ] **Step 3: Write `scripts/n8n_sandbox.py`**

```python
"""The sandbox copies of the WhatsApp bot and "Hand to a person" (feature 19).

    python scripts/n8n_sandbox.py           # transform and print what would be created
    python scripts/n8n_sandbox.py --apply   # credentials, then the two workflows (POST, or PUT on a SANDBOX id), then activate

The live workflows are only ever read (GET). Every write targets an id this
script created; write() refuses any id in LIVE_IDS.
"""
import copy, json, os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from supabase_functions import env, set_env

LIVE_IDS = {"u2JjrbcNPYyyh3yl", "oB66atFlWwtkSGgN", "lXofknAbE5wu5nwQ", "IVNR5iNn7bQS8JgP",
            "i3VMdCnXZGooI1Dj", "pduAdXjX1EU7cA6E", "pvMuradcJOASapF0"}
LIVE_TEAMS = "const TEAMS = { collections: 1, operations: 2, management: 3, service: 4 };"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def n8n(method, path, body=None):
    e = env()
    req = urllib.request.Request(e["N8N_BASE_URL"].strip().rstrip("/") + path, method=method,
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                                 headers={"X-N8N-API-KEY": e["N8N_API_KEY"].strip(), "accept": "application/json",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def load(wid):
    return n8n("GET", "/api/v1/workflows/" + wid)


def replace_once(text, old, new):
    assert text.count(old) == 1, "expected exactly one %r, found %d" % (old[:60], text.count(old))
    return text.replace(old, new)


def rewrite_node(n, cfg):
    """URLs and credentials: the sandbox account, the sandbox function, the sandbox tokens."""
    p = n.setdefault("parameters", {})
    url = p.get("url")
    if isinstance(url, str):
        url = url.replace("/api/v1/accounts/2/", "/api/v1/accounts/%d/" % cfg["account_id"])
        url = re.sub(r"/functions/v1/debt-tools(?![-\w])", "/functions/v1/debt-tools-sandbox", url)
        if url.endswith("/webhook/homies-debt-tools"):
            url = cfg["supabase_url"] + "/functions/v1/debt-tools-sandbox"
            p["authentication"], p["genericAuthType"] = "genericCredentialType", "httpHeaderAuth"
            n["credentials"] = {"httpHeaderAuth": cfg["cred_tool_secret"]}
        p["url"] = url
    for ctype, c in list((n.get("credentials") or {}).items()):
        if c.get("name") == "Chatwoot admin (api_access_token)":
            n["credentials"][ctype] = dict(cfg["cred_admin"])
        elif c.get("name") == "Chatwoot bot (api_access_token)":
            n["credentials"][ctype] = dict(cfg["cred_bot"])


def noop(wf, name):
    n = next(x for x in wf["nodes"] if x["name"] == name)
    n.update({"type": "n8n-nodes-base.noOp", "typeVersion": 1, "parameters": {}})
    n.pop("credentials", None)


def chat_log_from_chatwoot(wf, cfg):
    """`Anything newer?` read Supabase `messages`. The sandbox's log is its
    Chatwoot conversation: the fetch keeps the old node's slot, and a Code node
    named `Anything newer?` hands its seven readers the same rows as before."""
    old = next(x for x in wf["nodes"] if x["name"] == "Anything newer?")
    old["name"] = "Anything newer? (fetch)"
    old["parameters"] = {"method": "GET", "options": {"timeout": 10000},
                         "url": "=%s/api/v1/accounts/%d/conversations/{{ $('Sort').first().json.conv_id }}/messages"
                                % (cfg["chatwoot_url"], cfg["account_id"]),
                         "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"}
    old["credentials"] = {"httpHeaderAuth": dict(cfg["cred_admin"])}
    code = {"name": "Anything newer?", "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [old["position"][0] + 180, old["position"][1] + 140],
            "parameters": {"jsCode": (
                "// Feature 19: the sandbox keeps no chat log of its own; its Chatwoot conversation\n"
                "// is the log. These are the rows the live `messages` query returned: newest first,\n"
                "// at most 12, both directions, private notes left out.\n"
                "const payload = ($input.first().json.payload || []);\n"
                "return payload\n"
                "  .filter(m => (m.message_type === 0 || m.message_type === 1) && !m.private)\n"
                "  .sort((a, b) => b.id - a.id).slice(0, 12)\n"
                "  .map(m => ({ json: { external_id: String(m.id), body: m.content || '',\n"
                "    direction: m.message_type === 0 ? 'inbound' : 'outbound',\n"
                "    message_type: m.content_type === 'input_select' ? 'menu' : 'text' } }));")}}
    wf["nodes"].append(code)
    conns = wf["connections"]
    for src in conns.values():
        for lst in src.get("main", []):
            for c in lst:
                if c["node"] == "Anything newer?":
                    c["node"] = "Anything newer? (fetch)"
    out = conns.pop("Anything newer?")
    conns["Anything newer? (fetch)"] = {"main": [[{"node": "Anything newer?", "type": "main", "index": 0}]]}
    conns["Anything newer?"] = out


def base_copy(wf, name, settings):
    w = copy.deepcopy(wf)
    return {"name": name, "nodes": w["nodes"], "connections": w["connections"], "settings": settings}


def sandboxify_handover(wf, cfg):
    out = base_copy(wf, "SANDBOX — Hand to a person", {"executionOrder": "v1", "timezone": "Asia/Jerusalem"})
    for n in out["nodes"]:
        rewrite_node(n, cfg)
        if n["name"] == "Decide the routing":
            t = cfg["teams"]
            n["parameters"]["jsCode"] = replace_once(
                n["parameters"]["jsCode"], LIVE_TEAMS,
                "const TEAMS = { collections: %d, operations: %d, management: %d, service: %d };"
                % (t["collections"], t["operations"], t["management"], t["service"]))
    return out


def sandboxify_bot(wf, cfg):
    out = base_copy(wf, "SANDBOX — WhatsApp bot", {"executionOrder": "v1", "binaryMode": "separate"})
    live_tool = next(n for n in out["nodes"] if n["name"] == "get_request_status")["credentials"]["httpHeaderAuth"]
    cfg = dict(cfg, cred_tool_secret=dict(live_tool))
    for n in out["nodes"]:
        rewrite_node(n, cfg)
        if n["type"] == "n8n-nodes-base.webhook":
            n["parameters"]["path"] = "homies-whatsapp-sandbox"
            n["webhookId"] = "homies-whatsapp-sandbox-v1"
        if n["type"] == "n8n-nodes-base.executeWorkflow":
            n["parameters"]["workflowId"] = {"__rl": True, "value": cfg["handover_id"], "mode": "id"}
        if n["name"] == "Sort":
            js = n["parameters"]["jsCode"]
            live = re.search(r'const SHARED = "([^"]+)"', js).group(1)
            n["parameters"]["jsCode"] = replace_once(js, 'const SHARED = "%s"' % live,
                                                     'const SHARED = "%s"' % cfg["sandbox_secret"])
    for name in ("Show typing", "Show typing again", "Log inbound", "Log reply"):
        noop(out, name)
    chat_log_from_chatwoot(out, cfg)
    return out


def write(wf, env_key):
    e = env()
    wid = e.get(env_key, "").strip()
    assert wid not in LIVE_IDS, "refusing to write a live workflow"
    if wid:
        n8n("PUT", "/api/v1/workflows/" + wid, wf)
    else:
        wid = n8n("POST", "/api/v1/workflows", wf)["id"]
        set_env(env_key, wid)
    assert wid not in LIVE_IDS
    n8n("POST", "/api/v1/workflows/%s/activate" % wid)
    return wid


def credential(env_key, name, token):
    e = env()
    if e.get(env_key, "").strip():
        return {"id": e[env_key].strip(), "name": name}
    made = n8n("POST", "/api/v1/credentials", {"name": name, "type": "httpHeaderAuth",
                                               "data": {"name": "api_access_token", "value": token}})
    set_env(env_key, made["id"])
    return {"id": made["id"], "name": name}


def config(apply):
    e = env()
    cfg = {"account_id": int(e["SANDBOX_CW_ACCOUNT_ID"]), "chatwoot_url": e["CHATWOOT_URL"].strip().rstrip("/"),
           "supabase_url": e["SUPABASE_URL"].strip().rstrip("/"), "sandbox_secret": e["SANDBOX_WEBHOOK_SECRET"].strip(),
           "teams": json.loads(e["SANDBOX_CW_TEAMS"]), "handover_id": e.get("SANDBOX_N8N_HANDOVER_ID", "").strip() or "PENDING"}
    if apply:
        cfg["cred_admin"] = credential("SANDBOX_N8N_CRED_ADMIN", "SANDBOX Chatwoot admin", e["SANDBOX_CW_ADMIN_TOKEN"].strip())
        cfg["cred_bot"] = credential("SANDBOX_N8N_CRED_BOT", "SANDBOX Chatwoot bot", e["SANDBOX_CW_BOT_TOKEN"].strip())
    else:
        cfg["cred_admin"] = {"id": "DRY", "name": "SANDBOX Chatwoot admin"}
        cfg["cred_bot"] = {"id": "DRY", "name": "SANDBOX Chatwoot bot"}
    return cfg


def main():
    apply = "--apply" in sys.argv
    cfg = config(apply)
    handover = sandboxify_handover(load("oB66atFlWwtkSGgN"), cfg)
    print("handover copy: %d nodes" % len(handover["nodes"]))
    if apply:
        cfg["handover_id"] = write(handover, "SANDBOX_N8N_HANDOVER_ID")
    bot = sandboxify_bot(load("u2JjrbcNPYyyh3yl"), cfg)
    if "--section6" in sys.argv:
        from n8n_sandbox_section6 import section6
        bot = section6(bot)
    print("bot copy: %d nodes" % len(bot["nodes"]))
    if apply:
        print("handover %s | bot %s | both active" % (cfg["handover_id"], write(bot, "SANDBOX_N8N_BOT_ID")))
    else:
        print("Dry run. --apply creates them.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the offline test**

Run: `python scripts/check_n8n_sandbox.py`
Expected: `check_n8n_sandbox: copy ok`

- [ ] **Step 5: Create the workflows, then compare**

Run: `python scripts/n8n_sandbox.py --apply`
Expected: `handover <id> | bot <id> | both active`. Both ids are new and not in `LIVE_IDS`.

Run: `python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json`
Expected: `live system unchanged`

- [ ] **Step 6: Commit**

```bash
git add scripts/n8n_sandbox.py scripts/check_n8n_sandbox.py
git commit -m "Feature 19: sandbox copies of the WhatsApp bot and Hand to a person (own webhook, account, function, chat log); live workflows only read"
```

---

### Task 6: Yariv's section 6, in the sandbox copy only

**Files:**
- Create: `scripts/n8n_sandbox_section6.py`
- Modify: `scripts/check_n8n_sandbox.py` (append the section 6 checks)

**Interfaces:**
- Consumes: the output of `sandboxify_bot(...)`.
- Produces: `section6(bot, supabase_cred) -> dict`, where `supabase_cred` is the live `Anything newer?` node's `httpHeaderAuth` credential ("Homies Supabase service key", used only for a GET). The menu has two buttons; the four representative-button passages are gone from the prompt; `WHO_RULE` is added; the nodes "Who is writing?" and "Add who" are added; the text of `Answer the resident` carries `who_text`.

- [ ] **Step 1: Append the failing checks to `scripts/check_n8n_sandbox.py`**

```python
from n8n_sandbox_section6 import section6, WHO_RULE
supa = next(n for n in keep_bot["nodes"] if n["name"] == "Anything newer?")["credentials"]["httpHeaderAuth"]
s6 = section6(bot, supa)
by6 = {n["name"]: n for n in s6["nodes"]}
assert "לדבר עם נציג" not in by6["Sort"]["parameters"]["jsCode"], "the menu still offers a representative"
prompt = by6["Answer the resident"]["parameters"]["options"]["systemMessage"]
assert "לדבר עם נציג" not in prompt, "the prompt still describes the representative button"
assert WHO_RULE in prompt
assert by6["Who is writing?"]["parameters"]["url"].startswith("=https://nmxlhlmcnnggnnuxyelt.supabase.co/rest/v1/residents?phone=eq.%2B")
assert by6["Who is writing?"].get("alwaysOutputData") is True
assert s6["connections"]["Still the last word?"]["main"][0] == [{"node": "Who is writing?", "type": "main", "index": 0}]
assert {c["node"] for c in s6["connections"]["Add who"]["main"][0]} == {"Worth a word?", "Show typing"}
assert "$('Add who')" in by6["Answer the resident"]["parameters"]["text"]
print("check_n8n_sandbox: section 6 ok")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python scripts/check_n8n_sandbox.py`
Expected: `ModuleNotFoundError: No module named 'n8n_sandbox_section6'`

- [ ] **Step 3: Write `scripts/n8n_sandbox_section6.py`**

```python
"""Yariv's section 6 (docs/discovery/yariv-alignment-2026-10.md), applied ONLY
to the sandbox copy of the WhatsApp bot (feature 19):
  A. no representative button: two menu buttons, and the prompt passages about
     the third one removed. A typed request for a person keeps the 18 Oct rule
     already in the prompt: help first, then the matter, and the team only for
     what is beyond the bot.
  B. the sender recognised from Homies' records: "Who is writing?" reads
     `residents` by phone, "Add who" adds a bracket fact, and WHO_RULE tells
     the model to confirm instead of asking. The balance keeps its typed name and phone.
Every edit asserts that its anchor occurs exactly once, so a changed live prompt
fails loudly instead of being half-edited.
"""
import copy
from n8n_sandbox import replace_once

WHO_RULE = (
    "לפעמים כתוב לך בסוגריים שהפונה מזוהה במערכת, עם השם, הבניין והדירה שלו. זה מידע אמין מהרשומות של הומי'ז, "
    "ולכן אתה לא מבקש ממנו שוב לא שם, לא בניין ולא דירה: הם נחשבים כאילו הוא אמר לך אותם. כשאתה פותח קריאה על משהו "
    "אצלו, אתה שואל רק אם זה המקום, במשפט אחד קצר, כמו \"זה לגבי בר כוכבא 23, דירה 1?\", ומכניס אותם לכלי. אם כתובות "
    "לו כמה דירות, אתה שואל באיזו מהן מדובר. אם הוא מספר על בניין אחר, ממשיכים לפי מה שהוא אומר. רק יתרה נשארת כמו "
    "שהיא: הכלי של היתרה עדיין מבקש שם מלא וטלפון, ואת זה אתה שואל.")

PROMPT_CUTS = [
    (" וגם כשהוא כותב שהוא רוצה נציג, זאת לא הלחיצה על הכפתור: הוא כבר אמר מה הוא רוצה, ומשם ממשיכים.", ""),
    (", חוץ מהלחיצה על \"לדבר עם נציג\" שעליה תקרא בהמשך,", ","),
    ("את הדלת הזאת רק הוא פותח, חוץ מאותה לחיצה על \"לדבר עם נציג\":", "את הדלת הזאת רק הוא פותח:"),
    ("\"פתיחת קריאת שירות\", \"מצב קריאה קיימת\" או \"לדבר עם נציג\".", "\"פתיחת קריאת שירות\" או \"מצב קריאה קיימת\"."),
    ("שני הראשונים אומרים לך מה הוא רוצה", "שניהם אומרים לך מה הוא רוצה"),
    ("ולכן בלחיצה על אחד משני הראשונים הברכה כבר ניתנה", "ולכן בלחיצה על אחד מהם הברכה כבר ניתנה"),
]
REP_TAP_START = " \"לדבר עם נציג\" אומר שהוא רוצה לדבר עם מישהו"
REP_TAP_END = "וממשיכים משם."
TIME_ANCHOR = "+ ' [השעה בישראל עכשיו '"
ADD_WHO = (
    "// Feature 19 (Yariv's section 6): who is writing, from Homies' records, so the bot\n"
    "// does not ask again for what is known. Passes `Still the last word?` through and adds `who_text`.\n"
    "const base = $('Still the last word?').all();\n"
    "const rows = $input.all().map(i => i.json).filter(r => r && (r.full_name || r.building));\n"
    "const first = (s) => String(s || '').trim().split(/\\s+/)[0] || '';\n"
    "let who = '';\n"
    "if (rows.length === 1) {\n"
    "  const r = rows[0];\n"
    "  who = ' [הפונה מזוהה במערכת: ' + first(r.full_name) + ', ' + r.building + ', דירה ' + r.unit + '.]';\n"
    "} else if (rows.length > 1) {\n"
    "  who = ' [הפונה מזוהה במערכת: ' + first(rows[0].full_name) + ', עם כמה דירות: '\n"
    "      + rows.map(r => r.building + ' דירה ' + r.unit).join('; ') + '.]';\n"
    "}\n"
    "return base.map(b => ({ json: { ...b.json, who_text: who } }));")


def section6(bot, supabase_cred):
    out = copy.deepcopy(bot)
    by = {n["name"]: n for n in out["nodes"]}
    sort = by["Sort"]["parameters"]
    sort["jsCode"] = replace_once(sort["jsCode"], '    { title: "לדבר עם נציג",      value: "other" },\n', "")
    sort["jsCode"] = replace_once(sort["jsCode"], '  "לדבר עם נציג":       "other",\n', "")
    opts = by["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in PROMPT_CUTS:
        sm = replace_once(sm, old, new)
    start = sm.index(REP_TAP_START)
    end = sm.index(REP_TAP_END, start) + len(REP_TAP_END)
    assert sm.count(REP_TAP_START) == 1
    sm = sm[:start] + sm[end:]
    anchor = "אתה שירות הלקוחות של הומי'ז, כולו."
    para_end = sm.index("\n\n", sm.index(anchor))
    sm = sm[:para_end] + "\n\n" + WHO_RULE + sm[para_end:]
    assert "לדבר עם נציג" not in sm
    opts["systemMessage"] = sm
    ans = by["Answer the resident"]["parameters"]
    ans["text"] = replace_once(ans["text"], TIME_ANCHOR,
                               "+ ($('Add who').isExecuted ? ($('Add who').first().json.who_text || '') : '') " + TIME_ANCHOR)
    still = by["Still the last word?"]
    supabase_cred = next(n for n in out["nodes"] if n["name"] == "Anything newer? (fetch)") and \
        next(n for n in bot["nodes"] if n.get("credentials", {}).get("httpHeaderAuth", {}).get("name") == "Homies Supabase service key")["credentials"]
    who = {"name": "Who is writing?", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
           "position": [still["position"][0] + 200, still["position"][1] - 160],
           "alwaysOutputData": True, "onError": "continueRegularOutput",
           "parameters": {"method": "GET", "options": {"timeout": 5000},
                          "url": "=https://nmxlhlmcnnggnnuxyelt.supabase.co/rest/v1/residents?phone=eq.%2B{{ $('Sort').first().json.to }}&select=full_name,building,unit",
                          "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"},
           "credentials": copy.deepcopy(supabase_cred)}
    add = {"name": "Add who", "type": "n8n-nodes-base.code", "typeVersion": 2,
           "position": [still["position"][0] + 400, still["position"][1] - 160], "parameters": {"jsCode": ADD_WHO}}
    out["nodes"] += [who, add]
    after = out["connections"]["Still the last word?"]
    out["connections"]["Still the last word?"] = {"main": [[{"node": "Who is writing?", "type": "main", "index": 0}]]}
    out["connections"]["Who is writing?"] = {"main": [[{"node": "Add who", "type": "main", "index": 0}]]}
    out["connections"]["Add who"] = after
    return out
```

Note: the bot's `Log inbound` node (which held the Supabase service-key credential) is a NoOp after Task 5, so `section6` takes the credential from the bot passed in. The test runs `section6` on `sandboxify_bot`'s output. If no node there still carries "Homies Supabase service key", read it from the live copy (`live_bot`) and pass it in instead.

- [ ] **Step 4: Run the checks**

Run: `python scripts/check_n8n_sandbox.py`
Expected: `check_n8n_sandbox: copy ok` and `check_n8n_sandbox: section 6 ok`

- [ ] **Step 5: Push the section 6 version to the sandbox bot only, then compare**

Run: `python scripts/n8n_sandbox.py --apply --section6`
Expected: `handover <same id> | bot <same id> | both active`. It is a PUT on the SANDBOX ids.

Run: `python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json`
Expected: `live system unchanged`

- [ ] **Step 6: Commit**

```bash
git add scripts/n8n_sandbox_section6.py scripts/check_n8n_sandbox.py
git commit -m "Feature 19: Yariv's section 6 in the sandbox bot only (two menu buttons, representative passages out, the sender recognised from residents)"
```

---

### Task 7: The chat page

**Files:**
- Create: `scripts/sandbox_chat.py`

**Interfaces:**
- Consumes: `SANDBOX_CW_INBOX_IDENTIFIER`, `SANDBOX_PERSONAS` and `CHATWOOT_URL` from `.env`.
- Produces:
  - `GET /` serves the page;
  - `GET /api/personas` returns `[{"key", "label"}]`;
  - `POST /api/start {"key"}` returns `{"conv"}`;
  - `POST /api/send {"key", "conv", "content"}` returns `{"ok"}`;
  - `GET /api/messages?key=&conv=` returns `[{"id", "out", "content", "buttons"}]`.
- Persona contacts are cached in `local/sandbox/contacts.json` (gitignored), as `key -> source_id`.

- [ ] **Step 1: Write the server and page**

```python
"""Talk to the sandbox bot as a tenant (feature 19).

    python scripts/sandbox_chat.py   # then open http://127.0.0.1:8765

One page, plus a proxy to Chatwoot's public client API for the sandbox API inbox.
"Writing as" comes from SANDBOX_PERSONAS in .env (label:+phone, never committed).
Each persona is a Chatwoot contact carrying that phone, which is what the bot
reads, as on WhatsApp. Nothing here touches the live account, the live bot or WhatsApp.
"""
import json, os, sys, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from supabase_functions import env

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "local", "sandbox", "contacts.json")
E = env()
CW = E["CHATWOOT_URL"].strip().rstrip("/") + "/public/api/v1/inboxes/" + E["SANDBOX_CW_INBOX_IDENTIFIER"].strip()
PERSONAS = {"p%d" % i: (lbl.strip(), ph.strip())
            for i, (lbl, ph) in enumerate(p.split(":", 1) for p in E["SANDBOX_PERSONAS"].split(","))}

PAGE = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Homies sandbox chat</title>
<style>
body{font-family:system-ui,Arial,sans-serif;margin:0;background:#efeae2;color:#111}
header{background:#075e54;color:#fff;padding:10px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
header select,header button{font-size:15px;padding:4px 8px}
#log{padding:12px;display:flex;flex-direction:column;gap:6px;height:calc(100vh - 130px);overflow-y:auto}
.m{max-width:75%;padding:7px 10px;border-radius:8px;white-space:pre-wrap;line-height:1.4}
.in{align-self:flex-start;background:#dcf8c6}.out{align-self:flex-end;background:#fff}
.btns{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}.btns button{font-size:14px;padding:4px 8px}
form{display:flex;gap:8px;padding:8px;background:#f0f0f0}form input{flex:1;font-size:16px;padding:8px}
</style></head><body>
<header><strong>סביבת ניסוי — מיכאל</strong>
<label>כותב בתור <select id="who"></select></label><button id="new">שיחה חדשה</button></header>
<div id="log"></div>
<form id="f"><input id="t" autocomplete="off" placeholder="הודעה…"><button>שליחה</button></form>
<script>
let conv = null, key = null, seen = 0;
const $ = (id) => document.getElementById(id);
async function j(url, body) {
  const r = await fetch(url, body ? {method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify(body)} : {});
  return r.json();
}
async function start() {
  key = $("who").value; $("log").innerHTML = ""; seen = 0;
  conv = (await j("/api/start", {key})).conv;
}
async function send(text) {
  if (!conv || !text.trim()) return;
  await j("/api/send", {key, conv, content: text});
}
async function poll() {
  if (conv) {
    const msgs = await j("/api/messages?key=" + key + "&conv=" + conv);
    for (const m of msgs.slice(seen)) {
      const d = document.createElement("div");
      d.className = "m " + (m.out ? "out" : "in"); d.textContent = m.content;
      if (m.buttons.length) {
        const b = document.createElement("div"); b.className = "btns";
        for (const t of m.buttons) { const x = document.createElement("button"); x.textContent = t; x.onclick = () => send(t); b.appendChild(x); }
        d.appendChild(b);
      }
      $("log").appendChild(d); $("log").scrollTop = 1e9;
    }
    seen = msgs.length;
  }
  setTimeout(poll, 1500);
}
(async () => {
  for (const p of await j("/api/personas")) { const o = document.createElement("option"); o.value = p.key; o.textContent = p.label; $("who").appendChild(o); }
  $("new").onclick = start; $("f").onsubmit = (e) => { e.preventDefault(); send($("t").value); $("t").value = ""; };
  await start(); poll();
})();
</script></body></html>"""


def cw(method, path, body=None):
    req = urllib.request.Request(CW + path, method=method,
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                                 headers={"Content-Type": "application/json", "User-Agent": "homies/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def contact(key):
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    if key not in cache:
        label, phone = PERSONAS[key]
        cache[key] = cw("POST", "/contacts", {"identifier": "sbx-" + key, "name": label, "phone_number": phone})["source_id"]
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(cache, open(CACHE, "w", encoding="utf-8"))
    return cache[key]


class H(BaseHTTPRequestHandler):
    def reply(self, obj, ctype="application/json"):
        data = obj.encode("utf-8") if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200); self.send_header("content-type", ctype + "; charset=utf-8"); self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = dict(urllib.parse.parse_qsl(u.query))
        if u.path == "/":
            return self.reply(PAGE, "text/html")
        if u.path == "/api/personas":
            return self.reply([{"key": k, "label": v[0]} for k, v in PERSONAS.items()])
        if u.path == "/api/messages":
            msgs = cw("GET", "/contacts/%s/conversations/%s/messages" % (contact(q["key"]), q["conv"]))
            return self.reply([{"id": m["id"], "out": m.get("message_type") == 1, "content": m.get("content") or "",
                                "buttons": [i.get("title") for i in ((m.get("content_attributes") or {}).get("items") or [])]}
                               for m in sorted(msgs or [], key=lambda m: m["id"]) if m.get("message_type") in (0, 1)])
        self.send_error(404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        if self.path == "/api/start":
            return self.reply({"conv": cw("POST", "/contacts/%s/conversations" % contact(body["key"]), {})["id"]})
        if self.path == "/api/send":
            cw("POST", "/contacts/%s/conversations/%s/messages" % (contact(body["key"]), body["conv"]), {"content": body["content"]})
            return self.reply({"ok": True})
        self.send_error(404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("sandbox chat on http://127.0.0.1:8765 (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
```

- [ ] **Step 2: A smoke test with no model spend.** A bare hello gets the system menu from `Sort` itself; no model runs.

Run: `python scripts/sandbox_chat.py`, open `http://127.0.0.1:8765`, choose "לא מוכר", and send `שלום`.
Expected: the menu text "<hour word> 👋 כאן הומי'ז. במה אפשר לעזור?" with **two** buttons, and no "לדבר עם נציג".

- [ ] **Step 3: Compare, then commit**

Run: `python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json`
Expected: `live system unchanged`

```bash
git add scripts/sandbox_chat.py
git commit -m "Feature 19: local chat page for the sandbox (public API proxy, writing as any persona)"
```

---

### Task 8: Acceptance run

**Files:**
- Create: `scripts/sandbox_drive.py`

**Interfaces:**
- Consumes: the same public API as Task 7 (it imports `contact`, `cw` and `PERSONAS` from `sandbox_chat`).

- [ ] **Step 1: Write the driver**

```python
"""Scripted conversations against the sandbox bot (feature 19). SPENDS OpenRouter
(the live credential, shared by owner decision): about 15 model replies,
roughly 6 cents each on Gemini 3.1 Pro. Run only on the owner's go.

    python scripts/sandbox_drive.py              # list the scenarios
    python scripts/sandbox_drive.py --run all    # or --run ido_lift,menu_two
"""
import re, sys, time
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from sandbox_chat import PERSONAS, contact, cw

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def persona(label):
    return next(k for k, (l, _) in PERSONAS.items() if l == label)

SCENARIOS = {
    "menu_two":   ("לא מוכר", ["שלום"],                                  [r"במה אפשר לעזור"], [r"לדבר עם נציג"]),
    "ido_lift":   ("עידו",    ["המעלית תקועה בקומה 3", "כן"],             [r"בר כוכבא 23", r"SBX-\d+"], [r"באיזה בניין", r"איזו דירה"]),
    "unknown":    ("לא מוכר", ["נשרפה נורה בלובי"],                       [r"בניין|כתובת"], []),
    "rep_typed":  ("עידו",    ["אני רוצה לדבר עם נציג"],                  [r"\?"], []),
    "gas":        ("יריב",    ["יש ריח חזק של גז בחדר המדרגות"],          [r"SBX-\d+"], [r"תתקשר|תפתח חלון|101|102|103"]),
    "balance":    ("עידו",    ["כמה אני חייב?"],                           [r"שם|טלפון"], [r"\d{3,} ?₪|שקל"]),
}

def turn(key, conv, text, wait=45):
    before = len(cw("GET", "/contacts/%s/conversations/%s/messages" % (contact(key), conv)) or [])
    cw("POST", "/contacts/%s/conversations/%s/messages" % (contact(key), conv), {"content": text})
    deadline, last, quiet = time.time() + wait, before + 1, 0
    while time.time() < deadline:
        time.sleep(3)
        msgs = cw("GET", "/contacts/%s/conversations/%s/messages" % (contact(key), conv)) or []
        if len(msgs) > last:
            last, quiet = len(msgs), 0
        elif last > before + 1:
            quiet += 3
            if quiet >= 9:
                break
    msgs = sorted(cw("GET", "/contacts/%s/conversations/%s/messages" % (contact(key), conv)) or [], key=lambda m: m["id"])
    return [m.get("content") or "" for m in msgs[before + 1:] if m.get("message_type") == 1]

def run(name):
    label, lines, must, mustnt = SCENARIOS[name]
    key = persona(label)
    conv = cw("POST", "/contacts/%s/conversations" % contact(key), {})["id"]
    said = []
    print("== %s (as %s)" % (name, label))
    for line in lines:
        out = turn(key, conv, line)
        said += out
        print("  tenant:", line)
        for o in out: print("  bot:   ", o.replace("\n", " / "))
    text = "\n".join(said)
    fails = [r for r in must if not re.search(r, text)] + ["NOT " + r for r in mustnt if re.search(r, text)]
    print("  ->", "PASS" if not fails else "FAIL " + str(fails))
    return not fails

if __name__ == "__main__":
    if "--run" not in sys.argv:
        for k, v in SCENARIOS.items(): print(k, "as", v[0], "|", " / ".join(v[1]))
        sys.exit(0)
    names = list(SCENARIOS) if sys.argv[sys.argv.index("--run") + 1] == "all" else sys.argv[sys.argv.index("--run") + 1].split(",")
    ok = sum(run(n) for n in names)
    print("%d/%d scenarios pass" % (ok, len(names)))
```

- [ ] **Step 2: Get the owner's go.** Ask: "The acceptance run costs about $1 of OpenRouter: 6 scenarios, about 15 replies. Go?" Run only on a yes.

- [ ] **Step 3: Run it**

Run: `python scripts/sandbox_drive.py --run all`
Expected: `6/6 scenarios pass`. Read every transcript as well, since a regex pass is not a quality pass.

- [ ] **Step 4: Prove production was untouched**

Run: `python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json`
Expected: `live system unchanged`

- [ ] **Step 5: The owner's own chat**

Hand over `python scripts/sandbox_chat.py` and the link. Note what the owner finds.

- [ ] **Step 6: Briefing files and commit**

Update `docs/features/19-whatsapp-sandbox/feature.md` (Status), the feature 19 row in `docs/README.md`, `HANDOVER.md`, `CONTEXT.md` and `docs/WORKLOG.md`: the ids, the `.env` keys, how to run it, the results and how to delete it.

```bash
git add scripts/sandbox_drive.py docs/features/19-whatsapp-sandbox docs/README.md HANDOVER.md CONTEXT.md docs/WORKLOG.md
git commit -m "Feature 19: sandbox built and accepted; production fingerprint unchanged"
```

---

## Deleting the sandbox (for reference)

The steps, in order:
1. n8n: `DELETE /api/v1/workflows/<SANDBOX_N8N_BOT_ID>` and `<SANDBOX_N8N_HANDOVER_ID>`, and `DELETE /api/v1/credentials/<SANDBOX_N8N_CRED_ADMIN>` and `<SANDBOX_N8N_CRED_BOT>`.
2. Supabase: `DELETE /v1/projects/<ref>/functions/debt-tools-sandbox`.
3. Chatwoot: rails runner `Account.find(<SANDBOX_CW_ACCOUNT_ID>).destroy!` and `User.find_by(email: "sandbox-admin@homies-sandbox.test")&.destroy!`.
4. Remove the `SANDBOX_*` keys from `.env`.

Then `python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json` must still say `live system unchanged`.
