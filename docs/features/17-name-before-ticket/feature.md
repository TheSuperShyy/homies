# 17 — Name and number before a ticket

**Estimate:** 2d
**Depends on:** 02 (intake, the voice agent), 11 (WhatsApp bot)
**Status:** designed 22 Oct 2026, owner approved the design; not built

## Purpose

No ticket opens without the name of the person reporting it and a number to
reach them. Homies' updated spec (22 Oct, *אפיון מעודכן לאישור*, section 1)
lists the details an agent collects: name, phone, building, flat, then the
request. The owner placed the name at the moment a ticket is opened, not at
the start of the conversation (22 Oct): *"before we can open a ticket we
should include the name"*.

Today none of the bot's tickets carries a name (0 of 31 in the 30 days to
22 Oct), and a phone call through Omni's line keeps no number when the
number arrives in its local form, so the team cannot call the reporter back.

## Behaviour

Before opening a ticket the agent has these four things. It asks only for
what is missing, in this order, and never asks for something twice:

1. **Name.** Unless the person already said it in this conversation.
2. **Phone.** On WhatsApp it is the number they write from and is never
   asked. On a phone call it is the number the call came from. The agent
   asks for a number and reads it back only when the call has none (a
   Homies internal extension, a hidden number, a web call).
3. **Building.** Checked by the ticket tool, as today. A building Homies
   does not manage is said straight away, before any name is asked.
4. **Flat.** When the person is a resident.

Then the ticket opens. What happened is already known, because it is the
reason there is a ticket.

**It sounds like a person, not a form.** One short question woven into the
conversation, no explanation of why unless the person resists, no
announcement that details are being collected. On a call, the name on its
own and then the building and flat: speech recognition hears short answers
better. On WhatsApp, one message for all three, because people type them on
one line. For feel only, never quoted into a prompt: *"על איזה שם לרשום את הקריאה?"*,
*"באיזה בניין, ומה מספר הדירה?"*, on WhatsApp *"על איזה שם לרשום את
הקריאה, ובאיזה בניין ודירה?"*.

**Exceptions, each one deliberate:**

- **A person in danger.** The team is alerted at once (`notify_team`,
  emergency), as today. The name and building are asked after the alert,
  then the ticket opens. The alert never waits for a name.
- **Someone who will not give a name.** The agent says once, in its own
  words, that it is so the team knows who to contact. If they still refuse,
  the ticket opens marked as name not given. Never a third ask.
- **A number on OXS's record (WhatsApp).** The name is still asked: the
  name on record belongs to the flat and may be someone else in it.
- **A call we placed (the debt agent).** The name and number come from the
  call's resident. Nothing is asked.
- **Payment tickets** follow the same rule: they are tickets.

## Interface

**`open_request`** (the voice intake agent and the WhatsApp bot), new fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `reporter_name` | string | yes, unless `name_declined` | The person's name as they said it. |
| `name_declined` | boolean | no | True only after they refused a second time. |
| `reporter_phone` | string | phone calls with no number of their own | The number they gave, in any form. Ignored on WhatsApp. |

New refusals, in the shape the tool already uses (`opened: false` plus a
`reason`). No row is written when one is returned.

```json
{ "ok": true, "opened": false, "reason": "need_name" }
{ "ok": true, "opened": false, "reason": "need_phone" }
```

Order of refusals, first one wins: a building that resolves to nothing we
manage (`street_unknown`, `need_number`, `number_not_on_street`,
`ambiguous`), then `need_name`, then `need_phone`, then `need_building`.

**The switch.** `NAME_REQUIRED_CHANNELS` (function secret,
comma-separated: `voice`, `whatsapp`). A channel is enforced only once its
agent's tool carries the new fields. Unset means the tool behaves exactly as
before, apart from storing a name when one is sent.

**`notify_team`**: an optional `caller_name`. The note sent to the team
starts with the name and the number when they are known.

## The caller's number on a phone call

`ctx.callerPhone` is taken in this order:

1. `call.customer.number`, as today.
2. Otherwise the user part of `call.customer.sipUri`, through `phoneOf()`.
   Omni sends outside callers in local form (`031234567`, `0509902043`),
   which Vapi leaves out of `customer.number`.
3. **Nothing** when the call comes from a Homies internal extension: the
   caller's display name is 2 to 4 digits and the number is Homies' own line,
   077-6687949. Those are staff calling from inside the office.

A call placed by Omni's dialer arrives with the display name
`dialer-<number>` and that number in the SIP URI; rule 2 reads it.

The same value goes into `interactions.caller_phone`, from the first tool
call and from the end-of-call report.

## Data

- `requests.reported_by_name`: the name, now written (the column exists and
  has been empty on every bot ticket).
- `requests.reported_by_phone`: the call's number, the number they gave, or
  the WhatsApp sender, as today.
- `interactions.caller_phone`: as above.
- **The OXS copy** (still on for the test number only): `reportedBy` stays
  OXS's own tenant for the flat (the 24 Sep rule). The description gains
  `[דיווח: <name>, <phone>]` so staff know who reported it.
- **Dashboard, tickets page:** the caller column shows the name above the
  number.

## Acceptance

1. **Voice, played calls:** in 10 common-area fault reports, the reference
   is never read out before the name was asked for or given, and every row
   has `reported_by_name`.
2. **Voice, tool:** `open_request` with no `reporter_name` and no
   `name_declined` on a call we did not place returns `need_name` and writes
   no row.
3. **Caller number:** a call from extension 201 (`"201"
   <sip:972776687949@…>`) stores `caller_phone` null and the agent asks for
   a number. A call from `031234567` stores `+97231234567`. A dialer call
   from `dialer-0509902043` stores `+972509902043`.
4. **WhatsApp, played chats:** the same as 1 and 2, and the phone is never
   asked for.
5. **Emergencies:** in 10 played emergencies, the team alert comes before
   any question about the name.
6. **Refusal:** a played tenant who refuses twice gets a ticket marked as
   name not given, and is never asked a third time.
7. **The debt agent:** `open_request` with no name on a call we placed still
   opens, with the resident's name from the call.
8. **No regression:** `scripts/check_whatsapp_rules.py` stays green, and
   `scripts/check_tools.py` passes against the deployed function.
