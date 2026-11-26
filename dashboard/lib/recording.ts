import 'server-only';

// A call's recording, for its page (26 Nov; the owner: "in the dashboard of the calls can we add the
// recording on that?").
//
// Calls are recorded again since 26 Oct, but Vapi keeps them in a private bucket: the
// `recordingUrl` the end-of-call report gives (saved as interactions.audio_url) answers 400 to
// anyone without Vapi's own credentials, so the player that has been on the page since August never
// played one. Vapi hands out signed links that work for about half an hour when the call is read
// (`artifact.presignedMonoUrl`), so the page asks for one each time it opens. Vapi keeps recordings
// for a limited time; after that there is nothing to play, and the page says so.

const VAPI = 'https://api.vapi.ai';

export type Recording =
  | { state: 'ready'; url: string }
  | { state: 'gone' }          // Vapi has no recording (never recorded, or no longer kept)
  | { state: 'unavailable' };  // Vapi did not answer in time, or refused

/** The playable link a Vapi call record carries, mono (both sides) first. */
export function signedLinkOf(call: any): string | null {
  const a = call?.artifact ?? {};
  const url = a.presignedMonoUrl ?? a.presignedStereoUrl ?? null;
  return typeof url === 'string' && /^https:\/\//.test(url) ? url : null;
}

/** A fresh link to this call's recording. Never throws. */
export async function recordingOf(callId: string | null | undefined): Promise<Recording> {
  const key = process.env.VAPI_PRIVATE_KEY;
  if (!callId || !/^[0-9a-f-]{36}$/i.test(callId)) return { state: 'gone' };
  if (!key) return { state: 'unavailable' };
  try {
    const res = await fetch(`${VAPI}/call/${callId}`, {
      headers: { Authorization: `Bearer ${key}`, 'User-Agent': 'homies-dashboard' },
      cache: 'no-store',
      signal: AbortSignal.timeout(6000),
    });
    // A call from the old Vapi account, or one Vapi no longer has: nothing to play.
    if (res.status === 400 || res.status === 404) return { state: 'gone' };
    if (!res.ok) return { state: 'unavailable' };
    const url = signedLinkOf(await res.json());
    return url ? { state: 'ready', url } : { state: 'gone' };
  } catch {
    return { state: 'unavailable' };
  }
}
