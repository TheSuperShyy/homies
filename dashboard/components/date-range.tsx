'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

/**
 * The date filter: presets, then a calendar.
 *
 * ONE ROW, ABOVE EVERYTHING, SCOPING EVERYTHING. Not one picker per chart —
 * three ranges on one screen means three numbers that cannot be compared with
 * each other, and the first question anybody asks of a dashboard is whether
 * calls went up while tickets went down.
 *
 * PRESETS BEFORE THE CALENDAR, because nobody wants to fight a calendar grid
 * for "last 30 days" — that is the range a reader picks nine times out of ten,
 * and it should be one click, not two date selections.
 *
 * The calendar itself is `<input type="date">`. It is the browser's own date
 * picker: a real month grid, keyboard-operable, localised, translated, and
 * aware of the reader's own locale — and it costs nothing, where a React date
 * picker is 30-50kB on a page that currently ships 189 bytes.
 *
 * The whole state lives in the URL, like every other filter here, so a range is
 * something you can send a colleague. `router.push` rather than a plain GET
 * form so the navigation stays client-side and the tab does not reload.
 */

export function DateRange({
  from, to, today, presets, labels,
}: {
  from: string;
  to: string;
  today: string;
  presets: { days: number; label: string; href: string; on: boolean }[];
  labels: { from: string; to: string; apply: string; custom: string };
}) {
  const router = useRouter();
  const [f, setF] = useState(from);
  const [t, setT] = useState(to);

  return (
    <div className="rangebar">
      <nav className="seg" aria-label={labels.custom}>
        {presets.map((p) => (
          <Link key={p.days} href={p.href} aria-current={p.on ? 'true' : undefined}>
            {p.label}
          </Link>
        ))}
      </nav>

      <form
        className="rangeform"
        onSubmit={(e) => {
          e.preventDefault();
          // Guard the obvious mistake rather than rejecting it: a range entered
          // backwards is a slip, not a request for an empty chart.
          const [a, b] = f <= t ? [f, t] : [t, f];
          router.push(`/?from=${a}&to=${b}`);
        }}
      >
        <label>
          <span>{labels.from}</span>
          {/* `max` stops the two inputs producing a range that cannot exist,
              inside the picker itself, before anything is submitted. */}
          <input type="date" value={f} max={t || today}
                 onChange={(e) => setF(e.target.value)} required />
        </label>
        <label>
          <span>{labels.to}</span>
          <input type="date" value={t} min={f} max={today}
                 onChange={(e) => setT(e.target.value)} required />
        </label>
        <button type="submit" className="btn-nav">{labels.apply}</button>
      </form>
    </div>
  );
}
