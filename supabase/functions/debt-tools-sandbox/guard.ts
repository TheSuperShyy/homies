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
 *     back gets the row it sent plus an id. A `requests` row gets a reference
 *     in the live shape, 999-9NNNNN-YY: the bot's reply guards only recognise
 *     \d{3}-\d{3,6}-\d{2}, and a serial from 900001 up can never match a real
 *     ticket (the highest real serial is about 29,000), so a lookup by it finds nothing.
 *     The serial is random, not counted: a counter restarts with every cold
 *     start, and the 27 Oct run gave two tickets the same number.
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
    if (table === "requests" && m === "POST") {
      const serial = 900001 + Math.floor(Math.random() * 99999);
      row.reference = `999-${serial}-${String(new Date().getUTCFullYear()).slice(-2)}`;
    }
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
