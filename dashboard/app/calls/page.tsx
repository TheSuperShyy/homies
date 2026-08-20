import { serverClient } from '@/lib/supabase-server';
import { Pager, pageFrom, pageRange, perParam, sizeFrom } from '@/components/pager';

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

// Tabs and pager both go through the shared component now, so the only local
// concern left is that switching view keeps the rows-per-page and drops the
// page number: page four of "all calls" is not page four of "no answer".
function tabHref(view: string, size: number, search?: string) {
  const q = new URLSearchParams();
  if (view !== 'all') q.set('view', view);
  const per = perParam(size);
  if (per) q.set('per', per);
  // A search survives a tab switch. Looking for "elevator" and then narrowing
  // to inbound is one thought, and losing the word halfway through it is the
  // kind of small betrayal that stops people using a filter at all.
  if (search) q.set('q', search);
  const s = q.toString();
  return s ? `/calls?${s}` : '/calls';
}

function Tabs({ view, size, search }: { view: string; size: number; search?: string }) {
  return (
    <nav className="tabs">
      {TABS.map(([key, label]) => (
        <a key={key} href={tabHref(key, size, search)} className={view === key ? 'on' : ''}>{label}</a>
      ))}
    </nav>
  );
}

/**
 * Search what was said.
 *
 * A stored transcript nobody can search is an archive, not a record: the call is
 * "in there somewhere" and finding the one where a resident mentioned the lift
 * means opening them one at a time.
 *
 * A GET form, so the search lands in the URL — linkable, bookmarkable, sendable
 * to somebody else, and it survives the back button. `q` is matched against the
 * transcript AND the summary: the summary is the sentence a person remembers,
 * the transcript is where the words actually are.
 */
function Search({ view, size, search }: { view: string; size: number; search?: string }) {
  return (
    <form method="get" action="/calls" className="search">
      {view !== 'all' && <input type="hidden" name="view" value={view} />}
      {perParam(size) && <input type="hidden" name="per" value={perParam(size)!} />}
      <input name="q" defaultValue={search ?? ''} dir="auto"
             placeholder="Search what was said - Hebrew or English" />
      <button type="submit">Search</button>
      {search && (
        <a href={tabHref(view, size)} className="muted" style={{ fontSize: 13 }}>clear</a>
      )}
    </form>
  );
}

// Newer/Older rather than Previous/Next: every view here is ordered newest
// first, and "previous" is ambiguous about which way that runs.
function CallPager({ view, page, size, total }: {
  view: string; page: number; size: number; total: number;
}) {
  return (
    <Pager basePath="/calls" page={page} size={size} total={total}
           params={{ view: view === 'all' ? undefined : view }}
           prev="Newer" next="Older" unit="rows" />
  );
}

function when(ts?: string | null) {
  return ts ? ts.slice(0, 16).replace('T', ' ') : '—';
}

async function NoAnswer({ page, size }: { page: number; size: number }) {
  const [from, to] = pageRange(page, size);
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
      <CallPager view="no_answer" page={page} size={size} total={count ?? 0} />
    </>
  );
}

async function LinksSent({ page, size }: { page: number; size: number }) {
  const [from, to] = pageRange(page, size);
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
      <CallPager view="links" page={page} size={size} total={count ?? 0} />
      <p className="muted" style={{ fontSize: 13 }}>
        &ldquo;sent&rdquo; means OXS confirmed the link went out — whether it was <em>paid</em> is
        only visible in OXS, so nothing here counts as money received.
      </p>
    </>
  );
}

async function CallList({ view, page, size, search }: {
  view: string; page: number; size: number; search?: string;
}) {
  const direction = view === 'inbound' || view === 'outbound' ? view : undefined;
  const [from, to] = pageRange(page, size);
  let q = serverClient()
    .from('interactions')
    .select('id,external_call_id,direction,caller_phone,summary,transcript,disposition,duration_seconds,latency_ms,started_at', { count: 'exact' })
    .eq('channel', 'voice');
  if (direction) q = q.eq('direction', direction);
  if (search) {
    // Strip the characters PostgREST reads as `or` syntax before they reach the
    // filter. A comma or a bracket typed into the box would otherwise come back
    // as a parse error instead of results, and somebody searching for
    // "255-1013-26, elevator" has done nothing wrong.
    const safe = search.replace(/[,()\\]/g, ' ').trim();
    if (safe) q = q.or(`transcript.ilike.%${safe}%,summary.ilike.%${safe}%`);
  }
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
            {search
              ? <>Nothing said in a call matches &ldquo;{search}&rdquo;.</>
              : direction ? `No ${direction} calls recorded yet.` : 'No calls recorded yet.'}
            <br />
            <span style={{ fontSize: 13 }}>
              {search
                ? 'Only calls with a transcript can match, and the oldest calls have none.'
                : 'End-of-call reports were wired on 8 Aug; rows appear here from the next call placed.'}
            </span>
          </div>
        )}
      </div>
      <CallPager view={view} page={page} size={size} total={count ?? 0} />
    </>
  );
}

export default async function Calls({
  searchParams,
}: { searchParams?: { view?: string; page?: string; per?: string; q?: string } }) {
  const view = searchParams?.view ?? 'all';
  const page = pageFrom(searchParams);
  const size = sizeFrom(searchParams);
  const search = searchParams?.q?.trim() || undefined;
  // The two outcome views read call_outcomes, which carries no transcript, so
  // the box there would be a search that silently does nothing. Shown only
  // where it actually searches something.
  const searchable = view !== 'no_answer' && view !== 'links';
  return (
    <>
      <h1>Calls</h1>
      <Tabs view={view} size={size} search={search} />
      {searchable && <Search view={view} size={size} search={search} />}
      {view === 'no_answer' ? <NoAnswer page={page} size={size} />
        : view === 'links' ? <LinksSent page={page} size={size} />
        : <CallList view={view} page={page} size={size} search={search} />}
    </>
  );
}
