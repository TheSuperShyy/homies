# Homies — feature status

**As of 16 September 2026.** Every feature, what state it is in, and what each
missing piece is waiting on.

Written for the people who will use and buy the system. Nothing here describes
how it is built. The previous version of this page was dated 11 August; the
changes since then are marked **new**.

---

## Legend

| | |
|---|---|
| ✅ | **Working** — a resident or a staff member can do this today |
| ⚠️ | **Working, with a limit** worth knowing about |
| 🕐 | **Built, not switched on yet** — finished, waiting on a decision or a scheduled push |
| ❌ | **Not available yet** |

---

## 1. The WhatsApp assistant

| | Feature | |
|---|---|---|
| ✅ | **Open a maintenance ticket** | Takes the fault, the building, the apartment and how urgent it is, then gives back a reference number the resident can quote later. The same ticket a staff member sees. |
| ✅ | **Check a ticket already opened** | By quoting the reference, or just by their apartment. Answers in a sentence. |
| ✅ | **Check the open balance for an apartment** | The amount and which months, answered on the spot, after the resident identifies themselves. |
| ✅ | **Tap a menu instead of typing** | Common requests are offered as buttons. |
| ✅ | **Send a photo or a voice note** | Recognised, and the assistant asks for the detail it still needs. |
| ✅ | **Always replies in Hebrew** | Whatever language the resident writes in. |
| ✅ **new** | **Pass a matter to the team** | Payment arrangements, a disputed bill, a document, moving in or out, a contract, a quote, or a request for a person: the assistant tells the right team in the staff inbox and tells the resident the team knows. A staff member can then reply in the same WhatsApp thread, and the assistant steps aside. |
| ✅ **new** | **"I want to pay" opens a ticket** | A resident who wants to pay gets a ticket with a reference, and the collections team is told. |
| ✅ | **Only buildings Homies manages** | An address that is not one of yours gets a clear answer and no ticket. |
| 🕐 **new** | **No emergency numbers, no safety instructions** | On your instruction: in an emergency the assistant opens an urgent ticket and alerts the team at once, and does not tell the resident what to do or whom to call. Built and tested; goes live with this week's push. |
| 🕐 **new** | **A fault inside the apartment is the resident's** | A blocked sink, a tap, an appliance: the assistant says kindly that this is theirs and opens no ticket. Common property and the building's systems still get a ticket. Goes live with this week's push. |
| ⚠️ | **Message the company's number** | Still runs on a **test number**, not Homies' business number. Meta access was granted on 15 September; the switch is scheduled with you. See §5. |

## 2. The voice agent — outbound, debt collection

| | Feature | |
|---|---|---|
| ✅ | **Call a resident about unpaid months** | Confirms who is on the line before saying anything about money, states the apartments, the months and the amount once, and handles what people actually say: they will pay, they have already paid, they dispute it, or they refuse. |
| ✅ | **Take a promise to pay** | Records the date in the resident's own words. |
| ✅ | **Record a disputed charge** | The resident sends proof to the office mailbox; the agent does not argue. |
| ✅ | **Record a request for a standing order** | Passed to the office to set up. |
| ✅ | **Hand the call to the office** | Recorded as a request for someone to ring back. It never claims to be putting anyone through. |
| 🕐 **new** | **Talks like a person, and faster** | Rewritten on your feedback: a warm opening ("Hi Michal, how are you?"), no script, plural address, no repeating the caller's words, and about three seconds less waiting between turns. Ready for you to hear before it goes live. |
| ❌ | **Ring an actual telephone** | Every call today is a **web call from a browser page**. There is no phone number. See §5. |

## 3. The voice agent — inbound, intake

| | Feature | |
|---|---|---|
| ✅ | **Take a maintenance report and give a reference** | Reads the reference back so the caller can quote it. |
| ✅ | **Answer what an apartment owes** | In the same call, after the caller identifies themselves. |
| ✅ | **Answer the status of an existing ticket** | Live from the system, not a promise to check. |
| ✅ | **Keep a half-finished report** | If a caller drops off mid-sentence, what they gave is kept rather than lost. |
| ✅ **new** | **Pass a matter to the team** | The same as on WhatsApp: the team is told in the staff inbox, a staff member phones the resident back. |
| ✅ **new** | **"I want to pay" opens a ticket** | As on WhatsApp. |
| 🕐 **new** | **Only buildings Homies manages** | An address that is not yours: the agent asks once more (a street can be misheard on a phone line), then says Homies does not manage that building, and opens nothing. Goes live with this week's push. |
| 🕐 **new** | **No emergency numbers, no safety instructions** | As on WhatsApp. |
| 🕐 **new** | **Plural address, no echoing** | The agent no longer guesses whether it is talking to a man or a woman, and no longer plays the caller's sentence back. Goes live with this week's push. |
| 🕐 **new** | **The company name, said right** | Five ways of writing the name were recorded through the agent's own voice. Once you pick the one that sounds right, it is applied everywhere the name is spoken. |
| ❌ | **Be reachable on a telephone number** | Same blocker as above. See §5. |

