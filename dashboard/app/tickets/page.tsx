import { revalidatePath } from 'next/cache';
import { serverClient } from '@/lib/supabase-server';
import { Pager, pageFrom, pageRange, perParam, sizeFrom } from '@/components/pager';

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
}: { searchParams: { status?: string; page?: string; per?: string } }) {
  const status = searchParams.status;
  const page = pageFrom(searchParams);
  const size = sizeFrom(searchParams);
  const [from, to] = pageRange(page, size);
  let q = serverClient()
    .from('requests')
    .select('reference,description,building,unit,type,urgency,status,opened_via,created_at,reported_by_phone',
            { count: 'exact' });
  if (status) q = q.eq('status', status);
  const { data, error, count } = await q
    .order('created_at', { ascending: false })
    .range(from, to);

  const tabs = ['', ...STATUSES];

  // The chosen size survives a change of tab. Picking 50 and then filtering to
  // "open" should not quietly hand back ten rows.
  const per = perParam(size);
  const tabHref = (t: string) => {
    const q = new URLSearchParams();
    if (t) q.set('status', t);
    if (per) q.set('per', per);
    const s = q.toString();
    return s ? `/tickets?${s}` : '/tickets';
  };

  return (
    <>
      <h1>Tickets</h1>
      <nav style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        {tabs.map((t) => (
          <a key={t || 'all'} href={tabHref(t)}
             className="pill" style={{ opacity: (status ?? '') === t ? 1 : 0.55 }}>
            {t || 'all'}
          </a>
        ))}
      </nav>
      <Pager page={page} size={size} total={count ?? 0} basePath="/tickets"
             params={{ status }} unit="tickets" />
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <table>
            <thead><tr>
              <th>Reference</th><th>What</th><th>Where</th><th>Caller</th><th>Type</th>
              <th>Urgency</th><th>Status</th><th>Via</th><th>Opened</th>
            </tr></thead>
            <tbody>
              {data.map((r: any) => (
                <tr key={r.reference}>
                  <td className="mono">{r.reference}</td>
                  <td dir="auto">{r.description}</td>
                  <td dir="auto">{r.building}{r.unit ? ` · ${r.unit}` : ''}</td>
                  {/* The number the call came from, kept since 19 Aug. It is
                      the only thing on an inbound ticket that cannot be
                      mis-heard, and on a needs_review row where the audio
                      failed it is often the only way back to the person. */}
                  <td className="mono">{r.reported_by_phone ?? <span className="muted">—</span>}</td>
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
    </>
  );
}
