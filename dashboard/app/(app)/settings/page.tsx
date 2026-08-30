import { serverClient } from '@/lib/supabase-server';
import { getLocale, getTheme, translator, type Key, type Locale } from '@/lib/i18n';
import { IconAlert, IconCheck, IconMoon, IconSignOut, IconSun } from '@/components/icons';
import { AvatarPicker } from '@/components/avatar-picker';
import {
  changePassword, removeAvatar, saveAvatar, saveName, setLocale, setTheme, signOut,
} from './actions';

/**
 * The account page: who you are signed in as, how you appear to the rest of the
 * interface, your password, and the two choices this dashboard remembers.
 *
 * WHAT IS DELIBERATELY NOT HERE. No notification preferences and no roles.
 * There is no store to raise a notification from, and one policy — `staff_read`
 * — grants every signed-in account the same read of every table. A settings
 * page whose switches do nothing is worse than a short one, so this is the
 * short one, and it says out loud what it does not do.
 *
 * ALMOST NO CLIENT JAVASCRIPT. Every control here is a form posting to a server
 * action that writes and redirects back, and the outcome comes back in the
 * query string — the shape this dashboard uses everywhere else. The one
 * exception is the photo, which has to be resized in the browser; see
 * `components/avatar-picker.tsx` for why.
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

const ERRORS: Record<string, Key> = {
  wrong: 'settings.errWrong',
  mismatch: 'settings.errMismatch',
  short: 'settings.errShort',
  same: 'settings.errSame',
  failed: 'settings.errFailed',
  image: 'settings.errImage',
  big: 'settings.errBig',
  upload: 'settings.errUpload',
};

const DONE: Record<string, Key> = {
  password: 'settings.pwSaved',
  name: 'settings.nameSaved',
  photo: 'settings.photoSaved',
};

export default async function Settings({ searchParams }: {
  searchParams?: { ok?: string; e?: string };
}) {
  const locale = getLocale();
  const theme = getTheme();
  const t = translator(locale);

  // The shell gets its copy of all this from headers the middleware set,
  // precisely to avoid asking. This page asks properly because it needs the two
  // timestamps as well, and one round trip on one page is the honest cost of
  // showing when the account was opened.
  const { data: { user } } = await serverClient().auth.getUser();
  const meta = (user?.user_metadata ?? {}) as { display_name?: string; avatar_url?: string };
  const email = user?.email ?? '';
  const chosen = (meta.display_name ?? '').trim();
  const fallback = email ? email.split('@')[0].replace(/[._-]+/g, ' ') : '';
  const initials = (chosen || fallback || 'H').trim().slice(0, 2);

  const err = searchParams?.e ? ERRORS[searchParams.e] : undefined;
  const done = searchParams?.ok ? DONE[searchParams.ok] : undefined;

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
      {done && (
        <div className="notice ok" role="status">
          <IconCheck /><span>{t(done)}</span>
        </div>
      )}
      {err && (
        <div className="notice bad" role="alert">
          <IconAlert /><span>{t(err)}</span>
        </div>
      )}

      <div className="setcol">
        <section>
          <h2>{t('settings.profile')}</h2>
          <div className="panel">
            <AvatarPicker
              current={meta.avatar_url ?? ''}
              initials={initials}
              save={saveAvatar}
              remove={removeAvatar}
              labels={{
                choose: t('settings.photoChoose'),
                change: t('settings.photoChange'),
                remove: t('settings.photoRemove'),
                save: t('settings.photoSave'),
                saving: t('settings.photoSaving'),
                hint: t('settings.photoHint'),
                errType: t('settings.errImage'),
                errBig: t('settings.errBig'),
                errRead: t('settings.errRead'),
              }}
            />

            <form className="setinline" action={saveName}>
              <label htmlFor="name">{t('settings.name')}</label>
              <div className="row">
                {/* `dir="auto"` so a Hebrew name is not laid out left-to-right
                    inside an interface the reader has set to English, and vice
                    versa. The field belongs to whatever is typed in it. */}
                <input id="name" name="name" type="text" dir="auto" maxLength={60}
                       defaultValue={chosen} placeholder={fallback}
                       aria-describedby="namehint" />
                <button type="submit">{t('settings.nameSave')}</button>
              </div>
              <p className="hint" id="namehint">{t('settings.nameHint')}</p>
            </form>
          </div>
        </section>

        <section>
          <h2>{t('settings.account')}</h2>
          <div className="panel">
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
