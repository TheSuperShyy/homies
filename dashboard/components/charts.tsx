/**
 * The two charts on the overview. Server components, inline SVG, no library.
 *
 * WHY NO CHART LIBRARY. The rest of this dashboard ships zero JavaScript per
 * page; recharts or chart.js would put 40-90kB of client bundle on the one
 * page a manager opens most, to draw a donut with three segments and seven
 * bars. Both shapes below are arithmetic and a path string.
 *
 * WHY THE HOVER LAYER IS `<title>`. A tooltip that follows the cursor needs a
 * client component, which is the bundle this file exists to avoid. Every
 * segment and every bar carries a `<title>`, which is the browser's own
 * tooltip — real hover text, announced by screen readers, costing nothing. The
 * trade is paid for in the other direction: every value is also printed, in the
 * legend and on the axis, so nothing is discoverable ONLY by hovering.
 *
 * COLOUR IS NOT CHOSEN HERE. The three series read `--cat-1..3`, which are
 * validated in `design-system/tokens/app.css`. Never hardcode a fill.
 */

export type Slice = { key: string; label: string; value: number; token: string };

/* -------------------------------------------------------------- donut ----- */

/**
 * Part-to-whole for the three kinds of thing the system did this week.
 *
 * A donut is the weakest of the part-to-whole forms and it is the right one
 * here for two narrow reasons: there are three segments, not eight, and the
 * values are far apart rather than close — the two conditions under which a
 * reader can actually judge the arcs. If a fourth series is ever added, or the
 * values converge, this should become a stacked bar rather than a fatter ring.
 *
 * Drawn as one circle per segment with `stroke-dasharray`, which gives exact
 * arc lengths and a real gap between neighbours without any trigonometry. The
 * gap is drawn in the surface colour, so segments never touch — two saturated
 * fills meeting edge to edge is what makes a chart look loud.
 */
export function Donut({
  slices, total, totalLabel, size = 168,
}: { slices: Slice[]; total: number; totalLabel: string; size?: number }) {
  const stroke = 22;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  // A 2px gap between neighbours, but only where there IS a neighbour: with a
  // single non-zero segment the ring must close, not carry a notch.
  const drawn = slices.filter((s) => s.value > 0);
  const gap = drawn.length > 1 ? 2 : 0;

  let acc = 0;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}
         role="img" className="donut"
         aria-label={`${totalLabel}: ${total}`}>
      {/* The track. Without it a mostly-empty ring reads as a broken one. */}
      <circle cx={size / 2} cy={size / 2} r={r} fill="none"
              stroke="var(--surface-2)" strokeWidth={stroke} />
      {drawn.map((s) => {
        const len = (s.value / total) * c;
        const dash = Math.max(len - gap, 0.5);
        // -90deg so the first segment starts at twelve o'clock rather than at
        // three, which is where a reader expects a ring to begin.
        const el = (
          <circle key={s.key} cx={size / 2} cy={size / 2} r={r} fill="none"
                  stroke={`var(${s.token})`} strokeWidth={stroke}
                  strokeDasharray={`${dash} ${c - dash}`}
                  strokeDashoffset={-acc}
                  transform={`rotate(-90 ${size / 2} ${size / 2})`}>
            <title>{`${s.label}: ${s.value} (${Math.round((s.value / total) * 100)}%)`}</title>
          </circle>
        );
        acc += len;
        return el;
      })}
      {/* The hero number sits in the hole, which is the only thing a donut has
          that a pie does not. */}
      <text x={size / 2} y={size / 2 - 2} textAnchor="middle"
            className="donut-n">{total}</text>
      <text x={size / 2} y={size / 2 + 16} textAnchor="middle"
            className="donut-k">{totalLabel}</text>
    </svg>
  );
}

/**
 * The legend. Always present — three series means identity must never be
 * carried by colour alone — and it doubles as the table view the light-mode
 * contrast warning requires, because every value is written out beside its
 * swatch rather than left to the arcs.
 */
export function Legend({ slices, total, emptyNote }: {
  slices: Slice[]; total: number; emptyNote?: string;
}) {
  return (
    <ul className="legendlist">
      {slices.map((s) => (
        <li key={s.key}>
          <span className="sw" style={{ background: `var(${s.token})` }} aria-hidden="true" />
          <span className="lab">{s.label}</span>
          <span className="val">{s.value}</span>
          <span className="pct">
            {s.value > 0 && total > 0
              ? `${Math.round((s.value / total) * 100)}%`
              : emptyNote}
          </span>
        </li>
      ))}
    </ul>
  );
}

