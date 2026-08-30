import './globals.css';
import { Noto_Sans_Hebrew, Poppins } from 'next/font/google';
import { dir, getLocale, getTheme } from '@/lib/i18n';

/**
 * The document, and nothing else.
 *
 * The app's furniture — sidebar, topbar, account block — used to live here too,
 * switched off by a path test when the page was /login. That test read the
 * pathname from a request header, and it was correct only for as long as every
 * navigation was a full page load. Once the nav became client-side the root
 * layout stopped re-rendering between routes, so the test would go stale and a
 * sign-out could land on the login form with the entire signed-in menu still
 * wrapped around it — the exact thing reported on 26 Aug.
 *
 * So the shell moved into `app/(app)/layout.tsx`. `(app)` is a route group: the
 * parentheses keep it out of the URL, so `/tickets` is still `/tickets`, but it
 * is a real layout boundary. /login sits outside it and therefore cannot have
 * the shell, by structure rather than by a condition somebody has to remember.
 */

/**
 * Two families, both self-hosted.
 *
 * Poppins is the design system's face and covers Latin and digits. It has no
 * Hebrew — not one glyph — and half of this interface is Hebrew, so Noto Sans
 * Hebrew sits immediately behind it in the stack and the browser resolves per
 * glyph: Poppins for a reference number, Noto for the name beside it.
 *
 * `next/font` rather than the system's `@import url(fonts.googleapis.com)`.
 * That import is a render-blocking request to a third party on every cold
 * load — DNS, TLS, then a CSS file that itself points at more files. next/font
 * downloads both faces at build time, serves them from our own origin and
 * inlines the @font-face rules into the page, so the text paints in the right
 * face the first time.
 */
const poppins = Poppins({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-poppins',
});

const hebrew = Noto_Sans_Hebrew({
  subsets: ['hebrew', 'latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-hebrew',
});

export const metadata = { title: 'Homies' };
// Never cache. Every page here is a live view of a table that changes while
// someone is looking at it.
export const dynamic = 'force-dynamic';

export default function Layout({ children }: { children: React.ReactNode }) {
  const locale = getLocale();
  const theme = getTheme();

  return (
    <html lang={locale} dir={dir(locale)} data-theme={theme}
          className={`${poppins.variable} ${hebrew.variable}`}>
      <body>{children}</body>
    </html>
  );
}
