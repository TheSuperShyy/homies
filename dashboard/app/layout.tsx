import './globals.css';
import { serverClient } from '@/lib/supabase-server';
import { redirect } from 'next/navigation';

export const metadata = { title: 'Homies' };
// Never cache. Every page here is a live view of a table that changes while
// someone is looking at it.
export const dynamic = 'force-dynamic';

async function signOut() {
  'use server';
  await serverClient().auth.signOut();
  redirect('/login');
}

export default async function Layout({ children }: { children: React.ReactNode }) {
  const { data: { user } } = await serverClient().auth.getUser();
  return (
    <html lang="en">
      <body>
        {/* Demo mode: the nav shows for everyone — there is no login to gate it
            behind. The sign-out button only appears when a session exists. */}
        <header className="top">
          <strong>Homies</strong>
          <nav>
            <a href="/">Overview</a>
            <a href="/tickets">Tickets</a>
            <a href="/debts">Debts</a>
            <a href="/conversations">Conversations</a>
            <a href="/calls">Calls</a>
          </nav>
          {user && (
            <form action={signOut}>
              <button>Sign out</button>
            </form>
          )}
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
