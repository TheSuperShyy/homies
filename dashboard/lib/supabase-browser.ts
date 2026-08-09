// The browser half. Kept in its own file because the server half imports
// `next/headers`, and a Client Component that imports it — even without using
// it — fails the build outright. One shared module looked tidier and did not
// compile.
//
// The ANON key, always. The service role key bypasses every RLS policy in
// migration 009 and must never enter a browser bundle: with it, the project URL
// alone hands a stranger 12 real residents' names, phones and debts.
import { createBrowserClient } from '@supabase/ssr';

export function browserClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
