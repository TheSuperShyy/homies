import './globals.css';
import { Noto_Sans_Hebrew, Poppins } from 'next/font/google';
import { cookies, headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { serverClient } from '@/lib/supabase-server';
import {
  COOKIE, THEME_COOKIE, dir, getLocale, getTheme, translator, type Locale,
} from '@/lib/i18n';
import {
  NAV_ICON, IconBell, IconBuilding, IconLanguage, IconMoon, IconSearch,
  IconSettings, IconSignOut, IconSun,
} from '@/components/icons';

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

async function signOut() {
  'use server';
  await serverClient().auth.signOut();
  redirect('/login');
}

// Writes the reader's language and comes back to the page they were on. A
// server action rather than a link because it changes state: a GET that
// rewrites a cookie is one a prefetch can fire without anybody clicking.
async function setLocale(formData: FormData) {
  'use server';
  const next = String(formData.get('to') ?? 'he') === 'en' ? 'en' : 'he';
  cookies().set(COOKIE, next, { path: '/', maxAge: 60 * 60 * 24 * 365, sameSite: 'lax' });
  redirect(String(formData.get('back') ?? '/'));
}

// Same shape for the theme, and for the same reason. Server-side means the
// `data-theme` attribute is in the first byte of HTML, so there is no frame
// where the page is dark and then turns light.
async function setTheme(formData: FormData) {
  'use server';
  const next = String(formData.get('to') ?? 'dark') === 'light' ? 'light' : 'dark';
  cookies().set(THEME_COOKIE, next, { path: '/', maxAge: 60 * 60 * 24 * 365, sameSite: 'lax' });
  redirect(String(formData.get('back') ?? '/'));
}

// Grouped, the way the design system's sidebar is: the things you look at, then
// the thing you operate. One group of five and one of one is not much of a
// division, but it is a true one — Import is the only page that writes.
const NAV = [
  ['nav.group.main', [
    ['overview', '/'],
    ['tickets', '/tickets'],
    ['debts', '/debts'],
    ['conversations', '/conversations'],
    ['calls', '/calls'],
  ]],
  ['nav.group.support', [
    ['sync', '/sync'],
  ]],
] as const;

export default async function Layout({ children }: { children: React.ReactNode }) {
  const locale = getLocale();
  const theme = getTheme();
  const t = translator(locale);
  const other: Locale = locale === 'he' ? 'en' : 'he';

  const h = headers();
  // Which nav item to mark current, and where the two switches come back to.
  // The path arrives as a request header the middleware sets — see the note
  // there for why neither `x-invoke-path` nor `referer` works.
  const path = h.get('x-pathname') || '/';
  const here = (href: string) =>
    href === '/' ? path === '/' : path.startsWith(href);

  // WHO IS SIGNED IN, WITHOUT ASKING TWICE. This used to be
  // `await serverClient().auth.getUser()`, which is a full network round trip
  // to the auth server — and the middleware had already made exactly that call
  // for exactly this request, one millisecond earlier, to decide whether to let
  // it through at all. Two identical round trips, and the second one blocked
  // the entire shell: nothing could stream to the browser, not even the
  // sidebar, until it came back. The middleware now passes what it learned
  // down as a request header, so this is free.
  const email = h.get('x-user-email') || '';
  const name = email ? email.split('@')[0].replace(/[._-]+/g, ' ') : '';
  const initials = (name || 'H').trim().slice(0, 2);

  // The login page stands alone. Rendering the sidebar around a sign-in form
  // shows a logged-out visitor the app's entire menu — six links they cannot
  // use, wrapped around the box that says they cannot use them. Reported from
  // a screenshot on 26 Aug, the day the wall went up: the shell below is the
  // signed-in furniture, and /login is by definition the one page whose reader
  // is not signed in. The middleware guarantees this is also the ONLY page a
  // logged-out visitor reaches, so one path test covers every case.
  if (path === '/login') {
    return (
      <html lang={locale} dir={dir(locale)} data-theme={theme}
            className={`${poppins.variable} ${hebrew.variable}`}>
        <body>{children}</body>
      </html>
    );
  }

  return (
    <html lang={locale} dir={dir(locale)} data-theme={theme}
          className={`${poppins.variable} ${hebrew.variable}`}>
      <body>
        <div className="shell">
          <nav className="rail" aria-label={t('nav.menu')}>
            <a className="brand" href="/">
              <span className="mark"><IconBuilding /></span>
              <span>
                <b>{t('app.name')}</b>
                <small>{t('app.subtitle')}</small>
              </span>
            </a>

            {/* The reference puts the greeting in the sidebar, under the
                wordmark, rather than in the page. It belongs to the session,
                not to the view, and keeping it out of the content column means
                every page can open with its own H1 instead of repeating it. */}
            <div className="railgreet">
              <b>{name ? `${t('chrome.greeting')}, ${name}` : t('chrome.greeting')}</b>
              <small>{t('chrome.greetingSub')}</small>
            </div>

            {NAV.map(([group, items]) => (
              <div key={group} className="navgroupwrap">
                <div className="navgroup">{t(group as any)}</div>
                <div className="navlist">
                  {items.map(([key, href]) => {
                    const Icon = NAV_ICON[key];
                    return (
                      <a key={href} href={href}
                         aria-current={here(href) ? 'page' : undefined}>
                        <Icon />
                        <span>{t(`nav.${key}` as any)}</span>
                      </a>
                    );
                  })}
                </div>
              </div>
            ))}

            <div className="railfoot">
              <form action={setLocale} className="langswitch">
                <input type="hidden" name="to" value={other} />
                {/* Back to the page they were reading, not to the home
                    page: changing language mid-way through a filtered list and
                    landing on the overview loses the filter and the scroll. */}
                <input type="hidden" name="back" value={path} />
                <button type="submit" aria-label={t('lang.switchLabel')}>
                  <IconLanguage />
                  <span>{t('lang.switch')}</span>
                </button>
              </form>
              {email && (
                <form action={signOut} className="langswitch">
                  {/* The label is hidden below the sidebar breakpoint, so the
                      accessible name has to come from somewhere else or the
                      button becomes an unnamed icon on a phone. */}
                  <button type="submit" aria-label={t('nav.signOut')}>
                    <IconSignOut />
                    <span>{t('nav.signOut')}</span>
                  </button>
                </form>
              )}
            </div>
          </nav>

          <div className="col">
            {/* The topbar is desk-only, by CSS. On a phone the rail already
                occupies the top of the screen and a second bar under it would
                take a third of the viewport before any content. */}
            <header className="topbar">
              <div className="mid">
                {/* PLACEHOLDER, AND LABELLED AS ONE. The reference's centre is
                    a search pill, and nothing in this app searches tickets,
                    debts, conversations and calls in one query — building that
                    means new data logic, which this pass does not touch. So it
                    is drawn to the system's exact Input spec, disabled, and
                    says "soon" rather than quietly swallowing what you type. */}
                <div className="searchpill is-placeholder">
                  <IconSearch />
                  <input type="search" disabled aria-disabled="true"
                         placeholder={t('chrome.search')} />
                  <span className="soon">{t('chrome.soon')}</span>
                </div>
              </div>

              <div className="right">
                <form action={setTheme} className="themeswitch">
                  <input type="hidden" name="to" value={theme === 'light' ? 'dark' : 'light'} />
                  <input type="hidden" name="back" value={path} />
                  <span className="lbl" aria-hidden="true">
                    {theme === 'light' ? <IconSun /> : <IconMoon />}
                  </span>
                  <button type="submit" aria-pressed={theme === 'light'}
                          aria-label={t('theme.switchLabel')}>
                    <span className="knob" />
                  </button>
                </form>

                {/* Both placeholders. There is no notification store and no
                    settings page; drawing them live and dead is the honest
                    state of the shell, and removing them would mean redrawing
                    this bar the day either one exists. */}
                <span className="iconbtn" aria-disabled="true"
                      title={`${t('chrome.notifications')} — ${t('chrome.soon')}`}>
                  <IconBell />
                </span>
                <span className="iconbtn" aria-disabled="true"
                      title={`${t('chrome.settings')} — ${t('chrome.soon')}`}>
                  <IconSettings />
                </span>

                {email && (
                  <div className="who-block">
                    {/* The reference uses photographic avatars. There are no
                        photographs of Homies staff and there is no field to put
                        one in, so this is the system's own initials fallback,
                        which is a real component and not a stand-in. */}
                    <span className="avatar" aria-hidden="true">{initials}</span>
                    <span>
                      <b dir="auto">{name}</b>
                      <small>{email}</small>
                    </span>
                  </div>
                )}
              </div>
            </header>

            <main>
              <div className="page">{children}</div>
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
