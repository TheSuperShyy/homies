import { serverClient } from '@/lib/supabase-server';

/**
 * Split a Vapi transcript into turns.
 *
 * Vapi writes one speaker per line, prefixed `AI:` or `User:`, and wraps
 * nothing — a ninety-second answer is one very long line. Rendering that as a
 * monospace block (which is what this page did until 20 Aug) is technically
 * "viewable" and nobody could actually read it: no speaker separation, no
 * paragraphs, and Hebrew running left-to-right inside a code font.
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

function secs(n?: number | null) {
  if (!n) return null;
  return n >= 60 ? `${Math.floor(n / 60)}m ${n % 60}s` : `${n}s`;
}

export default async function Call({ params }: { params: { id: string } }) {
  const { data: c, error } = await serverClient()
    .from('interactions').select('*').eq('id', params.id).maybeSingle();

  if (error || !c) return <div className="empty">{error?.message ?? 'Call not found.'}</div>;

  const spoken = c.transcript ? turns(c.transcript) : [];

  // Compact key/value rows, not the big number cards the overview uses. These
  // are reference details you glance at once — sizing them like headline
  // figures is what pushed the conversation itself below the fold.
  const facts: [string, any][] = [
    ['When', c.started_at?.replace('T', ' ').slice(0, 16)],
    ['Direction', c.direction],
    ['Number', c.caller_phone],
    ['Length', secs(c.duration_seconds)],
    ['Turns', spoken.length || null],
    ['Latency', c.latency_ms ? `${c.latency_ms}ms` : null],
    ['Outcome', c.disposition],
  ];

  return (
    <>
      <h1 style={{ marginBottom: 4 }}>Call</h1>
      <p style={{ margin: '0 0 16px' }}>
        <a href="/calls" className="muted" style={{ fontSize: 13 }}>&larr; All calls</a>
      </p>

      {/* Conversation first and widest; everything else beside it. Stacks to one
          column under 900px, and the sidebar goes first there so a phone still
          gets the facts before a two-minute transcript. */}
      <div className="callgrid">
        <div>
          <div className="panel">
            <div className="panelhead">
              <span>Conversation</span>
              {/* Said once, because the alternative was printing "Michael" and
                  "Caller" above all 22 bubbles — the same two words repeated
                  down the page, which is noise, not information. */}
              <span className="legend">
                <i className="dot resident" /> Caller
                <i className="dot bot" /> Michael
              </span>
            </div>

            {/* The raw block is kept as the fallback rather than deleted: if
                Vapi changes its prefixes, an unparsed transcript still has to be
                readable, and a page rendering nothing would look like a call
                where nothing was said. */}
            {spoken.length > 1 ? (
              <div className="thread scroll">
                {spoken.map((t, i) => (
                  <div key={i} className={`msg ${t.who}`} dir="auto">{t.text}</div>
                ))}
              </div>
            ) : (
              <div className="transcript" dir="auto">
                {c.transcript ?? <span className="muted">No transcript on this call.</span>}
              </div>
            )}
          </div>
        </div>

        <aside className="side">
          {c.summary && (
            <div className="panel">
              <div className="panelhead"><span>Summary</span></div>
              <div style={{ padding: '12px 14px', fontSize: 14 }} dir="auto">{c.summary}</div>
            </div>
          )}

          {c.audio_url && (
            <div className="panel">
              <div className="panelhead"><span>Recording</span></div>
              <div style={{ padding: 12 }}>
                <audio controls src={c.audio_url} style={{ width: '100%' }} />
                {/* Vapi deletes its own recordings after 14 days and nothing
                    copies them out yet, so an old call's player is a dead
                    control that looks like a broken page. Say which it is. */}
                <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
                  Vapi keeps recordings 14 days. Older calls play nothing.
                </div>
              </div>
            </div>
          )}

          <div className="panel">
            <div className="panelhead"><span>Details</span></div>
            <div className="rows">
              {facts.filter(([, v]) => v).map(([k, v]) => (
                <div className="row" key={k}>
                  <span className="muted">{k}</span>
                  <span className="mono">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* The tool calls are what the agent actually DID, as opposed to what
              it said it did — the distinction that cost a day of debugging on
              8 Aug. Collapsed, because it is JSON and it is long: the one
              section on this page that is read only when something is wrong. */}
          {Array.isArray(c.tool_calls) && c.tool_calls.length > 0 && (
            <details className="panel">
              <summary className="panelhead">
                <span>Tools called</span><span className="mono">{c.tool_calls.length}</span>
              </summary>
              <div className="transcript" style={{ fontSize: 12 }}>
                {JSON.stringify(c.tool_calls, null, 2)}
              </div>
            </details>
          )}

          {c.external_call_id && (
            <div className="muted mono" style={{ fontSize: 11, wordBreak: 'break-all' }}>
              {c.external_call_id}
            </div>
          )}
        </aside>
      </div>
    </>
  );
}