## 4. The office dashboard

| | Feature | |
|---|---|---|
| ✅ | **Sign in** | Since 26 August every page requires a login. |
| ✅ | **Hebrew, right to left** | Hebrew is the default. If a screen shows English, the language switch in the menu was flipped on that browser; flip it back. |
| ✅ | **See every maintenance ticket** | Newest first, with building, apartment, urgency, and how it came in. |
| ✅ | **Change a ticket's status** | Open, in progress, resolved, cancelled. |
| ✅ | **See who owes what, apartment by apartment, or by owner** | With a month filter, and a view that can be sent to a colleague as a link. |
| ✅ | **Read back any conversation** | WhatsApp threads and call transcripts. |
| ✅ | **See every call and how it ended** | Including calls that reached voicemail, the wrong person, or no answer. |
| ✅ **new** | **Take over a conversation from the bot** | Through the staff inbox: reply in the thread and the assistant steps aside. |
| 🕐 **new** | **See what was finished, not only what is open** | A "resolved" count on the overview, next to open and urgent, and a "closed tickets" line in the activity chart in place of the payment-links line that was always zero. Goes live with the next dashboard deploy. |
| 🕐 **new** | **A "needs review" tab** | Tickets the voice agent could not place fully now have their own tab. |
| 🕐 **new** | **Words instead of codes** | Ticket type, channel, call direction and how a call ended are shown in Hebrew rather than as system codes. |
| 🕐 **new** | **Test records removed** | The test calls and test tickets from our own checks (85 calls, 15 tickets) are being removed, and our test tools now clean up after themselves. The counts you saw were inflated by these. |

---

## 5. Not available yet, and what each is waiting on

### ❌ Calls to and from a real phone number

Everything on the voice side works, but only as a browser call. Residents
cannot ring the company and the system cannot ring them.

**Waiting on:** the phone line from the supplier. This blocks more than
anything else on this list.

### ✅ Sending a payment link to the resident — on WhatsApp (17 Sep)

A resident who writes "I want to pay" gets their own payment link in the
chat, generated by the management system for their apartment, only when the
number they write from is the one on file. During a phone call the agent can
still only record that a link should go out: a call has nowhere to put a URL,
and messaging the person afterwards needs the Meta template Homies does not
have yet.

### ⚠️ The company's own WhatsApp number

The assistant runs on a test number. Meta business access was granted on
15 September, so the switch to your number can now be scheduled; it replaces
the current menu on that number.

**Waiting on:** a date, agreed with you.

### ❌ Staff seats in the shared inbox

The inbox works, but only one seat exists. The team alerts above go to teams
with no members yet.

**Waiting on:** the names and emails of the staff who need access, and which
department each covers.

---

## 6. What is in the system right now

| | |
|---|---|
| **Residents** | Loaded from the management system and refreshed automatically twice a day |
| **Tickets** | Imported from the management system every fifteen minutes; the dashboard shows the same tickets your dispatchers see |
| **Arrears** | Computed from payment records, one row per unpaid month; the Debts page is the figure to work from |
| **Test data** | Being removed this week (see §4) |

### ⚠️ The safety interlock

**Every resident is still marked "not handed over", which means the system
cannot call anybody.** A person has to review and release residents before any
campaign runs. **Nothing will dial until that is done on purpose.**

---

## 7. Decisions needed from Homies

1. **Listen to two recordings and choose**: the company name (five versions)
   and the debt agent's new opening line. Both go live as soon as you pick.
2. **Order the phone line.** This unblocks more than anything else here.
3. **Confirm the arrears figures**, or say where the office records arrears.
4. **Decide how residents send payment proof** — WhatsApp screenshot or email.
5. **Set a date for the WhatsApp number switch**, now that Meta access is in.
6. **Name the staff who need inbox access**, and which departments they cover.
7. **The Telkom quote**: nothing is paid without your approval, as you asked.
8. **Nir's WhatsApp scripts**: we are waiting to receive them.
