# 16 — Human handover — context

## Why this exists

PRD item 3 asks for "seamless human handover" on one central number. The
toggle half existed since 21 Aug (a human reply silences the bot). The alert
half did not: WORKLOG 9891 (16 Aug) recorded that `transfer_to_human` notifies
nobody, and it stayed that way through the Chatwoot cutover. A resident told
"a representative will get back to you" stopped chasing, and the row sat in
`call_outcomes`. The owner asked on 3 Sep how representatives would be alerted
at all, given the shared number. This is the answer.

## Decisions

**14 Sep, evening — the note speaks to a rep, not to the builder.** The
owner read a note in translation ("Source: Bot decision", "There is no
escalation for such a request") and asked for words a non-technical person
understands. The test: could a new rep act on the note with no one
explaining the system? So: what happened, who it is, what they want, what
to do — nothing about how the note came to exist, except the backstop,
which says in one sentence that the bot told the resident the team knows
and the note was made for that reason. The words live in one place
(`n8n_handover.py`, DECIDE); the harness prints them, so a rewording is a
run of `n8n_handover_test.py` and a read of four shapes: emergency,
escalation, voice, morning page.

**14 Sep, afternoon — voice joined, on the same wire.** The owner asked for
the chatbot's durability on the inbound voice agent. What was found first:
the voice tool text said *call after telling the caller a representative
will get back to them … close the call after calling it* — a promise and a
hang-up — and its handler notified nobody; and the WhatsApp `notify_team`
had been posting six reasons the handler's allow-list did not know, stored
as `caller_request` for a day (migration 030 widened the CHECK to three
vocabularies). Decided: a voice call becomes a Chatwoot conversation **only
so the mention has somewhere to land** — a dedicated `api` inbox, nothing
sent back out of it; the caller's words go in as an incoming message
because that is what sets `waiting_since` (an empty thread would be
`served` by the next tick in office hours); the contact is the CALL, not
the apartment, because the ask comes before the address and an identity
built on the address opened a second thread mid-call with the same notes
on it (the first live probe) — the apartment is the contact's name and the
number its phone, and those are how a later call is found; contact calls on
the admin token (not on the bot's allow-list), the note on the bot (a
User's self-mention notifies nobody); a fresh webhook secret in n8n's
credential store, never the leaked `N8N_WEBHOOK_SECRET`; the backstop
lives at end of call, in code, because there is no mid-call hook without
`conversation-update`. Step 0 measured before anything was built: the
account-scoped agent bot writes on an inbox it is not attached to (note,
attributes, priority, team, labels all 2xx) and its team mention raised
`conversation_mention` 694 — so the sub-workflow keeps its bot credential
("Design A"). The debt agent shares the handler and is gated out by
assistant id. Probed on the candidate prompt with the repo's tool
declarations (`prompt_probe.py --file … --repo-tools`): after two text
rounds, the tool fires with the right reason on every threshold ask and the
number a caller gives late reaches the team; what stays is gpt-4.1's
"יחזרו אליך" and a "רוצה שאעביר?" question on the money asks — recorded,
not chased.

**14 Sep — the mention is back, as a team note, and the sentence in front of
it has to be true.** Owner's refinement: the bot is all of customer support;
past its threshold it says it has let the right team know; "a mention in
Chatwoot is ok, like regular" is what makes that true. Decided with it: the
reasons name the matter and choose the team; priority medium except
emergencies; the guard is per reason within 24 h (`handover_reasons`); only
an emergency escalates — nobody was promised a time, and paging Management
ten minutes after a dues question is the workload this exists to cut (my
call, stated to the owner in the plan); office details only when asked;
emergencies never end on the office line. Measured on the first probes of
the day (execs 40747–40796): gemini-2.5-flash called the tool once in five
and *wrote* that it had told the team the other four times, promising a
call-back in three — so the prompt now says saying is not doing, the
sentence ends at "the team knows", nobody is asked to confirm, no help is
"sent", and the backstop regex learned the intent and call-back shapes
(`לרשום|לעדכן|להעביר`, `יחזרו אליכם|יצרו קשר`). After that: four of five
tool calls with the right reason and team, no call-back promises, the
decline respected; still open, a reflex to append "יטפלו בזה" / "בדרך" /
"לשלוח עזרה" in about half the replies, and the national number skipped in
one of two lift runs. Recorded, not chased with more rules.

**13 Sep — no paging at all, on WhatsApp.** Owner's direction, verbatim in
`feature.md`, in force for one day. The three paths below were removed from
the WhatsApp workflow by `scripts/n8n_whatsapp_nopage.py` and the mention
came back the next day under `n8n_whatsapp_teamnote.py`; the decisions that
follow describe how the alert worked from 3 Sep and still govern the
sub-workflow. Rejected on 13 Sep, by the owner, with the cost
stated: keeping emergencies as the one paging case. He chose office details
for those too. What replaced paging is in the prompt: the bot handles a
fault (ticket), a balance or a status (tools), and for office matters says
the office handles it and gives its details, without saying it passed
anything on and without promising a call. The claim signal, the 24-hour
guard, the department rule and the escalation clocks are all dormant.

**The alert is a private note that @mentions the department's team.** Chatwoot
expands `[@x](mention://team/<id>/<name>)` to every member and raises a
`conversation_mention` for each, on every channel the person has enabled.
Rejected: assigning the team (notifies nobody — there is no team-changed
handler); letting Chatwoot's own bot-handoff event broadcast (pings all 19
seats, and needs bot threads kept `pending`, which the owner reversed on 21
Aug); n8n round-robin to one online agent (n8n would own availability state
Chatwoot already owns, and a person at lunch is a black hole). Round-robin may
return as an escalation step once shifts are real.

**Chatwoot only, no side channel.** Owner's choice, 3 Sep, from four options.
Email on every handover, a WhatsApp template to staff phones (blocked until
business verification anyway), Telegram and SMS were all declined. Email may
come back as the level-2 escalation once the office mailbox credentials exist.

**The bot keeps answering while a handover waits.** Owner's choice. A silence
gate would leave a 22:00 follow-up unanswered; the representative joins a live
thread instead. The prompt already says the bot and the departments are one
service.

**Out of hours, queue until 09:00.** Owner's choice. Nothing is paged at night;
the first tick after 09:00 pages everything labelled `after-hours`. The bot
says the office is closed in its own words, from the office-hours fact plus
the time clause now injected on every turn. No on-call branch was built.

**Writes on the bot token, the read on the admin token.** Bots may call show,
toggle_priority, custom_attributes, assignments, labels and messages (Chatwoot's
own allow-list), so no service user was needed and the activity log says
"Assigned to service by Homies bot", which is true. The read moved to the
admin token because of a Chatwoot bug (below). A dedicated "dispatcher" user
was in the plan and turned out unnecessary; the SSH route to create one was
also blocked, which is what forced the check that made it unnecessary.

**State lives on the conversation, in custom attributes, and every stamp is
the whole set.** `POST /custom_attributes` replaces on 4.16.2 (measured), so the
Code node lays the change over the existing attributes, staff-set ones
included. Labels are written as a union for the same reason.

**The department is the model's judgment, never a keyword table.** The owner's
rule from 2 Sep. `department` is a tool argument with the four meanings in its
description; missing or invalid falls back to Operations for an emergency and
Service otherwise. The resident is still never told which department — the
31 Aug rule — only that the team has it.

**Fire and forget from the bot; wait from the ticker.** The bot's reply is not
delayed by six Chatwoot calls and a Chatwoot outage cannot stop it. The ticker
waits because it runs once a minute and nothing is behind it.

**Escalation at 10 and then 15 more minutes, and no further.** Defaults, not
the owner's numbers yet. Level 2 mentions every team; the office-mailbox email
is not built until its credentials exist.

**The guard is 24 hours, per conversation, upgrade excepted.** The tool and the
promise sentence can fire in one turn, and a tap is followed by the model's own
tool call a turn later; both were live double-fires. Only an `emergency` over a
non-emergency gets a second note. The promise backstop also stands down now
when the tool ran — since 1 Sep it decided on the sentence alone and transferred
twice.

## Constraints

- Chatwoot 4.16.2: `GET /conversations/{id}` with an agent-bot token answers
  500 once a team is assigned (bisected 3 Sep; priority, labels and attributes
  are fine). The admin read is unaffected.
- `POST /labels` and `POST /custom_attributes` replace the set.
- **A team with "allow auto assign" on hands the conversation to a member the
  moment the team is assigned** ("Assigned to Assaf Clix via service by Homies
  bot", 3 Sep). That silences the bot on the thread and lets the 15-minute
  handback return it to the bot: the exact failure this feature exists to
  prevent. The flag is OFF on all four teams since 3 Sep and must stay off;
  the mention is the alert, the team is only routing.
- Chatwoot keeps one notification per conversation per user: a newer one
  (any type) deletes the older ones (`RemoveDuplicateNotificationJob`). The
  push and email for the older one have already gone out by then; only the
  bell entry is replaced.
- **Mentioned users must be inbox members, or the mention is dropped in
  silence.** `MentionService#valid_mentionable_user_ids` is
  `account.administrators + inbox.members`, and the mentioned ids are
  intersected with it: an agent who is not on the inbox gets no notification,
  no email, no participant row, and cannot see the conversation at all. An
  administrator is always mentionable, which is why the owner's own login
  worked while the first real seat silently got nothing (6 Sep). A seat is
  added under Settings -> Inboxes -> Collaborators, or by
  `POST /inbox_members {inbox_id, user_ids}`.
- A mention also calls `add_mentioned_users_as_participants`, so the paged
  conversation appears in that person's **Mentions** and **Participating**
  views (`ConversationFinder` supports `assignee_type=mention` and
  `participating`). That, not an assignment, is what makes a handover show up
  in a rep's window.
- The sender's own mention is skipped -- but only for a `User` sender, which is
  why the bot's team mentions notify everyone including the owner.
- Bot tokens cannot list conversations; the ticker fetches with the admin token.
- The conversations list returns 25 per page. The handback fetch is capped
  there (pre-existing); the escalation fetch filters on the `handover` label
  so it stays small.
- SMTP is live since 6 Sep (Brevo free relay, `scripts/chatwoot_smtp.py`):
  invites, password resets and the email channel on *assigned*/*mentioned*
  now work once a seat turns them on.
- The representatives work on PCs. Browser push is already served by this
  install (the dashboard config carries the VAPID public key and `/sw.js`
  answers 200, checked 3 Sep); a mention becomes a Windows toast from Chrome
  or Edge only while the browser process is running, so the practical rule is
  Chatwoot installed as a browser app that starts at sign-in. Audio alerts
  play on private notes in an open tab, but their scope is per assignment and
  a waiting handover is unassigned, so audio at "unassigned" scope also rings
  on every resident message in every bot thread. The mobile app is irrelevant.
- Meta's 24-hour window: a representative replying more than 24 hours after
  the resident's last message needs an approved template, which needs business
  verification.

## Known failure modes

- **Teams are empty apart from the owner's login in Service, so a mention
  reaches one PC today.** By design until the seats exist; the note, labels
  and priority land either way.
- **A seat with "new conversation" notifications on gets pinged at the first
  bot reply of every conversation**, because `Show it in Open` flips
  pending → open with the bot token and Chatwoot treats that as a bot handoff.
  Keep that preference off; the handover alert is the mention. Swapping the
  node to a user token would remove the event entirely.
- **A representative who handles a handover by phone and never replies or
  resolves keeps the escalation running.** "Handled" means a reply or a resolve
  in Chatwoot.
- **The push toggle can look on with no subscription behind it.** Seen 3 Sep on
  the owner's PC: preferences right, toggle on, `NotificationSubscription`
  count zero on the server, so every push job ran in 100 ms with nothing to
  send. The browser's `pushManager.subscribe` never completed, which the
  dashboard does not surface. The check and the fixes are in `pc-setup.md`
  ("If no toast arrives"); the server-side proof is the subscription count.
  Resolved the same afternoon: re-enabling push in the browser registered the
  subscription (10:19 UTC), the next page ran a real push job and the owner
  confirmed the Windows toast.
- **A model that never calls the tool and never writes the handover sentence**
  leaves no handover. Same gap as before; the tap path does not depend on the
  model.

## Open questions

- Whether "יטפלו בזה" ("the team will handle it") is a promise the owner
  minds. The prompt says the sentence ends at "the team knows"; the model
  adds the clause about half the time anyway.
- *(Closed 15 Sep: wanting to pay is a `payment` ticket AND the note, on
  both bots; a balance read first is fine.)* Whether "I want to pay my dues" should be a `payment` note first or a
  balance check first. The model chose the balance check on 14 Sep.
- Who the 19 seats are, per team. SMTP is live (6 Sep); this is what remains
  to decide when the alert reaches anyone.
- The reason → department default and the 10 / 15 minute clocks, once the
  owner has watched a week of real handovers.
- Whether level 2 should also email the office mailbox -- credentials exist
  now (Brevo), the decision is still open.
- Voice: gpt-4.1 says "הצוות … יחזרו אליך" in most replies even after the
  tool ran (the note is true; the promise is not ours to make), and asks
  "רוצה שאעביר לצוות?" on the money asks before calling. Two prompt rounds
  and a tool-result hint did not move it; a third round is the owner's call.
- Voice: a thread in the Voice inbox is closed by a rep pressing Resolve
  after phoning. Until the seats exist nobody does that, and the ticker's
  `handover` fetch reads the first page (25) only -- paginate it if unresolved
  voice notes ever pile up.
- Voice: the number a caller dictates may land in the note in WORDS (the
  every-number-in-words rule bleeds into the tool argument; the tool text
  now says arguments are never spoken). Readable either way.
- `retryOnFail` is inert on every Chatwoot write in the sub-workflow: they
  continue on error, and n8n only retries a node that throws (found in the
  14 Sep review). The WhatsApp path has run that way since 3 Sep; the
  voice-note workflow's two load-bearing writes stop the workflow instead.
  Deciding the same for the sub-workflow is a follow-up.

## Related

`scripts/n8n_whatsapp_teamnote.py` (14 Sep: `notify_team`, the note branch,
its snapshot and `--restore`), `scripts/n8n_whatsapp_nopage.py` (13 Sep: the
removal it builds on), `scripts/n8n_handover.py` (the sub-workflow),
`scripts/n8n_whatsapp_handover.py` (the bot wiring, superseded),
`scripts/n8n_handback_escalate.py` (the ticker),
`scripts/n8n_handover_test.py` (the harness), and for voice (14 Sep)
`scripts/chatwoot_voice_inbox.py` (the inbox and the bot-token probe),
`scripts/n8n_voice_note.py` (the voice-note workflow),
`scripts/voice_note_test.py` (nine cases through the Edge Function),
`supabase/030_team_note_reasons.sql`, and the pre-change snapshots
`docs/handover/n8n-whatsapp-live-03sep-before-handover.json` and
`docs/handover/n8n-handback-live-03sep-before-escalation.json` (secret
redacted; `--restore` re-inserts it from `.env`). Plan:
`~/.claude/plans/i-need-to-plan-structured-boot.md`.
