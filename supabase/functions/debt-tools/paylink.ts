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
 * When WhatsApp's id is looked for after a send. A message WhatsApp took
 * carries the id within a moment, so the first look comes early and a yes ends
 * the waiting; only a refusal uses them all.
 */
export const DELIVERY_WAITS_MS = [700, 900, 1400];

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
