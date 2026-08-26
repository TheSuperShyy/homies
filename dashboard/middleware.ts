// Refreshes the Supabase session cookie on every request and bounces anyone
// without one to /login.
//
// The redirect is belt and braces, not the security boundary: RLS is. If this
// file were deleted tomorrow, a logged-out visitor would reach the pages and
// see empty tables, because the policies in migration 009 return no rows
// without a session. This exists so they see a login form instead of a
// dashboard that looks broken.
import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  // THE LAYOUT NEEDS TO KNOW WHICH PAGE IT IS RENDERING, and a server layout in
  // the App Router has no way to ask. `x-invoke-path` is a Next internal that
  // is not there in 14.2, and `referer` is the page you came FROM, so a nav
  // built on it highlights the item you just left. Setting it on the REQUEST
  // headers here is the supported route: it reaches the server component and
  // never goes back to the browser.
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-pathname', request.nextUrl.pathname);

  let response = NextResponse.next({ request: { headers: requestHeaders } });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (list: { name: string; value: string; options: CookieOptions }[]) => {
          list.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request: { headers: requestHeaders } });
          list.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options));
        },
      },
    },
  );

  // getUser(), not getSession(). getSession() reads the cookie and believes it;
  // getUser() asks the auth server whether the token is real.
  await supabase.auth.getUser();

  // Demo mode (9 Aug 2026): no login wall. The redirect to /login is removed
  // and migration 010 gives the anon role read access, so a logged-out visitor
  // sees data rather than empty tables. To re-lock, restore the redirect here
  // and drop the anon_read policies — see supabase/010_open_dashboard.sql.
  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
