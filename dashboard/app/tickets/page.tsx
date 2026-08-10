import { revalidatePath } from 'next/cache';
import { serverClient } from '@/lib/supabase-server';
import { Pager, pageFrom, pageRange } from '@/components/pager';

// The four values the check constraint on requests.status accepts. The list is
// duplicated from the schema on purpose: the server action validates against
// it before touching the database, so a forged form posts a clean error here
// rather than a Postgres constraint failure.
const STATUSES = ['open', 'in_progress', 'resolved', 'cancelled'];

// A server action rather than a route handler: the form posts here with no
// client JS, and the anon key is all it carries — migration 011 grants that
// role UPDATE on the status column and nothing else, so even a hand-crafted
// request through this action cannot rewrite a description or a reference.
async function updateStatus(formData: FormData) {
  'use server';
  const reference = String(formData.get('reference') ?? '');
  const status = String(formData.get('status') ?? '');
  if (!reference || !STATUSES.includes(status)) return;
  await serverClient().from('requests').update({ status }).eq('reference', reference);
  revalidatePath('/tickets');
}

// `searchParams` rather than client-side state: a filtered view should be a URL
// somebody can send to a colleague.
export default async function Tickets({
  searchParams,
}: { searchParams: { status?: string; page?: string } }) {
  const status = searchParams.status;
  const page = pageFrom(searchParams);
  const [from, to] = pageRange(page);
  let q = serverClient()
    .from('requests')
    .select('reference,description,building,unit,type,urgency,status,opened_via,created_at',
            { count: 'exact' });
  if (status) q = q.eq('status', status);
  const { data, error, count } = await q
    .order('created_at', { ascending: false })
    .range(from, to);

  const tabs = ['', ...STATUSES];

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
                  <td>
                    <form action={updateStatus} className="status-edit">
                      <input type="hidden" name="reference" value={r.reference} />
                      <select name="status" defaultValue={r.status}
                              className={`pill ${r.status}`}>
                        {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                      <button type="submit" className="pill">save</button>
                    </form>
                  </td>
                  <td className="muted">{r.opened_via}</td>
                  <td className="muted mono">{r.created_at.slice(0, 16).replace('T', ' ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : !error && <div className="empty">No tickets{status ? ` with status ${status}` : ''}.</div>}
      </div>
      <Pager page={page} total={count ?? 0} basePath="/tickets"
             params={{ status }} unit="tickets" />
    </>
  );
}
