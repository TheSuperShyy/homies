import { serverClient } from '@/lib/supabase-server';
import { PAGE_SIZE } from '@/components/pager';

// One page, four views, state in the URL. The two extra views answer the two
// questions ops actually asks after an outbound day: who never picked up, and
// who was sent a link.
const TABS = [
  ['all', 'All calls'],
  ['inbound', 'Inbound'],
  ['outbound', 'Outbound'],
  ['no_answer', 'No answer'],
  ['links', 'Links sent'],
] as const;

function href(view: string, page: number) {
  const q = new URLSearchParams();
  if (view !== 'all') q.set('view', view);
  if (page > 1) q.set('page', String(page));
  const s = q.toString();
  return s ? `/calls?${s}` : '/calls';
}

function Tabs({ view }: { view: string }) {
  return (
    <nav className="tabs">
      {TABS.map(([key, label]) => (
        <a key={key} href={href(key, 1)} className={view === key ? 'on' : ''}>{label}</a>
      ))}
    </nav>
  );
}

// Pagination is offset-based over a created_at-descending order. New rows
// arriving between clicks shift the window slightly; for a review dashboard
// that beats cursor bookkeeping.
function Pager({ view, page, total }: { view: string; page: number; total: number }) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages <= 1) return null;
  return (
    <div className="pager">
      {page > 1
        ? <a href={href(view, page - 1)}>&larr; Newer</a>
        : <span className="muted">&larr; Newer</span>}
      <span className="muted mono">page {page} of {pages} · {total} rows</span>
      {page < pages
        ? <a href={href(view, page + 1)}>Older &rarr;</a>
        : <span className="muted">Older &rarr;</span>}
    </div>
  );
}

function when(ts?: string | null) {
  return ts ? ts.slice(0, 16).replace('T', ' ') : '—';
}

function range(page: number): [number, number] {
  const from = (page - 1) * PAGE_SIZE;
  return [from, from + PAGE_SIZE - 1];
}

async function NoAnswer({ page }: { page: number }) {
  const [from, to] = range(page);
  const { data, error, count } = await serverClient()
    .from('call_outcomes')
    .select('id,attempt,created_at,residents(full_name,phone,building,unit)', { count: 'exact' })
    .eq('outcome', 'no_answer')
    .order('created_at', { ascending: false })
    .range(from, to);

  return (
    <>
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <table>
            <thead><tr>
              <th>When</th><th>Resident</th><th>Phone</th><th>Building</th><th>Unit</th><th>Attempt</th>
            </tr></thead>
            <tbody>
              {data.map((r: any) => (
                <tr key={r.id}>
                  <td className="muted mono">{when(r.created_at)}</td>
                  <td dir="auto">{r.residents?.full_name ?? <span className="muted">unknown</span>}</td>
                  <td className="mono">{r.residents?.phone ?? '—'}</td>
                  <td dir="auto">{r.residents?.building ?? '—'}</td>
                  <td className="mono">{r.residents?.unit ?? '—'}</td>
                  <td className="mono">{r.attempt ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : !error && <div className="empty">Nobody has gone unanswered yet.</div>}
      </div>
      <Pager view="no_answer" page={page} total={count ?? 0} />
    </>
  );
}

async function LinksSent({ page }: { page: number }) {
  const [from, to] = range(page);
  const { data, error, count } = await serverClient()
    .from('payment_links')
    .select('id,amount,period,status,created_at,residents(full_name,phone,building,unit)', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range(from, to);

  return (
    <>
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <table>
            <thead><tr>
              <th>When</th><th>Resident</th><th>Phone</th><th>Building</th><th>Amount</th><th>Period</th><th>Status</th>
            </tr></thead>
            <tbody>
              {data.map((r: any) => (
                <tr key={r.id}>
                  <td className="muted mono">{when(r.created_at)}</td>
                  <td dir="auto">{r.residents?.full_name ?? <span className="muted">unknown</span>}</td>
                  <td className="mono">{r.residents?.phone ?? '—'}</td>
                  <td dir="auto">{r.residents?.building ?? '—'}</td>
                  <td className="mono">₪{Number(r.amount).toLocaleString()}</td>
                  <td className="mono">{r.period?.slice(0, 7) ?? '—'}</td>
                  <td><span className={`pill ${r.status === 'sent' ? 'resolved' : r.status === 'failed' ? 'needs_review' : 'open'}`}>{r.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : !error && <div className="empty">No payment links sent yet.</div>}
      </div>
      <Pager view="links" page={page} total={count ?? 0} />
      <p className="muted" style={{ fontSize: 13 }}>
        &ldquo;sent&rdquo; means OXS confirmed the link went out — whether it was <em>paid</em> is
        only visible in OXS, so nothing here counts as money received.
      </p>
    </>
  );
}

async function CallList({ view, page }: { view: string; page: number }) {
  const direction = view === 'inbound' || view === 'outbound' ? view : undefined;
  const [from, to] = range(page);
  let q = serverClient()
    .from('interactions')
    .select('id,external_call_id,direction,caller_phone,summary,transcript,disposition,duration_seconds,latency_ms,started_at', { count: 'exact' })
    .eq('channel', 'voice');
  if (direction) q = q.eq('direction', direction);
  const { data, error, count } = await q.order('started_at', { ascending: false }).range(from, to);

  return (
    <>
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
                  <td className="muted mono">{when(c.started_at)}</td>
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
            {direction ? `No ${direction} calls recorded yet.` : 'No calls recorded yet.'}<br />
            <span style={{ fontSize: 13 }}>
              End-of-call reports were wired on 8 Aug; rows appear here from the next call placed.
            </span>
          </div>
        )}
      </div>
      <Pager view={view} page={page} total={count ?? 0} />
    </>
  );
}

export default async function Calls({ searchParams }: { searchParams?: { view?: string; page?: string } }) {
  const view = searchParams?.view ?? 'all';
  const page = Math.max(1, parseInt(searchParams?.page ?? '1', 10) || 1);
  return (
    <>
      <h1>Calls</h1>
      <Tabs view={view} />
      {view === 'no_answer' ? <NoAnswer page={page} />
        : view === 'links' ? <LinksSent page={page} />
        : <CallList view={view} page={page} />}
    </>
  );
}
