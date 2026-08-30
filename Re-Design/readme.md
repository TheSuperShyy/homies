# Stovest Design System

A dual-theme dashboard design system derived from two reference shots supplied by the user (in `uploads/`):

- **Dark reference ("Stovest" stock dashboard)** — the source of truth for **layout and design language**: sidebar + topbar chrome, pill-shaped controls, bordered cards on a near-black canvas, blue accent.
- **Light reference ("Skillset" dashboard)** — used **only as the light-mode color palette**: warm gray canvas, white cards, near-black primary. Its layout is NOT part of this system.

No codebase or Figma was provided; everything here is authored from those screenshots. There is **no logo asset** — render the wordmark in plain type (`Sto` white + `vest` in accent).

## Theming

Dark is the default (`:root`). Light mode = `data-theme="light"` on any ancestor. All components read semantic tokens only, so they theme automatically.

## CONTENT FUNDAMENTALS

- Tone: concise, friendly-professional. Sentence case for body/buttons ("See all", "Most Viewed"), Title Case for nav items and card titles ("Portfolio Performance").
- Micro-labels are uppercase, letter-spaced, muted ("MAIN MENU", "SUPPORT").
- Personal, second person greeting: "Welcome, Naya" + a one-line muted subtitle ("Here's your stock portfolio overview").
- Numbers are the heroes: large currency values with explicit `$` and thousands separators; deltas always signed and colored (`+3.68 ($ 5.32)` green, `-3.4%` red).
- No emoji. No exclamation marks.

## VISUAL FOUNDATIONS

- **Color (dark)**: near-black canvas `--bg-0`, cards `--surface-1` outlined by `--border-1` (borders, not shadows). Single blue accent `--accent #2D7FF9` used sparingly: active nav item, selected pill, chart line. Green/red strictly for gains/losses.
- **Color (light)**: warm gray canvas `#E5E4E1`, white cards with hairline borders + very soft shadow. Accent becomes near-black `#22251F`; green/red keep their roles.
- **Type**: Poppins everywhere (substitute — see Caveats). UI default 13px/400, titles 14–16px/600, hero numbers 34px/600. Uppercase micro-labels 11px with 0.06em tracking.
- **Shape**: pill-heavy. Buttons, filter chips, search, tags = fully rounded (`--radius-pill`). Cards 20px, nested tiles 14px, app frame 26px.
- **Depth**: dark theme = flat, 1px borders only; light theme adds `--shadow-card` (very soft). Popovers use `--shadow-pop`.
- **Hero texture**: featured cards (Total Holding) carry a faint concentric-ring "swirl" motif in the top-right corner — `var(--text-1)` strokes at ~4–5% opacity, clipped by the card. Built into `StatCard hero`.
- **Layout**: fixed sidebar (232px) with grouped nav; topbar with center search pill and right-side icon buttons + profile; 12-col content grid with 16–24px gaps; cards padded 20–24px.
- **States**: hover = one surface step up (`--surface-2` → `--surface-3`) or `--accent-hover`; active nav = solid accent fill with white text; selected filter pill = accent fill; focus = `--focus-ring`. Transitions 120–200ms ease, no bounces.
- **Charts**: single-series area chart, accent line with vertical gradient fill (`--chart-fill-top` → bottom), dashed hover crosshair, dark tooltip pill. Sparklines in tables use positive/negative colors.
- **Imagery**: photographic avatars only (circular). No illustrations, gradients or textures on backgrounds.

## ICONOGRAPHY

No icon assets were extractable from screenshots. The reference uses thin 1.5px-stroke line icons — **Lucide (CDN)** is the substitute:
`<script src="https://unpkg.com/lucide@latest"></script>` then `lucide.createIcons()`, or copy individual SVGs. Icons render at 16–18px in `--text-2`, inheriting `currentColor`. No emoji, no unicode glyphs as icons.

## Index

- `styles.css` — global entry; imports everything in `tokens/`.
- `tokens/` — `colors.css` (dark `:root` + `[data-theme="light"]`), `typography.css`, `spacing.css`, `effects.css`, `fonts.css`.
- `guidelines/` — foundation specimen cards (Design System tab).
- `components/core/` — Button, IconButton, Input, Select, Checkbox, Switch, Badge, Avatar.
- `components/display/` — Card, StatCard, DataTable.
- `components/navigation/` — Tabs, SidebarItem.
- `ui_kits/dashboard/` — full Stovest dashboard recreation with dark/light toggle.
- `SKILL.md` — agent-skill entry point.

## Intentional additions

- **StatCard** — the reference's core repeated element (ticker/stat tiles); promoted to a primitive.
- **DataTable** — watchlist/overview tables appear twice in the reference.

## Caveats

- Fonts: exact source typeface unknown; **Poppins (Google Fonts)** substituted. Provide font files to swap.
- Icons: Lucide substituted for the unidentified line-icon set.
- Colors are eyeballed from screenshots, not sampled from source files.
