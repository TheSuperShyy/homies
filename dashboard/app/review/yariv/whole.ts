// A ticket number, a phone number, an hour or an email address must not break in the middle of a line,
// and must read left to right inside the Hebrew. On the first local build "255-" ended one line and
// "1600-26" began the next. So each is cut out as its own run, and the page keeps it whole.

export type Run = { text: string; whole: boolean };

// An email address, or digits joined by hyphens or colons (255-1600-26, 077-6687949, 09:00).
// A date ("ב-4 בנובמבר") and a check's number ("6.2") are ordinary text.
const WHOLE = /[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\d+(?:[-:]\d+)+/g;

export function runs(text: string): Run[] {
  const out: Run[] = [];
  let at = 0;
  for (const m of text.matchAll(WHOLE)) {
    const start = m.index ?? 0;
    if (start > at) out.push({ text: text.slice(at, start), whole: false });
    out.push({ text: m[0], whole: true });
    at = start + m[0].length;
  }
  if (at < text.length) out.push({ text: text.slice(at), whole: false });
  return out;
}

// One paragraph per line of the source; empty lines are dropped.
export function paragraphs(text: string): string[] {
  return text.split('\n').map((p) => p.trim()).filter(Boolean);
}
