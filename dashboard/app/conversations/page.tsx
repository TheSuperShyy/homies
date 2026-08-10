import { serverClient } from '@/lib/supabase-server';
import { Pager, pageFrom, pageRange } from '@/components/pager';

export default async function Conversations({
  searchParams,
}: { searchParams?: { page?: string } }) {
  const page = pageFrom(searchParams);
  const [from, to] = pageRange(page);
  const { data, error, count } = await serverClient()
    .from('v_conversations').select('*', { count: 'exact' })
    .order('last_message_at', { ascending: false }).range(from, to);

  return (
    <>
      <h1>Conversations</h1>
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <table>
            <thead><tr>
              <th>Who</th><th>Last message</th><th>Messages</th>
              <th>Lang</th><th>Human</th><th>Last activity</th>
            </tr></thead>
            <tbody>
              {data.map((c: any) => (
                <tr key={c.phone}>
                  <td>
                    <a href={`/conversations/${encodeURIComponent(c.phone)}`}>
                      {/* A name when the phone matches a resident, the number
                          when it does not. An unmatched number is a signal, not
                          a blank: it means somebody outside the imported list
                          is writing in. */}
                      {c.full_name ?? <span className="mono">{c.phone}</span>}
                      {c.building && <div className="muted" dir="auto">{c.building}{c.unit ? ` · ${c.unit}` : ''}</div>}
                    </a>
                  </td>
                  <td dir="auto">{c.last_message}</td>
                  <td className="mono">{c.message_count}<span className="muted"> / {c.from_resident} in</span></td>
                  <td className="muted">{c.lang ?? '—'}</td>
                  <td>{c.touched_by_human ? 'yes' : <span className="muted">bot only</span>}</td>
                  <td className="muted mono">{c.last_message_at?.slice(0, 16).replace('T', ' ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : !error && <div className="empty">No conversations yet.</div>}
      </div>
      <Pager page={page} total={count ?? 0} basePath="/conversations"
             unit="conversations" />
    </>
  );
}
