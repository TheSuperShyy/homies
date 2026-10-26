// The sandbox entry (feature 19). Order matters: the guard replaces fetch
// before app.ts creates its Supabase client and starts serving. app.ts is the
// live debt-tools index.ts byte for byte; scripts/sandbox_function.py uploads
// it under that name and checks the bytes.
import "./guard_install.ts";
import "./app.ts";
