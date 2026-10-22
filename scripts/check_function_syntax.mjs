// There is no Deno on this machine, so a typo in the Edge Function would only
// show at deploy. This strips the TypeScript (Node's own parser, which throws
// on a syntax error) and asks Node to parse the result as a module.
//   node scripts/check_function_syntax.mjs
import { stripTypeScriptTypes } from "node:module";
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";

const dir = new URL("../supabase/functions/debt-tools/", import.meta.url);
const out = mkdtempSync(join(tmpdir(), "debt-tools-"));
let bad = 0;
for (const name of ["identity.ts", "index.ts"]) {
  try {
    const js = stripTypeScriptTypes(readFileSync(new URL(name, dir), "utf8"), { mode: "transform" });
    const path = join(out, name.replace(/\.ts$/, ".mjs"));
    writeFileSync(path, js);
    execFileSync(process.execPath, ["--check", path], { stdio: "pipe" });
    console.log("ok   ", name);
  } catch (e) {
    bad++;
    console.log("FAIL ", name, String(e.stderr ?? e.message).split("\n").slice(0, 6).join("\n"));
  }
}
process.exit(bad ? 1 : 0);
