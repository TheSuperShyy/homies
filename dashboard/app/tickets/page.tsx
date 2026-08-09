import { serverClient } from '@/lib/supabase-server';

// `searchParams` rather than client-side state: a filtered view should be a URL
// somebody can send to a colleague.
export default async function Tickets({
  searchParams,
}: { searchParams: { status?: string } }) {
  const status = searchParams.status;
  let q = serverClient()
    .from('requests')
    .select('reference,description,building,unit,type,urgency,status,opened_via,created_at')
    .order('created_at', { ascending: false })
    .limit(200);
  if (status) q = q.eq('status', status);
  const { data, error } = await q;

  const tabs = ['', 'open', 'in_progress', 'needs_review', 'resolved'];

  return (
    <>
      <h1>Tickets</h1>
      <nav style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        {tabs.map((t) => (
          <a key={t || 'all'} href={t ? `/tickets?status=${t}` : '/tickets'}
             className="pill" style={{ opacity: (status ?? '') === t ? 1 : 0.55 }}>
            {t || 'all'}
          </a>
        ))}
      </nav>
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <table>
            <thead><tr>
              <th>Reference</th><th>What</th><th>Where</th><th>Type</th>
              <th>Urgency</th><th>Status</th><th>Via</th><th>Opened</th>
            </tr></thead>
            <tbody>
              {data.map((r: any) => (
                <tr key={r.reference}>
                  <td className="mono">{r.reference}</td>
                  <td dir="auto">{r.description}</td>
                  <td dir="auto">{r.building}{r.unit ? ` · ${r.unit}` : ''}</td>
                  <td className="muted">{r.type}</td>
                  <td>{r.urgency}</td>
                  <td><span className={`pill ${r.status}`}>{r.status}</span></td>
                  <td className="muted">{r.opened_via}</td>
                  <td className="muted mono">{r.created_at.slice(0, 16).replace('T', ' ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : !error && <div className="empty">No tickets{status ? ` with status ${status}` : ''}.</div>}
      </div>
    </>
  );
}
