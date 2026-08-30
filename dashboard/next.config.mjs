/** @type {import('next').NextConfig} */

/**
 * `distDir` is configurable so a production build can be run WITHOUT standing
 * on a running dev server.
 *
 * Both `next dev` and `next build` write to `.next` by default. Run a build
 * while the dev server is up and the build rewrites the directory underneath
 * it: the server keeps serving the manifest it loaded at boot, the hashed
 * chunks that manifest points at no longer exist, and the browser starts
 * getting 404s for its own stylesheet. The page then renders with NO CSS —
 * which does not look like a missing stylesheet, it looks like the app
 * exploded: every inline SVG loses its width and fills the viewport, in
 * Chrome's default visited-link purple. That is exactly what happened on
 * 30 Aug 2026, twice, and it cost a round of "it's broken" with no error
 * anywhere in the log, because nothing HAD errored.
 *
 * So: verification builds go to their own directory.
 *
 *     NEXT_DIST_DIR=.next-verify npx next build
 *
 * Dev and the real deploy both keep `.next` and are unaffected.
 */
export default {
  reactStrictMode: true,
  distDir: process.env.NEXT_DIST_DIR || '.next',
};
