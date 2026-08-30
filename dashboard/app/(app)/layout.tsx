import Link from 'next/link';
import { cookies, headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { serverClient } from '@/lib/supabase-server';
import { COOKIE, THEME_COOKIE, getLocale, getTheme, translator, type Locale } from '@/lib/i18n';
import { BackField, RailNav, TabBar, type NavGroup, type NavItem } from '@/components/nav';
import {
  NAV_ICON, IconImport, IconLanguage, IconMoon, IconSearch,
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
// the things you operate. The division is a true one — the second group is the
// only place in the app where pressing something changes state rather than
// filtering a view.
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
    ['settings', '/settings'],
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
  //
  // The chosen name and photo ride along on the same request for the same
  // reason; both are metadata on the auth user, so the call the middleware
  // already made carries them. The name is percent-encoded there because
  // headers are latin-1 and Hebrew is not.
  const h = headers();
  const email = h.get('x-user-email') || '';
  const encoded = h.get('x-user-name');
  const chosen = encoded ? decodeURIComponent(encoded) : '';
  const photo = h.get('x-user-avatar') || '';
  // The email-derived name is the fallback, not the value. It was always a
  // guess — "clixteam579" is not what anybody is called — and now there is
  // somewhere to say so properly.
  const name = chosen || (email ? email.split('@')[0].replace(/[._-]+/g, ' ') : '');
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

  // The same five destinations as the sidebar's first group, under the names
  // they go by when a label has 78px rather than 200 — see `tab.*` in i18n.
  const tabs: NavItem[] = NAV[0][1].map(([key, href]) => {
    const Icon = NAV_ICON[key];
    return { href, label: t(`tab.${key}` as any), icon: <Icon /> };
  });

  return (
    <div className="shell">
      <nav className="rail" aria-label={t('nav.menu')}>
        <Link className="brand" href="/">
          {/* The real mark, not the generic building glyph that stood in for
              it. Two files rather than one because the logo carries a black
              ladder and figure that disappear on a near-black sidebar; the
              dark variant draws both in white.

              THE VARIANT IS PICKED HERE, ON THE SERVER, because the theme is a
              cookie this layout has already read. The login page used to do
              this with `<picture media="(prefers-color-scheme: dark)">`, which
              was right while the theme followed the operating system and wrong
              the moment it became a switch in the topbar — a reader on a light
              OS who chose the dark theme got the black-figure logo on a black
              ground. Same asset, same bug, fixed the same way. */}
          <img className="mark" alt=""
               src={theme === 'light' ? '/homies-mark.png' : '/homies-mark-dark.png'} />
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
                <IconSignOut className="flipx" />
                <span>{t('nav.signOut')}</span>
              </button>
            </form>
          )}
        </div>
      </nav>

      {/* THE PHONE'S TOP BAR. Brand on one side, the two things you operate on
          the other — Import and Settings — which are exactly the two the tab
          bar below does not carry. Desk-width readers never see this; they have
          the sidebar, which has all seven. */}
      <header className="mtop">
        <Link className="brand" href="/">
          <img className="mark" alt=""
               src={theme === 'light' ? '/homies-mark.png' : '/homies-mark-dark.png'} />
          <span><b>{t('app.name')}</b></span>
        </Link>
        <div className="mtop-acts">
          <Link className="iconbtn" href="/sync"
                aria-label={t('nav.sync')} title={t('nav.sync')}>
            <IconImport />
          </Link>
          <Link className="iconbtn" href="/settings"
                aria-label={t('nav.settings')} title={t('nav.settings')}>
            <IconSettings />
          </Link>
        </div>
      </header>

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

            {/* The gear is a real destination now. The bell that used to sit
                beside it is gone rather than left dim: nothing in this app
                raises a notification, there is no store to put one in, and a
                permanently disabled control is furniture the reader has to
                learn to ignore. It comes back the day something has to be
                announced, and not before. */}
            <Link className="iconbtn" href="/settings"
                  aria-label={t('chrome.settings')} title={t('chrome.settings')}>
              <IconSettings />
            </Link>

            {email && (
              // A link, because the name in the corner is where half of all
              // readers look for their own account before they find the gear.
              <Link className="who-block" href="/settings">
                {/* The reference uses photographic avatars, and since 30 Aug
                    there is somewhere to put one — /settings. Initials are the
                    fallback for an account that has not set one, which is the
                    system's own variant and a real component rather than a
                    stand-in. */}
                <span className="avatar" aria-hidden="true">
                  {photo ? <img src={photo} alt="" /> : initials}
                </span>
                <span>
                  <b dir="auto">{name}</b>
                  <small>{email}</small>
                </span>
              </Link>
            )}
          </div>
        </header>

        <main>
          <div className="page">{children}</div>
        </main>
      </div>

      <TabBar items={tabs} label={t('nav.tabs')} />
    </div>
  );
}
