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
  const { data: { user } } = await supabase.auth.getUser();

  // AND HAND THE ANSWER DOWN, so the layout does not ask again. The root layout
  // needs to know who is signed in to render the account block and the sign-out
  // button; calling `auth.getUser()` there is a second full round trip to the
  // auth server for a question this request has already answered, and it blocks
  // the shell from streaming while it waits. The header is set on the REQUEST,
  // exactly like `x-pathname` above, so it reaches the server component and
  // never goes back to the browser.
  if (user?.email) requestHeaders.set('x-user-email', user.email);

  // The login wall, restored 26 Aug 2026 on the owner's ask. Demo mode
  // (9 Aug) had removed this redirect and opened the tables to anon; migration
  // 026 closed the tables again, so this redirect is back to being what it
  // always was — the polite half of the lock. RLS is the security boundary:
  // delete this file and a logged-out visitor sees empty tables, not data.
  const path = request.nextUrl.pathname;
  if (!user && path !== '/login') {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  // Signed in and on /login: nothing to do there — go to the dashboard.
  if (user && path === '/login') {
    return NextResponse.redirect(new URL('/', request.url));
  }

  return response;
}

export const config = {
  // Static files are excluded from the wall by extension, not by name. The
  // night the redirect came back it caught /homies-logo.png too, and the login
  // page rendered a broken image of its own brand: the request for the logo
  // was 307'd to the page that was asking for it. Files under public/ are
  // exactly the assets pages need BEFORE a session exists; there is nothing
  // secret in an image the login page itself displays, and anything secret
  // does not belong in public/ anyway.
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|svg|webp|ico)$).*)',
  ],
};
