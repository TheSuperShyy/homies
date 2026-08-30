import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { serverClient } from '@/lib/supabase-server';
import {
  COOKIE, THEME_COOKIE, getLocale, getTheme, translator, type Key, type Locale,
} from '@/lib/i18n';
import { IconAlert, IconCheck, IconMoon, IconSignOut, IconSun } from '@/components/icons';

/**
 * The account page: who you are signed in as, your password, and the two
 * choices this dashboard remembers about you.
 *
 * WHAT IS DELIBERATELY NOT HERE. No display name, no avatar upload, no
 * notification preferences, no team management. There is no profile table to
 * hold a name, no store to raise a notification from, and no role column to
 * manage — every signed-in account reads every table through one policy called
 * `staff_read`. A settings page whose controls do nothing is worse than a short
 * one, so this is the short one, and it says out loud what it does not do.
 *
 * NO CLIENT JAVASCRIPT. Every control is a form posting to a server action that
 * writes and redirects back here, the same shape the language switch in the
 * shell already uses. Feedback comes back in the query string, because that is
 * where this dashboard puts state everywhere else.
 */

/** Dates here carry a year — "signed in 04/09" is ambiguous on an old account. */
function fullDate(iso: string | null | undefined, l: Locale) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return new Intl.DateTimeFormat(l === 'he' ? 'he-IL' : 'en-GB', {
    timeZone: 'Asia/Jerusalem',
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(d);
}

async function signOut() {
  'use server';
  await serverClient().auth.signOut();
  redirect('/login');
}

// The shell defines its own copies of these two. A server action declared in a
// layout cannot be imported by a page, so they are duplicated rather than
// shared — the same reason the login page carries its own setLocale. Both
// always come back here, so neither needs the shell's hidden `back` field.
async function setLocale(formData: FormData) {
  'use server';
  const next = String(formData.get('to') ?? 'he') === 'en' ? 'en' : 'he';
  cookies().set(COOKIE, next, { path: '/', maxAge: 60 * 60 * 24 * 365, sameSite: 'lax' });
  redirect('/settings');
}

async function setTheme(formData: FormData) {
  'use server';
  const next = String(formData.get('to') ?? 'dark') === 'light' ? 'light' : 'dark';
  cookies().set(THEME_COOKIE, next, { path: '/', maxAge: 60 * 60 * 24 * 365, sameSite: 'lax' });
  redirect('/settings');
}

/**
 * Change the signed-in account's password.
 *
 * THE CURRENT PASSWORD IS CHECKED EVEN THOUGH SUPABASE DOES NOT REQUIRE IT.
 * `updateUser({ password })` will happily rewrite the password of whoever holds
 * the session cookie, which means an unlocked laptop on a desk in the office is
 * enough to lock the owner out of their own dashboard. Signing in again with
 * the password typed in the first box costs one round trip and closes that.
 *
 * Nothing is caught here: `redirect()` works by throwing, so a try/catch around
 * any of this would swallow the redirect and render a blank action.
 */
async function changePassword(formData: FormData) {
  'use server';
  const current = String(formData.get('current') ?? '');
  const next = String(formData.get('next') ?? '');
  const again = String(formData.get('again') ?? '');

  // Cheap checks first, so a typo in the confirmation never reaches the auth
  // server and never counts against its rate limit.
  if (next !== again) redirect('/settings?e=mismatch');
  if (next.length < 8) redirect('/settings?e=short');
  if (next === current) redirect('/settings?e=same');

  const db = serverClient();
  const { data: { user } } = await db.auth.getUser();
  if (!user?.email) redirect('/login');

  const { error: wrong } = await db.auth.signInWithPassword({
    email: user.email, password: current,
  });
  // 400 is "those credentials are not right". Anything else — 429 from the rate
  // limiter, a 5xx — is not the reader's mistake and must not be reported as
  // one, or they sit there retyping a password that was correct all along.
  if (wrong) redirect(wrong.status === 400 ? '/settings?e=wrong' : '/settings?e=failed');

  const { error } = await db.auth.updateUser({ password: next });
  if (error) redirect('/settings?e=failed');
  redirect('/settings?ok=1');
}

const ERRORS: Record<string, Key> = {
  wrong: 'settings.errWrong',
  mismatch: 'settings.errMismatch',
  short: 'settings.errShort',
  same: 'settings.errSame',
  failed: 'settings.errFailed',
};

export default async function Settings({ searchParams }: {
  searchParams?: { ok?: string; e?: string };
}) {
  const locale = getLocale();
  const theme = getTheme();
  const t = translator(locale);

  // The shell gets the email from a header the middleware set, precisely to
  // avoid this call. This page asks properly because it needs the two
  // timestamps as well, and one round trip on one page is the honest cost of
  // showing when the account was opened.
  const { data: { user } } = await serverClient().auth.getUser();
  const email = user?.email ?? '';
  const name = email ? email.split('@')[0].replace(/[._-]+/g, ' ') : '';
  const initials = (name || 'H').trim().slice(0, 2);

  const err = searchParams?.e ? ERRORS[searchParams.e] : undefined;

  return (
    // One column for the whole page, heading and banner included — see .setpage.
    <div className="setpage">
      <div className="pagehead">
        <h1>{t('settings.title')}</h1>
        <p>{t('settings.blurb')}</p>
      </div>

      {/* role="status" and role="alert": the outcome of pressing a button has to
          reach a screen reader, and after a redirect there is nothing else on
          the page to say whether it worked. */}
      {searchParams?.ok && (
        <div className="notice ok" role="status">
          <IconCheck /><span>{t('settings.pwSaved')}</span>
        </div>
      )}
      {err && (
        <div className="notice bad" role="alert">
          <IconAlert /><span>{t(err)}</span>
        </div>
      )}

      <div className="setcol">
        <section>
          <h2>{t('settings.account')}</h2>
          <div className="panel">
            <div className="setwho">
              <span className="avatar" aria-hidden="true">{initials}</span>
              <span>
                <b dir="auto">{name}</b>
                <small>{t('chrome.staff')}</small>
              </span>
            </div>
            <div className="setrow">
              <span className="lbl">{t('settings.email')}</span>
              <span className="val mono">{email || '—'}</span>
            </div>
            <div className="setrow">
              <span className="lbl">{t('settings.lastSignIn')}</span>
              <span className="val">{fullDate(user?.last_sign_in_at, locale)}</span>
            </div>
            <div className="setrow">
              <span className="lbl">{t('settings.created')}</span>
              <span className="val">{fullDate(user?.created_at, locale)}</span>
            </div>
            <p className="setnote">
              {t('settings.accessAll')} {t('settings.whoAdds')}
            </p>
          </div>
        </section>

        <section>
          <h2>{t('settings.password')}</h2>
          <div className="panel">
            <form className="setform" action={changePassword}>
              {/* A password manager will not offer to save an update unless it
                  can see which account the new password belongs to. This is
                  that field, hidden, and the action never reads it. */}
              <input type="text" name="username" autoComplete="username"
                     value={email} readOnly hidden aria-hidden="true" tabIndex={-1} />

              <label htmlFor="current">{t('settings.currentPw')}</label>
              <input id="current" name="current" type="password" required
                     autoComplete="current-password" />

              <label htmlFor="next">{t('settings.newPw')}</label>
              <input id="next" name="next" type="password" required minLength={8}
                     autoComplete="new-password" aria-describedby="pwrule" />

              <label htmlFor="again">{t('settings.againPw')}</label>
              <input id="again" name="again" type="password" required minLength={8}
                     autoComplete="new-password" />

              <p className="hint" id="pwrule">{t('settings.pwRule')}</p>
              <div><button type="submit">{t('settings.pwSave')}</button></div>
            </form>
          </div>
        </section>

        <section>
          <h2>{t('settings.appearance')}</h2>
          <div className="panel">
            <div className="setrow">
              <span className="lbl">{t('settings.theme')}</span>
              {/* Two one-button forms rather than a toggle. A toggle only ever
                  says "the other one"; these say which of the two you are on,
                  which is the thing a settings page exists to answer. */}
              <div className="choice">
                <form action={setTheme}>
                  <input type="hidden" name="to" value="dark" />
                  <button type="submit" aria-pressed={theme === 'dark'}>
                    <IconMoon />{t('theme.dark')}
                  </button>
                </form>
                <form action={setTheme}>
                  <input type="hidden" name="to" value="light" />
                  <button type="submit" aria-pressed={theme === 'light'}>
                    <IconSun />{t('theme.light')}
                  </button>
                </form>
              </div>
            </div>
            <div className="setrow">
              <span className="lbl">{t('settings.language')}</span>
              {/* Each language written in itself. "Hebrew" is no use to a reader
                  who cannot read the label telling them where Hebrew is. */}
              <div className="choice">
                <form action={setLocale}>
                  <input type="hidden" name="to" value="he" />
                  <button type="submit" lang="he" aria-pressed={locale === 'he'}>עברית</button>
                </form>
                <form action={setLocale}>
                  <input type="hidden" name="to" value="en" />
                  <button type="submit" lang="en" aria-pressed={locale === 'en'}>English</button>
                </form>
              </div>
            </div>
            <p className="setnote">{t('settings.remembered')}</p>
          </div>
        </section>

        <section>
          <h2>{t('settings.session')}</h2>
          <div className="panel">
            <div className="setrow">
              <span className="lbl">{t('settings.signOutNote')}</span>
              <form action={signOut}>
                <button type="submit" className="danger">
                  <IconSignOut className="flipx" />{t('nav.signOut')}
                </button>
              </form>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
