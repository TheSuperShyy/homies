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
 * Tickets opened per day.
 *
 * "Daily" is change over time, and a ring cannot show change over time — a pie
 * of seven days would answer "which day was busiest" and refuse to answer
 * "is this getting better", which is the question a daily number is asked. So
 * the same period gets a column chart as well as a segment of the donut.
 *
 * One series, so one hue and no legend: the title names it. Only the largest
 * day is labelled directly — a number over every column is the noise this is
 * meant to replace, and the rest are one hover away.
 */
export function DailyBars({ days, emptyLabel }: { days: Day[]; emptyLabel: string }) {
  const max = Math.max(...days.map((d) => d.value), 1);
  const peak = days.reduce((a, b) => (b.value > a.value ? b : a), days[0]);
  if (!days.some((d) => d.value > 0)) {
    return <div className="chart-empty">{emptyLabel}</div>;
  }
  return (
    <div className="bars" role="img"
         aria-label={days.map((d) => `${d.label}: ${d.value}`).join(', ')}>
      {days.map((d) => (
        <div className="bar" key={d.date}>
          <div className="barval">
            {/* Selective direct labels: the peak only. */}
            {d.date === peak.date && d.value > 0 ? d.value : ' '}
          </div>
          <div className="barwrap">
            <div className="barfill"
                 style={{ height: `${Math.max((d.value / max) * 100, d.value > 0 ? 3 : 0)}%` }}
                 title={`${d.label}: ${d.value}`} />
          </div>
          <div className="barlab">{d.label}</div>
        </div>
      ))}
    </div>
  );
}

/**
 * Buckets rows into calendar days.
 *
 * IN JERUSALEM TIME, NOT UTC, and that is the whole reason this is a function
 * rather than a `slice(0, 10)`. Supabase returns `created_at` as UTC, Israel
 * runs two or three hours ahead of it, and slicing the ISO string files
 * anything logged between midnight and 03:00 local under the previous day —
 * so an early-morning emergency call would appear on the wrong column, and the
 * column labels, which ARE formatted in Jerusalem time, would disagree with
 * the bars above them. Both sides use the same zone now.
 *
 * A day with no rows stays in the list as a zero, so an empty Tuesday is a gap
 * you can see rather than a column that quietly is not there.
 */
const TZ = 'Asia/Jerusalem';
// en-CA because it is the locale whose short date IS `YYYY-MM-DD`, which makes
// it the cheapest way to get a zoned date key out of Intl.
const KEY = new Intl.DateTimeFormat('en-CA', {
  timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit',
});

export function byDay(
  rows: { created_at: string }[] | null | undefined,
  days: number,
  fmt: (d: Date) => string,
): Day[] {
  const out: Day[] = [];
  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 864e5);
    out.push({ date: KEY.format(d), label: fmt(d), value: 0 });
  }
  const index = new Map(out.map((d) => [d.date, d]));
  for (const r of rows ?? []) {
    const hit = index.get(KEY.format(new Date(r.created_at)));
    if (hit) hit.value += 1;
  }
  return out;
}
