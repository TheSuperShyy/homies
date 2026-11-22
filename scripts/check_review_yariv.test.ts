// The reviewers' page, second section: Yariv's comments (9 Nov, then 18-19 Nov), each beside our answer.
//   node --test scripts/check_review_yariv.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { REPLIES, STATUSES, VIEWS, countByStatus, itemsFor, toView } from "../dashboard/app/review/yariv/replies.ts";
import { paragraphs, runs } from "../dashboard/app/review/yariv/whole.ts";

test("the page carries Yariv's twelve comments of 9 Nov in his numbering, then the three of 18-19 Nov", () => {
  assert.deepEqual(REPLIES.items.map((i) => i.id),
    ["1.1", "2.1", "2.2", "2.3", "2.4", "3.2", "4.1", "5.1", "5.2", "6.2", "6.3", "7.2",
     "n18-1", "n18-2", "n19-1"]);
});

test("a later comment carries the day Yariv wrote it; the twelve of 9 Nov carry their check's number only", () => {
  for (const i of REPLIES.items) {
    if (i.id.startsWith("n")) assert.match(i.given ?? "", /^\d{1,2} בנובמבר$/, i.id);
    else assert.equal(i.given, undefined, i.id);
  }
});

test("every comment has both sides, and a status the page knows", () => {
  for (const i of REPLIES.items) {
    assert.ok(i.comment.trim().length > 0, `${i.id} has no comment`);
    assert.ok(i.answer.trim().length > 0, `${i.id} has no answer`);
    assert.ok(STATUSES.includes(i.status), `${i.id}: ${i.status}`);
  }
});

test("the dropdown: all fifteen, only the three since 9 Nov, or only the twelve of 9 Nov", () => {
  assert.deepEqual([...VIEWS], ["all", "new", "old"]);
  assert.equal(itemsFor("all", REPLIES.items).length, 15);
  assert.deepEqual(itemsFor("new", REPLIES.items).map((i) => i.id), ["n18-1", "n18-2", "n19-1"]);
  assert.equal(itemsFor("old", REPLIES.items).length, 12);
  assert.ok(itemsFor("old", REPLIES.items).every((i) => !i.id.startsWith("n")));
});

test("the dropdown address: only all, new or old; anything else, a repeated one included, is all", () => {
  assert.equal(toView("new"), "new");
  assert.equal(toView("old"), "old");
  for (const v of [undefined, "", "x", "NEW", ["new"]]) assert.equal(toView(v), "all", String(v));
});

test("the counts at the top: twelve done, one unchanged, two answers", () => {
  assert.deepEqual(countByStatus(REPLIES.items), { done: 12, same: 1, answered: 2 });
});

test("what the page says around the comments is Hebrew, as on the replies page", () => {
  const around = [REPLIES.title, REPLIES.lede, REPLIES.updated, ...Object.values(REPLIES.labels)];
  for (const s of around) assert.ok(!/[A-Za-z]/.test(s), s);
});

test("runs: a ticket number, a phone number, an hour and an email address each stay whole", () => {
  assert.deepEqual(runs("מספר הקריאה הוא 255-1600-26. אנחנו"), [
    { text: "מספר הקריאה הוא ", whole: false },
    { text: "255-1600-26", whole: true },
    { text: ". אנחנו", whole: false },
  ]);
  assert.deepEqual(runs("שלכם, 077-6687949."), [
    { text: "שלכם, ", whole: false }, { text: "077-6687949", whole: true }, { text: ".", whole: false },
  ]);
  assert.deepEqual(runs("09:00 עד 17:00").filter((r) => r.whole).map((r) => r.text), ["09:00", "17:00"]);
  assert.deepEqual(runs("לכתובת sherut@homies-management.co.il, עם").filter((r) => r.whole).map((r) => r.text),
    ["sherut@homies-management.co.il"]);
});

test("runs: a date, a check's number and plain words are left as they are", () => {
  for (const s of ["בפגישה ב-4 בנובמבר", "כמו ב-6.2.", "קריאת שירות ב-OXS.", "אין כאן מספרים"]) {
    assert.deepEqual(runs(s), [{ text: s, whole: false }], s);
  }
});

test("runs: nothing is lost or reordered", () => {
  for (const i of REPLIES.items) {
    for (const side of [i.comment, i.answer]) {
      assert.equal(runs(side).map((r) => r.text).join(""), side);
    }
  }
});

test("paragraphs: one per line, and empty lines are dropped", () => {
  assert.deepEqual(paragraphs("צריך להוסיף :\nפתחתי\n\n  סוף  "), ["צריך להוסיף :", "פתחתי", "סוף"]);
});
