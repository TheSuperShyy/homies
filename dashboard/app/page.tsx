import { serverClient } from '@/lib/supabase-server';

// Counts, not a chart library. Four numbers a manager can read in two seconds
// beat a dashboard that takes a second to render and a minute to interpret.
async function count(table: string, query = '') {
  const { count } = await serverClient()
    .from(table).select('*', { count: 'exact', head: true, ...(query ? {} : {}) })
    .or(query || 'id.not.is.null');
  return count ?? 0;
}

export default async function Overview() {
  const db = serverClient();
  const since = new Date(Date.now() - 7 * 864e5).toISOString();

  const [tickets, open, urgent, convos, calls, recent] = await Promise.all([
    db.from('requests').select('*', { count: 'exact', head: true }),
    db.from('requests').select('*', { count: 'exact', head: true }).in('status', ['open', 'in_progress']),
    db.from('requests').select('*', { count: 'exact', head: true }).in('urgency', ['high', 'emergency']).in('status', ['open', 'in_progress']),
    db.from('v_conversations').select('*'),
    db.from('interactions').select('*', { count: 'exact', head: true }).eq('channel', 'voice'),
    db.from('requests').select('reference,description,building,unit,urgency,status,opened_via,created_at')
      .gte('created_at', since).order('created_at', { ascending: false }).limit(8),
  ]);

  const cards = [
    ['Open tickets', open.count ?? 0],
    ['Urgent, open', urgent.count ?? 0],
    ['Tickets, all time', tickets.count ?? 0],
    ['Conversations', convos.data?.length ?? 0],
    ['Calls recorded', calls.count ?? 0],
  ] as const;

  return (
    <>
      <h1>Overview</h1>
      <div className="cards">
        {cards.map(([k, n]) => (
          <div className="card" key={k}>
            <div className="n">{n}</div>
            <div className="k">{k}</div>
          </div>
        ))}
      </div>

      <h2>Last 7 days</h2>
      <div className="panel">
        {recent.data?.length ? (
          <table>
            <thead><tr>
              <th>Reference</th><th>What</th><th>Where</th>
              <th>Urgency</th><th>Status</th><th>Via</th><th>Opened</th>
            </tr></thead>
            <tbody>
              {recent.data.map((r: any) => (
                <tr key={r.reference}>
                  <td className="mono">{r.reference}</td>
                  <td dir="auto">{r.description}</td>
                  <td dir="auto">{r.building}{r.unit ? ` · ${r.unit}` : ''}</td>
                  <td>{r.urgency}</td>
                  <td><span className={`pill ${r.status}`}>{r.status}</span></td>
                  <td className="muted">{r.opened_via}</td>
                  <td className="muted mono">{r.created_at.slice(0, 16).replace('T', ' ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <div className="empty">Nothing in the last 7 days.</div>}
      </div>
    </>
  );
}
