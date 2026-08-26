import { revalidatePath } from 'next/cache';
import { serverClient } from '@/lib/supabase-server';
import { Pager, pageFrom, pageRange, perParam, sizeFrom } from '@/components/pager';
import { getLocale, label, translator, when, type T } from '@/lib/i18n';
import { IconInbox } from '@/components/icons';

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
 * Whether OXS is still serving this ticket, and when it stopped.
 *
 * OXS never marks a call closed — it stops returning it. Measured 24 Aug: 34
 * calls live against 70 we hold, three of them leaving the feed within one
 * hour. Whether leaving means resolved is still an open question with Homies,
 * so this reports the fact and refuses to draw the conclusion: a ticket that
 * has dropped out is flagged, not silently resolved.
 *
 * The importer runs every fifteen minutes and GitHub's scheduler is
 * best-effort, so anything seen inside the last 45 minutes counts as current.
 */
function InOxs({ seen, t }: { seen?: string | null; t: T }) {
  if (!seen) return null;
  const mins = Math.round((Date.now() - Date.parse(seen)) / 60000);
  if (mins < 45) return <span className="sub">{t('tickets.inOxs')}</span>;
  const gone = mins < 1440 ? `${Math.round(mins / 60)}h` : `${Math.round(mins / 1440)}d`;
  return (
    <span className="sub" style={{ color: 'var(--review)' }}
          title={t('tickets.lastSeen', { when: seen })}>
      {t('tickets.goneOxs', { ago: gone })}
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
  const { data, error, count } = await q
    .order('created_at', { ascending: false })
    .range(from, to);

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
          <a key={s || 'all'} href={tabHref(s)}
             aria-current={(status ?? '') === s ? 'true' : undefined}>
            {s ? label(t, 'status', s) : t('status.all')}
          </a>
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
                  <td className="mono">{r.reference}</td>
                  <td dir="auto">
                    {r.description}
                    {/* WHAT OXS ACTUALLY KNOWS ABOUT THIS TICKET.
                        Their `status` field reads `open` on every service call
                        they have ever served, so the Status column opposite is
                        ours and says nothing about their side. The movement is
                        here: the dispatcher's own note, newest first, imported
                        since 24 Aug. Their words, untranslated — this is what a
                        resident is told when they ring and ask. */}
                    {r.oxs_notes?.length > 0 && (
                      <span className="sub" dir="auto">
                        ↳ {r.oxs_notes[0]}
                        {r.oxs_notes.length > 1 && (
                          <span style={{ opacity: 0.7 }}>
                            {' · '}{t('tickets.earlier', { n: r.oxs_notes.length - 1 })}
                          </span>
                        )}
                      </span>
                    )}
                  </td>
                  <td dir="auto">{r.building}{r.unit ? ` · ${r.unit}` : ''}</td>
                  {/* The number the call came from, kept since 19 Aug. It is
                      the only thing on an inbound ticket that cannot be
                      mis-heard, and on a needs_review row where the audio
                      failed it is often the only way back to the person. */}
                  <td className="mono">{r.reported_by_phone ?? <span className="muted">—</span>}</td>
                  <td className="muted">{r.type}</td>
                  <td><span className={`urg ${r.urgency}`}>{label(t, 'urgency', r.urgency)}</span></td>
                  <td>
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
                  <td className="muted">{r.opened_via}</td>
                  <td className="muted mono">
                    {when(r.created_at, locale)}
                    {r.opened_via === 'oxs' && <InOxs seen={r.oxs_last_seen_at} t={t} />}
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
