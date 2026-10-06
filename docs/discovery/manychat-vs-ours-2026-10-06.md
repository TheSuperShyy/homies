# The old ManyChat bot vs our WhatsApp bot, as of 6 Oct 2026

As of 6 Oct 2026, replacing the 5 Oct page. The old side is from the 22 Sep scan of the ManyChat page and editor, not re-read. The "ours" side is the live bot today, and the Tested column says how each feature was checked: the live chats as the test tenant Assaf Clix on 5 Oct (afternoon, before the fixes; evening, after them), the emergency runs, the "done" message on 6 Oct, and the 48 practice conversations of 4 Oct.

## In short

- **24 features:** 9 better, 9 different on purpose, 2 matched, 4 missing.
- **New since 5 Oct:** emergencies are a row of their own (fixed and retested on 5 Oct), ticket status moved from Matched to Better (it now finds a ticket from a description), and the "done" message was checked again on 6 Oct.
- **Still missing:** the same four as on 5 Oct.

## Feature by feature

| Feature | ManyChat (22 Sep scan) | Ours today (6 Oct) | Tested | Verdict |
|---|---|---|---|---|
| Entry link | `WhatsApp URL #1`, a button on a website | None. Residents write to the number. | Nothing to test. | **Missing** |
| Greeting and menu | Fixed greeting, a "continue" button, a six-row list, every time | A greeting by the hour with three buttons on a bare hello: open a service ticket, ticket status, talk to a representative. The bot can also show the buttons itself when someone is lost. | Live, 5 Oct: all three buttons used by the six test tenants; the menu came on every hello. | Different |
| Identifying the resident | Four questions (name, address, floor, flat) on five of six paths, every time; nothing remembered, nothing checked | The WhatsApp number says who is writing. Building and flat are asked together in one question, only when a ticket needs them; a flat left out is filled from Homies' records; the building is checked against the ones Homies manages. A typed name and phone only for the balance (a security check, asked once, any country's number). | Live, 5 Oct: worked in all six chats. Gap: it still asked Assaf which building, though his number is on file. | Different |
| "Already in the app?" gate | "Yes" ends the chat with reassurance; nothing is filed | None. A described fault becomes a ticket; a status question reads the system. | Live, 5 Oct: faults went straight to tickets. | Different |
| Push to the OXS app | Three times: pay there, open calls there, get updates there | Not a menu step. The payment link the bot sends is the resident's own OXS link. | Live, 5 Oct: the link was sent in two chats. | Different |
| Service call | Filed to a Monday board; the resident gets no reference number | Opens a numbered ticket (255-…), reads the number back, and shows it on the dashboard. | Live, 5 Oct: the intercom (255-1347-26) from a long, chatty story, and the dark parking (255-1348-26) from three words full of typos. | Better |
| Emergencies | No emergency path (none in the 22 Sep scan) | An urgent ticket with its number, and nothing else: no advice, no instructions, no "the team is on the way", no phone numbers. Pushed, "that's the only thing I can do from here". After office hours the alert to the team waits until 09:00. | Live, 5 Oct: the first run failed (folded into another ticket, advice and "on the way" sent). Fixed the same evening; on the fixed bot the urgent ticket 255-1349-26 opened and nothing forbidden reached the tenant. | Better |
| Photo | Optional yes/no, then one image attached to the Monday update | Kept with the ticket if one is sent (private storage, thumbnails on the dashboard). The bot does not ask for one. | Practice run, 4 Oct: passed (the copy into storage was not run). Not tested live. | Different |
| Elevator fault | "Did you contact the elevator company?", then the company and a description, emailed to the office inbox | A ticket like any other, urgent when someone is stuck. No elevator-company question and no email. | Live, 5 Oct: the lift ticket 255-1343-26 opened. The elevator-company step does not exist. | **Missing** |
| Repeated elevator problem | Written down and closed with no follow-up | Opened as a ticket | Covered by the lift test above. | Different |
| Quote for a prospect | An intro, three building questions, each answer written to a leads board | A note to the team with the details; no leads board. | Practice run, 4 Oct: the note went out. | **Missing** |
| House manager | Description to the inbox, assigned to a user who no longer exists | A note to the team that names a person. After office hours the alert waits until 09:00. | Live, 5 Oct: a call-back request was passed on; it was after hours, so the alert waited for the morning, as designed. | Better |
| Payments | App gate, then the app link, then a rep or close | The balance after a typed name and phone, and the resident's personal payment link. "I want to pay" with no link opens a payment ticket and tells the team. | Live, 5 Oct: the link was sent twice. Open bug: the balance (2,000 ₪) was found but never reached the tenant. | Better |
| Accounting and talk to a rep | Free text, assigned to a team member | "Talk to a representative" opens with "Hi, this is Michael from Homies, how are you today?". Asked straight out, he says he is the digital assistant and offers a person. A person's reply in the inbox pauses the bot. | Live, 5 Oct: the greeting, and the honest "digital assistant" answer to "person or bot?". | Better |
| Back to menu | On two questions | The menu comes back on a bare hello, or when the bot shows it. | Live, 5 Oct: on every hello. | Matched |
| Unanswered question | The chat is closed silently, with no message | Nothing closes; the next message carries on. | Not tested on purpose. | Different |
| Ticket status | A field that remembers the last report | Looks up the flat's or building's open tickets, by number or by description, and says honestly when there is no date. | Live, 5 Oct: found the mould ticket 255-1341-26 from a description alone (it could not before the 5 Oct fix). Was "Matched" on 5 Oct. | Better |
| "Done" message | Monday status drives a flow (silent for a month, wording never seen) | When the office marks a WhatsApp ticket resolved on the dashboard, the resident gets the approved "your ticket was handled and closed" message within 2 minutes. | Live, 6 Oct: 255-1346-26 resolved on the dashboard, delivered to the phone 2 minutes later. | Better |
| 23-hour follow-up | A flow, never seen wired | None | Nothing to test. | **Missing** |
| Test tag | A tag, checked by nothing | Test messages are skipped in code | Not tested. | Different |
| General questions | Not in the menu | Answers about services, regions and the fee from Homies' own list, and nothing invented. | Live, 5 Oct: what the 250 ₪ fee covers, item by item. | Better |
| Alert to a person | Assigned to a team member, with no alert | A named person is mentioned in the inbox, on WhatsApp and from the phone agent. After office hours the alert waits until 09:00. | Live, 5 Oct: two alerts held until the morning, as designed. | Better |
| Stack | Monday for tickets, Make as the router, ManyChat as the inbox | Our own database and dashboard, n8n, Chatwoot, Meta WhatsApp | Not a test item. | Different |
| OXS | Never read or written | Read only; tickets are copied to OXS for one test number only. | Live, 5 Oct: the test tickets reached OXS. | Matched |

## Found in testing, still open

- The balance amount is not said: the bot finds it, but the reply that carries it is stopped and the second try leaves it out (5 Oct).
- A known resident is still asked which building (5 Oct).
- "Anything else?" ends too many replies, five in a row in one chat (5 Oct).
- Michael once spoke of himself in the feminine (מבינה) (5 Oct).

## What we are missing, in the order it would hurt residents

1. **Elevator faults.** Needs the per-building elevator company list from Yariv.
2. **The 23-hour nudge.** Cheap: a scheduled check over open tickets, no template needed.
3. **Photo to the team.** Covered if the team works in the dashboard.
4. **Quote leads board.** A second place to write; the owner decides.

## What the old bot had that we should not copy

- **Silent close** on any unanswered question.
- **Chats assigned to "Unknown user",** so house-manager and quote chats may have reached nobody.
- **The office email** as the only record of an elevator fault.

## Open decisions for the owner

- Whether a bot ticket should also land on the old Monday board before the cutover.
- Whether the elevator branch asks the resident for the company, or looks it up per building once Yariv supplies the list.
- Whether to build the 23-hour nudge at all, given that the old trigger was never confirmed.
