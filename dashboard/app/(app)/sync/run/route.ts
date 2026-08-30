import { NextRequest, NextResponse } from 'next/server';

// Start an import from the dashboard.
//
// The token lives here and never reaches the browser: a fine-grained PAT with
// Actions write on this repository only, held as a Vercel environment variable.
// Without it the page does not render the button at all, so this handler is
// only reachable by someone posting to it directly — hence the check below
// rather than a comment saying it cannot happen.
const REPO = 'TheSuperShyy/homies';
const WORKFLOW = 'oxs-sync.yml';

export async function POST(req: NextRequest) {
  const token = process.env.GITHUB_DISPATCH_TOKEN;
  if (!token) {
    return NextResponse.redirect(new URL('/sync?err=no-token', req.url), 303);
  }

  const form = await req.formData();
  // Absent checkbox means unchecked, which means a real import. The default in
  // the form is CHECKED — the safe direction, since the destructive reading of
  // an ambiguous click is "write to the live database".
  const dry = form.get('dry_run') === 'true';

  const r = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/vnd.github+json',
        Authorization: `Bearer ${token}`,
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ref: 'main', inputs: { dry_run: String(dry) } }),
    },
  );

  // GitHub answers 204 with no body and takes a few seconds to register the
  // run, so the redirect cannot show it immediately. `started` is what the page
  // uses to say "asked for, give it a moment" rather than appearing to ignore
  // the click.
  const where = r.status === 204 ? '/sync?started=1' : `/sync?err=${r.status}`;
  return NextResponse.redirect(new URL(where, req.url), 303);
}
