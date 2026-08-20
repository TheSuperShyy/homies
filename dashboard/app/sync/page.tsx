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
 * Jerusalem. Those exit `success` in about seven seconds. Reporting them as
 * successful imports would be the most misleading thing this page could do —
 * it would show green all day while nothing had come in since Tuesday.
 */
function realImport(r: Run) {
  return r.conclusion === 'success'
    && (Date.parse(r.updated_at) - Date.parse(r.created_at)) > 60_000;
}

export default async function Sync() {
  const db = serverClient();
  const [{ list, error }, residents, charges, requests] = await Promise.all([
    runs(),
    db.from('residents').select('id', { count: 'exact', head: true }).eq('source', 'oxs'),
    db.from('charges').select('id', { count: 'exact', head: true }).eq('source', 'oxs'),
    db.from('requests').select('id', { count: 'exact', head: true }).eq('opened_via', 'oxs'),
  ]);

  const lastReal = list.find(realImport);
  const lastFail = list.find((r) => r.conclusion === 'failure');
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
        </div>
        <div className="card">
          <div className="k">Charges from OXS</div>
          <div className="n">{charges.count ?? '—'}</div>
        </div>
        <div className="card">
          <div className="k">Requests from OXS</div>
          <div className="n">{requests.count ?? '—'}</div>
        </div>
      </div>

      {!lastReal && !running && (
        <div className="panel" style={{ padding: 14, marginBottom: 18 }}>
          <strong>Nothing has ever imported on a schedule.</strong>{' '}
          <span className="muted">
            Every row above arrived from a run by hand. The schedule fired twice a
            day and failed on the first step, because the six credentials it needs
            were never set on the repository.
          </span>
        </div>
      )}

      {lastFail && lastReal && Date.parse(lastFail.created_at) > Date.parse(lastReal.updated_at) && (
        <div className="panel" style={{ padding: 14, marginBottom: 18 }}>
          <strong style={{ color: 'var(--review)' }}>The last run failed.</strong>{' '}
          <span className="muted">Nothing has come in since {ago(lastReal.updated_at)}.</span>{' '}
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
