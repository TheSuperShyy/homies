import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { COOKIE, getLocale, getTheme, translator, type Locale } from '@/lib/i18n';
import { LoginForm } from '@/components/login-form';
import { IconLanguage } from '@/components/icons';

// Sign-in only. There is no sign-up form on purpose: accounts are created by an
// admin in the Supabase dashboard, the same reasoning as ENABLE_ACCOUNT_SIGNUP
// being off in Chatwoot. A public registration form on a URL that reads real
// residents' debts is not a feature.
//
// A server component that hands the labels to a client form. The split exists
// because the language is a cookie and the form needs state; see login-form.tsx.
//
// Standalone since 26 Aug: the root layout renders this path without the app
// shell, so the brand and the language switch live HERE — the sidebar that
// used to provide both is deliberately absent from a page whose reader is not
// signed in.

// The layout's setLocale comes back to the page it was called from; this one
// only ever comes back here. Duplicated rather than shared because a server
// action defined in a layout cannot be imported by a page.
async function setLocale(formData: FormData) {
  'use server';
  const next = String(formData.get('to') ?? 'he') === 'en' ? 'en' : 'he';
  cookies().set(COOKIE, next, { path: '/', maxAge: 60 * 60 * 24 * 365, sameSite: 'lax' });
  redirect('/login');
}

export default function Login() {
  const locale = getLocale();
  const theme = getTheme();
  const t = translator(locale);
  const other: Locale = locale === 'he' ? 'en' : 'he';
  return (
    <LoginForm labels={{
      title: t('login.title'),
      email: t('login.email'),
      password: t('login.password'),
      submit: t('login.submit'),
      working: t('login.working'),
    }}>
      {/* The company's real logo, supplied 26 Aug. It carries the name and the
          Hebrew subtitle itself, so no text beside it — the alt is for screen
          readers and for the broken-image case. No plate: the white box around
          the mark was the first attempt and read as a white square, so the
          logo floats on the page instead, in a per-theme variant — the source
          wordmark is near-black and would vanish on the dark ground, so the
          dark file has it recolored white. Both derive from Homies-Logo.png
          at the repo root. */}
      <div className="authbrand">
        {/* Server-picked, not `<picture media="(prefers-color-scheme: dark)">`.
            That media query was correct while the theme followed the operating
            system; since the theme became a cookie and a switch in the topbar
            it has been answering the wrong question, and a reader on a light OS
            who chose the dark theme got the near-black wordmark on a near-black
            page. The theme is known here. */}
        <img src={theme === 'light' ? '/homies-logo.png' : '/homies-logo-dark.png'}
             alt={`${t('app.name')} — ${t('app.subtitle')}`} />
      </div>
      <form action={setLocale} className="authlang">
        <input type="hidden" name="to" value={other} />
        <button type="submit" aria-label={t('lang.switchLabel')}>
          <IconLanguage />
          <span>{t('lang.switch')}</span>
        </button>
      </form>
    </LoginForm>
  );
}
