# OXS payment link — the endpoint as we use it (rev 1.3, 17 Sep 2026)

The vendor's spec is `local/media/OXS_External_API_v1-rev1.3.pdf` (not in the
repo). This is the part of it the bot depends on, so a cold session does not
need the PDF. No key values here; the keys live in `.env` only.

## The call

`GET https://api.oxs.co.il/api/external/v1/apartments/:apartmentId/payment-link`
Header `x-api-key`, **finance** module, read-only key (`OXS_KEY_DEBTS`).
Optional `?payerId=` narrows to one payer; we never send it (400 if stale).

Response, always `links` as an array:

```
{ "status": 1, "data": { "apartmentId", "buildingId",
  "links": [ { "payerId", "payerType": 1 tenant | 2 owner | 3 manager,
               "payerRole", "firstName", "isMain", "link" } ] } }
```

- `apartmentId` is the OXS `_id` — ours is `apartments.id` (016), refreshed
  by `scripts/oxs_buildings_sync.py` (last run 17 Sep; 4,145 apartments).
- One link per payer; an owner and a tenant get two. **Every link of an
  apartment opens the same debt**; they differ only in who is identified.
- **Each call mints a NEW link.** Links never expire. Store the one you got;
  we do (`payment_links.link`), and a second ask returns it with no call.
- `links: []` with 200 = no active payer. Not an error.
- The link's host is the OXS tenant app, not the API. Use it verbatim.

## Errors

| code | meaning | what we do |
|---|---|---|
| 400 | `payerId` not an active payer here | never sent, so never seen |
| 401 | key missing / unknown / disabled / **expired** | `unavailable` → ticket route |
| 403 | wrong module, or the id is another company's, malformed, or unknown | `unavailable` |
| 409 | the payer pays for several apartments in this building | `several_apartments` → ticket route |
| 429 | rate limit, `Retry-After` in the body | `unavailable`, no retry inside the turn |

Rate limits are **per key**: 60 a minute, 1,000 an hour. The finance key also
serves the twice-daily CI sweeps (a handful of GETs); the bot adds one GET per
first ask per resident. One key per integration is what the spec asks for;
the owner chose to reuse `OXS_KEY_DEBTS` for now.

## Keys expire

Every OXS key expires: default 365 days, maximum 730, reminders emailed 30, 7
and 1 day before. **Rotation replaces the secret and does not extend expiry.**
An expired key answers 401, which the bot turns into `unavailable` and the
ticket route — silently. **Nobody has recorded when Homies' three keys
expire; ask Yariv / OXS support and write it in HANDOVER.**

## Sensitivity

Whoever holds a link can view and pay that apartment's balance, forever. So:
only to the number on file (the bot's identity rule), never in a log line
(`get_payment_link` logs status codes and apartment ids only), never selected
by the dashboard (the Links tab shows that one went out, not the URL). It does
reach `messages.body`, Chatwoot and n8n execution data, the same places the
balance already reaches — the staff audience, accepted and named.
