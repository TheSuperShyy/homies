// The balance's name check with English letters (sandbox, 29 Oct).
//   node --test scripts/check_names.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { hebrewSkeletons, latinSkeleton, sameNameAnyScript } from "../supabase/functions/debt-tools-sandbox/names.ts";

test("the owner's chat: 'ido clix' is עידו קליקס", () => {
  assert.equal(sameNameAnyScript("עידו קליקס", "ido clix"), true);
  assert.equal(sameNameAnyScript("עידו קליקס", "Ido Clix"), true);
  assert.equal(sameNameAnyScript("עידו קליקס", "עידו קליקס"), true);   // Hebrew, as before
  assert.equal(sameNameAnyScript("עידו קליקס", "clix ido"), true);     // order never mattered
});

test("common Israeli names in their usual English spellings", () => {
  const pairs: Array<[string, string]> = [
    ["מיכאל כהן", "Michael Cohen"], ["רחל לוי", "Rachel Levi"], ["חיים כהן", "Haim Cohen"],
    ["חיים כהן", "Chaim Kohen"], ["יצחק אברהם", "Yitzhak Avraham"], ["אבי בן דוד", "Avi Ben David"],
    ["שירה מזרחי", "Shira Mizrahi"], ["נועה פרץ", "Noa Peretz"], ["אסף קליקס", "Assaf Clix"],
    ["יריב לוי", "Yariv Levi"], ["משה ביטון", "Moshe Biton"], ["אחמד מוחמד", "Ahmad Mohammed"],
    ["הדר אלון", "Hadar Alon"], ["צבי גולן", "Tzvi Golan"],
  ];
  for (const [heb, lat] of pairs) assert.equal(sameNameAnyScript(heb, lat), true, `${lat} / ${heb}`);
});

test("another person's name still fails", () => {
  assert.equal(sameNameAnyScript("עידו קליקס", "dan cohen"), false);
  assert.equal(sameNameAnyScript("עידו קליקס", "ido cohen"), false);    // every word must match
  assert.equal(sameNameAnyScript("מיכאל כהן", "Michael Levi"), false);
  assert.equal(sameNameAnyScript("עידו קליקס", "דן כהן"), false);
});

test("two words on both sides, as sameName always asked", () => {
  assert.equal(sameNameAnyScript("עידו קליקס", "ido"), false);
  assert.equal(sameNameAnyScript("עידו", "ido clix"), false);
  assert.equal(sameNameAnyScript("", "ido clix"), false);
  assert.equal(sameNameAnyScript("עידו קליקס", ""), false);
});

test("a word that reduces to nothing matches nothing", () => {
  assert.equal(latinSkeleton("aya"), "");
  assert.equal(sameNameAnyScript("איה כהן", "aya cohen"), false);
});

test("the skeletons themselves", () => {
  assert.equal(latinSkeleton("clix"), "KLKS");
  assert.equal(latinSkeleton("Yitzhak"), "SK");
  assert.deepEqual(hebrewSkeletons("קליקס"), ["KLKS"]);
  assert.ok(hebrewSkeletons("לוי").includes("LB") && hebrewSkeletons("לוי").includes("L"));
  assert.ok(hebrewSkeletons("חיים").includes("M") && hebrewSkeletons("חיים").includes("KM"));
});
