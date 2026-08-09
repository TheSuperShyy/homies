import { serverClient } from '@/lib/supabase-server';

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

  return (
    <>
      <h1>Call</h1>
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
        <div className="transcript" dir="auto">
          {c.transcript ?? <span className="muted">No transcript on this call.</span>}
        </div>
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
