import { serverClient } from '@/lib/supabase-server';
import { getLocale, label, translator, when } from '@/lib/i18n';
import { IconInbox } from '@/components/icons';
import {
  Donut, Legend, MetricCard, bucketSeries, grainFor, labeller, type Slice,
} from '@/components/charts';
import { DateRange } from '@/components/date-range';
import Link from 'next/link';

/** A calendar day in Jerusalem, as `YYYY-MM-DD`. Every date on this page is
 *  computed in the office's own zone — the alternative is a "today" that turns
 *  over at 2am local and a "last 7 days" that is sometimes six. */
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const JDAY = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Jerusalem', year: 'numeric', month: '2-digit', day: '2-digit',
});
const jday = (d: Date) => JDAY.format(d);
const shift = (iso: string, days: number) =>
  jday(new Date(new Date(iso + 'T12:00:00Z').getTime() + days * 864e5));
const spanOf = (from: string, to: string) =>
  Math.round((Date.parse(to + 'T12:00:00Z') - Date.parse(from + 'T12:00:00Z')) / 864e5) + 1;

export default async function Overview({
  searchParams,
}: { searchParams?: { from?: string; to?: string } }) {
  const db = serverClient();
  const locale = getLocale();
  const t = translator(locale);
  const since = new Date(Date.now() - 7 * 864e5).toISOString();

  // ---- the window -------------------------------------------------------
  // Whatever the reader picked, or the last seven days. VALIDATED, not
  // trusted: both dates arrive from the URL, and a malformed or reversed pair
  // should give the default view rather than an empty chart or a hung request.
  const today = jday(new Date());
  const ok = (v?: string) => (DATE_RE.test(v ?? '') ? v! : undefined);
  let to = ok(searchParams?.to) ?? today;
  let from = ok(searchParams?.from) ?? shift(to, -6);
  if (from > to) [from, to] = [to, from];
  if (to > today) to = today;
  // A year is the cap. Not a policy, a guard: the three queries below pull
  // rows rather than counts, and an unbounded range is a request to send the
  // whole table to the browser.
  if (spanOf(from, to) > 366) from = shift(to, -365);

  const span = spanOf(from, to);
  const grain = grainFor(span);
  // Bounds for the query. `to` is a whole day, so the upper bound is the START
  // of the next day and exclusive — `lte` on a date silently drops everything
  // logged after midnight on the last day of the range, which is the last day
  // anybody actually looks at.
  const gte = from + 'T00:00:00+03:00';
  const lt = shift(to, 1) + 'T00:00:00+03:00';
  // The same length again, immediately before it, so each metric can say which
  // way it moved.
  const prevFrom = shift(from, -span) + 'T00:00:00+03:00';

  const [tickets, open, urgent, convos, calls, recent,
         winTickets, winCalls, winLinks,
         prevTickets, prevCalls, prevLinks] = await Promise.all([
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
    db.from('requests').select('created_at').gte('created_at', gte).lt('created_at', lt),
    db.from('interactions').select('created_at').eq('channel', 'voice')
      .gte('created_at', gte).lt('created_at', lt),
    db.from('payment_links').select('created_at').eq('status', 'sent')
      .gte('created_at', gte).lt('created_at', lt),

    // The period before, for the deltas. Counts only — nothing plots these, so
    // pulling the rows would be three round trips of data nobody reads.
    db.from('requests').select('*', { count: 'exact', head: true })
      .gte('created_at', prevFrom).lt('created_at', gte),
    db.from('interactions').select('*', { count: 'exact', head: true }).eq('channel', 'voice')
      .gte('created_at', prevFrom).lt('created_at', gte),
    db.from('payment_links').select('*', { count: 'exact', head: true }).eq('status', 'sent')
      .gte('created_at', prevFrom).lt('created_at', gte),
  ]);

  // COLOUR FOLLOWS THE ENTITY, NEVER ITS RANK. Tickets are slot 1 whether they
  // are the biggest number on the page or the smallest, so a reader who
  // learned "orange is calls" is never re-taught by changing the date range.
  const lab = labeller(locale, span);
  const metrics = [
    { key: 'tickets', token: '--cat-1', label: t('chart.tickets'),
      rows: winTickets.data, prev: prevTickets.count ?? 0,
      note: undefined as string | undefined },
    { key: 'calls', token: '--cat-2', label: t('chart.calls'),
      rows: winCalls.data, prev: prevCalls.count ?? 0,
      note: undefined as string | undefined },
    { key: 'links', token: '--cat-3', label: t('chart.links'),
      rows: winLinks.data, prev: prevLinks.count ?? 0,
      note: (winLinks.data?.length ?? 0) === 0 ? t('chart.linksNote') : undefined },
  ].map((m) => ({
    ...m,
    value: m.rows?.length ?? 0,
    series: bucketSeries(m.rows, from, to, grain, lab),
  }));

  const slices: Slice[] = metrics.map((m) => ({
    key: m.key, label: m.label, value: m.value, token: m.token,
  }));
  const activity = slices.reduce((n, s) => n + s.value, 0);

  // Presets first — nobody fights a calendar grid for "last 30 days".
  const presets = [7, 30, 90].map((d) => ({
    days: d,
    label: t(('range.d' + d) as any),
    href: '/?from=' + shift(today, -(d - 1)) + '&to=' + today,
    on: to === today && span === d,
  }));

  const shown = new Intl.DateTimeFormat(locale === 'he' ? 'he-IL' : 'en-GB',
    { timeZone: 'UTC', day: 'numeric', month: 'short' });
  const windowLabel =
    shown.format(new Date(from + 'T00:00:00Z')) + ' \u2013 ' +
    shown.format(new Date(to + 'T00:00:00Z'));

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

      {/* ONE filter row, above everything it scopes. Not one picker per chart:
          three ranges on one screen means three numbers that cannot be
          compared with each other, and the first question anybody asks of a
          dashboard is whether calls went up while tickets went down. */}
      <div className="panel" style={{ marginBlockStart: 20 }}>
        <div className="panelhead">
          <span>{t('chart.activity')}</span>
          <span className="faint">{windowLabel}</span>
        </div>

        <div className="rangewrap">
          <DateRange
            from={from} to={to} today={today} presets={presets}
            labels={{
              from: t('range.from'), to: t('range.to'),
              apply: t('range.apply'), custom: t('range.custom'),
            }}
          />
        </div>

        <div className="chartcard">
          <div className="mixtile">
            <Donut slices={slices} total={activity} totalLabel={t('chart.events')} size={132} />
            <Legend slices={slices} total={activity} emptyNote={t('chart.nothingYet')} />
          </div>

          {/* SMALL MULTIPLES: each metric its own frame and its own vertical
              scale. That is not a dual axis — the thing never to build — it is
              three charts side by side, so 171 tickets and 0 payment links can
              both be read instead of the second one being an invisible line
              along the floor of the first one's scale. */}
          <div className="metrics">
            {metrics.map((m) => (
              <MetricCard
                key={m.key}
                label={m.label}
                value={m.value}
                token={m.token}
                days={m.series}
                previous={m.prev}
                prevLabel={t('chart.vsPrev')}
                emptyLabel={t('chart.noneInRange')}
                note={m.note}
              />
            ))}
          </div>
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
