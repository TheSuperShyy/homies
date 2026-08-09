import { serverClient } from '@/lib/supabase-server';

export default async function Calls() {
  const { data, error } = await serverClient()
    .from('interactions')
    .select('id,external_call_id,direction,caller_phone,summary,transcript,disposition,duration_seconds,latency_ms,started_at')
    .eq('channel', 'voice')
    .order('started_at', { ascending: false })
    .limit(200);

  return (
    <>
      <h1>Calls</h1>
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <table>
            <thead><tr>
              <th>When</th><th>Direction</th><th>Number</th><th>Summary</th>
              <th>Outcome</th><th>Length</th><th>Latency</th><th></th>
            </tr></thead>
            <tbody>
              {data.map((c: any) => (
                <tr key={c.id}>
                  <td className="muted mono">{c.started_at?.slice(0, 16).replace('T', ' ')}</td>
                  <td>{c.direction}</td>
                  <td className="mono">{c.caller_phone ?? '—'}</td>
                  <td dir="auto">{c.summary ?? <span className="muted">no summary</span>}</td>
                  <td className="muted">{c.disposition ?? '—'}</td>
                  <td className="mono">{c.duration_seconds ? `${c.duration_seconds}s` : '—'}</td>
                  {/* The <800ms target from the plan, visible per call rather
                      than as an average that hides the bad ones. */}
                  <td className="mono" style={{ color: c.latency_ms > 800 ? 'var(--review)' : undefined }}>
                    {c.latency_ms ? `${c.latency_ms}ms` : '—'}
                  </td>
                  <td>{c.transcript && <a href={`/calls/${c.id}`}>transcript</a>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : !error && (
          <div className="empty">
            No calls recorded yet.<br />
            <span style={{ fontSize: 13 }}>
              End-of-call reports were wired on 8 Aug; rows appear here from the next call placed.
            </span>
          </div>
        )}
      </div>
    </>
  );
}
