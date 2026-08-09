// The server half — Server Components only. Also the ANON key: what grants
// access is the signed-in user's session in the cookies, read against the
// `staff_read` policies. A logged-out request reads nothing, and reads it as an
// empty list rather than an error, which is why the middleware redirects
// instead of letting someone stare at a dashboard that looks merely broken.
import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { cookies } from 'next/headers';

export function serverClient() {
  const store = cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => store.getAll(),
        // Server Components cannot set cookies. The middleware refreshes the
        // session on every request, so swallowing this is correct rather than
        // lazy — without the try/catch every page render throws.
        setAll: (list: { name: string; value: string; options: CookieOptions }[]) => {
          try {
            list.forEach(({ name, value, options }) => store.set(name, value, options));
          } catch {}
        },
      },
    },
  );
}
