import './globals.css';
import { Noto_Sans_Hebrew } from 'next/font/google';
import { cookies, headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { serverClient } from '@/lib/supabase-server';
import { COOKIE, dir, getLocale, translator, type Locale } from '@/lib/i18n';
import { NAV_ICON, IconBuilding, IconLanguage, IconSignOut } from '@/components/icons';

// One family that covers both alphabets. The old stack was system-ui, which on
// Windows renders Hebrew in whatever the OS falls back to — usually a face with
// a different weight and x-height from the Latin beside it, which is why the
// mixed rows looked pasted together. next/font self-hosts it, so there is no
// request to Google at runtime and no flash of the fallback.
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

const NAV = [
  ['overview', '/'],
  ['tickets', '/tickets'],
  ['debts', '/debts'],
  ['conversations', '/conversations'],
  ['calls', '/calls'],
  ['sync', '/sync'],
] as const;

export default async function Layout({ children }: { children: React.ReactNode }) {
  const { data: { user } } = await serverClient().auth.getUser();
  const locale = getLocale();
  const t = translator(locale);
  const other: Locale = locale === 'he' ? 'en' : 'he';

  // Which nav item to mark current, and where the language switch comes back
  // to. The path arrives as a request header the middleware sets — see the note
  // there for why neither `x-invoke-path` nor `referer` works.
  const path = headers().get('x-pathname') || '/';
  const here = (href: string) =>
    href === '/' ? path === '/' : path.startsWith(href);

  // The login page stands alone. Rendering the sidebar around a sign-in form
  // shows a logged-out visitor the app's entire menu — six links they cannot
  // use, wrapped around the box that says they cannot use them. Reported from
  // a screenshot on 26 Aug, the day the wall went up: the shell below is the
  // signed-in furniture, and /login is by definition the one page whose reader
  // is not signed in. The middleware guarantees this is also the ONLY page a
  // logged-out visitor reaches, so one path test covers every case.
  if (path === '/login') {
    return (
      <html lang={locale} dir={dir(locale)} className={hebrew.variable}>
        <body>
          {children}
        </body>
      </html>
    );
  }

  return (
    <html lang={locale} dir={dir(locale)} className={hebrew.variable}>
      <body>
        <div className="shell">
          {/* The sign-out button only appears when a session exists. */}
          <nav className="rail" aria-label={t('nav.menu')}>
            <a className="brand" href="/">
              <span className="mark"><IconBuilding /></span>
              <span>
                <b>{t('app.name')}</b>
                <small>{t('app.subtitle')}</small>
              </span>
            </a>

            <div className="navlist">
              {NAV.map(([key, href]) => {
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
              {user && (
                <form action={signOut} className="langswitch">
                  <button type="submit">
                    <IconSignOut />
                    <span>{t('nav.signOut')}</span>
                  </button>
                </form>
              )}
            </div>
          </nav>

          <main>
            <div className="page">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
