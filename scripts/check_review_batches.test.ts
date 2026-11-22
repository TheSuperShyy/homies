// The answers page's dropdown: a set's chats in batches (22 Nov, the owner: "also on the answer").
//   node --test scripts/check_review_batches.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { chatsFor, toBatchView } from "../dashboard/app/review/batches.ts";

const batches = [{ id: "new", label: "new ones" }, { id: "old", label: "old ones" }];
const chats = [{ n: 1, batch: "old" }, { n: 2, batch: "old" }, { n: 9, batch: "new" }, { n: 10 }];

test("all shows every chat, a batch only its own, and a chat with no batch only under all", () => {
  assert.deepEqual(chatsFor("all", chats).map((c) => c.n), [1, 2, 9, 10]);
  assert.deepEqual(chatsFor("new", chats).map((c) => c.n), [9]);
  assert.deepEqual(chatsFor("old", chats).map((c) => c.n), [1, 2]);
});

test("the address: only one of the set's batches; anything else, a repeated one included, is all", () => {
  assert.equal(toBatchView("new", batches), "new");
  assert.equal(toBatchView("old", batches), "old");
  for (const v of [undefined, "", "x", "NEW", ["new"]]) assert.equal(toBatchView(v, batches), "all", String(v));
  assert.equal(toBatchView("new", []), "all");
});
