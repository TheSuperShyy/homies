import { NextResponse } from 'next/server';

// Typed chat with the voice agents — same brain, no audio.
//
// Vapi's hosted Chat API needs a card on file this org does not have (402,
// checked 2 Sep), so the loop Vapi would run is run here instead: the system
// prompt and tool definitions are read off the LIVE assistant — what a caller
// reaches, not what the repo says — the model is the same one the assistant
// runs on Vapi, and tool calls go to the real Edge Function, so a typed
// conversation opens a real ticket with a real reference number. This is the
// prompt_chat.py engine grown up: real tools instead of mocks.
//
// What a typed chat does NOT do: no end-of-call report (nothing lands on the
// Calls page), and a ticket it opens says opened_via "voice" — channel() keys
// off the call id and a chat id is not "wa:". Known, accepted for now.
//
// The route holds three secrets the browser must never see: the Vapi private
// key (reads the assistant), the OpenRouter key (pays for the model), and the
// tool secret (authorises the Edge Function). All server-side env.

const MODEL = 'openai/gpt-4.1-mini'; // what both assistants run on Vapi
const MAX_TOOL_ROUNDS = 6;           // same ceiling as prompt_probe.turn()

const ASSISTANTS: Record<string, string | undefined> = {
  intake: process.env.NEXT_PUBLIC_VAPI_INTAKE_ASSISTANT_ID,
  debt: process.env.NEXT_PUBLIC_VAPI_DEBT_ASSISTANT_ID,
};

type CacheEntry = { at: number; prompt: string; first: string; tools: any[] };
const cache = new Map<string, CacheEntry>();
const CACHE_MS = 5 * 60 * 1000;

async function assistantConfig(id: string): Promise<CacheEntry> {
  const hit = cache.get(id);
  if (hit && Date.now() - hit.at < CACHE_MS) return hit;
  const res = await fetch(`https://api.vapi.ai/assistant/${id}`, {
    headers: { Authorization: `Bearer ${process.env.VAPI_PRIVATE_KEY}` },
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`Vapi ${res.status}`);
  const a = await res.json();
  const entry: CacheEntry = {
    at: Date.now(),
    prompt: (a?.model?.messages ?? [])
      .filter((m: any) => m?.role === 'system')
      .map((m: any) => m?.content ?? '')
      .join(''),
    first: a?.firstMessage ?? '',
    // Only function tools reach the model; the filter mirrors prompt_probe.
    tools: (a?.model?.tools ?? [])
      .filter((t: any) => t?.function)
      .map((t: any) => ({ type: 'function', function: t.function })),
  };
  cache.set(id, entry);
  return entry;
}

function resolve(text: string, vars: Record<string, string>): string {
  return text.replace(/\{\{(\w+)\}\}/g, (_, k) => vars[k] ?? '');
}

/** The Edge Function answers exactly what it answers Vapi mid-call. */
async function runTools(
  calls: any[], chatId: string, assistantId: string, vars: Record<string, string>,
): Promise<{ role: 'tool'; tool_call_id: string; content: string }[]> {
  const url = `${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/debt-tools`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-homies-secret': process.env.TOOL_SECRET ?? '',
    },
    body: JSON.stringify({
      message: {
        type: 'tool-calls',
        toolCalls: calls.map(c => ({
          id: c.id,
          function: { name: c.function?.name, arguments: c.function?.arguments },
        })),
        call: { id: chatId, type: 'webCall', assistantId, assistantOverrides: { variableValues: vars } },
      },
    }),
    cache: 'no-store',
  });
  const body = await res.json().catch(() => ({}));
  const byId = new Map<string, string>(
    (body?.results ?? []).map((r: any) => [String(r.toolCallId), String(r.result ?? '')]),
  );
  return calls.map(c => ({
    role: 'tool' as const,
    tool_call_id: c.id,
    content: byId.get(c.id) ?? JSON.stringify({ ok: false, error: `tools ${res.status}` }),
  }));
}

export async function POST(req: Request) {
  if (!process.env.VAPI_PRIVATE_KEY || !process.env.OPENROUTER_API_KEY || !process.env.TOOL_SECRET) {
    return NextResponse.json({ error: 'not configured' }, { status: 503 });
  }

  let body: any;
  try { body = await req.json(); } catch {
    return NextResponse.json({ error: 'bad json' }, { status: 400 });
  }

  const assistantId = ASSISTANTS[String(body?.agent)];
  const chatId = String(body?.chatId ?? '');
  const history = Array.isArray(body?.messages) ? body.messages : [];
  const vars: Record<string, string> =
    body?.variables && typeof body.variables === 'object' ? body.variables : {};
  if (!assistantId || !/^chat-[\w-]{8,64}$/.test(chatId) || history.length === 0) {
    return NextResponse.json({ error: 'bad request' }, { status: 400 });
  }

  try {
    const cfg = await assistantConfig(assistantId);
    const first = resolve(cfg.first, vars);
    const messages: any[] = [
      { role: 'system', content: resolve(cfg.prompt, vars) },
      // The greeting opens the conversation for the model too — a probe run
      // without it scored an agent introducing itself mid-call.
      ...(first ? [{ role: 'assistant', content: first }] : []),
      ...history
        .slice(-40)
        .filter((m: any) => m?.role === 'user' || m?.role === 'assistant')
        .map((m: any) => ({ role: m.role, content: String(m.content ?? '').slice(0, 2000) })),
    ];

    const called: string[] = [];
    for (let i = 0; i < MAX_TOOL_ROUNDS; i++) {
      const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${process.env.OPENROUTER_API_KEY}`,
          'content-type': 'application/json',
        },
        body: JSON.stringify({
          model: MODEL, messages, temperature: 0.3,
          ...(cfg.tools.length ? { tools: cfg.tools } : {}),
        }),
        cache: 'no-store',
      });
      const out = await res.json().catch(() => ({}));
      const msg = out?.choices?.[0]?.message;
      if (!msg) return NextResponse.json({ error: 'model failed' }, { status: 502 });

      const calls = msg.tool_calls ?? [];
      messages.push({ role: msg.role, content: msg.content ?? '', ...(calls.length ? { tool_calls: calls } : {}) });
      if (!calls.length) {
        return NextResponse.json({ first, reply: msg.content ?? '', tools: called });
      }
      called.push(...calls.map((c: any) => c.function?.name ?? '?'));
      messages.push(...await runTools(calls, chatId, assistantId, vars));
    }
    return NextResponse.json({ error: 'tool loop did not settle' }, { status: 502 });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 200) }, { status: 502 });
  }
}
