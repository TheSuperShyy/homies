import { serverClient } from '@/lib/supabase-server';

/**
 * Split a Vapi transcript into turns.
 *
 * Vapi writes one speaker per line, prefixed `AI:` or `User:`, and wraps
 * nothing — a ninety-second answer is one very long line. Rendering that as a
 * monospace block (which is what this page did until 20 Aug) is technically
 * "viewable" and nobody could actually read it: no speaker separation, no
 * paragraphs, and Hebrew running right-to-left inside a left-aligned code font.
 *
 * A continuation line — one with no recognised prefix — belongs to the turn
 * above it rather than becoming a turn of its own. That happens whenever the
 * caller's speech contains a newline, and dropping those lines would silently
 * lose words from the record.
 */
function turns(raw: string): { who: 'bot' | 'resident'; text: string }[] {
  const out: { who: 'bot' | 'resident'; text: string }[] = [];
  for (const line of raw.split(/\r?\n/)) {
    const m = /^\s*(AI|Assistant|Bot|User|Customer|Human)\s*:\s*(.*)$/i.exec(line);
    if (m) {
      const who = /^(ai|assistant|bot)$/i.test(m[1]) ? 'bot' : 'resident';
      out.push({ who, text: m[2] });
    } else if (out.length && line.trim()) {
      out[out.length - 1].text += '\n' + line;
    }
  }
  return out.filter((t) => t.text.trim());
}

export default async function Call({ params }: { params: { id: string } }) {
  const { data: c, error } = await serverClient()
    .from('interactions').select('*').eq('id', params.id).maybeSingle();

  if (error || !c) return <div className="empty">{error?.message ?? 'Call not found.'}</div>;

  const facts: [string, any][] = [
    ['Started', c.started_at?.replace('T', ' ').slice(0, 19)],
    ['Direction', c.direction],
    ['Number', c.caller_phone],
    ['Length', c.duration_seconds ? `${c.duration_seconds}s` : null],
    ['Latency', c.latency_ms ? `${c.latency_ms}ms` : null],
    ['Outcome', c.disposition],
    ['Vapi call', c.external_call_id],
  ];

  const spoken = c.transcript ? turns(c.transcript) : [];

  return (
    <>
      <h1>Call</h1>
      <p style={{ margin: '-10px 0 18px' }}>
        <a href="/calls" className="muted" style={{ fontSize: 13 }}>&larr; All calls</a>
      </p>

      <div className="cards" style={{ marginBottom: 18 }}>
        {facts.filter(([, v]) => v).map(([k, v]) => (
          <div className="card" key={k}>
            <div className="k">{k}</div>
            <div className="mono" style={{ fontSize: 14 }}>{String(v)}</div>
          </div>
        ))}
      </div>

      {c.summary && (<><h2>Summary</h2>
        <div className="panel"><div className="transcript" dir="auto">{c.summary}</div></div></>)}

      {c.audio_url && (<><h2>Recording</h2>
        <div className="panel" style={{ padding: 14 }}>
          <audio controls src={c.audio_url} style={{ width: '100%' }} />
        </div></>)}

      <h2>Transcript</h2>
      <div className="panel">
        {/* Laid out as the conversation it was. The raw block is kept as the
            fallback rather than deleted: if Vapi changes its prefixes, an
            unparsed transcript still has to be readable, and a page that
            renders nothing would look like a call with nothing said on it. */}
        {spoken.length > 1 ? (
          <div className="thread">
            {spoken.map((t, i) => (
              <div key={i} className={`msg ${t.who}`} dir="auto">
                <div className="who">{t.who === 'bot' ? 'Michael' : 'Caller'}</div>
                {t.text}
              </div>
            ))}
          </div>
        ) : (
          <div className="transcript" dir="auto">
            {c.transcript ?? <span className="muted">No transcript on this call.</span>}
          </div>
        )}
      </div>

      {/* The tool calls are what the agent actually DID, as opposed to what it
          said it did — the distinction that cost a day of debugging on 8 Aug. */}
      {Array.isArray(c.tool_calls) && c.tool_calls.length > 0 && (
        <>
          <h2>Tools called</h2>
          <div className="panel">
            <div className="transcript">{JSON.stringify(c.tool_calls, null, 2)}</div>
          </div>
        </>
      )}
    </>
  );
}
