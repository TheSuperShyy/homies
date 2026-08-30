/**
 * The hero card's ornament: a row of rooftops.
 *
 * WHAT IT REPLACED, AND WHY. The design system's hero carries a set of
 * concentric rings — a fine motif, and an inherited one: it came from a stock
 * portfolio dashboard, where a ring reads as a dial or a market. On a card
 * counting open maintenance tickets for a building-management company it meant
 * nothing at all. This is the one place the system's own ornament was worth
 * swapping rather than copying, because ornament is where a product either
 * says whose it is or says nothing.
 *
 * So: pitched roofs, flat roofs and lit windows, echoing the roof in the
 * Homies mark now sitting in the sidebar. Same treatment as the rings it
 * replaces — `--text-1` at a few percent, clipped into the corner, never
 * competing with the number it sits behind.
 *
 * Inline SVG rather than a background image because it inherits the theme for
 * free: one `currentColor`, two themes, no second asset and no media query.
 */

type Block = {
  x: number; w: number; h: number;
  /** A pitched roof, like the mark, or a flat one. Mixed on purpose — a row of
   *  identical houses reads as a pattern; a row of different ones reads as a
   *  street, which is what this company actually looks after. */
  pitched?: boolean;
  cols: number; rows: number;
};

// Drawn on a 220x120 field, buildings standing on the baseline at y=120.
const SKYLINE: Block[] = [
  { x: 4,   w: 34, h: 52, cols: 2, rows: 3 },
  { x: 46,  w: 44, h: 84, pitched: true, cols: 3, rows: 4 },
  { x: 98,  w: 30, h: 42, cols: 2, rows: 2 },
  { x: 136, w: 46, h: 68, pitched: true, cols: 3, rows: 3 },
  { x: 190, w: 30, h: 38, cols: 2, rows: 2 },
];

const BASE = 120;
const WIN = 5;      // a window
const GAP = 4;      // between windows

export function HeroMotif() {
  return (
    <svg className="heromotif" viewBox="0 0 220 120" aria-hidden="true"
         preserveAspectRatio="xMidYMax meet" focusable="false">
      <g fill="currentColor" stroke="currentColor" strokeWidth="1.6"
         strokeLinejoin="round">
        {SKYLINE.map((b) => {
          const top = BASE - b.h;
          // The pitch is a quarter of the width, which is roughly the angle in
          // the logo — steep enough to read as a roof at this size.
          const peak = b.w * 0.26;
          const winW = b.cols * WIN + (b.cols - 1) * GAP;
          const winH = b.rows * WIN + (b.rows - 1) * GAP;
          const wx = b.x + (b.w - winW) / 2;
          const wy = top + (b.pitched ? peak + 8 : 10);
          return (
            <g key={b.x}>
              <rect x={b.x} y={top} width={b.w} height={b.h}
                    fill="none" opacity="0.16" />
              {b.pitched && (
                <path d={`M${b.x - 5} ${top} L${b.x + b.w / 2} ${top - peak} L${b.x + b.w + 5} ${top}`}
                      fill="none" opacity="0.16" />
              )}
              {Array.from({ length: b.rows }).map((_, r) =>
                Array.from({ length: b.cols }).map((_, c) => {
                  const y = wy + r * (WIN + GAP);
                  // Windows stop at the roofline rather than being drawn
                  // through it — a lit window below ground is the detail that
                  // makes decoration look accidental.
                  if (y + WIN > BASE - 8) return null;
                  return (
                    <rect key={`${r}-${c}`} stroke="none" opacity="0.1"
                          x={wx + c * (WIN + GAP)} y={y}
                          width={WIN} height={WIN} rx="1" />
                  );
                }),
              )}
            </g>
          );
        })}
        {/* The street the row stands on. One hairline, the same weight as the
            chart baselines elsewhere on this page. */}
        <path d="M0 120 H220" fill="none" opacity="0.16" />
      </g>
    </svg>
  );
}