/* --------------------------------------------------------------- bars ----- */

export type Day = { date: string; label: string; value: number };

/**
 * One metric's own card: its number, how it moved, and its shape over the
 * chosen window.
 *
 * "Each with its own metrics" is small multiples — three charts on the same
 * time axis, each with its OWN vertical scale. That is not a dual axis, which
 * is the thing never to build: a dual axis puts two scales behind one set of
 * marks and invents a correlation. Here each chart owns its frame, and the
 * reader compares shapes rather than heights. It also means 171 tickets and 0
 * payment links can sit side by side without the second one being an invisible
 * line along the floor.
 *
 * THE DELTA IS DELIBERATELY NOT GREEN OR RED. The design system colours its
 * deltas as gains and losses, which is right for a stock and wrong for this:
 * more tickets opened is not good news and fewer is not bad news, and painting
 * it green would be the dashboard making a judgement it has no basis for. It
 * stays in muted ink with an arrow, which states the direction and leaves the
 * meaning to the person reading it.
 */
export function MetricCard({
  label, value, token, days, previous, prevLabel, emptyLabel, note,
}: {
  label: string; value: number; token: string; days: Day[];
  previous: number; prevLabel: string; emptyLabel: string; note?: string;
}) {
  // No previous period means no percentage — dividing by zero is not "up
  // 100%", it is "there is nothing to compare this with". The row still
  // occupies its height so the three cards stay aligned; it just says nothing,
  // which is the honest thing for it to say.
  const delta = previous > 0
    ? Math.round(((value - previous) / previous) * 100)
    : null;
  return (
    <div className="metric">
      <div className="metric-head">
        <span className="sw" style={{ background: `var(${token})` }} aria-hidden="true" />
        <span className="metric-k">{label}</span>
      </div>
      <div className="metric-n">{value}</div>
      <div className="metric-d">
        {delta !== null && (
          <span className="faint">
            <span aria-hidden="true">{delta > 0 ? '↑' : delta < 0 ? '↓' : '→'}</span>{' '}
            {Math.abs(delta)}% {prevLabel}
          </span>
        )}
      </div>
      <Bars days={days} token={token} emptyLabel={emptyLabel} />
      {note && <p className="metric-note">{note}</p>}
    </div>
  );
}

/**
 * The columns.
 *
 * One series, one hue — the hue belongs to the metric, not to its rank, so
 * tickets stay blue whether they are the biggest number on the page or the
 * smallest. Only the largest column is labelled: a number over every column is
 * the noise a chart exists to replace, and the rest carry a `<title>`.
 */
