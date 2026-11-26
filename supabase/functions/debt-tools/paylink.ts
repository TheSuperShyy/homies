// The debt call's payment link: how long the caller waits for it (10 Nov).
//
// send_payment_link answers while the tenant is on the line, and Vapi stops
// waiting after its tool timeout. On the first real debt call (26 Oct) the tool
// took about 12 s and Vapi gave up at 10: the tenant heard an improvised line
// with a wrong office number while the function was still working. The time
// went on steps run one after another, among them a model's line that the
// template then threw away and one fixed 2 s wait before looking for
// WhatsApp's id. The rules below are the timing ones. Pure, so Node can test
// them: scripts/check_paylink.test.ts.

/** Meta takes free text only inside 24 hours of the tenant's last message. */
export const WINDOW_MS = 24 * 3600 * 1000;

/**
 * Is the tenant's WhatsApp window open? `lastInMs` is their last message to
 * our number, 0 when they never wrote. Shut is the ordinary case on a debt
 * call: we ring someone who has not written to us, so the link goes as the
 * template and no model line is needed.
 */
export function windowOpen(lastInMs: number, nowMs: number): boolean {
  return lastInMs > 0 && nowMs - lastInMs <= WINDOW_MS;
}

/**
 * May free text go into this Chatwoot conversation? (26 Nov, the owner's call to Ido: "why did the
 * whatsapp message did not send we have a template message on it".) Until then the Chatwoot route
 * never asked: it posted the link as free text to everyone, waited, and sent the template only after
 * Meta refused, so nearly every debt call left a failed message above the delivered template.
 * Chatwoot answers `can_reply` on a conversation, and for a WhatsApp inbox it is Meta's own rule:
 * the contact's last message in it is under 24 hours old. Only an explicit false shuts the window;
 * a read that failed, or a Chatwoot without the field, keeps the old way (free text, then the
 * template after a refusal).
 */
export function freeTextAllowed(conversation: unknown): boolean {
  return (conversation as any)?.can_reply !== false;
}

/**
 * When WhatsApp's id is looked for after a send. A message WhatsApp took
 * carries the id within a moment, so the first look comes early and a yes ends
 * the waiting; only a refusal uses them all.
 */
export const DELIVERY_WAITS_MS = [700, 900, 1400];

/**
 * 17 Nov (the owner, after a test call that waited about 8 s for the link: "the
 * delay is super trash ... make it fast"): the tenant no longer waits on the
 * line for WhatsApp. send_payment_link answers once the link exists; the send,
 * WhatsApp's id and the office's rows finish after the answer. So the agent is
 * told the link is on its way, never that it arrived. A send that fails later
 * files the OPEN ticket as before, and the office sends the link by hand.
 */
export const ON_ITS_WAY = "The link is on its way to their WhatsApp, to the number we have. Say it is on its "
  + "way and ask them to finish the payment when it arrives; do not say it has already arrived.";

/**
 * One send per call while it is still going: a second ask in the same call is
 * told the link is on its way instead of sending it twice (the row that says
 * "sent" is only written when the send is done). `key` is the call's
 * interaction id; without one there is nothing to hold.
 */
export function claimOnce(inFlight: Set<string>, key: string | null): boolean {
  if (!key) return true;
  if (inFlight.has(key)) return false;
  inFlight.add(key);
  return true;
}

/**
 * Ask `check` after each wait and stop at the first yes. A read that throws is
 * a "not yet": the next wait asks again. False only when every wait was used.
 */
export async function pollUntil(
  check: () => Promise<boolean>,
  waitsMs: number[],
  sleep: (ms: number) => Promise<void> = (ms) => new Promise((r) => setTimeout(r, ms)),
): Promise<boolean> {
  for (const ms of waitsMs) {
    await sleep(ms);
    try {
      if (await check()) return true;
    } catch {
      // not yet
    }
  }
  return false;
}

/** Step times for one log line: "lookups 412, template 1530, total 2030" (ms). */
export function stopwatch(now: () => number = Date.now) {
  const t0 = now();
  let last = t0;
  const laps: string[] = [];
  return {
    lap(label: string) {
      const t = now();
      laps.push(`${label} ${t - last}`);
      last = t;
    },
    total() {
      return now() - t0;
    },
    text() {
      return [...laps, `total ${now() - t0}`].join(", ");
    },
  };
}
