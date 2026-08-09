'use client';
import { useState } from 'react';
import { browserClient } from '@/lib/supabase-browser';

// Sign-in only. There is no sign-up form on purpose: accounts are created by an
// admin in the Supabase dashboard, the same reasoning as ENABLE_ACCOUNT_SIGNUP
// being off in Chatwoot. A public registration form on a URL that reads real
// residents' debts is not a feature.
export default function Login() {
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
    <form className="auth" onSubmit={submit}>
      <h1>Sign in</h1>
      {error && <div className="err">{error}</div>}
      <input type="email" placeholder="Email" value={email} autoComplete="username"
             onChange={(e) => setEmail(e.target.value)} required />
      <input type="password" placeholder="Password" value={password} autoComplete="current-password"
             onChange={(e) => setPassword(e.target.value)} required />
      <button className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
    </form>
  );
}
