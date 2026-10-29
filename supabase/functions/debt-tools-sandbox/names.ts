// The balance's name check, taking a name typed in English letters (sandbox, 29 Oct).
//
// The owner's own chat as Ido: "ido clix" was typed, the record reads עידו קליקס,
// and get_balance's sameName() compares whole words, so the number given, Ido's
// own, was answered "the details do not match". Every tenant who writes their
// name in Latin letters fails the same way.
//
// So a word in Latin letters is compared by its consonants: each side is reduced
// to a skeleton of sound classes, vowels and the silent letters dropped, and a
// run of one class counted once. "clix" and קליקס are both K L K S. The letters
// that read two ways (ו as a vowel or V, ח as KH or a bare H, which an English
// spelling often drops) give the Hebrew side several skeletons, and any one of
// them may match. A word typed in Hebrew is still compared exactly, as before.
//
// It is the second half of a check whose first half is the phone number, which
// must already be the record's. A looser name match costs little there, and a
// stricter one tells real tenants their details are wrong.
//
// Pure, with no imports, so scripts/check_names.test.ts runs it under Node.

const HEBREW: Record<string, string[]> = {
  "א": [""], "ה": [""], "ע": [""], "י": [""],
  "ו": ["", "B"], "ח": ["K", ""],
  "ב": ["B"], "ג": ["G"], "ד": ["D"], "ז": ["S"], "ט": ["T"],
  "כ": ["K"], "ך": ["K"], "ק": ["K"], "ל": ["L"], "מ": ["M"], "ם": ["M"],
  "נ": ["N"], "ן": ["N"], "ס": ["S"], "צ": ["S"], "ץ": ["S"], "ש": ["S"],
  "פ": ["P"], "ף": ["P"], "ר": ["R"], "ת": ["T"],
};

const LATIN: Record<string, string> = {
  a: "", e: "", i: "", o: "", u: "", y: "", h: "",
  b: "B", v: "B", w: "B", c: "K", k: "K", q: "K", d: "D", f: "P", p: "P",
  g: "G", j: "G", l: "L", m: "M", n: "N", r: "R", s: "S", z: "S", t: "T", x: "KS",
};

const once = (s: string) => s.replace(/(.)\1+/g, "$1");
const hebrew = (w: string) => /[א-ת]/.test(w);

function words(v: unknown): string[] {
  return String(v ?? "")
    .replace(/["'`׳״]/g, "")
    .toLowerCase()
    .split(/[\s-]+/)
    .filter(Boolean);
}

/** "Yitzhak" -> S K: "tz" and "ts" are the one letter צ. */
export function latinSkeleton(word: string): string {
  let out = "";
  for (const ch of word.toLowerCase().replace(/t[sz]/g, "s")) out += LATIN[ch] ?? "";
  return once(out);
}

/** Every way a Hebrew word can sound in consonants; at most 64. */
export function hebrewSkeletons(word: string): string[] {
  let all = [""];
  for (const ch of word) {
    const ways = HEBREW[ch];
    if (!ways) continue;
    const next: string[] = [];
    for (const a of all) for (const w of ways) next.push(a + w);
    all = [...new Set(next)].slice(0, 64);
  }
  return [...new Set(all.map(once))];
}

function sounds(word: string): string[] {
  return (hebrew(word) ? hebrewSkeletons(word) : [latinSkeleton(word)]).filter(Boolean);
}

/**
 * get_balance's name half: every word they typed is a word of the name on
 * record, exactly or, when typed in Latin letters, by its consonants. At least
 * two words on both sides, as sameName() has always asked.
 */
export function sameNameAnyScript(stored: unknown, given: unknown): boolean {
  const on = [...new Set(words(stored))];
  const said = [...new Set(words(given))];
  if (on.length < 2 || said.length < 2) return false;
  return said.every((w) => {
    if (on.includes(w)) return true;
    if (hebrew(w)) return false;
    const mine = latinSkeleton(w);
    return mine !== "" && on.some((s) => sounds(s).includes(mine));
  });
}
