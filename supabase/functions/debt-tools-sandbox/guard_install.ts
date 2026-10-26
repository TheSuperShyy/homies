// Runs before app.ts (see index.ts): from here on every fetch passes the guard.
import { install } from "./guard.ts";

globalThis.fetch = install(globalThis.fetch.bind(globalThis), Deno.env.get("SUPABASE_URL") ?? "");
