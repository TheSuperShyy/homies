'use client';
import { useState } from 'react';
import { browserClient } from '@/lib/supabase-browser';

/**
 * The only client component on the dashboard, and it is one because signing in
 * needs `useState` and a keystroke handler.
 *
 * Its labels arrive as props rather than being looked up here: the language
 * lives in a cookie and `cookies()` is server-only, so a client component
 * cannot read it without either shipping the whole dictionary to the browser or
 * guessing from `navigator.language` — which would put the login page in a
 * different language from every page behind it.
 */
export type LoginLabels = {
  title: string; email: string; password: string; submit: string; working: string;
};

// `children` render above the form, inside the centered column — the brand
// and the language switch. They come from the server page because they need
// the cookie locale and a server action, and this file is the one client
// component; passing them as RSC children keeps it that way.
export function LoginForm({ labels, children }:
    { labels: LoginLabels; children?: React.ReactNode }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError('');
    const { error } = await browserClient().auth.signInWithPassword({ email, password });
    if (error) { setError(error.message); setBusy(false); return; }
    // Hard navigation, not router.push: the middleware has to see the new
    // cookie, and a client-side transition does not give it that chance.
    window.location.href = '/';
  }

  return (
    <div className="authwrap">
      <div className="authbox">
      {children}
      <form className="auth" onSubmit={submit}>
        <h1>{labels.title}</h1>
        {/* role="alert" so a screen reader is told the sign-in failed. Without
            it the message appears silently and the only cue is visual. */}
        {error && <div className="err" role="alert">{error}</div>}
        {/* A real label above each field, not a placeholder doing the job. A
            placeholder disappears the moment somebody types, which is exactly
            when they look up to check which box they are in. */}
        <label htmlFor="email">{labels.email}</label>
        <input id="email" type="email" value={email} autoComplete="username"
               onChange={(e) => setEmail(e.target.value)} required />
        <label htmlFor="password">{labels.password}</label>
        <input id="password" type="password" value={password} autoComplete="current-password"
               onChange={(e) => setPassword(e.target.value)} required />
        <button className="primary" disabled={busy}>
          {busy ? labels.working : labels.submit}
        </button>
      </form>
      </div>
    </div>
  );
}
