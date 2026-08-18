# 01 — Identity — context

## Why this exists

A maintenance request with no location is worthless. Today a resident says their
building and apartment to a human who types it; the risk is a typo. With an
agent the risk moves to ASR, and it moves to the exact field where a mistake is
most expensive — send a plumber to apartment 22 instead of 2 and the cost is a
wasted visit and an angry resident.

## Decisions

**The bot asks, rather than using caller ID.** Forced first, then chosen. Vapi
web calls carry no phone number and the demo runs on web calls because no
Israeli DID exists yet. But asking is also correct: the demo is an open mic with
the laptop passed around, so a faked identity would apply to everyone in the
room. And it is a genuine release-1 path — residents call from work phones, from
a spouse's phone, from numbers that were never in OXS. Caller ID becomes an
optimisation that skips the questions when it happens to match, never the only
route in.

**Building first, name last.** Building is the most constrained field of the
three and therefore the most recoverable from bad audio. Name is the least
reliable — Hebrew name transcription produces near-misses constantly — so it
confirms a match rather than finding one. Matching on a transcribed Hebrew name
would generate false positives, and a false positive here is worse than no match
at all, because it silently attaches the request to the wrong household.

**An unmatched caller still gets a ticket.** The alternative — refusing to
proceed until identity resolves — turns a leak report into a dead end. The
building and unit are captured as text regardless, which is enough for dispatch.
`resident_id` stays null and the row is still complete.

**Multiple matches resolve to the household, not the individual.** For a
maintenance request the apartment is what matters. Spending three turns
disambiguating between spouses is a worse experience than occasionally
attributing a request to the wrong person in the right flat.

## Constraints

- Vapi web calls have no caller ID. Not configurable.
- Azure `he-IL` is the only viable Hebrew STT; Deepgram has no Hebrew at all.
- Israeli building references are inconsistent in the wild: street plus number,
  a name, or an internal OXS code, depending on who is speaking.
- ~200 buildings and ~10,000 apartments, so `(building, unit)` is selective
  enough to be a practical key.

## Known failure modes

- **Apartment number misheard.** The dominant one. Mitigated by read-back here
  and by the normaliser in [05-messy-input](../05-messy-input/context.md).
- **Building spoken as a name we hold as an address**, or the reverse. Loose
  matching plus a clarifying question; below a confidence floor, treat as
  unmatched rather than guessing.
- **Caller does not know the building's registered name.** Fall back to the
  street. Residents reliably know their street.
- **Seed data is not real data.** The demo runs against ten seeded residents
  with invented names. Anyone from the room calling about their own building
  will be unmatched, which is correct behaviour but reads as failure if not
  explained. Say so during the opening.

## Open questions

- ~~Does Homies have a canonical building list we can import, or is it free text
  in OXS?~~ **Answered 13 Aug: canonical, and imported.** `/buildings` returns
  193 records (173 active) and `/buildings/:id/apartments` returns their 4,092
  flats; both now live in Supabase (migration 016) and refresh via
  `scripts/oxs_buildings_sync.py`. So loose matching is a **fallback, not the
  design** — an address is matched against the real list, and what does not
  match is refused rather than recorded. Two measured facts changed the shape
  of it: street + number is unique across the whole portfolio, so *the city is
  never worth asking for*; and the registered street name is sometimes longer
  than the spoken one (`אלתרמן נתן`), so matching needs a second,
  number-anchored pass. See
  [11-whatsapp-bot/prompt.md](../11-whatsapp-bot/prompt.md).
- Should an unmatched caller be asked for a callback number? It is the one piece
  of information that makes an unmatched ticket actionable. Deferred to
  rehearsal — it costs a turn, and turns are expensive on a call.

## Related

[The demo design](../../specs/2026-08-02-demo-design.md) ·
[02-intake](../02-intake/feature.md) ·
[05-messy-input](../05-messy-input/feature.md) ·
[001_slice_schema.sql](../../../supabase/001_slice_schema.sql) lines 17–32
