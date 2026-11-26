// The dashboard shows the dialer and the calls only (25 Nov): dashboard/lib/sections.ts.
//   node --test scripts/check_sections.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { HOME, hiddenPath } from "../dashboard/lib/sections.ts";

test("the dialer, the calls and settings stay", () => {
  for (const path of ["/dialer", "/dialer/test", "/calls", "/calls/0b1f9a52-3c1e-4d2a-9a77-1f2e3d4c5b6a",
                      "/settings"]) {
    assert.equal(hiddenPath(path), false, path);
  }
});

test("the sign-in, the reviewers' pages and the API routes are not the menu's business", () => {
  for (const path of ["/login", "/review", "/review/yariv", "/api/voice-chat"]) {
    assert.equal(hiddenPath(path), false, path);
  }
});

test("everything else goes to the dialer, the overview at / included", () => {
  for (const path of ["/", "/tickets", "/debts", "/conversations", "/conversations/+972541234567",
                      "/search", "/sync", "/sync/run", "/dialerx", "/callsy", "/settings2",
                      "/voice"]) {
    assert.equal(hiddenPath(path), true, path);
  }
  assert.equal(hiddenPath(HOME), false);
});
