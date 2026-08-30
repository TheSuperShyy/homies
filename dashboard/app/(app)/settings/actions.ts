'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { serverClient } from '@/lib/supabase-server';
import { COOKIE, THEME_COOKIE } from '@/lib/i18n';

/**
 * Everything the settings page writes.
 *
 * In their own file rather than inline in the page because one of them —
 * `saveAvatar` — is called from a client component, and a client component can
 * import from a `'use server'` module but cannot import from a page.
 *
 * Every one of them redirects, and none of them is wrapped in a try/catch:
 * `redirect()` works by throwing, so catching around it swallows the navigation
 * and leaves the reader looking at a blank response.
 *
 * WHERE THE NAME AND THE PHOTO ARE KEPT. In `auth.users.raw_user_meta_data`,
 * not in a profiles table — see `supabase/029_staff_avatars.sql` for the whole
 * argument. The short version: the middleware already calls `getUser()` on
 * every request, so metadata reaches the shell for free, and a table would put
 * a second database round trip in front of every page render.
 *
 * That storage is writable by the account it belongs to, which is right for a
 * name and a picture and would be WRONG for anything that grants access. If
 * roles ever arrive they do not go here.
 */

type Meta = { display_name?: string | null; avatar_url?: string | null; avatar_path?: string | null };

/** Metadata is merged key by key, so read what is there before writing part of it. */
async function currentMeta() {
  const db = serverClient();
  const { data: { user } } = await db.auth.getUser();
  if (!user) redirect('/login');
  return { db, user, meta: (user.user_metadata ?? {}) as Meta };
}

export async function signOut() {
  await serverClient().auth.signOut();
  redirect('/login');
}

// The shell defines its own copies of these two. A server action declared in a
// layout cannot be imported by a page, and these always come back here, so
// neither needs the shell's hidden `back` field.
export async function setLocale(formData: FormData) {
  const next = String(formData.get('to') ?? 'he') === 'en' ? 'en' : 'he';
  cookies().set(COOKIE, next, { path: '/', maxAge: 60 * 60 * 24 * 365, sameSite: 'lax' });
  redirect('/settings');
}

export async function setTheme(formData: FormData) {
  const next = String(formData.get('to') ?? 'dark') === 'light' ? 'light' : 'dark';
  cookies().set(THEME_COOKIE, next, { path: '/', maxAge: 60 * 60 * 24 * 365, sameSite: 'lax' });
  redirect('/settings');
}

/**
 * The name shown in the sidebar and the corner.
 *
 * Capped at 60 characters because it is rendered in a fixed-width sidebar and
 * in a topbar beside an email address; longer than that and it is not a name,
 * it is a paragraph in a place with no room for one. Emptying the box is a
 * deliberate action — it puts the email-derived fallback back.
 */
export async function saveName(formData: FormData) {
  const { db, meta } = await currentMeta();
  const name = String(formData.get('name') ?? '').replace(/\s+/g, ' ').trim().slice(0, 60);
  await db.auth.updateUser({ data: { ...meta, display_name: name || null } });
  redirect('/settings?ok=name');
}

const DATA_URL = /^data:(image\/(?:webp|jpeg|png));base64,([A-Za-z0-9+/=]+)$/;
// The bucket enforces this too (029). Both, because the bucket's copy is the
// one that holds when somebody calls the storage API without going through here.
const MAX_BYTES = 262144;

/**
 * The profile photo.
 *
 * ARRIVES AS A DATA URL, ALREADY SQUARE AND ALREADY 256px. The browser does
 * that — see `components/avatar-picker.tsx` — because there is no image library
 * on this server and the alternative is storing whatever came off somebody's
 * phone. A 4MB photograph fetched behind the topbar of every page is not a
 * profile picture, it is a bandwidth bill.
 *
 * Which means the numbers below are not the real defence: a signed-in account
 * can call the storage API directly and skip this function entirely. The
 * bucket's own size and MIME limits are the defence. These exist so a bad file
 * fails here, with a message, instead of failing there, silently.
 */
export async function saveAvatar(formData: FormData) {
  const { db, user, meta } = await currentMeta();

  const match = DATA_URL.exec(String(formData.get('image') ?? ''));
  if (!match) redirect('/settings?e=image');
  const [, mime, b64] = match;

  const bytes = Buffer.from(b64, 'base64');
  if (!bytes.length || bytes.length > MAX_BYTES) redirect('/settings?e=big');

  // The path starts with the user's id because the storage policies in 029 read
  // exactly that first segment. Rename the folder scheme and the policies stop
  // matching — they would deny every upload rather than allow the wrong one,
  // but it would still be broken.
  const ext = mime === 'image/png' ? 'png' : mime === 'image/jpeg' ? 'jpg' : 'webp';
  const path = `${user.id}/${Date.now()}.${ext}`;

  const up = await db.storage.from('avatars').upload(path, bytes, {
    contentType: mime,
    // A year. The filename carries a timestamp, so a new photo is a new URL and
    // nothing ever has to be revalidated — the old one simply stops being asked
    // for.
    cacheControl: '31536000',
    upsert: false,
  });
  if (up.error) redirect('/settings?e=upload');

  const { data: pub } = db.storage.from('avatars').getPublicUrl(path);

  // Remove the one it replaces. Not critical — nothing points at it any more —
  // but a bucket that only ever grows is a bucket somebody has to clean out by
  // hand later, and the account that owns the old file is the account doing
  // this, so the delete policy allows it.
  if (meta.avatar_path && meta.avatar_path !== path) {
    await db.storage.from('avatars').remove([meta.avatar_path]);
  }

  await db.auth.updateUser({
    data: { ...meta, avatar_url: pub.publicUrl, avatar_path: path },
  });
  redirect('/settings?ok=photo');
}

export async function removeAvatar() {
  const { db, meta } = await currentMeta();
  if (meta.avatar_path) await db.storage.from('avatars').remove([meta.avatar_path]);
  await db.auth.updateUser({ data: { ...meta, avatar_url: null, avatar_path: null } });
  redirect('/settings?ok=photo');
}

/**
 * Change the signed-in account's password.
 *
 * THE CURRENT PASSWORD IS CHECKED EVEN THOUGH SUPABASE DOES NOT REQUIRE IT.
 * `updateUser({ password })` will happily rewrite the password of whoever holds
 * the session cookie, which means an unlocked laptop on a desk in the office is
 * enough to lock the owner out of their own dashboard. Signing in again with
 * the password typed in the first box costs one round trip and closes that.
 */
export async function changePassword(formData: FormData) {
  const current = String(formData.get('current') ?? '');
  const next = String(formData.get('next') ?? '');
  const again = String(formData.get('again') ?? '');

  // Cheap checks first, so a typo in the confirmation never reaches the auth
  // server and never counts against its rate limit.
  if (next !== again) redirect('/settings?e=mismatch');
  if (next.length < 8) redirect('/settings?e=short');
  if (next === current) redirect('/settings?e=same');

  const db = serverClient();
  const { data: { user } } = await db.auth.getUser();
  if (!user?.email) redirect('/login');

  const { error: wrong } = await db.auth.signInWithPassword({
    email: user.email, password: current,
  });
  // 400 is "those credentials are not right". Anything else — 429 from the rate
  // limiter, a 5xx — is not the reader's mistake and must not be reported as
  // one, or they sit there retyping a password that was correct all along.
  if (wrong) redirect(wrong.status === 400 ? '/settings?e=wrong' : '/settings?e=failed');

  const { error } = await db.auth.updateUser({ password: next });
  if (error) redirect('/settings?e=failed');
  redirect('/settings?ok=password');
}
