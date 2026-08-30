import { getLocale, translator } from '@/lib/i18n';

/**
 * What the reader looks at while the database answers.
 *
 * WHY THIS EXISTS AT ALL. Every page in this dashboard is a server component
 * that awaits Supabase before it returns any HTML, and the root layout is
 * `force-dynamic`, so nothing is cached. Until now that meant the browser held
 * the OLD page on screen — or a white rectangle on a cold load — for the whole
 * round trip, with no sign that anything had been clicked. Next streams a
 * `loading.tsx` the instant navigation starts, so the shell and these
 * skeletons paint immediately and the wait becomes visible progress instead of
 * a frozen window.
 *
 * WHY SHAPES AND NOT A SPINNER. A spinner is one thing that is then replaced
 * by a completely different thing, so the layout moves under the reader's
 * cursor at the moment the data lands. These are built to the same heights,
 * the same column count and the same paddings as the real rows — same `<table>`
 * with the same cell padding, same `.card` with the same type sizes — so when
 * the real content arrives it lands exactly where the grey was.
 *
 * ACCESSIBILITY. The whole block is `aria-hidden` and one polite live region
 * announces "Loading…" once. Without that a screen reader walks eleven empty
 * table rows and reads nothing eleven times.
 */

function Announce() {
  const t = translator(getLocale());
  return (
    <span role="status" aria-live="polite" className="sr-only">
      {t('load.loading')}
    </span>
  );
}

/** The stat strip on the overview: one hero tile and four ordinary ones. */
export function CardsSkeleton({ n = 5, hero = false }: { n?: number; hero?: boolean }) {
  return (
    <>
      <Announce />
      <div className="cards" aria-hidden="true">
        {Array.from({ length: n }, (_, i) => (
          <div key={i} className={`card sk-card${hero && i === 0 ? ' hero' : ''}`}>
            <span className="sk sk-line k" />
            <span className="sk n" />
          </div>
        ))}
      </div>
    </>
  );
}

/**
 * A panel with a table in it. `cols` is the real column count of the page this
 * stands in for — a four-column skeleton in front of a nine-column table is
 * the layout jump this component exists to prevent.
 */
export function TableSkeleton({
  cols, rows = 8, head = true,
}: { cols: number; rows?: number; head?: boolean }) {
  return (
    <>
      <Announce />
      <div className="panel" aria-hidden="true">
        <div className="scrollx">
          <table>
            {head && (
              <thead>
                <tr>
                  {Array.from({ length: cols }, (_, c) => (
                    <th key={c}><span className="sk sk-line" style={{ width: 62 }} /></th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {Array.from({ length: rows }, (_, r) => (
                <tr key={r} className="sk-tr">
                  {Array.from({ length: cols }, (_, c) => (
                    <td key={c}>
                      {/* One cell per row wears a pill rather than a line, in
                          the column where the real table shows a status. It
                          keeps the grey from reading as ruled paper. */}
                      {c === cols - 3
                        ? <span className="sk sk-pill" />
                        : <span className="sk sk-line" />}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

/** The filter pills above a list, at the real `.seg` height. */
export function SegSkeleton({ n = 4 }: { n?: number }) {
  return (
    <div className="seg" aria-hidden="true">
      {Array.from({ length: n }, (_, i) => (
        <span key={i} className="sk" style={{ height: 30, width: 84, borderRadius: 999 }} />
      ))}
    </div>
  );
}

/**
 * A panel of label/value rows — the settings page's shape, not a table's.
 *
 * Built out of the real `.setrow`, so the grey lines sit at the same height and
 * the same insets as the text that replaces them.
 */
export function RowsSkeleton({ rows = 3, head = false }: { rows?: number; head?: boolean }) {
  return (
    <div className="panel" aria-hidden="true">
      {head && (
        <div className="setwho">
          <span className="sk" style={{ height: 44, width: 44, borderRadius: '50%' }} />
          <span style={{ display: 'grid', gap: 7 }}>
            <span className="sk sk-line" style={{ width: 120 }} />
            <span className="sk sk-line" style={{ width: 70, height: 9 }} />
          </span>
        </div>
      )}
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="setrow">
          <span className="sk sk-line" style={{ width: 96 }} />
          <span className="sk sk-line" style={{ width: r % 2 ? 128 : 168 }} />
        </div>
      ))}
    </div>
  );
}

/** A page title, so the heading does not pop in after everything else. */
export function HeadSkeleton() {
  return (
    <div className="pagehead" aria-hidden="true">
      <span className="sk" style={{ height: 22, width: 190, borderRadius: 8 }} />
    </div>
  );
}
