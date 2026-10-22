# 17 — Context: why, and what was ruled out

## Where this came from (22 Oct 2026)

Homies sent an updated spec for approval. Its section 1 says the voice agent
collects the caller's name, phone, building address, flat when relevant, and
the nature of the request. Section 6 says the WhatsApp bot identifies the
person and building and does not ask again for what can be reliably
identified.

A read-only check against live showed the gap. The voice agent never asks a
name, and no bot ticket in 30 days carried one (`reported_by_name` was empty
on 31 of 31). Homies' old ManyChat bot asks four questions on five of its
six doors: full name, address, floor, flat. Yariv described the call
centre the same way on 15 Sep. The owner's question was the right one:
*"how can we identify who open the ticket then"*.

## Why the name was dropped before

On purpose, and wrongly. On WhatsApp the number already identifies the
sender, and OXS holds a name for every flat (8,016 residents, all with a name
and a phone), so asking looked like the old bot's form, which Yariv and the
owner had called robotic. On 15 Sep the bot asked for a full name before a
payment ticket, and that was treated as a bug: tickets were cut down to
building and flat, and the name stayed only on the balance check (Homies'
13 Aug security rule). What that missed:

- the name in OXS belongs to the flat, not the person (a household, an owner
  when the caller rents, a relative);
- on a phone call nothing identifies the caller at all;
- Homies' team works with the name; their old bot and their call centre both
  ask for it.

## The caller-ID finding (22 Oct, corrected the same day)

The three calls that stored Homies' office number came from internal
extensions 200, 201 and 202: staff testing from inside the office. Omni does
pass outside callers' numbers, in local form (`03…`, `05…`). Vapi leaves
those out of `customer.number`, and nothing in our code read the SIP URI, so
two outside calls on 21 Oct stored no number at all. That is our fix, not
Omni's. A dialer call also arrived with `dialer-<the number it rang>` as the
caller's name, which matters for feature 15 later.

## Choices, and what was ruled out

- **Asked when the ticket opens, not at the start** (owner, 22 Oct). The
  first design opened every call with *"עם מי אני מדבר?"*. Rejected: the
  owner wants the name as part of opening a ticket. The conversation still
  starts with what happened.
- **A backend refusal behind the prompt.** On 23 Aug the chat model was
  taught to verify, then open, and in five live runs it never chained the
  second call. A rule that must hold goes in code: `open_request` refuses
  without a name, the way it already refuses without a building.
- **A switch per channel.** If the function enforced the name before an
  agent's tool could send one, that agent would get `need_name` forever and
  open nothing. So each channel is switched on only after its tool ships.
- **The name asked even when OXS has one.** The record names the flat, not
  the person writing. Confirming the OXS name (*"am I speaking with Adi?"*)
  was considered and dropped: it reads an OXS name to whoever holds the
  phone.
- **One message on WhatsApp, two questions on a call.** Text is typed in one
  line; speech is heard better in short answers.
- **Ruled out: a fixed form** (four questions with buttons, like ManyChat).
  The spec's section 3 asks for a natural conversation.
- **Ruled out: a separate "identify the caller" tool** at the start. It adds
  a model round trip on every call (tool turns already take about 6 seconds,
  21 Oct) and was only needed for the start-of-call design.

## Testing

Automatic, and with no OpenRouter spend (the wallet is under a dollar and
the owner's rule is no paid test runs without their go):

- **The backend's pure rules** (the caller's number from the call, internal
  extensions, the order of refusals) live in a small module the function
  imports, and run as Node tests on every change.
- **Played conversations:** Claude plays the tenants as real people, and
  plays the agent from the candidate prompt and tool texts, with tool
  results that follow the new backend. A checker scores each transcript
  against the acceptance list.
- **The existing gates:** `check_whatsapp_rules.py` for WhatsApp, and
  `check_tools.py` against the deployed function.
- **Before it counts as done:** the owner's own test call through 208 and
  their phone on WhatsApp.
