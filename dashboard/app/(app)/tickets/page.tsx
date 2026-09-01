import { revalidatePath } from 'next/cache';
import { serverClient } from '@/lib/supabase-server';
import { Pager, pageFrom, pageRange, perParam, sizeFrom } from '@/components/pager';
import { getLocale, label, translator, when, type T } from '@/lib/i18n';
import { IconInbox } from '@/components/icons';
import Link from 'next/link';

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
/**
 * A ticket the last import looked for in OXS and did not find.
 *
 * TWO WRONG VERSIONS OF THIS BADGE SHIPPED BEFORE THIS ONE, and the second is
 * the instructive one.
 *
 * It said "gone from OXS" whenever a ticket had not been seen for 45 minutes.
 * That reads as a fact about the ticket and is a fact about the IMPORTER: if
 * the job has not run, every open ticket is 45 minutes stale at once, and none
 * of them has gone anywhere. `oxs-requests.yml` asks for a run every fifteen
 * minutes and GitHub delivers about five a day, so the badge was lit on all 54
 * open tickets for most of the day while exactly 0 were missing. A warning that
 * is always on is not a warning.
 *
 * The comparison that means something is against the last run rather than
 * against the clock. Every ticket in the feed gets stamped with one timestamp
 * per run, so the newest stamp in the table IS when the importer last looked.
 * A ticket older than that was looked for and not found; a ticket equal to it
 * was there. Importer lag is then a separate fact with one value for the whole
 * system, and it belongs on /sync, which already reports it.
 *
 * Nothing renders in the ordinary case, deliberately. A row per ticket saying
 * "still fine" is the same mistake in a friendlier colour.
 */
function InOxs({ seen, status, lastRun, t }:
               { seen?: string | null; status?: string; lastRun?: string | null; t: T }) {
  const live = status === 'open' || status === 'in_progress';
  if (!live || !seen || !lastRun) return null;
  if (Date.parse(seen) >= Date.parse(lastRun)) return null;
  return (
    <span className="sub" style={{ color: 'var(--review)' }}
          title={t('tickets.lastSeen', { when: seen })}>
      {t('tickets.notInOxs')}
    </span>
  );
}

