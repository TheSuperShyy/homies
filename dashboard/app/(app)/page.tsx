import { serverClient } from '@/lib/supabase-server';
import { getLocale, label, translator, when } from '@/lib/i18n';
import { IconInbox } from '@/components/icons';
import { Donut, DailyBars, Legend, byDay, type Slice } from '@/components/charts';
import Link from 'next/link';

export default async function Overview() {
  const db = serverClient();
  const locale = getLocale();
  const t = translator(locale);
  const since = new Date(Date.now() - 7 * 864e5).toISOString();

  // The charts' window. Seven days, the same seven the table under them
  // covers — two windows on one page means every number has to be read twice
  // before it can be compared with the one beside it.
  const week = new Date(Date.now() - 7 * 864e5).toISOString();

  const [tickets, open, urgent, convos, calls, recent,
         weekTickets, weekCalls, weekLinks] = await Promise.all([
    db.from('requests').select('*', { count: 'exact', head: true }),
    db.from('requests').select('*', { count: 'exact', head: true }).in('status', ['open', 'in_progress']),
    db.from('requests').select('*', { count: 'exact', head: true }).in('urgency', ['high', 'emergency']).in('status', ['open', 'in_progress']),
    db.from('v_conversations').select('*'),
    db.from('interactions').select('*', { count: 'exact', head: true }).eq('channel', 'voice'),
    db.from('requests').select('reference,description,building,unit,urgency,status,opened_via,created_at')
      .gte('created_at', since).order('created_at', { ascending: false }).limit(8),

    // Three counts for the ring, and the ticket rows again — dated only —
    // because the ring needs the total and the columns need them bucketed by
    // day, and one trip is cheaper than two. `payment_links` is filtered to
    // `sent`: a row is written when the agent RAISES a link, and raising one is
    // not sending it.
    db.from('requests').select('created_at').gte('created_at', week),
    db.from('interactions').select('created_at').eq('channel', 'voice').gte('created_at', week),
    db.from('payment_links').select('created_at').eq('status', 'sent').gte('created_at', week),
  ]);

  const slices: Slice[] = [
    { key: 'tickets', label: t('chart.tickets'), value: weekTickets.data?.length ?? 0, token: '--cat-1' },
    { key: 'calls',   label: t('chart.calls'),   value: weekCalls.data?.length ?? 0,   token: '--cat-2' },
    { key: 'links',   label: t('chart.links'),   value: weekLinks.data?.length ?? 0,   token: '--cat-3' },
  ];
  const activity = slices.reduce((n, s) => n + s.value, 0);

  // Weekday initials in the reader's own language, from the same Intl the
  // dates in the table use. Hardcoding "Mon Tue Wed" would be English furniture
  // on a Hebrew page.
  const weekday = new Intl.DateTimeFormat(locale === 'he' ? 'he-IL' : 'en-GB',
    { timeZone: 'Asia/Jerusalem', weekday: 'short' });
  const days = byDay(weekTickets.data, 7, (d) => weekday.format(d));

  // Counts, not a chart library. Five numbers a manager can read in two seconds
  // beat a dashboard that takes a second to render and a minute to interpret.
  // The tone on each one is the semantic, not decoration: urgent-and-open is
  // the only red thing on the page, which is what makes it findable.
  //
  // THE FIRST ONE IS THE HERO, in the design system's sense: double width,
  // accent ground, the ring motif, and the number at 34px instead of 26. The
  // reference gives that treatment to the portfolio total, because a dashboard
  // that treats all its numbers alike has not said which one you came for.
  // Here it is open tickets — the count that decides whether anybody needs to
  // do anything today.
  const cards = [
    ['hero is-open', t('overview.openTickets'), open.count ?? 0],
    ['is-urgent',    t('overview.urgent'),      urgent.count ?? 0],
    ['',             t('overview.allTickets'),  tickets.count ?? 0],
    ['is-progress',  t('overview.convos'),      convos.data?.length ?? 0],
    ['',             t('overview.calls'),       calls.count ?? 0],
  ] as const;

  return (
    <>
      <div className="pagehead">
        <h1>{t('overview.title')}</h1>
      </div>

      <div className="cards">
        {cards.map(([tone, k, n]) => (
          <div className={`card ${tone}`} key={k}>
            <div className="k">{k}</div>
            <div className="n">{n}</div>
          </div>
        ))}
      </div>

      <div className="panel" style={{ marginBlockStart: 20 }}>
        <div className="panelhead">
          <span>{t('chart.activity')}</span>
          <span className="faint">{t('overview.last7')}</span>
        </div>
        <div className="chartcard">
          <div className="donutwrap">
            <Donut slices={slices} total={activity} totalLabel={t('chart.events')} />
            <Legend slices={slices} total={activity} emptyNote={t('chart.nothingYet')} />
          </div>
          <div>
            <h3 className="charttitle">{t('chart.perDay')}</h3>
            <DailyBars days={days} emptyLabel={t('chart.noActivity')} />
          </div>
          {/* A zero segment with nothing said about it reads as a broken chart
              rather than as a feature that is not finished. */}
          {slices[2].value === 0 && (
            <p className="chartnote">{t('chart.linksNote')}</p>
          )}
        </div>
      </div>

      {/* Card, with its title inside its own border rather than floating above
          it. The system has no free-standing section heading — a titled card is
          how it labels a block, and it keeps the label and the thing it labels
          inside one outline. */}
      <div className="panel" style={{ marginBlockStart: 20 }}>
        <div className="panelhead">
          <span>{t('overview.last7')}</span>
          <Link className="btn-nav" href="/tickets">{t('overview.seeAll')}</Link>
        </div>
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
