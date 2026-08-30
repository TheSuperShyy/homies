import Link from 'next/link';
import { cookies, headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { serverClient } from '@/lib/supabase-server';
import { COOKIE, THEME_COOKIE, getLocale, getTheme, translator, type Locale } from '@/lib/i18n';
import { BackField, RailNav, type NavGroup } from '@/components/nav';
import {
  NAV_ICON, IconBell, IconBuilding, IconLanguage, IconMoon, IconSearch,
  IconSettings, IconSignOut, IconSun,
} from '@/components/icons';

/**
 * The signed-in furniture: sidebar, topbar, account block.
 *
 * This is a route-group layout — `(app)` never appears in a URL — and it wraps
 * every page except /login. That is the whole point: /login is outside the
 * group, so it cannot render the shell, and nobody has to maintain a condition
 * that says so.
 *
 * It stays mounted across navigation, which is what makes moving between
 * tickets and debts feel instant instead of reloading the tab. Two consequences
 * follow from that and are handled in `components/nav.tsx`: anything in here
 * that depends on WHICH page is showing has to read the path on the client,
 * because this file is not re-rendered when the page under it changes.
 */

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

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const locale = getLocale();
  const theme = getTheme();
  const t = translator(locale);
  const other: Locale = locale === 'he' ? 'en' : 'he';

  // WHO IS SIGNED IN, WITHOUT ASKING TWICE. This used to be
  // `await serverClient().auth.getUser()`, which is a full network round trip
  // to the auth server — and the middleware had already made exactly that call
  // for exactly this request, one millisecond earlier, to decide whether to let
  // it through at all. Two identical round trips, and the second one blocked
  // the entire shell: nothing could stream to the browser, not even the
  // sidebar, until it came back. The middleware now passes what it learned
  // down as a request header, so this is free.
  const email = headers().get('x-user-email') || '';
  const name = email ? email.split('@')[0].replace(/[._-]+/g, ' ') : '';
  const initials = (name || 'H').trim().slice(0, 2);

  // The icons are rendered here and handed to the client nav as elements, so
  // the icon set never crosses into the browser bundle.
  const groups: NavGroup[] = NAV.map(([group, items]) => ({
    label: t(group as any),
    items: items.map(([key, href]) => {
      const Icon = NAV_ICON[key];
      return { href, label: t(`nav.${key}` as any), icon: <Icon /> };
    }),
  }));

  return (
    <div className="shell">
      <nav className="rail" aria-label={t('nav.menu')}>
        <Link className="brand" href="/">
          <span className="mark"><IconBuilding /></span>
          <span>
            <b>{t('app.name')}</b>
            <small>{t('app.subtitle')}</small>
          </span>
        </Link>

        {/* The reference puts the greeting in the sidebar, under the wordmark,
            rather than in the page. It belongs to the session, not to the view,
            and keeping it out of the content column means every page can open
            with its own H1 instead of repeating it. */}
        <div className="railgreet">
          <b>{name ? `${t('chrome.greeting')}, ${name}` : t('chrome.greeting')}</b>
          <small>{t('chrome.greetingSub')}</small>
        </div>

        <RailNav groups={groups} />

        <div className="railfoot">
          <form action={setLocale} className="langswitch">
            <input type="hidden" name="to" value={other} />
            <BackField />
            <button type="submit" aria-label={t('lang.switchLabel')}>
              <IconLanguage />
              <span>{t('lang.switch')}</span>
            </button>
          </form>
          {email && (
            <form action={signOut} className="langswitch">
              {/* The label is hidden below the sidebar breakpoint, so the
                  accessible name has to come from somewhere else or the button
                  becomes an unnamed icon on a phone. */}
              <button type="submit" aria-label={t('nav.signOut')}>
                <IconSignOut />
                <span>{t('nav.signOut')}</span>
              </button>
            </form>
          )}
        </div>
      </nav>

      <div className="col">
        {/* The topbar is desk-only, by CSS. On a phone the rail already occupies
            the top of the screen and a second bar under it would take a third
            of the viewport before any content. */}
        <header className="topbar">
          <div className="mid">
            {/* PLACEHOLDER, AND LABELLED AS ONE. The reference's centre is a
                search pill, and nothing in this app searches tickets, debts,
                conversations and calls in one query — building that means new
                data logic, which this pass does not touch. So it is drawn to the
                system's exact Input spec, disabled, and says "soon" rather than
                quietly swallowing what you type. */}
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
              <BackField />
              <span className="lbl" aria-hidden="true">
                {theme === 'light' ? <IconSun /> : <IconMoon />}
              </span>
              <button type="submit" aria-pressed={theme === 'light'}
                      aria-label={t('theme.switchLabel')}>
                <span className="knob" />
              </button>
            </form>

            {/* Both placeholders. There is no notification store and no settings
                page; drawing them live and dead is the honest state of the
                shell, and removing them would mean redrawing this bar the day
                either one exists. */}
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
                    photographs of Homies staff and there is no field to put one
                    in, so this is the system's own initials fallback, which is a
                    real component and not a stand-in. */}
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
  );
}
