// What the dashboard shows (25 Nov 2026). The owner: "in the dashboard i want everything gone only
// the dialer and call related should be seen here".
//
// One list, read by the menu (app/(app)/layout.tsx) and by the middleware, which sends a signed-in
// visitor on any other page to the dialer. The other pages (overview, tickets, debts, WhatsApp
// conversations, search, import) are still in the code, untouched: putting one back is adding its
// path here and its row to the menu.
//
// No imports, so the middleware can read it and scripts/check_sections.test.ts can run it under Node.

/** Where the dashboard opens, and where a hidden page sends you. */
export const HOME = '/dialer';

/** The pages that stay: the dialer (and its test calls), the phone calls, the agent's browser call,
 *  and the account's own settings (reached from the gear, not the menu). */
export const SHOWN = ['/dialer', '/calls', '/voice', '/settings'] as const;

/** Not dashboard pages at all: the sign-in, the reviewers' key-only pages, the API routes. */
const PASS = ['/login', '/review', '/api'] as const;

/** A path the dashboard no longer shows, so it goes to HOME instead. */
export function hiddenPath(path: string): boolean {
  const under = (p: string) => path === p || path.startsWith(p + '/');
  return !(PASS.some(under) || SHOWN.some(under));
}
