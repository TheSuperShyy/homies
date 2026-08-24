import { serverClient } from '@/lib/supabase-server';

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
      `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?per_page=8`,
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
function Freshness({ iso, verb }: { iso?: string | null; verb: string }) {
  if (!iso) return <div className="muted" style={{ fontSize: 12 }}>never</div>;
  const old = Date.now() - Date.parse(iso) > 26 * 3600_000;
  return (
    <div className="muted" style={{ fontSize: 12, color: old ? 'var(--review)' : undefined }}>
      {verb} {ago(iso)}
    </div>
  );
}

export default async function Sync() {
  const db = serverClient();

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
  const token = Boolean(process.env.GITHUB_DISPATCH_TOKEN);

  return (
    <>
      <h1 style={{ marginBottom: 4 }}>Import from OXS</h1>
      <p className="muted" style={{ margin: '0 0 18px', fontSize: 13 }}>
        Residents, arrears and maintenance requests, twice a day at midnight and
        3pm Israel time. OXS is read-only: nothing here ever writes back to it.
      </p>

      <div className="cards" style={{ marginBottom: 18 }}>
        <div className="card">
          <div className="k">Last real import</div>
          <div className="n" style={{ fontSize: 17 }}>
            {running ? 'running now' : lastReal ? ago(lastReal.updated_at) : 'never'}
          </div>
          {!running && lastReal && (
            <div className="muted" style={{ fontSize: 12 }}>took {took(lastReal.created_at, lastReal.updated_at)}</div>
          )}
        </div>
        <div className="card">
          <div className="k">Residents from OXS</div>
          <div className="n">{residents.count ?? '—'}</div>
          <Freshness iso={newRes.data?.created_at} verb="newest added" />
        </div>
        <div className="card">
          <div className="k">Arrears from OXS</div>
          <div className="n">{charges.count ?? '—'}</div>
          <Freshness iso={newChg.data?.updated_at} verb="last refreshed" />
        </div>
        <div className="card">
          <div className="k">Requests from OXS</div>
          <div className="n">{requests.count ?? '—'}</div>
          <Freshness iso={newReq.data?.updated_at} verb="last refreshed" />
        </div>
      </div>

      {!lastReal && !running && (
        <div className="panel" style={{ padding: 14, marginBottom: 18 }}>
          <strong style={{ color: 'var(--review)' }}>
            No run in this history imported anything.
          </strong>{' '}
          <span className="muted">
            Every run listed below either skipped as the wrong half of a
            daylight-saving pair, or started and did not finish. The rows above
            arrived from earlier runs — check the newest-row lines to see how
            long ago.
          </span>{' '}
          {list[0] && (
            <a href={list[0].html_url} className="mono" style={{ color: 'var(--accent)' }}>
              open the last log
            </a>
          )}
        </div>
      )}

      {lastFail && (!lastReal || Date.parse(lastFail.created_at) > Date.parse(lastReal.updated_at)) && (
        <div className="panel" style={{ padding: 14, marginBottom: 18 }}>
          <strong style={{ color: 'var(--review)' }}>
            The last run ended {lastFail.conclusion}.
          </strong>{' '}
          <span className="muted">
            {lastReal
              ? `Nothing has come in since ${ago(lastReal.updated_at)}.`
              : 'Nothing has come in from it.'}
          </span>{' '}
          <a href={lastFail.html_url} className="mono" style={{ color: 'var(--accent)' }}>see why</a>
        </div>
      )}

      <h2>Run it now</h2>
      <div className="panel" style={{ padding: 14, marginBottom: 18 }}>
        {token ? (
          // A GET form, so no client JavaScript ships for one button. The route
          // handler dispatches and redirects straight back here.
          <form method="post" action="/sync/run" className="search" style={{ margin: 0 }}>
            <button className="btn-sm" type="submit" disabled={Boolean(running)}>
              {running ? 'A run is already going' : 'Run import now'}
            </button>
            <label className="muted" style={{ fontSize: 13, display: 'flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" name="dry_run" value="true" defaultChecked />
              Dry run — fetch and report, write nothing
            </label>
          </form>
        ) : (
          <div className="muted" style={{ fontSize: 13 }}>
            <strong style={{ color: 'var(--ink)' }}>Button not wired yet.</strong> Triggering a
            run needs a GitHub token with permission to start workflows, held by
            this app rather than by a person. Add a fine-grained token scoped to
            this repository with <span className="mono">Actions: read and write</span>,
            as <span className="mono">GITHUB_DISPATCH_TOKEN</span> in the Vercel
            project. Everything above works without it.
          </div>
        )}
      </div>

      <h2>Recent runs</h2>
      <div className="panel">
        {error && <div className="empty">{error}</div>}
        {list.length ? (
          <table>
            <thead><tr>
              <th>When</th><th>Started by</th><th>Result</th><th>Took</th><th></th>
            </tr></thead>
            <tbody>
              {list.map((r) => {
                const skipped = r.conclusion === 'success' && !realImport(r);
                return (
                  <tr key={r.id}>
                    <td className="muted mono">{ago(r.created_at)}</td>
                    <td className="muted">{r.event === 'schedule' ? 'schedule' : 'by hand'}</td>
                    <td>
                      {r.status !== 'completed'
                        ? <span className="pill in_progress">running</span>
                        : skipped
                          // Named for what it is. "success" on a run that did
                          // nothing is how a dashboard lies without a bug.
                          ? <span className="pill cancelled">skipped — wrong hour</span>
                          : r.conclusion === 'success'
                            ? <span className="pill resolved">imported</span>
                            : <span className="pill needs_review">{r.conclusion}</span>}
                    </td>
                    <td className="mono">{r.status === 'completed' ? took(r.created_at, r.updated_at) : '—'}</td>
                    <td><a className="btn-sm" href={r.html_url}>Open log</a></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : !error && <div className="empty">No runs recorded yet.</div>}
      </div>

      <p className="muted" style={{ fontSize: 13, marginTop: 14 }}>
        Four scheduled runs a day, of which two are always skipped: GitHub&rsquo;s
        cron is UTC and has no daylight saving, so both possible Israel offsets
        are scheduled and the wrong one exits in seconds. A skipped run is not a
        failure.
      </p>
    </>
  );
}
