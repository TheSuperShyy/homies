import { serverClient } from '@/lib/supabase-server';
import { getLocale, translator, type T } from '@/lib/i18n';
import { IconAlert, IconInbox, IconOpenLink } from '@/components/icons';

// Where the importer runs. Chosen 20 Aug over a VPS cron and over porting the
// three Python importers into an Edge Function: the workflow already exists,
// already carries the Israel daylight-saving logic, and already knows the order
// the three imports have to run in. This page is the window onto it, not a
// second copy of it.
const REPO = 'TheSuperShyy/homies';
const WORKFLOW = 'oxs-sync.yml';

type Run = {
  id: number;
  status: string;
  conclusion: string | null;
  created_at: string;
  updated_at: string;
  event: string;
  html_url: string;
};

/**
 * The last few runs, straight from GitHub.
 *
 * No token: the repository is public, so its Actions history is public with it.
 * That is the reason this page works the moment it deploys — the Run now button
 * below needs a credential, the history does not, and a status page that only
 * works once somebody has issued a PAT is a status page nobody sees.
 *
 * `no-store` because a cached answer here is worse than none: the whole point
 * is to say whether the import ran in the last few hours.
 */
async function runs(): Promise<{ list: Run[]; error?: string }> {
  try {
    const r = await fetch(
      `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?per_page=20`,
      { cache: 'no-store', headers: { Accept: 'application/vnd.github+json' } },
    );
    if (!r.ok) return { list: [], error: `GitHub replied ${r.status}` };
    const j = await r.json();
    return { list: (j.workflow_runs ?? []) as Run[] };
  } catch (e: any) {
    return { list: [], error: e?.message ?? 'could not reach GitHub' };
  }
}