export function Bars({
  days, token, emptyLabel,
}: { days: Day[]; token: string; emptyLabel: string }) {
  const max = Math.max(...days.map((d) => d.value), 1);
  const peak = days.reduce((a, b) => (b.value > a.value ? b : a), days[0]);
  if (!days.length || !days.some((d) => d.value > 0)) {
    return <div className="chart-empty">{emptyLabel}</div>;
  }
  // Thin the axis labels rather than letting them collide. Every column keeps
  // its `<title>` and its place in the aria-label, so nothing is lost — the
  // axis just stops trying to name all fourteen of them in 240px.
  const every = Math.ceil(days.length / 7);
  return (
    <div className="bars" role="img"
         aria-label={days.map((d) => `${d.label}: ${d.value}`).join(', ')}>
      {days.map((d, i) => (
        <div className="bar" key={d.date}>
          <div className="barval">
            {d.date === peak.date && d.value > 0 ? d.value : ' '}
          </div>
          <div className="barwrap">
            <div className="barfill"
                 style={{
                   background: `var(${token})`,
                   height: `${Math.max((d.value / max) * 100, d.value > 0 ? 3 : 0)}%`,
                 }}
                 title={`${d.label}: ${d.value}`} />
          </div>
          <div className="barlab">
            {i % every === 0 || i === days.length - 1 ? d.label : ' '}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------- buckets --- */

/**
 * Rows -> columns, over an arbitrary window.
 *
 * TWO THINGS THIS GETS RIGHT AND A `slice(0, 10)` DOES NOT.
 *
 * 1. THE ZONE. Supabase returns `created_at` in UTC and Israel runs two or
 *    three hours ahead, so slicing the ISO string files anything logged between
 *    midnight and 03:00 local under the previous day — an early-morning
 *    emergency call lands on the wrong column, and the labels, which ARE
 *    formatted in Jerusalem time, then disagree with the bars above them.
 *
 * 2. THE BUCKET SIZE. Once the reader can pick their own range, "one column per
 *    day" stops working: ninety days is ninety slivers two pixels wide with
 *    unreadable labels underneath. So the window picks the bucket — days up to
 *    about a month, then weeks, then months — and the chart never draws more
 *    than ~31 columns whatever range is asked for.
 *
 * Empty buckets are kept as zeroes. A week with nothing in it is a fact worth
 * seeing, and dropping it would silently compress the time axis.
 */
const TZ = 'Asia/Jerusalem';
// en-CA because it is the locale whose short date IS `YYYY-MM-DD`, which makes
// it the cheapest way to get a zoned date key out of Intl.
const KEY = new Intl.DateTimeFormat('en-CA', {
  timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit',
});

export type Grain = 'day' | 'week' | 'month';

/**
 * The thresholds are set by the WIDTH OF A CARD, not by what looks reasonable
 * on a full-width chart. Each metric now lives in its own ~240px column, and
 * thirty daily columns in 240px is thirty five-pixel slivers with unreadable
 * labels underneath — so a month rolls up to weeks and a quarter still does,
 * and only a range longer than about fourteen weeks goes to months. The rule
 * of thumb: never more than ~14 columns in a card this size.
 */
export function grainFor(spanDays: number): Grain {
  if (spanDays <= 14) return 'day';
  if (spanDays <= 98) return 'week';
  return 'month';
}

/** The key a date falls under, for the chosen grain. Weeks start on Sunday,
 *  which is the Israeli working week — a Monday-start grid would split every
 *  week the office actually works. */
function bucketKey(d: Date, grain: Grain): string {
  const iso = KEY.format(d);              // YYYY-MM-DD in Jerusalem
  if (grain === 'day') return iso;
  if (grain === 'month') return iso.slice(0, 7) + '-01';
  const [y, m, day] = iso.split('-').map(Number);
  const at = new Date(Date.UTC(y, m - 1, day));
  at.setUTCDate(at.getUTCDate() - at.getUTCDay());   // back to Sunday
  return at.toISOString().slice(0, 10);
}

function step(d: Date, grain: Grain) {
  const n = new Date(d);
  if (grain === 'day') n.setUTCDate(n.getUTCDate() + 1);
  else if (grain === 'week') n.setUTCDate(n.getUTCDate() + 7);
  else n.setUTCMonth(n.getUTCMonth() + 1);
  return n;
}

export function bucketSeries(
  rows: { created_at: string }[] | null | undefined,
  from: string,
  to: string,
  grain: Grain,
  label: (isoKey: string, grain: Grain) => string,
): Day[] {
  const out: Day[] = [];
  const end = new Date(to + 'T00:00:00Z');
  let cur = new Date(bucketKey(new Date(from + 'T12:00:00Z'), grain) + 'T00:00:00Z');
  // The 400 cap is a guard, not a limit: `grainFor` already keeps this under
  // ~31, and an unbounded while-loop over user-supplied dates is how a bad URL
  // becomes a hung request.
  for (let i = 0; cur <= end && i < 400; i++) {
    const key = cur.toISOString().slice(0, 10);
    out.push({ date: key, label: label(key, grain), value: 0 });
    cur = step(cur, grain);
  }
  const index = new Map(out.map((d) => [d.date, d]));
  for (const r of rows ?? []) {
    const hit = index.get(bucketKey(new Date(r.created_at), grain));
    if (hit) hit.value += 1;
  }
  return out;
}

/** Column labels in the reader's language, sized to the grain: weekday
 *  initials for a short window, day/month once there are too many for that. */
export function labeller(locale: 'he' | 'en', spanDays: number) {
  const l = locale === 'he' ? 'he-IL' : 'en-GB';
  const wd = new Intl.DateTimeFormat(l, { timeZone: 'UTC', weekday: 'short' });
  const dm = new Intl.DateTimeFormat(l, { timeZone: 'UTC', day: 'numeric', month: 'short' });
  const mo = new Intl.DateTimeFormat(l, { timeZone: 'UTC', month: 'short' });
  return (key: string, grain: Grain) => {
    const d = new Date(key + 'T00:00:00Z');
    if (grain === 'month') return mo.format(d);
    if (grain === 'week') return dm.format(d);
    return spanDays <= 10 ? wd.format(d) : dm.format(d);
  };
}