export default async function Tickets({
  searchParams,
}: { searchParams: { status?: string; page?: string; per?: string } }) {
  const status = searchParams.status;
  const locale = getLocale();
  const t = translator(locale);
  const page = pageFrom(searchParams);
  const size = sizeFrom(searchParams);
  const [from, to] = pageRange(page, size);
  let q = serverClient()
    .from('requests')
    .select('reference,description,building,unit,type,urgency,status,opened_via,created_at,reported_by_phone,oxs_notes,oxs_last_update,oxs_last_seen_at',
            { count: 'exact' });
  if (status) q = q.eq('status', status);
  // One extra query, and it is what makes the badge above mean anything: the
  // newest stamp across every imported ticket is the moment the importer last
  // looked at OXS. Read unfiltered on purpose — a status tab or a page of
  // results must not change what "the last run" was.
  const [{ data, error, count }, newest] = await Promise.all([
    q.order('created_at', { ascending: false }).range(from, to),
    serverClient().from('requests').select('oxs_last_seen_at')
      .eq('opened_via', 'oxs')
      .order('oxs_last_seen_at', { ascending: false })
      .limit(1).maybeSingle(),
  ]);
  const lastRun = newest.data?.oxs_last_seen_at ?? null;

  const tabs = ['', ...STATUSES];

  // The chosen size survives a change of tab. Picking 50 and then filtering to
  // "open" should not quietly hand back ten rows.
  const per = perParam(size);
  // `tab`, not `t`: the translator is called `t` and a parameter shadowing it
  // here compiles and then renders every label as a status code.
  const tabHref = (tab: string) => {
    const q = new URLSearchParams();
    if (tab) q.set('status', tab);
    if (per) q.set('per', per);
    const qs = q.toString();
    return qs ? `/tickets?${qs}` : '/tickets';
  };

  return (
    <>
      <div className="pagehead"><h1>{t('tickets.title')}</h1></div>
      <nav className="seg" aria-label={t('col.status')}>
        {tabs.map((s) => (
          <Link key={s || 'all'} href={tabHref(s)}
             aria-current={(status ?? '') === s ? 'true' : undefined}>
            {s ? label(t, 'status', s) : t('status.all')}
          </Link>
        ))}
      </nav>
      <Pager page={page} size={size} total={count ?? 0} basePath="/tickets"
             params={{ status }} unit={t('tickets.unit')} t={t} />
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <div className="scrollx">
          <table>
            <thead><tr>
              <th>{t('col.reference')}</th><th>{t('col.what')}</th><th>{t('col.where')}</th>
              <th>{t('col.caller')}</th><th>{t('col.type')}</th>
              <th>{t('col.urgency')}</th><th>{t('col.status')}</th>
              <th>{t('col.via')}</th><th>{t('col.opened')}</th>
            </tr></thead>
            <tbody>
              {data.map((r: any) => (
                <tr key={r.reference}>
                  <td className="mono" data-label={t('col.reference')}>{r.reference}</td>
                  <td dir="auto" data-label={t('col.what')}>
                    {r.description}
                    {/* WHAT OXS ACTUALLY KNOWS ABOUT THIS TICKET.
                        Their `status` field reads `open` on every service call
                        they have ever served, so the Status column opposite is
                        ours and says nothing about their side. The movement is
                        here: the dispatcher's own note, newest first, imported
                        since 24 Aug. Their words, untranslated — this is what a
                        resident is told when they ring and ask. */}
                    {r.oxs_notes?.length > 0 && (
                      r.oxs_notes.length === 1 ? (
                        <span className="sub" dir="auto">↳ {r.oxs_notes[0]}</span>
                      ) : (
                        /* THE HISTORY IS THE USEFUL PART. "fittings ordered"
                           followed by "David handling it" is a ticket moving,
                           and one string is not — migration 022's own reasoning
                           for storing the array rather than `lastUpdateNote`.
                           This used to read "+2 earlier" as plain text with no
                           way to open them, which is a promise the row could
                           not keep. <details> keeps it a server component:
                           nav.tsx stays the only thing that crosses into the
                           browser. */
                        <details className="notes">
                          <summary className="sub" dir="auto">
                            ↳ {r.oxs_notes[0]}
                            <span style={{ opacity: 0.7 }}>
                              {' · '}{t('tickets.earlier', { n: r.oxs_notes.length - 1 })}
                            </span>
                          </summary>
                          <ol dir="auto">
                            {r.oxs_notes.slice(1).map((n: string, i: number) => (
                              <li key={i}>{n}</li>
                            ))}
                          </ol>
                        </details>
                      )
                    )}
                  </td>
                  <td dir="auto" data-label={t('col.where')}>{r.building}{r.unit ? ` · ${r.unit}` : ''}</td>
                  {/* The number the call came from, kept since 19 Aug. It is
                      the only thing on an inbound ticket that cannot be
                      mis-heard, and on a needs_review row where the audio
                      failed it is often the only way back to the person. */}
                  <td className="mono" data-label={t('col.caller')}>{r.reported_by_phone ?? <span className="muted">—</span>}</td>
                  <td className="muted" data-label={t('col.type')}>{r.type}</td>
                  <td data-label={t('col.urgency')}><span className={`urg ${r.urgency}`}>{label(t, 'urgency', r.urgency)}</span></td>
                  <td data-label={t('col.status')}>
                    <form action={updateStatus} className="status-edit">
                      <input type="hidden" name="reference" value={r.reference} />
                      <select name="status" defaultValue={r.status} aria-label={t('col.status')}>
                        {STATUSES.map((s) => (
                          <option key={s} value={s}>{label(t, 'status', s)}</option>
                        ))}
                      </select>
                      <button type="submit">{t('tickets.save')}</button>
                    </form>
                  </td>
                  <td className="muted" data-label={t('col.via')}>{r.opened_via}</td>
                  <td className="muted mono" data-label={t('col.opened')}>
                    {when(r.created_at, locale)}
                    {r.opened_via === 'oxs' && <InOxs seen={r.oxs_last_seen_at} status={r.status} lastRun={lastRun} t={t} />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : !error && (
          <div className="empty">
            <IconInbox />
            <div>{status
              ? t('tickets.emptyStatus', { status: label(t, 'status', status) })
              : t('tickets.empty')}</div>
          </div>
        )}
      </div>
    </>
  );
}