function ago(iso: string) {
  const mins = Math.round((Date.now() - Date.parse(iso)) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  if (h < 48) return `${h} hour${h === 1 ? '' : 's'} ago`;
  return `${Math.round(h / 24)} days ago`;
}

function took(a: string, b: string) {
  const s = Math.round((Date.parse(b) - Date.parse(a)) / 1000);
  return s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;
}

/**
 * A run that finished in seconds did not import anything.
 *
 * GitHub's cron is UTC and has no daylight saving, so the workflow is scheduled
 * four times a day and exits immediately on the two that are the wrong hour in
 * Jerusalem. Those exit `success` in about ten seconds. Reporting them as
 * successful imports would be the most misleading thing this page could do —
 * it would show green all day while nothing had come in since Tuesday.
 *
 * WHY THE DURATION IS TRUSTWORTHY AGAIN. It was not, between 20 and 24 Aug.
 * The guard was a step inside the one job that held the concurrency lock, so a
 * skipped twin sat in the queue for the whole of the real run before exiting in
 * three seconds — and GitHub counts queue time in `created_at`..`updated_at`,
 * which is all this page can see. A 45-minute run that concluded `success` and
 * imported nothing therefore read as a real import here. The guard now lives in
 * its own job outside the lock, so a twin never queues and its duration is its
 * own again.
 */
function realImport(r: Run) {
  return r.conclusion === 'success'
    && (Date.parse(r.updated_at) - Date.parse(r.created_at)) > 60_000;
}

/**
 * Anything that is not a completed success or a deliberate skip.
 *
 * `failure` is not the only way this workflow ends badly, and for two days it
 * was not the way it ended at all: the job kept exceeding its time limit
 * mid-import, which GitHub concludes as `cancelled`. This page looked only for
 * `failure`, so the banner below never fired while the import was dying twice a
 * day. Every other terminal conclusion is treated as a failure on purpose —
 * an unknown outcome on a job that writes to the database is not good news.
 */
function failed(r: Run) {
  return r.status === 'completed' && r.conclusion !== 'success';
}

/**
 * How old the newest row in a table is, coloured when that is too old.
 *
 * The import runs twice a day, so 26 hours means at least two runs have come
 * and gone without touching this table. That is the line the page was missing:
 * a count of 178 looks identical whether it landed last night or on 11 August.
 */
function Freshness({ iso, line, t }: {
  iso?: string | null; line: 'sync.newestAdded' | 'sync.refreshed'; t: T;
}) {
  if (!iso) return <span className="sub">{t('sync.never')}</span>;
  const old = Date.now() - Date.parse(iso) > 26 * 3600_000;
  return (
    <span className="sub" style={{ color: old ? 'var(--review)' : undefined }}>
      {t(line, { ago: ago(iso) })}
    </span>
  );
}

export default async function Sync() {
  const db = serverClient();
  const t = translator(getLocale());

  // A COUNT ON ITS OWN CANNOT GO STALE VISIBLY.
  //
  // These three numbers sat unchanged for a fortnight while the page reported
  // healthy: residents were current, arrears were 13 days old and requests 12,
  // and nothing on the screen said so. The newest row in each table is the one
  // fact that would have shown it, so it is now printed under every count.
  // `charges` and `requests` carry `updated_at`, which a nightly re-import
  // touches even when the amount has not changed; `residents` has only
  // `created_at`, so its line says "newest added" and means exactly that.
  const [{ list, error }, residents, charges, requests, newRes, newChg, newReq] =
    await Promise.all([
      runs(),
      db.from('residents').select('id', { count: 'exact', head: true }).eq('source', 'oxs'),
      db.from('charges').select('id', { count: 'exact', head: true }).eq('source', 'oxs'),
      db.from('requests').select('id', { count: 'exact', head: true }).eq('opened_via', 'oxs'),
      db.from('residents').select('created_at').eq('source', 'oxs')
        .order('created_at', { ascending: false }).limit(1).maybeSingle(),
      db.from('charges').select('updated_at').eq('source', 'oxs')
        .order('updated_at', { ascending: false }).limit(1).maybeSingle(),
      db.from('requests').select('updated_at').eq('opened_via', 'oxs')
        .order('updated_at', { ascending: false }).limit(1).maybeSingle(),
    ]);

  const lastReal = list.find(realImport);
  const lastFail = list.find(failed);
  const running = list.find((r) => r.status !== 'completed');

  // THE WRONG-HOUR TWINS ARE NOT LISTED.
  //
  // GitHub's cron is UTC and has no daylight saving, so this workflow is
  // scheduled at both possible Israel offsets and the wrong one exits in
  // seconds. That is by design, twice a day, for ever — which made half of
  // "Recent runs" a standing report about the scheduler rather than news about
  // the import, and a reader scanning for the last real import had to skip
  // every other row to find one.
  //
  // Only the table hides them. `lastReal`, `lastFail` and `running` above all
  // read the unfiltered list, so nothing that drives a banner changes. A failed
  // run is never hidden either: `skippedTwin` requires conclusion `success`.
  // The footnote says how many went, because a list that drops rows has to
  // admit it.
  const skippedTwin = (r: Run) => r.conclusion === 'success' && !realImport(r);
  const shown = list.filter((r) => !skippedTwin(r));
  const hidden = list.length - shown.length;
  const token = Boolean(process.env.GITHUB_DISPATCH_TOKEN);

  return (
    <>
      <div className="pagehead">
        <h1>{t('sync.title')}</h1>
        <p>{t('sync.blurb')}</p>
      </div>

      <div className="cards" style={{ marginBottom: 18 }}>
        <div className={`card ${running ? 'is-progress' : lastReal ? 'is-done' : 'is-urgent'}`}>
          <div className="n" style={{ fontSize: 17 }}>
            {running ? t('sync.runningNow') : lastReal ? ago(lastReal.updated_at) : t('sync.never')}
          </div>
          <div className="k">{t('sync.lastReal')}</div>
          {!running && lastReal && (
            <span className="sub">{t('sync.tookLabel', { d: took(lastReal.created_at, lastReal.updated_at) })}</span>
          )}
        </div>
        <div className="card">
          <div className="n">{residents.count ?? '—'}</div>
          <div className="k">{t('sync.residents')}</div>
          <Freshness iso={newRes.data?.created_at} line="sync.newestAdded" t={t} />
        </div>
        <div className="card">
          <div className="n">{charges.count ?? '—'}</div>
          <div className="k">{t('sync.arrears')}</div>
          <Freshness iso={newChg.data?.updated_at} line="sync.refreshed" t={t} />
        </div>
        <div className="card">
          <div className="n">{requests.count ?? '—'}</div>
          <div className="k">{t('sync.requests')}</div>
          <Freshness iso={newReq.data?.updated_at} line="sync.refreshed" t={t} />
        </div>
      </div>

      {!lastReal && !running && (
        <div className="notice bad">
          <IconAlert />
          <span>
            <strong>{t('sync.noneImported')}</strong>{' '}
            <span className="muted">{t('sync.noneWhy')}</span>{' '}
            {list[0] && (
              <a href={list[0].html_url} style={{ color: 'var(--accent)' }}>
                {t('sync.openLast')}
              </a>
            )}
          </span>
        </div>
      )}

      {lastFail && (!lastReal || Date.parse(lastFail.created_at) > Date.parse(lastReal.updated_at)) && (
        <div className="notice bad">
          <IconAlert />
          <span>
            <strong>{t('sync.lastEnded', { how: lastFail.conclusion ?? '—' })}</strong>{' '}
            <span className="muted">
              {lastReal
                ? t('sync.nothingSince', { ago: ago(lastReal.updated_at) })
                : t('sync.nothingFrom')}
            </span>{' '}
            <a href={lastFail.html_url} style={{ color: 'var(--accent)' }}>{t('sync.seeWhy')}</a>
          </span>
        </div>
      )}

      <h2>{t('sync.runNow')}</h2>
      <div className="panel" style={{ padding: 14, marginBottom: 18 }}>
        {token ? (
          // A GET form, so no client JavaScript ships for one button. The route
          // handler dispatches and redirects straight back here.
          <form method="post" action="/sync/run" className="search" style={{ margin: 0 }}>
            <button className="btn-sm" type="submit" disabled={Boolean(running)}>
              {running ? t('sync.running') : t('sync.runBtn')}
            </button>
            <label className="muted" style={{ fontSize: 13, display: 'flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" name="dry_run" value="true" defaultChecked />
              {t('sync.dryRun')}
            </label>
          </form>
        ) : (
          <div className="muted" style={{ fontSize: 13 }}>
            <strong style={{ color: 'var(--ink)' }}>{t('sync.notWiredT')}</strong>{' '}
            {t('sync.notWired')}
          </div>
        )}
      </div>

      <h2>{t('sync.recent')}</h2>
      <div className="panel">
        {error && <div className="empty">{error}</div>}
        {shown.length ? (
          <div className="scrollx">
          <table>
            <thead><tr>
              <th>{t('col.when')}</th><th>{t('sync.startedBy')}</th>
              <th>{t('sync.result')}</th><th>{t('sync.took')}</th><th></th>
            </tr></thead>
            <tbody>
              {shown.map((r) => ((
                  <tr key={r.id}>
                    <td className="muted mono" data-label={t('col.when')}>{ago(r.created_at)}</td>
                    <td className="muted" data-label={t('sync.startedBy')}>{r.event === 'schedule' ? t('sync.bySchedule') : t('sync.byHand')}</td>
                    <td data-label={t('sync.result')}>
                      {r.status !== 'completed'
                        ? <span className="pill in_progress">{t('sync.stateRunning')}</span>
                        : r.conclusion === 'success'
                          ? <span className="pill resolved">{t('sync.stateDone')}</span>
                          : <span className="pill needs_review">{r.conclusion}</span>}
                    </td>
                    <td className="mono num" data-label={t('sync.took')}>{r.status === 'completed' ? took(r.created_at, r.updated_at) : '—'}</td>
                    <td data-label=""><a className="btn-sm" href={r.html_url}><IconOpenLink />{t('sync.openLog')}</a></td>
                  </tr>
                )))}
            </tbody>
          </table>
          </div>
        ) : !error && (
          <div className="empty">
            <IconInbox />
            <div>{t('sync.empty')}</div>
          </div>
        )}
      </div>

      <p className="muted" style={{ fontSize: 13, marginBlockStart: 14 }}>
        {t('sync.footnote')}
        {hidden > 0 && <>{' '}{t('sync.hidden', { n: hidden })}</>}
      </p>
    </>
  );
}
