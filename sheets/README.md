# Resident lookup — Google Sheet

A data source the debt agent queries **during the call**. The agent asks "who is
+972501234567", and gets back their name, what they owe, which month, whether
they have already paid, and whether there is a card on file.

You can open the sheet, change a row, and the next call reflects it. That is the
whole point of using a spreadsheet rather than a database here.

## Files

| | |
|---|---|
| `residents.csv` | The ten mock residents. Import this into the sheet. |
| `Code.gs` | Apps Script that serves the sheet over HTTP. |

The rows match `supabase/002_slice_seed.sql` and `005_debt_seed.sql`, so whatever
is proven here carries over when this moves to Supabase.

## It is already live

Deployed on **ygrant.gatchalian@gmail.com**, verified end to end.

| | |
|---|---|
| Sheet | <https://docs.google.com/spreadsheets/d/1WHktpyNWOpxUtgWftZppd77c6UD2AwWnF9H_KahS8Pg/edit> |
| Endpoint | `https://script.google.com/macros/s/AKfycbz2eMk2O2zAD5m5dILQty8hPU__sszAjBLFKFP9I2nVapy4-P-9KnXgNk3S12Pg9HUGPw/exec` |
| Key | `CITX7qjFXG7yj0JNrbLJOt8pXkG2cY2U` |

Edit a row in the sheet and the next call sees it — no redeploy. Changing
`Code.gs` does need one: **Deploy → Manage deployments → ✏️ → New version**.
Creating a *new deployment* instead mints a new URL and the old one keeps serving
the old code, which is the confusing way to spend an afternoon.

> `curl` cannot test the `POST` path. Apps Script answers with a 302 to
> `googleusercontent.com` and `curl -L` retries it in a way Google rejects with
> **411 Length Required**. That is curl, not a broken endpoint. Use PowerShell's
> `Invoke-RestMethod`, which follows it correctly. `GET` is fine under curl.

## Rebuilding it from scratch

**1. Make the sheet.** `sheets.new`, then File → Import → Upload
`residents.csv` → *Replace current sheet*. `Code.gs` reads the first tab
regardless of its name, so there is nothing to rename.

Watch `card_last4` — Sheets turns `0715` into `715`, so set that column to
Format → Number → **Plain text**. None of the current ten have a leading zero,
and the script re-pads as a backstop, but a real import will hit this.

**2. Add the script.** Extensions → Apps Script, **from inside the sheet** — a
project started at script.google.com has no spreadsheet attached and every read
comes back empty. Select all, delete, paste
`Code.gs`. The secret is already set — nothing to fill in:

```
CITX7qjFXG7yj0JNrbLJOt8pXkG2cY2U
```

Run `selfTest` from the editor first. It should log **10 rows, 6 eligible** — the
same six `v_debt_call_queue` returns. If it says 10 eligible, the
`handed_over` / `do_not_call` columns imported as text and the filters are dead.

**3. Deploy.** Deploy → New deployment → **Web app**. Execute as **Me**, access
**Anyone** — the default is *Only myself*, which serves Vapi's servers a Google
login page instead of JSON and fails as a silent tool error. Copy the `/exec`
URL.

**4. Test it in a browser** before wiring anything:

```
<url>?key=SECRET&phone=+972501234567     → שחר, 450, card 4821
<url>?key=SECRET&phone=+972531234569     → משה, no card
<url>?key=SECRET&phone=+972581234572     → מיכל, paid: true, eligible: false
<url>?key=SECRET&phone=+972500000000     → found: false
<url>?key=wrong&phone=+972501234567      → unauthorised
<url>?key=SECRET                         → the whole call queue, 6 rows
```

All six confirmed against the live deployment.

## Clearing the test rows

Every rehearsal call appends to `call_outcomes`, `payment_tickets`, `promises`,
`disputes` and `call_requests`. After a few runs nobody can tell a real result
from a probe, so wipe them between sessions:

```
<url>?key=SECRET&clear=all              → empties all five write tabs
<url>?key=SECRET&clear=payment_tickets  → just the one
```

Headers stay; only the data rows go. **`residents` is refused by name** — it is
the input, it is hand-maintained, and there is no undo on a spreadsheet reachable
by URL. To reset it, re-import `residents.csv` over the tab by hand.

## What the agent receives

```json
{
  "found": true,
  "first_name": "שחר",
  "building": "הרצל 14",
  "unit": "12",
  "gender": "m",
  "card_last4": "4821",
  "has_card": true,
  "amount": "450",
  "month": "יולי",
  "status": "unpaid",
  "paid": false,
  "attempt": "1",
  "eligible": true
}
```

Field names match the prompt's template variables, so the values can be handed
straight to it.

`card_last4` is an empty string when there is no card — never null. The prompt
branches on exactly that to mean *do not ask for authorisation, and do not
mention a card at all*.

## The one thing to be careful about

A web app deployed with Access **Anyone** is reachable by anyone who has the URL.
`SECRET` is the only thing in front of it, and Apps Script cannot read custom
request headers — so the secret has to travel in the query string, where it ends
up in logs.

That is fine for ten fictional residents. **It is not fine for real Homies
data.** Real names, phone numbers and debts behind a guessable URL is a breach.
Before a single real resident row goes in, this moves to Supabase — the schema is
already written in `supabase/`, and `v_debt_call_queue` is the same contract.

Keep `SECRET` out of git.

## Limits

- ~300–800ms per lookup, which the resident hears as a pause. Acceptable for a
  demo; measure it before promising anything about latency.
- Apps Script has daily execution quotas. Fine for testing, not for 200
  calls/day across 10,000 apartments.
- No transactions. Two calls writing at once can clobber each other — which is
  why this is read-only for now.
