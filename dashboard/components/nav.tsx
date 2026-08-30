'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

/**
 * The sidebar's links, and the only client-side JavaScript in the shell.
 *
 * WHY THIS IS NOT A SERVER COMPONENT ANY MORE. The nav used to work out which
 * item was current from a request header the middleware set. That is correct
 * for a full page load and wrong the moment navigation becomes client-side: on
 * a move between two routes that share a layout, the App Router keeps the
 * layout mounted and only swaps the page below it. The sidebar would never
 * re-render, so the highlight would stay on whichever page you first landed
 * on — the nav would quietly lie about where you are. `usePathname` reads it
 * from the router instead, which is the thing that actually changed.
 *
 * The icons come in as rendered elements rather than imported here, so the
 * icon set stays on the server and out of the browser bundle. Only this file's
 * few lines cross over.
 */

export type NavItem = { href: string; label: string; icon: React.ReactNode };
export type NavGroup = { label: string; items: NavItem[] };

export function RailNav({ groups }: { groups: NavGroup[] }) {
  const path = usePathname();
  // "/" only matches itself. Every other entry owns its subtree, so a call's
  // detail page keeps Calls lit rather than lighting nothing.
  const here = (href: string) =>
    href === '/' ? path === '/' : path.startsWith(href);

  return (
    <>
      {groups.map((g) => (
        <div key={g.label} className="navgroupwrap">
          <div className="navgroup">{g.label}</div>
          <div className="navlist">
            {g.items.map((it) => (
              <Link key={it.href} href={it.href}
                    aria-current={here(it.href) ? 'page' : undefined}>
                {it.icon}
                <span>{it.label}</span>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

/**
 * The phone's navigation: five destinations across the bottom of the screen.
 *
 * WHAT IT REPLACED. The rail used to become a horizontal strip at the top on a
 * phone, and seven destinations do not fit across 390 points, so it scrolled —
 * which meant the bar opened showing "Debts", "Co" and "Impor", three of the
 * seven and two of them cut off mid-word. A reader has no way to know a strip
 * scrolls sideways until they try it, and a truncated word does not read as
 * "there is more here", it reads as broken.
 *
 * Five, not seven, because five is what fits at a legible size — and because
 * the split is a real one rather than an arbitrary cut. These five are the
 * views; Import and Settings are the two things you operate, and they sit in
 * the small bar at the top instead. Nothing is behind a "More" menu.
 *
 * At the bottom because that is where the thumb is, and because a phone browser
 * puts its own chrome down there too — the safe-area inset in the stylesheet is
 * what keeps this clear of the home indicator.
 */
export function TabBar({ items, label }: { items: NavItem[]; label: string }) {
  const path = usePathname();
  const here = (href: string) =>
    href === '/' ? path === '/' : path.startsWith(href);

  return (
    <nav className="tabbar" aria-label={label}>
      {items.map((it) => (
        <Link key={it.href} href={it.href}
              aria-current={here(it.href) ? 'page' : undefined}>
          {it.icon}
          <span>{it.label}</span>
        </Link>
      ))}
    </nav>
  );
}

/**
 * The hidden `back` field on the language and theme switches.
 *
 * Both are server actions that write a cookie and redirect, and both must come
 * back to the page the reader was on — changing language halfway down a
 * filtered list and landing on the overview loses the filter and the scroll.
 * The path has to be read on the client for the same reason as above: the
 * layout holding these forms is not re-rendered when the page under it
 * changes, so a value baked in on the server would send you back to wherever
 * you happened to enter the app.
 */
export function BackField() {
  return <input type="hidden" name="back" value={usePathname()} />;
}
