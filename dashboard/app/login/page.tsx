import { getLocale, translator } from '@/lib/i18n';
import { LoginForm } from '@/components/login-form';

// Sign-in only. There is no sign-up form on purpose: accounts are created by an
// admin in the Supabase dashboard, the same reasoning as ENABLE_ACCOUNT_SIGNUP
// being off in Chatwoot. A public registration form on a URL that reads real
// residents' debts is not a feature.
//
// A server component that hands the labels to a client form. The split exists
// because the language is a cookie and the form needs state; see login-form.tsx.
export default function Login() {
  const t = translator(getLocale());
  return (
    <LoginForm labels={{
      title: t('login.title'),
      email: t('login.email'),
      password: t('login.password'),
      submit: t('login.submit'),
      working: t('login.working'),
    }} />
  );
}
