# Homies — feature status

**As of 11 August 2026.** Every feature, what state it is in, and what each
missing piece is waiting on.

Written for the people who will use and buy the system. Nothing here describes
how it is built.

---

## Legend

| | |
|---|---|
| ✅ | **Working** — a resident or a staff member can do this today |
| ⚠️ | **Working, with a limit** worth knowing about |
| 🕐 | **Built, not switched on yet** — finished, waiting on a decision to go live |
| ❌ | **Not available yet** |

---

## 1. The WhatsApp assistant

| | Feature | |
|---|---|---|
| ✅ | **Open a maintenance ticket** | Takes the fault, the building, the apartment and how urgent it is, then gives back a reference number the resident can quote later. The same ticket a staff member sees. |
| ✅ | **Check a ticket already opened** | By quoting the reference, or just by their apartment. Answers in a sentence. |
| ✅ | **Check the open balance for an apartment** | The amount and which months, answered on the spot. |
| ✅ | **Tap a menu instead of typing** | Common requests are offered as buttons and answered instantly. |
| ✅ | **Send a photo or a voice note** | Recognised, and the assistant asks for the detail it still needs. |
| ✅ | **Reply in Hebrew or English** | It follows whichever language the resident writes in. |
| ⚠️ | **Message the company's number** | Runs on a **test number**, not Homies' business number. See §4. |

## 2. The voice agent — outbound, debt collection

| | Feature | |
|---|---|---|
| ✅ | **Call a resident about an unpaid month** | Opens the call, states the month and the amount, and handles the four things people actually say: they will pay, they have already paid, they dispute it, or they refuse. |
| ✅ | **Take a promise to pay** | Records the date in the resident's own words. |
| ✅ | **Record a disputed charge** | The month is put in review and the office is told, rather than the agent arguing. |
| ✅ | **Record a request for a standing order** | Passed to the office to set up. |
| ✅ | **Stop calling on request** | The resident asks to be left alone and the system stops. |
| ✅ | **Hand the call to the office** | Recorded as a request for someone to ring back. It never claims to be putting anyone through. |
| ❌ | **Ring an actual telephone** | Every call today is a **web call from a browser page**. There is no phone number. See §4. |

## 3. The voice agent — inbound, intake

| | Feature | |
|---|---|---|
| ✅ | **Take a maintenance report and give a reference** | Reads the reference back so the caller can quote it. |
| ✅ | **Answer what an apartment owes** | Answers in the same call rather than passing the caller to a person. |
| ✅ | **Answer the status of an existing ticket** | Live from the system, not a promise to check. |
| ✅ | **Keep a half-finished report** | If a caller drops off mid-sentence, what they gave is kept rather than lost. |
| ⚠️ | **Speak Hebrew naturally** | Hebrew is the working language, including correct male/female address. An English version exists for demonstrations. |
| ❌ | **Be reachable on a telephone number** | Same blocker as above. See §4. |

## 4. The office dashboard

| | Feature | |
|---|---|---|
| ✅ | **See every maintenance ticket** | Newest first, with building, apartment, urgency, and how it came in. |
| ✅ | **Change a ticket's status** | Open, in progress, resolved, cancelled. |
| ✅ | **See who owes what, apartment by apartment** | One row per apartment, largest first. |
| ✅ | **See it by owner instead** | One row per person, with all their apartments and their combined total — for deciding what to say on one call. |
| ✅ | **Filter debts by month** | The page opens on the month being collected. Any month is one click, and the view can be sent to a colleague as a link. |
| ✅ | **Read back any conversation** | WhatsApp threads and call transcripts, with the recording where one exists. |
| ✅ | **See every call and how it ended** | Including calls that reached voicemail, the wrong person, or no answer. |
| ✅ | **See headline counts** | Open tickets, urgent open tickets, all tickets, conversations, and calls recorded. |
| ⚠️ | **Open the dashboard** | Live on the web, but there is **no login** — anyone with the address can read it. Fine during the build, must be closed before real use. |
| ❌ | **See how many payment links were sent** | Not built, and nothing sends them yet. See §5. |
| ❌ | **Take over a conversation from the bot** | See §5. |

---

## 5. Not available yet, and what each is waiting on

### ❌ Calls to and from a real phone number

Everything on the voice side works, but only as a browser call. Residents
cannot ring the company and the system cannot ring them.

**Waiting on:** a phone line ordered from the supplier. The long pole is
**Homies' company registration documents** — an Israeli number cannot be issued
without them, and that step takes one to three weeks. **Nothing else on this
list blocks as much as this one.**

### ❌ Sending a payment link to the resident

During a call the agent can record that a payment link should go out, and that
request is stored. **Nothing delivers it** — no link has ever reached a
resident, which is also why the dashboard has no count of links sent.

**Waiting on:** a decision on who sends it. The building-management system
offers no way to generate the link automatically, so it either goes out from
the office by hand or the flow changes.

### ❌ A person taking over from the bot mid-conversation

When the bot cannot help it records that the office should follow up, and tells
the resident so. But a staff member cannot step into the live conversation.

**Waiting on:** the shared inbox being connected. The inbox software is already
running and already owns the number; it is simply not wired to the assistant.

### ❌ Anything happening automatically overnight

Resident and debt information is pulled from the management system by hand
whenever someone runs it. There is no nightly refresh, so the figures are only
as fresh as the last manual run.

**Waiting on:** scheduling work on our side. No external dependency.

### 🕐 A per-apartment answer for owners of several apartments

Finished, not switched on. Today, an owner of two apartments who asks what they
owe hears **one combined figure** rather than a figure per apartment, and
cannot be identified by their second apartment number. The office dashboard
already shows this correctly; only the assistant's own answer is waiting.

**Waiting on:** a decision to update the live assistant. The voice agent is
deliberately frozen at the moment.

---

## 6. What is in the system right now

| | |
|---|---|
| **Residents loaded** | 7,391, with real names and real mobile numbers, across 173 active buildings |
| **Apartments in arrears** | **122, owing ₪101,519.70**, held by 120 residents |
| **Months covered** | January to July 2026 — 108 apartments owe July, tapering to 4 owing January |
| **Not loaded** | A further **18 apartments owing ₪8,750** have no phone number on file in the management system, so they are not in the system and cannot be contacted by it |
| **Test data** | None. Every demo and placeholder record was removed on 10 August |

### ⚠️ The safety interlock

**Every resident is currently marked "not handed over", which means the system
cannot call anybody.** This is deliberate. A person has to review and release
residents before any campaign runs, so nobody is contacted by accident during
the build. **Nothing will dial until that is done on purpose.**

---

## 7. Decisions needed from Homies

1. **Order the phone line**, and provide the company registration documents.
   This unblocks more than anything else on the list.
2. **Confirm the arrears figures**, or say where the office records arrears.
   The management system's finance module reports only one debtor across all
   193 buildings, so the figures above were calculated from payment records
   rather than taken from the system directly. They are our figures, not yours
   — worth confirming before they are used for collection.
3. **Decide how residents send payment proof** — WhatsApp screenshot or email.
   Both work; the office needs to pick one.
4. **Decide who owns the WhatsApp number**, and grant business access rather
   than sharing a login.
5. **Name the staff who need inbox access**, and which departments they cover.
