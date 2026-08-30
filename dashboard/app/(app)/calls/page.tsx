import { serverClient } from '@/lib/supabase-server';
import { Pager, pageFrom, pageRange, perParam, sizeFrom } from '@/components/pager';
import { getLocale, translator, when, type Locale, type T } from '@/lib/i18n';
import { IconInbox, IconSearch, IconOpenLink } from '@/components/icons';
import Link from 'next/link';

// One page, four views, state in the URL. The two extra views answer the two
// questions ops actually asks after an outbound day: who never picked up, and
// who was sent a link.
const TABS = [
  ['all', 'calls.all'],
  ['inbound', 'calls.inbound'],
  ['outbound', 'calls.outbound'],
  ['no_answer', 'calls.noAnswer'],
  ['links', 'calls.links'],
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

function Tabs({ view, size, search, t }: {
  view: string; size: number; search?: string; t: T;
}) {
  return (
    <nav className="seg" aria-label={t('calls.title')}>
      {TABS.map(([key, key2]) => (
        <Link key={key} href={tabHref(key, size, search)}
           aria-current={view === key ? 'true' : undefined}>{t(key2)}</Link>
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
function Search({ view, size, search, t }: {
  view: string; size: number; search?: string; t: T;
}) {
  return (
    <form method="get" action="/calls" className="search">
      {view !== 'all' && <input type="hidden" name="view" value={view} />}
      {perParam(size) && <input type="hidden" name="per" value={perParam(size)!} />}
      <input name="q" defaultValue={search ?? ''} dir="auto"
             aria-label={t('calls.search')} placeholder={t('calls.search')} />
      <button type="submit"><IconSearch /> {t('calls.searchBtn')}</button>
      {search && (
        <Link href={tabHref(view, size)} className="muted" style={{ fontSize: 13 }}>
          {t('calls.clear')}
        </Link>
      )}
    </form>
  );
}

// Newer/Older rather than Previous/Next: every view here is ordered newest
// first, and "previous" is ambiguous about which way that runs.
function CallPager({ view, page, size, total, t }: {
  view: string; page: number; size: number; total: number; t: T;
}) {
  return (
    <Pager basePath="/calls" page={page} size={size} total={total}
           params={{ view: view === 'all' ? undefined : view }}
           prev={t('calls.newer')} next={t('calls.older')} unit={t('calls.unit')} t={t} />
  );
}

async function NoAnswer({ page, size, t, locale }: {
  page: number; size: number; t: T; locale: Locale;
}) {
  const [from, to] = pageRange(page, size);
  const { data, error, count } = await serverClient()
    .from('call_outcomes')
    .select('id,attempt,created_at,residents(full_name,phone,building,unit)', { count: 'exact' })
    .eq('outcome', 'no_answer')
    .order('created_at', { ascending: false })
    .range(from, to);

  return (
    <>
      <CallPager view="no_answer" page={page} size={size} total={count ?? 0} t={t} />
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <div className="scrollx">
          <table>
            <thead><tr>
              <th>{t('col.when')}</th><th>{t('col.resident')}</th><th>{t('col.phone')}</th>
              <th>{t('col.building')}</th><th>{t('col.unit')}</th><th>{t('col.attempt')}</th>
            </tr></thead>
            <tbody>
              {data.map((r: any) => (
                <tr key={r.id}>
                  <td className="muted mono">{when(r.created_at, locale)}</td>
                  <td dir="auto">{r.residents?.full_name ?? <span className="muted">{t('calls.unknown')}</span>}</td>
                  <td className="mono">{r.residents?.phone ?? '—'}</td>
                  <td dir="auto">{r.residents?.building ?? '—'}</td>
                  <td className="mono">{r.residents?.unit ?? '—'}</td>
                  <td className="mono num">{r.attempt ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : !error && (
          <div className="empty">
            <IconInbox />
            <div>{t('calls.emptyNoAnswer')}</div>
          </div>
        )}
      </div>
    </>
  );
}

async function LinksSent({ page, size, t, locale }: {
  page: number; size: number; t: T; locale: Locale;
}) {
  const [from, to] = pageRange(page, size);
  const { data, error, count } = await serverClient()
    .from('payment_links')
    .select('id,amount,period,status,created_at,residents(full_name,phone,building,unit)', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range(from, to);

  return (
    <>
      <CallPager view="links" page={page} size={size} total={count ?? 0} t={t} />
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <div className="scrollx">
          <table>
            <thead><tr>
              <th>{t('col.when')}</th><th>{t('col.resident')}</th><th>{t('col.phone')}</th>
              <th>{t('col.building')}</th><th>{t('col.amount')}</th>
              <th>{t('col.period')}</th><th>{t('col.status')}</th>
            </tr></thead>
            <tbody>
              {data.map((r: any) => (
                <tr key={r.id}>
                  <td className="muted mono">{when(r.created_at, locale)}</td>
                  <td dir="auto">{r.residents?.full_name ?? <span className="muted">{t('calls.unknown')}</span>}</td>
                  <td className="mono">{r.residents?.phone ?? '—'}</td>
                  <td dir="auto">{r.residents?.building ?? '—'}</td>
                  <td className="mono num">₪{Number(r.amount).toLocaleString()}</td>
                  <td className="mono">{r.period?.slice(0, 7) ?? '—'}</td>
                  <td><span className={`pill ${r.status === 'sent' ? 'resolved' : r.status === 'failed' ? 'needs_review' : 'open'}`}>{r.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : !error && (
          <div className="empty">
            <IconInbox />
            <div>{t('calls.emptyLinks')}</div>
          </div>
        )}
      </div>
      <p className="muted" style={{ fontSize: 13, marginBlockStart: 10 }}>
        {t('calls.linksNote')}
      </p>
    </>
  );
}

async function CallList({ view, page, size, search, t, locale }: {
  view: string; page: number; size: number; search?: string; t: T; locale: Locale;
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
      <CallPager view={view} page={page} size={size} total={count ?? 0} t={t} />
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <div className="scrollx">
          <table>
            <thead><tr>
              <th>{t('col.when')}</th><th>{t('col.direction')}</th><th>{t('col.number')}</th>
              <th>{t('col.summary')}</th><th>{t('col.outcome')}</th>
              <th>{t('col.length')}</th><th>{t('col.latency')}</th><th></th>
            </tr></thead>
            <tbody>
              {data.map((c: any) => (
                <tr key={c.id}>
                  <td className="muted mono">{when(c.started_at, locale)}</td>
                  <td>{c.direction}</td>
                  <td className="mono">{c.caller_phone ?? '—'}</td>
                  <td dir="auto">{c.summary ?? <span className="muted">{t('calls.noSummary')}</span>}</td>
                  <td className="muted">{c.disposition ?? '—'}</td>
                  <td className="mono num">{c.duration_seconds ? `${c.duration_seconds}s` : '—'}</td>
                  {/* The <800ms target from the plan, visible per call rather
                      than as an average that hides the bad ones. */}
                  <td className="mono num" style={{ color: c.latency_ms > 800 ? 'var(--review)' : undefined }}>
                    {c.latency_ms ? `${c.latency_ms}ms` : '—'}
                  </td>
                  {/* Shown on every row, not only ones with a transcript: the
                      page also carries the recording, the outcome and the tools
                      the agent called, so there is something to see even on a
                      call that produced no words. */}
                  <td><Link className="btn-sm" href={`/calls/${c.id}`}>
                    <IconOpenLink />{t('calls.view')}
                  </Link></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : !error && (
          <div className="empty">
            <IconInbox />
            <div>{search
              ? t('calls.emptySearch', { q: search })
              : direction
                ? t('calls.emptyDirection', { direction: t(`calls.${direction}` as any) })
                : t('calls.emptyNone')}</div>
            <div style={{ fontSize: 13, marginBlockStart: 4 }}>
              {search ? t('calls.emptySearchHint') : t('calls.emptyHint')}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default async function Calls({
  searchParams,
}: { searchParams?: { view?: string; page?: string; per?: string; q?: string } }) {
  const view = searchParams?.view ?? 'all';
  const locale = getLocale();
  const t = translator(locale);
  const page = pageFrom(searchParams);
  const size = sizeFrom(searchParams);
  const search = searchParams?.q?.trim() || undefined;
  // The two outcome views read call_outcomes, which carries no transcript, so
  // the box there would be a search that silently does nothing. Shown only
  // where it actually searches something.
  const searchable = view !== 'no_answer' && view !== 'links';
  return (
    <>
      <div className="pagehead"><h1>{t('calls.title')}</h1></div>
      <Tabs view={view} size={size} search={search} t={t} />
      {searchable && <Search view={view} size={size} search={search} t={t} />}
      {view === 'no_answer' ? <NoAnswer page={page} size={size} t={t} locale={locale} />
        : view === 'links' ? <LinksSent page={page} size={size} t={t} locale={locale} />
        : <CallList view={view} page={page} size={size} search={search} t={t} locale={locale} />}
    </>
  );
}
