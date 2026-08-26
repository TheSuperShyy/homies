import { serverClient } from '@/lib/supabase-server';
import { getLocale, label, translator, when } from '@/lib/i18n';
import { IconInbox } from '@/components/icons';

export default async function Overview() {
  const db = serverClient();
  const locale = getLocale();
  const t = translator(locale);
  const since = new Date(Date.now() - 7 * 864e5).toISOString();

  const [tickets, open, urgent, convos, calls, recent] = await Promise.all([
    db.from('requests').select('*', { count: 'exact', head: true }),
    db.from('requests').select('*', { count: 'exact', head: true }).in('status', ['open', 'in_progress']),
    db.from('requests').select('*', { count: 'exact', head: true }).in('urgency', ['high', 'emergency']).in('status', ['open', 'in_progress']),
    db.from('v_conversations').select('*'),
    db.from('interactions').select('*', { count: 'exact', head: true }).eq('channel', 'voice'),
    db.from('requests').select('reference,description,building,unit,urgency,status,opened_via,created_at')
      .gte('created_at', since).order('created_at', { ascending: false }).limit(8),
  ]);

  // Counts, not a chart library. Five numbers a manager can read in two seconds
  // beat a dashboard that takes a second to render and a minute to interpret.
  // The tone on each one is the semantic, not decoration: urgent-and-open is
  // the only red thing on the page, which is what makes it findable.
  const cards = [
    ['is-open',     t('overview.openTickets'), open.count ?? 0],
    ['is-urgent',   t('overview.urgent'),      urgent.count ?? 0],
    ['',            t('overview.allTickets'),  tickets.count ?? 0],
    ['is-progress', t('overview.convos'),      convos.data?.length ?? 0],
    ['',            t('overview.calls'),       calls.count ?? 0],
  ] as const;

  return (
    <>
      <div className="pagehead">
        <h1>{t('overview.title')}</h1>
      </div>

      <div className="cards">
        {cards.map(([tone, k, n]) => (
          <div className={`card ${tone}`} key={k}>
            <div className="n">{n}</div>
            <div className="k">{k}</div>
          </div>
        ))}
      </div>

      <h2>{t('overview.last7')}</h2>
      <div className="panel">
        {recent.data?.length ? (
          <div className="scrollx">
            <table>
              <thead><tr>
                <th>{t('col.reference')}</th><th>{t('col.what')}</th><th>{t('col.where')}</th>
                <th>{t('col.urgency')}</th><th>{t('col.status')}</th>
                <th>{t('col.via')}</th><th>{t('col.opened')}</th>
              </tr></thead>
              <tbody>
                {recent.data.map((r: any) => (
                  <tr key={r.reference}>
                    <td className="mono">{r.reference}</td>
                    <td dir="auto">{r.description}</td>
                    <td dir="auto">{r.building}{r.unit ? ` · ${r.unit}` : ''}</td>
                    <td><span className={`urg ${r.urgency}`}>{label(t, 'urgency', r.urgency)}</span></td>
                    <td><span className={`pill ${r.status}`}>{label(t, 'status', r.status)}</span></td>
                    <td className="muted">{r.opened_via}</td>
                    <td className="muted mono">{when(r.created_at, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">
            <IconInbox />
            <div>{t('overview.empty')}</div>
          </div>
        )}
      </div>
    </>
  );
}
