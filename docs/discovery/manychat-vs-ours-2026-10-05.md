# The old ManyChat bot vs our WhatsApp bot, as of 5 Oct 2026

Supersedes the "Old vs ours" table in `manychat-scan-2026-09-22.md`, which was true on 22 Sep
and is stale now: the menu changed on 4 Oct, the "done" message went live on 23 Sep, the
human handover alerts landed on 3 Sep, and the bot is at memory epoch 73.

The old side is taken from the 22 Sep scan (the editor screenshot plus the API), not re-read
today. The old bot may have been edited since; ask the client before treating a row as final.
The "ours" side is read from the live code paths and the 4 Oct QA run, with the source named
where it matters.

## In short

- **Same job, different shape.** The old bot is a router to people: six doors, each ends in a
  person, a Monday item, or an email, and nothing gives the resident a reference number. Ours
  is a bot that acts: it opens a numbered ticket, reads its status, and tells the resident
  what it can and cannot do.
- **We have what the old bot never did:** a ticket with a reference the resident can quote
  (`255-NNNN-YY`), status by number or by building and flat, a building balance and payment
  link, a "your ticket is done" message, handover alerts to a named rep on both WhatsApp and
  the voice agent, and general questions answered from the service catalogue.
- **The old bot did four things we do not:** an elevator-company gate with an office email,
  a photo step that files the photo to Monday, a quote intake that writes a leads board after
  every answer, and a 23-hour "is your request still relevant?" nudge. Two of the old doors
  also assigned chats to a team member who no longer exists, so for house-manager and quote
  chats the old bot may have reached nobody.

## Feature by feature

Status column: **Matched** (both do it, same outcome), **Better** (we do it and the old bot
could not), **Different** (both do it, differently on purpose), **Missing** (the old bot did it,
we do not), **Open** (neither is settled).

| Feature | ManyChat (22 Sep scan) | Ours today (5 Oct) | Status |
|---|---|---|---|
| Entry link | `WhatsApp URL #1` growth tool for a website button | None. Residents write to the number. | Missing |
| Greeting and menu | Fixed greeting, a "continue" button, a six-row list, shown every time | Fixed greeting with three reply buttons on a bare hello: open a service ticket, status of an existing ticket, talk to a representative (4 Oct). A hello that already carries a matter gets no buttons (20 Sep). The model can also show the menu on judgement (`show_menu`). | Different |
| Identifying the resident | Four questions (name, address, floor, flat) on five of six doors, every time | Building and flat asked together (18 Sep). The sender's number is the phone. Full name and phone asked only where money is read (`get_balance`). `verify_address` checks the building is one of ours. | Different |
| "Already in the app?" gate | Yes ends the chat with reassurance, nothing filed | None. A described fault becomes a ticket. A status question reads the database. | Different |
| Push to the OXS app | Three times: pay there, open calls there, get updates there | None as a menu step. The payment link is the resident's own OXS link (`get_payment_link`). | Different |
| Service call | Filed to Monday board 1270620891 with the whole intake; resident gets no reference | `open_request` writes a `requests` row with a `255-NNNN-YY` reference read back to the resident. Shown on the dashboard `/tickets`. Monday is not written. | Better |
| Photo | Optional yes/no, then one image attached to the Monday update | `store_media` attaches the photo to the request (private bucket, thumbnails on the dashboard). The bot does not invite a photo; it keeps one that arrives. | Different |
| Elevator fault | "Did you contact the elevator company?" gate, then company and description, emailed to the office inbox, which forwards in office hours | A service call like any other. No elevator-company field. No office email; the office sees it on the dashboard. | **Missing** |
| Repeated elevator problem | Written down and closed with no hook | Opened as a ticket | Different |
| Quote for a prospect | Intro, then three building questions (address, floors, flats), each answer written to the leads board | `notify_team` with the details, as a note for the team. No leads board. | Missing (board) |
| House manager | Description goes to the inbox, assigned to a deleted user | `notify_team`, a note to the team with a mention | Better |
| Payments | App gate, then the app link, then a rep or close | `get_balance` (name and phone), `get_payment_link`, "I want to pay" opens a ticket and tells the team. A payment link that cannot be sent opens an open request, so the office has the job (22 Sep). | Better |
| Accounting and talk to a rep | Free text, assigned to a team member | `notify_team`, which mentions a rep. A human reply in the inbox pauses the bot (`_claim`). | Better |
| Back to menu | On two questions | The menu returns on a bare hello or on `show_menu`. | Matched |
| Unanswered question | Chat closed silently, no message | Nothing closes. The next message continues the conversation (memory epoch). | Different |
| Last-report memory | A subscriber field | `get_request_status`, by reference or by building and flat | Matched |
| "Done" message | Monday status drives a ManyChat flow (silent for a month, wording not seen) | `ticket_resolved_he` template, proven end to end on 23 Sep (dashboard resolve, outbox, Chatwoot send). At cutover the template must be recreated on Homies' own WABA. | Better |
| 23-hour follow-up | A flow, not seen wired | None | **Missing** |
| Test tag `טסטים` | Tag, checked by nothing in the flow | Test prefixes skipped in code (`TEST_PREFIXES`) | Different |
| General questions and FAQ | Not in the menu | `get_service_info`: services, regions, fee, SLA | Better |
| Human handover alert | Assigned to a team member, no alert | A named rep is mentioned in Chatwoot on WhatsApp (3 Sep, feature 16) and on the voice agent (14 Sep) | Better |
| Stack | Monday for tickets, Make as router, ManyChat as inbox | Supabase and the dashboard for tickets, n8n as router, Chatwoot as inbox, Meta WhatsApp | Different |
| OXS | Never read or written | Read only. The ticket mirror exists but is switched on for one number only (24 Sep). | Matched in spirit |

## What we are missing, in the order it would hurt residents

1. **The elevator branch.** A resident with a stuck lift gets a ticket and a team note, but the
   company is not asked and nobody emails the elevator firm. Needs the per-building elevator
   company list from Yariv first; the old bot asked the resident instead, which is a worse
   source.
2. **The 23-hour nudge.** Cheap on our side: a cron over open tickets, and at 23 hours it needs
   no template. The old bot's trigger and wording were never seen, so this is a new feature,
   not a copy.
3. **The photo to the team.** We store the photo on the ticket. What the old bot added is a
   handoff to the Monday board, which we are not using. If the team lives in the dashboard, this
   is already covered.
4. **The quote leads board.** Our quote intake is one note to the team. If sales wants a board
   that grows with each answer, that is a second place to write and a decision for the owner.

## What the old bot had that we should not copy

- **Silent close on any unanswered question.** A resident who pauses mid-form is closed without a
  word. Ours keeps the conversation open.
- **Two doors assigned to "Unknown user".** House-manager and quote chats were routed to a team
  member ManyChat no longer has, so they may have sat unread. Ours notifies by name.
- **The office email as the only record of an elevator fault.** It is invisible to the
  dashboard and to any reference number.

## Open decisions for the owner

- Whether a bot ticket should also land on Monday board 1270620891 before the cutover (the open
  question from the Make scan, still unanswered).
- Whether the elevator branch should ask the resident for the company, or look it up per
  building once Yariv supplies the list.
- Whether to build the 23-hour nudge at all, given that the old trigger was never confirmed.
- The "Unknown user" finding still needs Yariv to be told, if the old bot is still reachable.

## Still not known

The other three old flows' content: the "done" wording, the 23-hour trigger, and the flow
created 30 Jul 2026 (`Untitled`). These need screenshots from the editor; the API does not return
flow content.
