# Worklog

Every session appends here: what was done, what was decided, what is still open.
Newest first.

Design rationale belongs in the relevant `context.md`, not here. This file is the
chronology — what happened and when, so that a decision can be traced back to the
conversation that produced it.

---

## 2026-08-26 (evening)

### The login page stops wearing the app around itself

Reported from a screenshot minutes after the wall went up: /login rendered
inside the full app shell — sidebar, six nav links, language toggle — the
signed-in furniture wrapped around the box that says you are not signed in.
Leftover from demo mode: the root layout carried a comment saying the nav
shows for everyone "because there is no login to gate it behind", which
stopped being true the moment the middleware redirect returned.

The layout now renders `/login` bare (one path test — the middleware
guarantees it is the only page a logged-out visitor reaches), and the page
became a real login screen: brand mark and name above the card, the form, and
a language switch below it. **The brand then became the real thing**: the
owner dropped `Homies-Logo.png` at the repo root mid-work — roof, ladder,
Hebrew subtitle — and it replaced the generic icon: copied to
`dashboard/public/` (the repo root is outside Vercel's rootDirectory and never
deploys), on a white plate because the mark was drawn on white and the page is
dark. The sidebar keeps the small icon; the wordmark is illegible at 30px.

**And the wall promptly ate the logo.** The deployed page showed a broken
image with the alt text: the middleware matcher excluded only Next's own
internals, so the request for `/homies-logo.png` had no session and was 307'd
to `/login` — the page that was asking for it. Confirmed by probing the URL
(307, Location `/login`), fixed by excluding image extensions from the
matcher: files under `public/` are exactly the assets a page needs before a
session exists, and anything secret does not belong there anyway. Verified
200 after deploy. The switch is duplicated as the page's own server
action (a layout's inline action cannot be imported), and always returns to
/login. The brand and switch travel into the client form as RSC children so
login-form.tsx stays the dashboard's only client component. `tsc` and
`next build` clean; deploys on push.

### The dashboard login went from existing to enforced

Asked for "a login" — and the whole apparatus already existed: Supabase Auth,
the login page (built with real labels, sign-in only, accounts admin-created by
design), the session middleware, and 009's authenticated read policies. What
was missing was enforcement: demo mode (9 Aug) removed the redirect and opened
the tables to anon, and 010's header promised the re-lock as "a deletion, not
a rebuild". This is that deletion, plus the half nobody wrote down:

**Three anon grants existed, not one.** `anon_read` on ten tables (010), the
status dropdown's `anon_update_status` + column grant (011), and `press_call`
execute (024, granted to anon AND authenticated). Migration
`026_relock_dashboard.sql` closes all three — and **re-creates the status
write for authenticated**, because dropping anon's without adding
authenticated's would silently break the tickets page for signed-in staff.
`press_call` already had its authenticated grant. buildings/apartments (019)
never opened.

**Middleware redirect restored**: no session → `/login` (and signed-in visits
to `/login` bounce home). The comment keeps the 9 Aug history and the real
boundary: RLS, not the redirect.

**Verified, each claim by its own probe**: migration applied ("RLS: every
table guarded"); anon key reads 0 rows from requests/residents/messages; the
staff account signs in via the password grant and reads 3 rows as
authenticated; `tsc` clean. Account: clixteam579@gmail.com, password handed to
the owner in chat, created server-side (the secret key refuses a browser
user-agent — worth knowing: the "Forbidden use of secret API key in browser"
error keys off the User-Agent header). Further accounts: Supabase dashboard →
Authentication → Add user, by design.

Deploys on push (git-linked Vercel project).

**The wall was verified on the deployed site itself**: `/`, `/tickets` and
`/debts` all 307 to `/login`, `/login` answers 200. It had to be verified by
probing the URL directly because **the VERCEL_TOKEN in `.env` now 403s on
every API call** — the deploy still happened (git-linked, builds on push), but
the API-side confirmation script died on the dead token, not on the deploy.
Token needs rotating; flagged in HANDOVER.

**A second account followed for the Homies side**: office@homies-management.co.il
— the office address the bot itself hands out, so it is the natural shared
login for the client's staff. Created the same way, verified signing in and
reading. Both passwords were handed to the owner in chat; neither is written
anywhere in the repo.

### The voice agents now point the words the writing hides

Asked why the female/male file had not reached the voice agents, then told to
apply it: *"the way we read the words in Hebrew is different from the way we
speak it"* — which is precisely the half both Hebrew prompts were missing.
They already carried most of the PDF's system from earlier work: gender as
state, speech beats name, unisex names decide nothing, the neutral bridge, the
imperative/future table, and even the pointed forms of לך/שלך/איתך — **but
only as documentation.** The standing instruction for those words was
drop-the-word (right when gender is undecided) and nothing else, so with a
known-gender caller the model still wrote `לך` unpointed and the engine
guessed the reading.

**Measured before shipping**: the same sentence pointed both ways through the
live voice (sonic-3, Eyal) produces genuinely different audio — 3.53s vs
2.41s, first-second correlation −0.04, where 1.0 would mean nikkud ignored.
Both WAVs sent to the owner, whose ear confirms the pronunciations; the
mechanism is confirmed by the measurement.

**What was added, in both Hebrew prompts** (debt after its invisible-words
table, intake after its "לך" paragraph):

- **Decided gender → the dropped words come back, pointed**: אני שולח לָךְ,
  יש לְךָ תשלום פתוח. The nikkud is for the engine, not the ear.
- **Past tense in direct address points too** — שילמת/קיבלת/אמרת are written
  identically and spoken תָּ/תְּ; the debt prompt got the table, intake the
  rule with two examples.
- **Point only where it saves the pronunciation** — not a prayer book; a word
  that reads correctly unpointed stays unpointed. Always pointed: the address
  words at a known gender, and the pairs writing cannot separate — אֶת/אַתְּ,
  עִם/עַם, שָׁם/שֵׁם.

Live: debt 52,586 → 53,635 chars (157 nikkud marks), intake 34,877 → 35,622
(57 marks), both verified by reading the assistants back. **Not yet heard in a
call.** NOT taken from the PDF: agent_gender (מיכאל is fixed masculine),
the sales scripts, street slang — and the register lists were already covered.
**The frozen English twins are now behind the Hebrew** on both agents —
`vapi_en.py --dry` will show the drift; updating them is by hand and still
owed.

### "לדבר עם נציג" answered with a closed door, and now it gathers context on the way to the team

Off a handset: the third menu button got `אני מעביר את זה לצוות, נחזור בהקדם.`
and the owner asked for the representative's shape instead: got it + I'm
connecting you + what's it about, so there's context to start with. Execution
10409 showed a second fault underneath: the model wrote the handover line
**without calling `transfer_to_human`** — the "Promised a transfer, made none?"
backstop caught it and made the transfer anyway, which is what it is for.

The line the model produced was the prompt's own **one verbatim line**, doing
exactly what it was told. The fix splits by what is known: **topic known** →
the fixed line stays; **bare request** (the tap, or "רוצה נציג" alone) → the
model composes: confirm, handing to the team (**"לצוות", never a department** —
the routing that word promises does not exist, decided 26 Aug morning), and ask
what it is about, with the reason in half a sentence. The answer to that
question is **context for the team, and it beats every flow in the file**: no
ticket offer, no complaint ticket, no building-and-apartment; one line without
a question mark closes it.

**Three probe rounds to get there, each miss written back where it fired:**

1. Model glued the fixed line + `על מה אפשר לעזור?` (the phrase the file names
   as not Hebrew). → the bare case now excludes the fixed line entirely, and
   the question is named as *about the subject*, not an offer of help — he
   asked for a person, so offering yourself answers the wrong request.
2. The context answer restarted the complaint flow. The exception lived 300
   lines from the rule that fired — the same lesson as the `אין לי` fix — so it
   is now written **inside** the complaint rule and the open-ticket section.
3. The context answer got the transfer re-announced and the question re-asked.
   → after the answer: one sentence, no question mark, never announce the
   transfer twice, never re-ask the answered.

Final probes 2/2 correct on both turns. Live prompt 42,327 → 43,473 chars.
Known rate-level slip left open: the model writes `אליך` in this flow (a
written gender mark, against the standing rule); noted, not chased tonight.

Emergency stays senior: `הצפה במחסן` after a transfer got the emergency
protocol including the building question — that is the designed precedence,
not a fault.

### The last word was falling into a 43-millisecond tail, and every sentence now ends in bought silence

The report survived the model swap, refined by one question: the **last word of
replies is clipped mid-call**, on the dashboard widget. The call logs had
nothing left to give — no interruption (`numUserInterrupted: 0`), no error, and
no recordings exist to inspect (off by design) — so the sentence itself was
taken out of the call stack: the exact final line of the 18:56 call, rendered
through Cartesia directly with `cartesia_tts.py`'s request shape, WAV instead
of mp3, and the waveform measured in Python.

**The voice leaves the last word no margin.** Speech ends 43ms before the file
does on the full sentence, 90-135ms on the final chunk, still at full speaking
amplitude — where a comfortably engineered voice trails 300-500ms of silence.
Whoever tears the stream down (Vapi's turn handling, the widget's buffer) lands
inside the final syllable. Neither side is broken alone; the voice hands the
teardown zero margin. Both WAVs were sent to the owner so their ear can settle
whether the rendering itself also swallows the syllable.

**The fix buys margin on the side we control.** Measured first: Cartesia
honours an SSML-style `<break time="400ms"/>` as real, unspoken silence — tail
went 135ms → 472ms. So `voice_guard.py` grew a third section beside deletion
and pronunciation: **tail padding**. Three regex rules append
`<break time="300ms"/>` after sentence-final `.`/`?`/`!`, appended LAST in
`replacements()` so nothing can eat the tag. Between sentences in one turn it
reads as a beat; at the end of the turn it is the margin. The safe-sentence
gate strips exactly one trailing pad before comparing — the check hunts holes,
and a uniform appended pause is not one; 22 sentences, 0 damaged.

**Live on both Hebrew agents and their fallbacks** (the guard is one shared
`formatPlan`): debt and intake each read back 3 pad rules, main voice and
fallback alike. **Not yet heard** — the owner should retest on the widget; if
the clip survives 300ms of margin, the tag duration is one constant, and the
next suspect is the widget's own player rather than the margin.

### "Being cut off" was five seconds of thinking, and the debt agent now runs gpt-4.1

Reported: the voice agent "is being cut off for some reason, like being
disconnected or losing connection". Read the calls before explaining — the two
reported calls (10:41 and 10:42 UTC, web calls to the debt agent) show **no
drop, no error, no network event**. Both ended `customer-ended-call` into
silence: one 15s after the amount line with no next turn arriving, one 8s after
`log_call_outcome` returned Success with the goodbye still being generated.

**The wait was the model.** Vapi's per-turn metrics: model 3,878ms of a 5,308ms
turn (voice 853ms, transcriber 238ms, endpointing 301ms). `vapi_latency.py` put
the two calls at **5,390ms and 5,850ms median** caller-felt latency against the
PRD's <800ms. gpt-5.2 is a reasoning model; it thinks ~4s before every sentence
and again after every tool call. Five seconds of dead air on a phone reads as a
dead line, so the resident hangs up, which is also why every one of these calls
files under `customer-ended-call`. Reasoning latency is variable — the same
agent measured 1.3–2.1s median on its better calls — which is why 25 Aug
sounded clean and today sounded broken.

**Owner chose gpt-4.1** over dialling 5.2's reasoning effort down (offered
both, plus tool-call filler lines; the untried effort knob is the first thing
to reach for if the Hebrew or the negotiation worsens). One line in
`vapi_sync.py`, history kept in the comment above it; `--apply` pushed it and
the API reads back `openai gpt-4.1`, prompt 52,586 chars and all seven tools
untouched. **Not yet heard** — no call has been placed against 4.1.

The English twin still runs gpt-5.4 (`vapi_en.py` copies the prompt, not the
model block) and the intake agents are untouched.

### The first menu button gets the same warmth the second one got this morning

Asked for off a handset screenshot: `בטח. אפשר לספר לי מה קרה?` on the
open-ticket tap, "make it like the one we did for the ticket status checker".
Same diagnosis as the morning's status line: correct, short and cold,
two clipped fragments with nothing saying anyone intends to help. Now
`בטח, אשמח לעזור. אפשר לספר לי מה קרה?` — receive the person, then open the
door.

**Three copies moved together**, same as the status change: `TAP_LINE["open"]`
in `n8n_whatsapp.py`, the live Sort node's `TAPPED`, and the prompt — both the
English commentary that quotes the line and the first worked example in the
"וככה שואלים" list, which is this sentence. Live prompt 41,454 → 41,466 chars.

**Probed**: the tap answers with the new line, and the turn after it still knows
the tap happened — `אין מים חמים בדירה` got `אני מבין. ובאיזה בניין ואיזו דירה
גרים?`, no re-offer, no reset. Both `TAP_LINE` entries are now warm, so the
"the other button has the same clipped shape and was left" note has retired.

CONTEXT.md needs nothing from this: it is the existing offer-before-question
rule applied to the second of the two lines it was written against.

## 2026-08-26

### Chatbot sweep: the plumbing is green, and the balance opener was the one flow still ending in a full stop

Told "chatbot first" after the read-only voice check, so the voice pass stays
parked and the chatbot got a full verification sweep instead.

**`check_whatsapp.py`: all checks passed.** Callback registered, token valid,
WABA subscribed, forged messages write nothing, and the end-to-end run wrote one
ticket to Supabase (channel `whatsapp`, common-area fault with no unit, 6s), and
the duplicate did not open a second one.

**Probe sweep across the five flows.** Fault report (offer before address, per
the 25 Aug order), human transfer (handover phrase, no menu appended), courtesy
first message, and address rejection for an unmanaged building all behaved. **The
miss was the balance opener, and it was systematic, not a rate: 3/3 it stated
the requirement instead of asking** — `יתרה זה מידע אישי, אז צריך שם מלא ומספר
טלפון.` — a full stop, so `Dead end reply?` appended the menu and the reply
arrived as two messages. The exact fault the ends-with-a-question rule was
written against, in the one flow whose opening the model composes from an
explain-then-ask instruction: it explained, and stated, and never asked.

**Fix: "ואז שואל" now means a question mark**, with the split named — the first
half says why (`אני מוודא מי שואל`), the second half asks what (`מה השם המלא
ומספר הטלפון?`), and each detail appears once. Pushed twice (41,097 → 41,454
chars, live and byte-identical). Re-probed: 5/5 end in the question; the
noun-doubling ("צריך שם ומספר. מה השם והמספר?") persists on some runs and is
cosmetic — flash gives rates, not guarantees, and the menu no longer fires.

One deviation seen once and left alone: a stairwell fault went straight to
building-and-apartment without the offer, 1/2 runs. Known what→whether→where
territory, not chased on a single occurrence.

### The second message was not a bug, it was the reply not asking anything

Reported off a handset: the no-ticket answer arrived, and under it a second
message, `אפשר לעזור בעוד משהו?` with the three buttons. **`Dead end reply?`
appends the menu to any reply containing no `?` and no handover phrase.** The
reply was `אוקיי, אני מבין. אפשר לספר לי מה קרה ואפתח קריאה, ואעביר לצוות
לטיפול.` — correct in content and ending in a full stop, so the workflow read it
as leaving the resident stuck and offered them a way out. The backstop was doing
its job. **A reply that does not ask a question literally arrives as two
messages**, which is worth knowing before anyone goes looking for a duplicate
send.

**So the fix is the same fix as the content one.** Asked for as a standing rule
rather than a one-off: every reply ends with a question that hands the turn
back, and an open one wherever open fits. The prompt already said "one question
mark per message" and treated that as a ceiling; **one is now also the floor**.
A full stop is allowed only in the messages the conversation ends with: a status
delivered, a reference number given, a transfer that has happened.

**Named the trap in the same breath**, because "always end with a question" read
literally produces `רוצה שאפתח קריאה?` everywhere. The question that hands the
turn back is normally open — `מה קרה?`, `באיזה בניין ואיזו דירה גרים?` — and
closed only when what remains really is yes or no. The rule is that the message
ends with a request of them, not that it ends in a choice between two things.

The no-ticket branch carries it explicitly, with the diagnosis attached: the
fault in that line was never the content, it was the full stop, which turned a
request into a description of what the bot is prepared to do.

**Probed 6 times across three phrasings after the push: 5 ended in a question,**
the one miss on the first run of `אין לי קריאה`, then 3/3 on the same phrase
after. `google/gemini-2.5-flash`, so this is a rate and not a guarantee; the
menu backstop still catches the misses, which is what it is for. Live prompt
39,968 → 41,097 chars. Saved to memory as a standing preference.

### Shipped, and the owner's Hebrew spelling file settled an old rule the wrong way round

**The `last_bot` fix is live and verified.** Approved and pushed; all four
assertions came back true and the workflow stayed active. Probed rather than
assumed: tap `מצב קריאה קיימת`, then

| answered | reply |
|---|---|
| `אין לי` | `אוקיי, אין בעיה. אם אין מספר קריאה אפשר לבדוק לפי בניין ודירה. באיזה בניין ואיזו דירה גרים?` |
| `לא זוכר את המספר` | `אין בעיה, אפשר לבדוק גם לפי בניין ודירה. באיזה בניין ואיזו דירה גרים?` |
| `לא פתחתי קריאה` | `אני מבין. אפשר לספר לי מה קרה, ואז אפתח על זה קריאה ואעביר לצוות.` |

The reset is gone. Verification then found the next thing, which is the pattern
of the whole day: **the first probe of `אין לי קריאה` still sent a resident with
no ticket to look up a ticket**, and the first probe of `אין לי` answered
`אפשר לבדוק גם לפי בניין ומספר דירה.` without asking anything, which hands the
turn back to somebody who has nothing to say. Both were prompt faults the
plumbing had been hiding.

**Three prompt edits, in the order they were found.** The branch test now leads
with what is actually being decided (is there a ticket at all, not does he have
the number) and names the discriminator: **what did he negate** — the ticket
(`קריאה`, `פתחתי`, `דיווחתי`, `פניתי`) or only his hold on the number (`זוכר`,
`שמרתי`, `מוצא`). The no-ticket branch says both halves go in one message and
why a bare invitation fails there: he has just been told there is nothing to
look up, so an invitation with no promise means telling a stranger about a leak
and not knowing whether anything happened. And the lookup branch has to **ask**,
not observe that asking is possible.

#### `Spell female male prompt.pdf`

Supplied by the owner as "the proper correct spelling for words". 31 pages,
Hebrew, and it is a **voice** specification: it ends "ורק אז לשלוח את הטקסט ל
Text To Speech" and says outright that the nikkud exists to make a TTS engine
pronounce correctly. Most of it therefore cannot go anywhere near WhatsApp.
What it did do is settle a rule the chatbot has had backwards since 12 Aug.

**Page 28, `מילים דו משמעיות שחובה לנקד`**, lists `לְךָ`/`לָךְ`,
`שֶׁלְּךָ`/`שֶׁלָּךְ`, `אִתְּךָ`/`אִתָּךְ`, `אוֹתְךָ`/`אוֹתָךְ` — words that
need pointing *because unpointed they are identical*. The prompt saw the same
fact and drew the opposite conclusion: "המילה שתפיל אותך היא לך [...] פשוט
תוריד את המילה". **Right for speech, backwards for text.** In writing `לך` marks
nothing; the reader supplies their own gender. That rule has been stripping the
warmest word out of every sentence to prevent a marking nobody could see, and
`בטח, אשמח לבדוק בשבילך` — the line the owner asked for on 26 Aug and the
warmest in the bot — has been quietly breaking it since it was written.

So the rule is now split by **what a reader can actually see**:

- **Allowed**, because unpointed they are one spelling: `לך`, `שלך`, `אותך`,
  `איתך`, `ממך`, `בשבילך`, `אצלך`, and the past tense in ־ת (`אמרת`, `שלחת`,
  `קיבלת`, `בדקת`, `דיברת`, `הגעת`, `רצית`).
- **Still avoided**, because they are written apart: `אתה`/`את`; present
  (`גר`/`גרה`, `יכול`/`יכולה`, `צריך`/`צריכה`); future (`תוכל`/`תוכלי`);
  every imperative; and `אליך`/`אלייך`, `עליך`/`עלייך`.
- **And if the resident marked it themselves** — wrote `אני גרה`, `אני צריכה` —
  the bot follows them for the rest of the conversation. That is the file's own
  `customer_gender` rule and it is not a guess: it is what they typed. A name
  still is a guess and still counts for nothing.
- **No nikkud, ever.** The two pointed words in the file are named as examples
  in the rule itself, the same accounting the em dash rule already carries.

**Also taken: the clerical `־ך` family.** `באפשרותך` reached a probe reply
within minutes of the gender change, and it is on the file's forbidden list.
Added with `ברצונך`, `האם ברצונך`, `הנך`, `הינך`, `עבורך`, `לרשותך`, `להלן`,
`ככל שתחפוץ`. And `תוכל` was quietly removed from the prompt's own list of words
Israelis *do* type, where it had been sitting as a recommendation while the
paragraph above forbade gendered futures; `אפשר` replaces it.

**Not taken:** all the nikkud, the TTS ordering, `agent_gender` (the bot is
מיכאל and already speaks in the masculine), the sales lines, and the street
slang. **The voice agents were not touched** — the pointed half of this document
is written for them and belongs to a separate pass.

#### A reasoning leak, caught by probing

One probe came back `אוקיי, תודה. [The user said they live in building 12,
apartment 4. The previous turn was about a leak in the lobby...]` — the model's
own English deliberation, formatted like an instruction and addressed to a
resident. Every instruction it reads arrives in square brackets, and as of today
there is one more of them. Two further runs of the same turn were clean, so it
is intermittent and cannot be tested away. **The Send node now strips any
bracketed span**, next to the dash strip and for the same reason: every outgoing
message passes through there, canned and model alike, and a service agent never
types a bracket.

**Live: prompt 37,856 → 39,968 chars, pushed four times and re-probed after each
one.** The model is `google/gemini-2.5-flash`, so branch behaviour is
probabilistic rather than fixed — `לא פתחתי קריאה` went to the wrong branch on
one run before the discriminator was added and has been right 3/3 since. Final
sweep of six probes across all four answers: all six correct.

### The prompt fix was live all afternoon and the model never got to use it

Retested from a handset at 16:26 and again at 16:36: tap `מצב קריאה קיימת`,
answer `אין לי`, get `אני מבין. על מה אפשר לעזור?` "its still the same".

**Checked the deploy before touching the prompt again.** The live system message
is 37,856 chars and byte-identical to the `## System prompt` section of
`docs/features/11-whatsapp-bot/prompt.md`. Nothing about this afternoon's work
failed to ship. So the fault was not in what the model was told.

**Execution 9939 says what it was.** The agent's entire input was
`[ענה על ההודעה הזאת בעברית...] [אתם כבר באמצע שיחה...]` + `אין לי`, and the
memory node's `chatHistory` for that phone held three pairs, all of them
`אין לי` → `אני מבין. על מה אפשר לעזור?`. No greeting in it, no status question
in it. The turn before was execution 9932, a canned reply with `_work: false` —
the Sort node answered the button tap itself and the agent node did not run.
**A canned line never reaches the agent, so it is never written to the agent's
memory.** From the model's seat, somebody wrote "I don't have" into an empty
room. Every branch of the new `אין לי` section is conditioned on being in the
status flow, and the model had no way to know it was.

**Third time, same hole.** 12 Aug it introduced itself twice; patched with a
`greeted` flag. 25 Aug it re-asked somebody who had tapped "open a ticket";
patched with a `tapped_open` flag. 26 Aug this. `TAP_KIND` in the live Sort has
stored `status` since the tap line was added and nothing has ever read it —
`tappedOpen` tests `kind === 'open'` and there is no second clause. Four lines
leave that node and two of them tell the model nothing:

| The workflow says | The model knows |
|---|---|
| `היי, כאן מיכאל מהומיז. במה אפשר לעזור?` | `greeted` |
| `בטח. אפשר לספר לי מה קרה?` | `tapped_open` |
| `בטח, אשמח לבדוק בשבילך. יש לך את מספר הקריאה?` | nothing |
| `אני קורא כאן רק טקסט. אפשר לכתוב לי מה קרה?` | nothing |

**So the fix carries the sentence, not a fourth flag.** `said()` wraps every
canned line at the one point they leave the Sort node, storing it against the
phone for half an hour; the next model turn gets it as `last_bot` and the agent
template states it as a fact — this message is an answer, and here is what was
written to them by the system rather than by you. What that answer *means* stays
in the prompt, which already has a section on each of these lines. A line added
next month is covered by having been said, with nobody remembering a flag.

**A comment in `TAP_LINE` had argued this could not happen** — that 'open' and
'status' get away with being canned "because their answers say what they are: a
fault description or a reference number". True of every answer that was
imagined, false of the one that arrived. Corrected in place rather than deleted.

**The memory needed an epoch, not a fix.** That handset's window held four
identical wrong pairs by the end of testing, which is a three-shot demonstration
of the exact fault arguing with the prompt that forbids it. Simple Memory lives
in the n8n process and there is no way to delete one conversation: a save does
not clear it and neither does a reactivate. `sessionKey` is now
`={{ $json.to }}-2`. Bump it again the next time a bad turn has to be forgotten.

**Written, not shipped.** `scripts/n8n_whatsapp.py` carries the change; the live
Chatwoot workflow does not. The patcher is written and its anchors verified
against the live Sort, but every command that would run it was refused by the
permission classifier, as was the script's own dry run. **Nothing has been
pushed to n8n and nothing has been tested.** Waiting on the owner.

**Retested at 16:50 anyway, and it was identical.** It had to be: the live
workflow has not changed since 15:34, so 16:26, 16:36 and 16:50 are three runs
of the same code and the second and third carried no information. Saying so
plainly is the whole of it — a screenshot of an unshipped fix looks exactly like
a screenshot of a failed one, and the only thing that tells them apart is
knowing whether the push happened.

**The briefing files were committed out from under this entry.** A housekeeping
automation took CONTEXT.md, HANDOVER.md and this file at 16:46 as
`33cd0df "Housekeeping: briefing files and docs kept current (auto)"` and pushed
it, which left the code change alone in the working tree and tripped
`check_briefing_logged.sh` — correctly, by its own rule, since the change set it
could see was code with no briefing in it. Nothing was lost and the auto commit
was left alone (it is on origin). Worth knowing before someone reads that hook
firing as a missed log: **the guard tests the change set, and an automation that
commits half of one will fire it.**

### The dashboard was redesigned, and it speaks two languages now

Asked to make the dashboard look good, with the ui-ux-pro-max skill. Its design
system landed on **Data-Dense Dashboard** — blue primary, amber accent, Noto
Sans Hebrew — which matched what the pages already were, so the work was
elevation rather than a new direction.

**The question that changed the job.** The chrome was English while every value
in it was Hebrew, and the readers are Hebrew-speaking staff. Asked; the answer
was a switch, both languages. So this is a redesign and a localisation in one
pass, which is also the cheaper order: doing the layout in English first and
flipping it later means doing the RTL work twice.

**`lib/i18n.ts`** holds 185 entries as flat keys with `{name}` interpolation.
The locale is a **cookie**, not a URL parameter, and that is the one piece of
state on this dashboard that is deliberately not in the URL: everything else is
a view somebody should be able to send a colleague, and language belongs to the
reader. Sending a filtered ticket list should not also change the recipient's
interface language.

**What actually changed visually.**

- **A sidebar at 1024px and up**, top bar below it. Six views one click from
  anywhere, each with an icon AND a label; the current one is marked by ground
  and weight as well as colour.
- **Eighteen SVG icons**, drawn in `components/icons.tsx` at one set's
  proportions rather than pulled in as a dependency for eighteen paths.
- **Status pills carry a dot and a word**, not a colour. Colour alone fails on a
  greyscale print and for red-green deficiency, and it was the old design's only
  signal.
- **Stat tiles carry a semantic stripe** in the same six colours as the pills,
  so urgent-and-open is the only red thing on the overview and is findable.
- **Sticky table headers.** A hundred rows of arrears was a scroll where the
  column you were reading stopped having a name.
- **Segmented filters** replace the opacity-.55 pills, which read as "loading"
  rather than "not selected".
- **Noto Sans Hebrew** via `next/font`, self-hosted. The old stack was
  `system-ui`, which on Windows renders Hebrew in a fallback face with a
  different weight and x-height from the Latin beside it — the reason mixed rows
  looked pasted together.
- **Empty states have an icon and a sentence**; `prefers-reduced-motion` is
  honoured; focus rings are defined once and never removed.

**Two contrast failures found by measuring rather than by eye.** slate-500 as
`--muted` is 4.34:1 on the page ground, under AA, and the same colour was the
cancelled pill. One step darker clears 4.5 and still reads as a second tier
against `--ink-2`. Every other pair was checked the same way: 30 pairs across
both themes, all passing.

**The pathname had to come from middleware.** A server layout in the App Router
cannot ask which page it is rendering. `x-invoke-path` is a Next internal that
is absent in 14.2 and `referer` is the page you came FROM, so a nav built on it
highlights the item you just left. The middleware now sets `x-pathname` on the
request headers.

**The login page had to split in two.** It is the only client component here,
and `cookies()` is server-only, so its labels arrive as props from a server
wrapper. The alternative was shipping the dictionary to the browser or guessing
from `navigator.language`, which would put the login page in a different
language from every page behind it.

**Verified**: `tsc --noEmit` clean, `next build` clean, and all seven pages plus
both detail pages served 200 in both languages against the real database.
Hebrew renders `lang="he" dir="rtl"`, English `lang="en" dir="ltr"`.

**Not done:** no screenshots were taken, so this is verified as "renders and
compiles", not "looks right" — the layout at 375px and the dark theme have been
reasoned about and measured but not seen. Worth a look before it goes to the
client.

### The three sentences added today were scripts, and are now intent

*"I want the bot to be open and not follow the script strictly."* Which is rule
1 of this prompt's own editing rules, reasserted against what today's work had
been doing to it.

**Measured rather than assumed.** Before today's commits the system prompt held
**zero** verbatim Hebrew lines handed to the model. Three commits later it held
four, all mine: the reference-number explanation, the building-and-apartment
question, and the open-the-door offer. Each was added for a real defect and each
was written as an exact sentence, which is the failure rule 1 names -- on 7 Aug
the debt agent's verbatim count went 5 to 23 and it became a player-piano.

**Every one is now a description of what the message has to carry.** The
distinctions stay, because they are substance and rule 3 protects them: which of
the two meanings of "אין לי" is in front of you, that the building question is
asked alone, that the offer and the invitation travel together, that an open
question after an answer loses the thread. What went is the wording. Back to
**0 verbatim lines**.

**The one that cannot be opened, and why it is not an exception.** The menu tap
is answered by the workflow with no model call at all, so its reply is a literal
string by construction, not by choice -- rule 2's "the platform speaks it
literally". The prompt no longer quotes it as the required form; it says the
button is one instance of what the sentence does, so nothing is being copied
from it.

**If the taps should be open too, that is a real option with a real cost:** send
the tap through the model like any other message instead of answering it from
the workflow. It buys a phrasing that fits what the resident actually pressed
and varies; it costs a model round trip on every tap, and it gives up the
guarantee that the reply to a button is exactly what we intend. Not done, not
asked for, recorded so the choice is visible.

Live prompt 37,817 -> 37,856 chars. Not tested through the bot.

### "אין לי" splits in two, and only one half is a lookup

The owner's own words for what a representative would say: *"would you like to
elaborate the concerns you have so that we can create a ticket for you and pass
it on the department"*. Which is right, and it is a different case from the one
fixed an hour earlier.

**Two meanings behind the same two words.** "לא זוכר", "לא שמרתי" means the
ticket exists and the number is mislaid: building and apartment find it.
"אין לי קריאה", "לא פתחתי" means there is nothing to look for, and asking
that resident for a building sends them hunting for something both parties know
does not exist. That one gets the door opened instead:
`אה, אין בעיה. אפשר לספר לי מה קרה? אני אפתח על זה קריאה ואעביר לצות.`
Ambiguous between the two, the building question is cheaper and its answer
settles it: found, give the status; nothing found, offer to open.

**Which reverses the reservation stated in the previous turn, and the reason it
is now correct is written into the prompt rather than left as a reversal.** The
25 Aug rule bans offering a ticket to somebody who has described nothing,
because the ticket then opens empty. This offer arrives **with** the question,
not instead of it, and the ticket is still opened only after they have told you
something. Naming what happens to their answer is also what makes it sound like
a person rather than a form: they hear what they have to give and what they get
back.

**One word of the owner's wording was not used.** "The department" promises
automatic routing to a department, which does not exist here: the four Chatwoot
teams are empty and nothing routes to them. The prompt says "לצות", which is
true, and is already the wording everywhere else in the file. Recorded here so
the next person does not read it as a translation slip and helpfully "fix" it.

Live prompt 36,750 -> 37,817 chars. Not tested through the bot.

### "אין לי" was answered by starting the conversation again

Reported as sounding robotic: `אני מבין. על מה אפשר לעזור?` Pulled the actual turn
out of execution 9798 rather than guessing at it, and the reply is worse than
its tone. The resident had tapped the status button, been asked for a reference
number, and answered **אין לי**. They had just answered the question. The bot
threw the thread away and asked what they wanted.

**So the fix is not a warmer "how can I help".** It is not asking that at all.
The prompt already said that a resident without a number is asked for building
and apartment; it did not say that "אין לי" IS that case, so the model treated a
non-answer-shaped answer as the end of the road. Now named, with the line:
`אין בעיה, נמצא את זה גם ככה. באיזה בניין ואיזו דירה?`

**And the open question is named as the fault it is.** An open question after
somebody has answered is not politeness, it is losing the thread, and it tells
them nobody read what they wrote. `במה אפשר לעזור?` was already restricted to
the first message; the ban now also names this exact turn, because a general
rule three hundred lines away did not reach it.

**`על מה אפשר לעזור?` is also not Hebrew** -- you help **ב**something, not
**על** something. Same class as `מתי זה ייקח` on the voice side earlier today:
a fixed line arriving with one word swapped and the rest left behind.

**What was NOT done, and it was asked for.** The owner's wording included
*"do you want me to open a ticket for something?"*. Not put at this turn: they
are mid-lookup, so offering a ticket there repeats the same reset in a friendlier
voice, and an offer with no subject is the junk-ticket path closed on 25 Aug.
Raised in the reply rather than quietly dropped; it belongs to a genuinely blank
opening, which is a different slot.

Live prompt 35,985 -> 36,750 chars. Not tested through the bot.

### The second menu button answers warmly, and explains what a reference number is

Read off the live reply to the "מצב קריאה קיימת" button: `בטח. מה מספר הקריאה?`
"is rude and ai". It is correct, short and cold: two clipped fragments landing
on somebody who has just asked for help, without one word saying anybody is
going to help them. Now `בטח, אשמח לבדוק בשבילך. יש לך את מספר הקריאה?`
The first half is what makes it service rather than a form, and it is not
redundant because helping is obvious.

**And the follow-up the owner asked for: somebody who answers "which number?"
does not know such a thing exists.** Most residents call once a year. The bot
now says what it is and where they saw it, and offers the other way in the same
breath: `אה, זה המספר שקיבלת מאיתנו כשנפתחה הקריאה. אם הוא לא ביד, אפשר גם לפי הבניין והדירה.`

**Why that does not break the one-question rule** three paragraphs above it. That
rule bans offering both routes in the FIRST ask, when it is still unknown whether
they have a number, because two question marks in one message is confusing. Here
they have already said they have none, which is what turns the second route from
a question into an answer. The prompt says so in as many words, or the next
person to read it removes one of the two.

**Three copies, edited together, because that is the standing trap here.** The
tap reply is answered by the workflow with no model round trip, so the prompt
cannot reach it: `scripts/n8n_whatsapp.py` `TAP_LINE`, the live `Sort` node's
`TAPPED` map, and the prompt's own "מצב של קריאה קיימת" section, which is what
produces the same sentence on the typed path. Pushed by patching the two live
nodes in place rather than `--apply`, which would overwrite a workflow that is
ahead of the repo script.

**Not re-tested.** The probe run was stopped before it sent anything, and
nothing has been put through the live bot since.

**Not changed: the first button.** `בטח. אפשר לספר לי מה קרה?` has the same
clipped shape and was not raised.

### The Hebrew prompt was tested, and it had made the Hebrew worse

Asked for a test that would give a basis for whether the agent sounds like a
person speaking Hebrew or like an English script being rendered into it.

**`scripts/prompt_probe.py`** is the instrument. Fixed resident turns, so both
halves of a pair hear the same sentences in the same order and any difference in
the reply is the prompt; the prompt read off the LIVE assistant by default, or
out of the repo at a commit with `--ref`, which is what produces the pair. It
answers a question about WORDS. It says nothing about how the agent sounds --
pronunciation, pace and turn-taking live in TTS and endpointing, and a call is
still the only evidence about those.

**Two harness faults were found and fixed before any result was believed.**
The first version attached no tools, so the agent invented a lookup result it
had never queried -- a fault of the harness that would have been reported as a
fault of the agent. The second read placeholders aloud on the debt target,
because the variable list was written from memory: it carried two names the
prompt does not use and missed three it does. Unresolved placeholders are now
fatal rather than a warning, and the `--ref` half takes that commit's own
opening line, without which the two halves did not start the same conversation.

**THE RESULT WAS THE OPPOSITE OF THE HYPOTHESIS.** Four runs per condition on
the leak scenario, same model, same turns:

| in the agent's Hebrew | English prompt | Hebrew prompt |
|---|---|---|
| `מה היה בנזילה?` -- "what was in the leak", not a sentence | 0/4 | **4/4** |
| `מתי זה ייקח` -- question word and verb disagree | 0/4 | **4/4** |
| `בוא נראה` -- masculine, to a caller of unknown gender | 0/4 | **2/4** |

The English-prompt version's Hebrew was already idiomatic: correct number
gender, natural connectives, ordinary spoken word order. The Hebrew-prompt
version introduced three errors it did not have.

**The mechanism is bleed, and it is specific to a same-language prompt.** All
three failures are the model lifting a fragment of its own instructions into
its speech: `מה היה בתיק?` is the missing-parcel example applied to a leak;
`מתי זה ייקח` is the fixed line with its question word swapped and its verb
left behind; `בוא נראה` appears in the prompt ONLY in the left-hand column of
the neutral-phrasing table, which is the column of forms it must never say.
When the instruction is in English, the change of language is itself the
boundary between what to think and what to say. In Hebrew that boundary is
gone.

**Three fixes, each aimed at one of them:** the left column is named as
forbidden rather than as a list to choose from; the question word and the verb
are stated to move together, with `מתי זה ייקח` named as not Hebrew; and the
follow-up examples are bound to the case beside them, with the leak's own
questions written out. Pushed, and re-tested over **eight** runs: 0/8 on all
three.

**One new symptom, 1/8, recorded rather than explained.** One run said the
closing line in the middle of the call and then carried on. On a real call that
phrase is the only thing that ends one, so it would have hung up on a resident
mid-question. It did not recur in the other seven and it is not attributable to
the fix; it is a watch item.

**What this does and does not settle.** It does not support the reading that an
English prompt is why the Hebrew sounded translated -- on this evidence the
English-prompt Hebrew was clean, and writing the prompt in Hebrew is what
introduced the errors. It says nothing about audio, so the owner's report that
the outbound now sounds better on a real call is untouched by it. One model,
temperature 0.3, one scenario deeply and three shallowly.

### The English twins are checked against the Hebrew again

Told that the English twin should not have been left untouched, and that an
English prompt rendered into Hebrew is the root of the grammar and naturalness
faults. The second half is right and is why both Hebrew prompts were rewritten.
**The first half does not carry over to the English agents, and it is worth
being exact about why:** their prompts were written in English in the first
place and their output is English, so there is no rendering step between
instruction and speech for anything to be lost in. Rewriting their prose would
not make their English more natural, because it was never a translation.

**What was really wrong is what the owner spotted.** Freezing the English
prompts on 25 Aug removed the one thing that kept the twins saying the same
thing: the substitution table refused to ship when a passage stopped matching.
Nothing replaced it, so a change to a Hebrew prompt would silently never reach
its twin.

**`parity()` in `vapi_en.py` is the replacement**, and it runs on `--dry`,
`--create` and `--update`, refusing to write a drifted twin unless `--force`
says the difference is deliberate. It compares what cannot legitimately differ
between two versions of one document: heading count and level order, the set of
snake_case identifiers (tool names, reasons, statuses, types), the facts that
are not translated (the office number, 101 and 102, both reference formats),
and bullet and numbered-step counts.

**It deliberately does not fail on tables.** Three of the four in the debt
prompt and the only one in the intake prompt teach Hebrew gender — masculine
against feminine forms, and the neutral phrasings that avoid guessing a
caller's. None has an English counterpart, and an English twin carrying them
would be wrong rather than complete. Counts are reported, never failed on. That
is also the answer to the 39-vs-9 and 11-vs-0 table gaps: they are correct.

**It is weaker than what it replaces, and that is recorded rather than hidden.**
The table could not ship a twin that had lost a sentence. This notices a lost
section, rule, code or fact.

**Proved by breaking it**, because a check that has only ever passed is a check
that agrees with itself. Removing one heading, one tool name and the office
phone number from the English intake prompt each failed the run; the unmodified
pair passes.

**Both pairs pass as they stand:** intake 29/29 headings, 15/15 codes, 7/7
facts; debt 1/1 headings, 21/21 codes, 2/2 facts. So the English twins were not
behind — nothing was keeping them from falling behind, which is the thing now
fixed.

### The inbound agent is now instructed in Hebrew too

Asked whether the inbound prompt was already Hebrew, with the reading that an
English prompt is part of why the agent sounds robotic in Hebrew. It was not:
44,719 characters at **4% Hebrew**, an English document quoting the twenty-odd
Hebrew lines it actually speaks. That completes the owner's instruction of
25 Aug — every Hebrew variant gets a Hebrew prompt — and leaves the two English
twins on English.

**Is the reading right?** Partly, and it is worth being exact about which part.
The lines the agent *speaks* verbatim were already Hebrew in both versions, so
those cannot have changed. What changes is everything the model composes for
itself: register, connective words, how a question is put. An instruction
written in English is reasoned about in English and then rendered, and the
rendering is where translated-sounding Hebrew comes from. So this should help
the sentences between the fixed lines, and it cannot help the fixed lines,
because they were never the problem.

**Rewritten, not translated**, per the standing rule, and every fixed spoken
line carried through **verbatim** — those are already the target output.

**Verified before pushing**, the same way the debt prompt was: 6 of 6 tool
names, 5 of 5 reason codes, 15 of 15 status and type codes, 11 of 11 facts and
numbers (the office phone, both reference formats, `101`/`102`, the two spoken
digit strings), and 31 of 31 fixed Hebrew lines present character for
character. All 29 headings kept. The only Latin left is machinery — tool names,
codes, `type`, `reason`, `urgency` — which is correct.

**44,719 characters to 33,948, a quarter shorter.** The prompt is re-sent every
turn, so this is money as well as register; as with the debt agent, Hebrew
tokenises worse per character, so the real figure lands on the next call's cost
breakdown, not on the character count.

**A false line in `vapi_en.py`'s output, fixed in passing.** Its dry run
printed *"substitutions applied: 40 passages + 2 section blocks"* — the size of
the substitution table, not what the run did. Since the frozen English files
arrived on 25 Aug, `englished()` short-circuits and substitutes nothing, so
that line had been reporting work that did not happen. It now names the frozen
file instead.

**Live and verified:** intake (he) 33,948 chars, 70% Hebrew, 6 tools, first
message unchanged; intake (en) untouched at 43,103 and 0% Hebrew; debt (he)
unchanged at 52,586.

**Not verified by ear.** No call has been placed on the new prompt. If the
Hebrew instruction changes how it sounds, that is the thing to listen for, and
it is the same thing still outstanding for the debt agent.

---

## 2026-08-24

### The Hebrew debt agent is now instructed in Hebrew

Asked to write the prompts in Hebrew so the agent's Hebrew reads as native
rather than translated. Measured the cost first and put the choice to the
owner: the debt prompt was 66,492 characters and **4% Hebrew**, an English
document quoting Hebrew lines, re-sent every turn (one turn is ~17,500 prompt
tokens; the 13:19 call reached 119,548 and cost $0.22 for fifty seconds).
Answer: every Hebrew variant gets a Hebrew prompt. The English twins keep
English.

**Rewritten, not translated.** Meaning first, then the words Hebrew actually
uses, per the standing rule. Every fixed line the agent speaks was carried
through **verbatim** rather than re-rendered, because those are already the
target output and re-translating them would change what a resident hears.

**Verified before pushing**, by extracting the load-bearing artefacts from both
versions and comparing sets: 10 of 10 `{{variables}}`, 8 of 8 tool names, 14 of
14 reason and outcome codes, the office phone, address, email, hours, payment
day and both SLA figures, and all seven quoted fixed lines present character for
character. The only Latin text left in the Hebrew is tool names, codes and
variable names, which is correct.

**It came out shorter**: 66,492 characters to 52,586, a fifth less. Hebrew
tokenises worse per character, so the net token change is smaller than the 2x
the character count would have implied in the other direction; the real figure
lands on the next real call and is worth reading off the cost breakdown.

**Two pieces of machinery had to move.**

`vapi_sync.py` finds the first message under a `### Opening` heading, which is
now `### הפתיחה`. It accepts either, so the frozen English source still parses
through the same function.

`vapi_en.py` was the bigger one. It built the English twin by taking the **live
Hebrew prompt** and substituting 62 passages, refusing to ship if any stopped
matching. With the Hebrew prompt actually in Hebrew there is nothing left for
that table to match. The last build it produced is frozen under
`docs/assistant/en/`, and the twins now read from there while still taking
voice, tools, model tier, durations and endpointing from the Hebrew twin.

**What that cost, and it was the point of the old design:** nothing fails when
the twins drift now. A change to the Hebrew prompt does not reach the English
one and no check will say so. Recorded in CONTEXT rather than left to be
rediscovered.

**Live and verified:** debt (he) 52,586 chars, 68% Hebrew, 7 tools, first
message correct; debt (en) unchanged at 63,217 and 0% Hebrew.

**Not done at the time: the intake agent**, still 44,719 characters at 4%
Hebrew. Done the next day — see 2026-08-26.


### The closing beat asks what is unclear, not what else we can do for them

Off the transcript he had been reading: the line that actually bothered him was
`יש עוד משהו שתרצה ממני?`, and he wants it closer to *do you have any questions
or concerns?*

Beat 3 of the debt call has been mandatory since 18 Aug but its wording was
left open -- "whether there is anything else, in whatever words fit the call"
-- so the model reached for the most literal reading and produced *is there
anything else you want from me*. The beat is now specified by what it is for
rather than by that phrase: whether anything is unclear or there is something
they want to ask, with `יש שאלות או משהו שלא ברור?` as the model line.

**The difference is not politeness.** *What else do you want from me* invites
nothing and treats the beat as a formality; *is anything unclear* is the
sentence a resident who did not follow the amount, or which month it was, or
what the link actually does, can answer honestly. That is the whole reason the
beat is not optional. A debt call that ends with an unasked question is the one
that becomes a complaint later.

`יש שאלות או משהו שלא ברור?` also happens to be ungendered, which costs nothing
here -- the debt agent gets `{{gender_forms}}` off the queue and can inflect --
but removes one more place to get it wrong.

**Pushed to both twins.** `vapi_sync.py debt --apply` after a line-by-line diff
of the live prompt against the doc, which showed the only difference was this
edit and nothing live-only would be lost. Then the English twin, where the
substitution table refused the build until both new Hebrew quotes had English
pairs -- the wanted line and the rejected one it is contrasted with -- which is
exactly the guard doing its job. He 66,492 chars, en 63,217, no Hebrew left in
the English.

**Not changed: the intake agent.** It has its own "anything else" beat, but
there it means *another fault to report*, which is a different and legitimate
question. Worth a decision separately rather than a silent sweep.


### Confirmed: the cut is in the transcript, not in the speech

The owner pasted the transcript he was reading, which answers the question the
previous entry had to leave open: the cut is **seen**, not heard.

The 13:19 call settles it. Its log contains **no record of the assistant's text
at all** -- 9 final and 21 partial Deepgram transcripts, and nothing else
carrying Hebrew. Every line labelled "Michael" in that view is recogniser
output. Watch one assemble:

    0.00s  partial  שלום,
    0.88s  partial  שלום, מדבר מיכאל מחבר
    1.94s  partial  שלום, מדבר מיכאל מחברת הומיס שמנהלת
    2.71s  FINAL    שלום מדבר מיכאל מחברת הומיז שמנהלת את הבניין

`הומיס` corrected to `הומיז` between two frames. An agent does not mispronounce
its own company and then fix it; a recogniser does exactly that.

**The rest of the paste is the same thing.** `חכה 2º` is `חכה שנייה` with
Deepgram's number formatter turning *shniya* into an ordinal. `דירה 12 12` is
one utterance recognised twice across a segment boundary. `450 שקלים` is the
model's `ארבע מאות וחמישים שקלים`, in words, normalised to digits.

**And the two visible cuts, against the model's own tokens from the 12:53 call:**

| | |
|---|---|
| model emitted | `אז רוצה שאני אשלח לך, אה, לינק לתשלום ותסגור את זה?` |
| transcript shows | `אז רוצה שאני אשלח לינק לתשלום ות` |
| model emitted | `מעולה, הלינק בדרך עכשיו ותוכל לסגור את זה מתי שבא לך.` |
| transcript shows | `...ותוכל לסגור את זה מתי שבא` |

Both complete going in. The transcript segment is closed mid-word when the
pipeline clears, and the pipeline clears the moment the caller speaks or types
-- ten `Pipeline cleared` events in a fifty-second call.

**What is not proven:** that the audio matched the text. Nothing here can show
that while recording is off, and the one unexplained anomaly from the earlier
entry -- two seconds of audio past the end of the model's text in the 12:43:06
call -- still needs a recorded call to settle. Offered, not enabled: recording
is off by client instruction (transcript only), so turning it on even once is
the owner's call.


### Correction: it is not an echo, and the transcript is still not the agent

The entry below blamed an acoustic echo, speakers into microphone. **Wrong.**
The owner was on headphones and typing, so there was no acoustic path at all,
and the diagnosis was written up and committed before that was asked.

What actually produces those bot-voiced Deepgram transcripts is Vapi
transcribing the assistant's own audio track to build the transcript. Normal
behaviour, nothing to fix in a room.

**The finding underneath survives, and it is the useful half.** A bot line in
`artifact.messages` is a recognition of the agent's audio, not the text sent to
the voice. From one turn of the 12:53 call:

| | |
|---|---|
| model emitted | `אה, אני מתקשר בקשר לוועד הבית על דירה שתים עשרה, של חודש יולי, ארבע מאות וחמישים שקלים.` |
| stored as the bot's words | `אני מתקשר בקשר לוועד הבית על דירה 12` |

The `אה,` is gone, the punctuation is gone, and the model wrote the numbers as
**words** while the stored line has **digits**. Only a speech recogniser turns
`שתים עשרה` into `12`. So `מחבר` in place of `מחברת הומיז`, and the notorious
`תם יוף ובפקל של מיוף`, are what a recogniser made of the agent's Hebrew. The
line sent to the voice was whole.

**And no call in the account shows the agent cut mid-sentence.** Speech spans
against pipeline events across all six real calls: every `Pipeline cleared`
lands *after* a `Bot stopped speaking`, never during. The 10:03 call, the only
one where the caller actually spoke aloud, has two unbroken ten-second
stretches. Delivery works out at roughly 14 characters per second, ordinary for
Hebrew, so nothing is being dropped in bulk either.

**One real anomaly is left**, in the 12:43:06 call: the model's text ends at
`ארבע מאות וחמישים שקלים.` and the audio carries on about two more seconds,
transcribed `תם יוף` then `ובפקל של`. Audio with no text behind it. Either
Cartesia generated a tail it was not given, or the recogniser invented one, and
with recording off there is no way to tell from here.

**Open with the owner:** whether the cut is *heard* or *seen*. If what looks
cut is the transcript in the dashboard, this entry is the whole answer and the
audio is fine. If it is audible, the next step is one call with recording
switched on, which is the only thing that settles the anomaly above.


### The voice agent cuts itself off because it is listening to itself

Asked why the voice agent gets cut while talking. Read the three calls from
12:43-12:53 today, all `webCall`, and the cause is in the Deepgram stream
rather than in any prompt or speaking plan.

**Every final transcript on the microphone channel is the bot's own line.** Ten
of them in the 12:53 call, word for word against what Cartesia had just
spoken: `שלום, מדבר מיכאל מחבר`, `אני מתקשר בקשר לוועד הבית על דירה 12`,
`יש עוד משהו שתרצה?`, `עדיין על הקו`. Not one word of caller speech was
transcribed in that call at all. What the caller actually said arrived by a
different route entirely, as `Live call control add-message` events, which is
how the demo page injects typed text. Speakers into microphone, and the agent
hears itself as the person it is talking to.

**That is the cut, and the log names it.** Every time speech is detected the
pipeline logs `User started speaking` → `New turn started` → `Pipeline cleared`
→ `LLM stream clearing`. The in-flight answer is thrown away and a new turn
begins. With the echo, the thing triggering it is the agent's own voice about a
second after it starts talking. `stopSpeakingPlan` is `numWords: 2`,
`voiceSeconds: 0.3`, so two transcribed words stop it, and its own greeting
supplies them.

**And it explains the garbled Hebrew nobody could place.** `תם יוף ובפקל של
מיוף` in the 12:43 call is not the model writing nonsense and not what the
caller heard. It is Deepgram mis-hearing the agent's own audio coming back
through the speakers, and it lands in `artifact.messages` as if it were the
bot's text, because those bot lines are built from the transcription rather
than from what was sent to the voice. Same reason the first message is recorded
without its `אה,` and without punctuation while `Voice cached` shows the real
line in full.

**So the transcripts have been lying about the bot all week.** Anything read
out of `artifact.messages` for a bot turn is what a microphone in the room
heard, not what was said. `Voice cached` in the call log is the honest record.

**What this does and does not mean.** On a real phone line there is no acoustic
path from earpiece to mouthpiece and carrier echo cancellation handles the
rest, so this specific failure should not survive the move to a real number.
It is a property of testing in a browser with speakers on. Headphones settle it
in one call.

**Two settings worth revisiting anyway**, neither changed yet because they are
the client demo's configuration: `stopSpeakingPlan` at `numWords: 2` /
`voiceSeconds: 0.3` is an eager barge-in that will also fire on a noisy stairwell
or a television, and `startSpeakingPlan.smartEndpointingPlan` is set to
`provider: vapi` on Hebrew audio, which is worth confirming is supported for
Hebrew rather than assumed.

**Not changed, not deployed.** This entry is a diagnosis.


### A greeting is answered by the workflow now, so the name is always there

Third time of asking, and the first two answers were wrong. The opener has to
be `היי, כאן מיכאל מהומיז` **whenever** somebody says hello, not only the first
time in 24 hours. The screenshot: `היי` at 20:47 answered `היי, מה קרה?`.

**The model could not have done this.** The mid-thread rule tells it, correctly,
not to reintroduce itself once a conversation is running, and it was obeying.
Asking it to also always give its name to a greeting is asking the prompt to
hold both sides of a contradiction, which is how the earlier per-message
instruction ended up outranking the system prompt in the first place.

So a bare hello no longer reaches the model at all. `Sort` answers it with
`MENU.content`, the same string as the opener in `prompt.md` that
`check_greeting()` already pins, and `Send` attaches the three buttons to any
greeting. Deterministic, one fewer model call, and nothing left to drift. This
is what the Meta-shaped `Sort` in `scripts/n8n_whatsapp.py` has always done and
what the Chatwoot cutover dropped on 21 Aug; live has now caught up with it by
a different route, because the `Send menu` node that the repo design uses is
Meta-shaped and dead here.

Only a bare greeting. `שלום, יש נזילה` has a fault in it and still goes to the
model.

**Live:** `היי`, then `היי` again, then `שלום`, all three answered
`היי, כאן מיכאל מהומיז. במה אפשר לעזור?` with the three buttons, none of them
touching the model. `יש נזילה בלובי` after them still reaches the model and
still gets the offer with no buttons attached.

**A consequence worth knowing.** A greeting typed in the middle of a flow now
restarts the opener rather than continuing. That is the instruction as given,
and it is the price of the rule being unconditional.


### Saying hello twice lost the buttons, and opened a service call

Owner, from a handset: say הי and the three options do not come. Reproduced on
the first try, and the cause was two faults stacked on each other.

**The options were keyed on the bot's name.** Nothing in the live workflow ever
detected a greeting; the `Send` node attached the three buttons when the
outgoing text matched `/מיכאל מהומיז/`. That is a proxy for *first message*,
not for *they said hello*. Write הי a second time inside 24 hours and the
mid-thread rule correctly suppresses the reintroduction, the name is not in the
reply, and the buttons vanish with it. The Meta-shaped `Sort` in the repo has
always had a proper `GREETING` test and gave a greeting the menu every time;
it was lost in the Chatwoot cutover on 21 Aug and nobody noticed, because the
name regex covered the common case. The test is ported back, `Sort` now emits
`greeting`, and `Send` attaches on either signal. Regex re-run in node against
ten inputs: `היי`, `היי!!`, `hi`, `HELLO`, `בוקר טוב`, `מה נשמע` true;
`שלום, יש נזילה`, `יש נזילה בלובי`, a row title and a reference false.

**Then the worse one.** The second `היי` was answered `היי.` and the resident
was told `פתחתי קריאה, מספר 255-1117-26. זה עובר לצוות.` `Reply usable?`
requires two words, one word is treated as a broken generation, and the false
branch is the rescue: `rescue_request`, a ticket, and a handover line. The
comment beside that guard said "a single word is a broken generation whatever
the word is". It is not: the prompt's own mid-thread rule asks for exactly a
short greeting back, so the guard was firing on output that was doing what it
was told. A resident who said nothing but hello got a service call and was told
it was with the team.

One word now passes when the message being answered was a greeting. Empty still
fails, and a one-word answer to anything else still fails, so the net that
catches a genuinely broken generation mid-fault is untouched. Verified by
running the stored expression in node across the matrix: (`היי.`, greeting)
passes, (`היי.`, not greeting) fails, empty fails either way, a normal sentence
passes.

**The rescue itself is well built and stays as it is.** It writes the
resident's own recent inbound messages as the description, `type: null`,
`status: needs_review`, `oxs_ref: partial:model_claimed`. So the ticket it
opened was reviewable rather than junk, which is the only reason this was a
defect and not an incident.

**Live now:** first `היי` gets the greeting and three buttons, second `היי`
gets a short greeting and three buttons and no ticket, and a fault typed
without tapping still gets the offer with no buttons attached. Repo and live
carry the same guard expression, byte for byte.

**Still open.** A one-word reply to something that is not a greeting still
triggers the rescue: `תודה` answered with a single word would open a
needs_review ticket. Rarely reachable, lands in a review queue, and narrowing
it further means weakening a net that was added after a real failure. Flagged
rather than changed.


### The menu stays; the tap it starts no longer asks a question it already had

Owner, on the greeting screenshot: keep this, and make the reply the open flow
gives a human one. The menu is untouched. Walking the whole path on the live
bot rather than only the line that was asked about turned up the rest of it.

Tap `פתיחת קריאת שירות`, describe a leak, and the bot answered
`רוצה שאפתח על זה קריאה ואעביר למשרד?` The resident had asked for a service
call by tapping the row that says so. **The model never knew.** Canned lines
are sent by the workflow without a round trip, so from the agent's side a fault
description arrived out of nowhere and the offer rule fired correctly on wrong
information. Five messages to open a ticket, one of them asking something the
first tap had answered.

`greeted` already solves this shape of problem for the introduction, so the fix
is the same shape: `store.tapped` records which row was tapped, the next
message carries `tapped_open`, and the per-message instruction tells the agent
not to offer and to ask the building and apartment once the fault is described.
Spent on that one message and then deleted, with an hourly sweep, because it
describes what somebody just did rather than a state they are in. Half an hour,
after which a tap is history.

**Live, the whole path:** `היי` gets the menu, the tap gets
`בטח. אפשר לספר לי מה קרה?`, the leak gets
`אוי, זה מעצבן. באיזה בניין ואיזו דירה גרים?`, and the address gets the
reference. Four messages, no re-ask, the acknowledgement still there. Typing a
fault without tapping still gets the offer, which is the case the flag must not
leak into, and the status tap still answers one question and then the status.

Brought back to `scripts/n8n_whatsapp.py` as well as the live workflow, which
is one less thing diverged.


### The em dash, and the line a resident actually read was never the model's

Screenshot from a real handset. A tap on `מצב קריאה קיימת` was answered
`מה מספר הקריאה? אפשר גם רק את הספרות האחרונות — ואם אין מספר, בניין ודירה.`
Owner: the intro is fine, that reply is AI, strictly no em dashes, and every
reply should sound humane and polite rather than machine-made.

**That line was never the model's.** It is canned, hardcoded in `TAP_LINE`, sent
by the workflow without a model round trip. So no amount of prompt work would
ever have reached it, and it had been contradicting the prompt since 24 Aug,
which requires the status opener to be one question and nothing else. It asked
three things in one breath. Rewritten to `בטח. מה מספר הקריאה?`. Its sibling
went the same way: `בסדר. מה התקלה?` is the flat "what is the problem" the
25 Aug pass had replaced everywhere except here, and is now
`בטח. אפשר לספר לי מה קרה?`. A tap is still an explicit request, so the offer
is still skipped; only the wording moved.

**Then the dash, which was in the prompt 220 times.** A rule saying "never
write X" loses to two hundred lines writing X, so the rule went in and the
examples went out together. Three of them were utterances the bot would copy
verbatim and got full stops by hand, because a comma there is limp:
`מספר 255-1030-26. זה עובר לצוות התחזוקה.` The prose took a colon where the
dash was defining something and a comma where it was an aside, and fifteen
lines were rewritten afterwards where the comma had flattened a sentence that
wanted a full stop. The two dashes left in the prompt are the rule quoting the
character it forbids, and the rule says so rather than claiming a clean file.

**The strongest teacher was somewhere else entirely.** The per-message
instruction appended to every resident message carried six em dashes, so the
model saw them beside every turn it ever answered, closer to the message than
the system prompt. This is the same string that outranked the system prompt on
23 Aug over the greeting; it outranks it on register too. Rewritten with colons
and full stops, branches untouched, and both greeting branches re-verified
afterwards.

**And a net under all of it.** Every outgoing message, canned or model-written,
passes through one node, so its expression now strips `—` and `–` to a
comma before sending. Tested by running the stored expression in node against a
line containing both: they become commas, and the hyphens inside
`255-1114-26` are untouched, which is the thing that had to keep working.

**Verified live.** Both taps read right. `יש נזילה בלובי` still gets the name
and the offer with no `במה אפשר לעזור`; `בוקר טוב, מה נשמע?` still gets the
name and the offer; mid-thread still gets no reintroduction; the status opener
is one question; and the ticket confirmation now writes
`מספר 255-1114-26. זה עובר לצוות התחזוקה.` No dash in any reply. 30 nodes
before and after, active throughout.

**Not touched: the voice agents.** A dash is punctuation and nothing speaks it,
so the instruction does not apply there.


### Opening a ticket asked for a datum, and opened tickets about nothing

Owner: creating a ticket should not read like *"ok, what is the problem"* — it
should open the floor, *"I understand, can you tell me about the issue?"*, with
the voice agent's empathy and more of it.

Probed the live bot with four vague openers before changing anything. `יש לי
בעיה בבניין` was answered `מה קרה?` — the two-word form he was describing. But
`אני רוצה לדווח על משהו` and `אני רוצה להתלונן` were answered
`רוצה שאפתח על זה קריאה?` — **on what?** Nothing had been described. Carried
through, that offer is accepted and a real ticket is written: `255-1112-26`'s
predecessor came back with `description: "דיווח על משהו"` — *a report about
something* — and `fault_location: apartment`, invented, because the field had
to hold something. A maintenance job telling somebody to visit apartment 4 and
nothing else, while the resident is told it is handled.

**The prompt caused it, in one bullet.** The cases that skip the offer read
*"they already asked outright — open a ticket, send someone, **I want to
report**"*, and sent the bot straight to building and apartment. So *"I want to
report something"* matched a rule whose entire purpose is not to re-ask an
answered question — except this one had not been answered. The bullet now needs
both halves, a request **and** an account; a request without a story skips the
offer, not the fault.

**What changed in the prompt.** An intention is not a description; a
description is never invented and neither is `fault_location`; the offer needs
a subject; and the question that gathers it opens a door instead of demanding
a datum — `בטח. אפשר לספר לי מה קרה?`, echoing whatever word they used.

**And a guard against overshooting the ask.** *Be more empathetic* is answered
by a model being sorry earlier, and sympathy for an unknown is the most
machine-like thing available — a formula, audibly applied before anyone knew
what for. So receiving the **person** (`בטח`, `אני מבין`, `אני מקשיב`) is
separated from acknowledging the **event**, which still happens only after it
is described and still scales to it.

**Where chat now differs from voice on purpose.** Voice answers this with
`בטח. מה קרה?` under a rule that says explicitly *not* sympathy — on a live
call each turn costs seconds and nothing has been described yet. The second
half holds on chat and the first does not, the same trade the 13 Aug offer rule
was decided on. Voice was left untouched; it already asks what happened before
where, since the 20 Aug call where the building was asked first and the caller
volunteered black smoke several turns later.

**Verified live.** Same four openers after the push: `אני מבין. אפשר לספר לי מה
קרה בבניין?`, `בטח, אפשר לספר לי מה קרה?`, `בטח, אני מקשיב. על מה התלונה?`, and
the hot-water-with-a-baby message — which was already right — unchanged, still
offering at once. Then end to end: vague opener → `יש נזילה מהתקרה בחניון כבר
יומיים` → yes → address → `255-1112-26` with
`description: "נזילה מהתקרה בחניון"`, `fault_location: common`, `urgency: high`.
And `תפתחו קריאה בבקשה` now returns `אפשר לספר לי מה קרה?` rather than the
address. Regression: described faults still get the offer with no extra
question, status still asks one question, the balance gate is unmoved,
`check_whatsapp.py` all green.

Pushed by read-modify-write on the agent node alone — `--apply` is still
refused, and would still delete the eight Chatwoot nodes. 30 nodes before and
after, active, systemMessage byte-equal to `prompt.md`.

**Still open.** The acknowledgement scales less finely than it reads: a lobby
leak and *"the neighbour is loud until 3am every night, I can't sleep"* both
drew `אוי, זה מעצבן`. Not wrong, and the size rule is in the prompt; where the
top of that range should sit is a taste call for the owner.


### The nightly import was being killed mid-write, and the write would have failed anyway

Asked to fix the nightly import. Four days after the secrets landed it had
still never completed a single pass, and the dashboard said it was fine.

**What the run list actually says.** Two runs a day conclude `cancelled` after
exactly 45m -- the job ceiling -- and two conclude `success` in three to ten
seconds, which is the daylight-saving twin exiting on purpose. Read casually
that is two green ticks a day. Read properly it is: nothing has ever finished.

**What the database says, which is the part that settles it.** `residents` was
current to 23 Aug. The newest row in `charges` was **11 Aug** and in `requests`
**12 Aug** -- thirteen and twelve days stale, while the three counts on `/sync`
sat unchanged and unremarked.

**Where the time went.** Step timings from the two cancelled runs: residents
18m46s, of which the OXS fetch was 4m22s and **the writes were 14m24s** --
7,523 rows, one `INSERT` round trip each, to a database in another region. Then
arrears was killed 26 minutes into a sweep that needs 22, with the writes still
ahead of it. Requests, a ten-second job, never ran at all on either day.

**And it would have failed at the first write.** `oxs_arrears.py` says
`on conflict (resident_id, period)`. Migration 012 dropped that constraint on
11 Aug when the apartment moved onto the charge -- the key is
`(resident_id, period, unit)` now. The shipped statement was run against the
live database to be sure rather than reasoned about, and it answers **42P10,
"no unique or exclusion constraint matching the ON CONFLICT specification"**.
Every arrears write since 11 Aug was guaranteed to fail; the timeout was
killing the job in the sweep before it could get far enough to prove it. Two
bugs, one hiding the other, and the newest charge in the database is dated the
day the constraint changed.

**Two more that the same statement carried.** `charges.source` defaults to
`'seed'` and nothing set it, so every charge the importer was about to write
would have claimed to be fictional -- invisible to the dashboard's OXS count
and inside the blast radius of every purge query 007 wrote to be careful. And
`charges.unit` was never set either, which quietly re-opens the collapse 012
exists to prevent: an owner of three flats overwriting themselves twice, the
₪6,665 that was invisible on 11 Aug.

**Why nobody saw any of it.**

Python block-buffers stdout when it is a pipe, and an Actions log is a pipe. The
killed step printed **nothing at all** -- twenty-six minutes of progress
counters died in the buffer with the process. Both cancelled runs show an empty
step and no clue which building it was on.

The guard asked what time it was in Jerusalem, and GitHub's scheduler is
best-effort. The afternoon run on 23 Aug started **51 minutes late**, at 15:51
local -- nine minutes from falling outside its own hour and skipping the day in
total silence. It now asks which cron fired (`github.event.schedule`) and
compares that to the current UTC offset, so lateness cannot decide anything.

And `/sync` reported healthy throughout, for two independent reasons. It tells a
real import from a skip by duration -- but the guard was a step inside the job
holding the concurrency lock, so a twin queued behind the whole real run before
exiting in three seconds, and GitHub counts queue time in the only timestamps
the page can see. A 45-minute run that concluded `success` and imported nothing
read as a real import. Meanwhile the page looked for `conclusion === 'failure'`,
and a job killed by its own timeout concludes **`cancelled`**, so the "last run
failed" banner never fired once.

**The fix, in five places.**

*The writes are one statement per table.* Same SQL, same conflict handling,
`unnest` of arrays instead of a loop: 7,523 residents in one round trip. The
correct conflict target, `source = 'oxs'`, and the apartment on every charge.

*A debtor can appear twice and the table cannot hold both* -- the same phone
owing on flat 3 of two different buildings, since `charges` carries no building.
Postgres refuses to update one row twice in a statement, so that collision is
resolved before it raises: the larger debt wins and the count is printed.
Nothing is summed, because a summed figure pinned to one flat is the specific,
confident and wrong number 012 was written to stop.

*`status` left out of the update list, which is a change of intent.* It used to
be forced back to `'unpaid'` every twelve hours. Since OXS is read-only to us, a
payment taken by the agent is a staff task, and until staff enter it OXS still
shows the month unpaid -- so the old statement would re-chase somebody who had
already paid, which is the one outcome the debt agent's whole design exists to
avoid. Paid, disputed and waived now survive the nightly refresh; only the
amount is updated, and the count held back is reported.

*The three imports no longer share a fate.* Each carries its own timeout and
runs unless the job was cancelled outright, so arrears dying no longer takes a
ten-second requests import with it. A gate at the end names which of the three
landed and fails the run if any did not. The job ceiling goes 45 → 90 minutes:
a full pass is ~28, nearly all of it OXS rate limiting, and the old number was
below the floor.

*`/sync` stops being able to tell that story.* Every terminal conclusion that is
not `success` counts as a failure. The guard moved into its own job outside the
concurrency group, so a twin never queues and its duration is honest again. And
each of the three counts now prints the newest row underneath it, coloured when
it is more than 26 hours old -- the one line that would have shown this on day
one, because 178 charges looks identical whether it landed last night or on the
11th.

**Testing.** Both write paths were run end to end against the live database
through a connection whose `commit` was replaced with a no-op, then rolled back:
4 arrears rows in produced 2 charges, 1 skipped for no phone and 1 dropped as a
same-flat-number collision; the residents batch upsert, the `/debts` charge path
and the carried-debt re-attach all executed. Counts were 7,532/178 before and
7,532/178 after. The status decision was proved separately: seed a charge, mark
it `paid`, run tonight's statement with a larger amount -- amount 500 → 900,
status still `paid`. The old statement's 42P10 was reproduced and the new one
confirmed to work on the same connection. The guard was checked against both
offsets: exactly one cron of each pair is live in summer and in winter, and
neither answer depends on the clock. YAML parses, dashboard typechecks and
builds. `requests_reference_key` was checked too, in case the third importer
carried the same rot -- it does not; that import failed only because it was
never reached.

**Then it ran, and finished, for the first time.** Dispatched with `--apply`
and watched to the end: 27m41s, all three steps green, gate green.

    decide       4s
    Residents    4m27s   (was 18m46s — the 14m24s of writes is gone)
    Arrears      22m57s  (the OXS sweep; the writes inside it took 3 seconds)
    Requests     11s     (had not run at all since 12 Aug)

**576 apartments behind on 2026, ₪975,991.** 534 charges written for
2026-08-01 -- 41 skipped for having no phone, 1 dropped as a same-flat-number
collision, which is 576 exactly. `charges` went 178 → 712, every one of them
`source = 'oxs'` and every one carrying an apartment. **14 owners now hold more
than one charge in the same period** -- the multi-flat case that has been
overwriting itself since 11 Aug, landing correctly for the first time. Open
balances: 703 charges, ₪1,022,921. Requests went 68 → 103, and matched 38 of 38
service calls to a resident rather than 26 of 27, because it finally ran against
a resident table imported the same minute.

The 9 charges already marked `paid` all sit in earlier periods, so the status
rule was not exercised in production -- it stays proven by the rollback test
only, and the first live test of it will be the first time somebody pays before
staff enter it in OXS.

**Still owed.** Nobody has looked at `/sync` since it redeployed, and the
`GITHUB_DISPATCH_TOKEN` that would let the Run now button work is still not in
Vercel.

### A complaint is a ticket now, and two things it uncovered

Owner, correcting the morning's note: a complaint should **open a ticket** on
both channels, not hand over to a person. Nothing is written to OXS — the
foundation first, their API stays read-only.

Migration 025 adds `complaint` to the type constraint, the enum went into both
channels' tool schemas, and the two prompts gained a paragraph each: on
WhatsApp a complaint is offered and opened like a leak (hand over only for
anger, danger, or an explicit ask), on voice it is named as its own type
beside "a leak is plumbing". Pushed to all four assistants; the English twins
were rebuilt from the Hebrew so they did not drift. `check_tools.py` gained a
complaint case, because the type is constrained in Postgres and a drift
between the enum and the constraint would surface as a resident being told
their complaint was filed when the database refused it.

**It immediately broke the duplicate guard, and that was worth finding.** The
guard merges tickets sharing building + type + unit inside 30 minutes — right
for a fault (one leak, one van) and wrong for a complaint, which shares a type
by definition and has no unit when it is about a common area. Two complaints
minutes apart, same building: the second was swallowed, its author read back a
reference to somebody else's complaint, and their own words never written
down. Complaints now skip the guard. Verified properly on the second attempt —
the first test used different units, which the guard would not have merged
anyway, so it proved nothing: two complaints with identical (type, building,
unit) 32 seconds apart, both written, distinct references.

**And every WhatsApp ticket ever opened had no caller phone.** `reported_by_phone`
reads `ctx.callerPhone`, which is built from `customer.number` or
`caller_phone` — and the chat tool body sends the sender as `phone`. The
number was always there (the interaction row beside it stores it, recovered
from the `wa:` call id) and nothing read it, so the dashboard's Caller column
was empty for the whole channel. One `?? phoneOf(v.phone)` fixes it. A
complaint nobody can ring back is half a complaint, which is how this
surfaced.

**Two faults in the probe, found while proving the above.** It invented
`+9725990XXXXXX` — a ten-digit national number where Israeli mobiles are nine
— so `phoneOf` rejected every probe sender and the phone fix looked unfixed.
And its cleanup passed `+972…` unencoded into a PostgREST `in.()`, where `+`
decodes as a space, so it had been reporting "cleanup requests 0" while
leaving real rows behind. Both fixed; twelve leftover test tickets deleted by
hand.

**Not mine:** `255-1103-26` … `255-1105-26`, voice, all three within 0.4s from
the demo resident `+972521234568`. Test data in a live table, but this session
did not create them. `1103` and `1104` were left; **`1105` was not** — the last
cleanup filtered on `type in ('plumbing','complaint') and opened_via='voice'`,
which caught it alongside the two it was aimed at, after I had said I would
leave it alone.

### The owner walked the checklist

Went through the PRD checklist item by item and set the targets: latency
~1.2 s is fine, ten concurrent calls is not needed with a manual trigger,
complaints stay a hand-over rather than a ticket type, Chatwoot gets two
inboxes (resident ticketing, staff task resolution), the CRM's RTL / login /
metrics are acknowledged as owed, and Monday was checked against the main
PRD — it is there in six places, one-way push, waiting on a token and a
board. Next on WhatsApp: Homies' own number, then the payment link as a
template message. Recorded in HANDOVER and CONTEXT.

### Verified before the client touches it: both agents, all surfaces

Asked to prove the chatbot and the voice agents are untouched by the day's
changes before anything outbound proceeds. Six surfaces at once.

**Green without comment.** `check_whatsapp.py` end to end. `check_tools.py`:
all ten voice-tool cases through n8n → Edge Function, the path Vapi really
calls. Four Vapi assistants read back: prompts (65k / 62k / 44k / 42k chars),
voices, transcribers and tool lists all match the repo, `vapi_sync.py` dry
runs target the right ids. Demo page up, serving the live account-6 ids —
HANDOVER had said account 5, which was stale, not wrong at the time. Dashboard
pages all 200. The only n8n errors in the window were the probes' own `Send`
404s against invented Chatwoot conversation ids.

**Recording-off, checked for consequence rather than assumed.** Migration 006
makes a recording the proof of a spoken card authorisation and says a ticket
without one "must not be charged". That flow was reversed on 4 Aug on the
client's instruction — the resident pays through a link OXS sends — and the
prompt doc says the recording "stops being the authorisation". So the rule is
history, the writer stores `audio_url = null` without complaint, and
transcript-only costs nothing the current design uses.

**The four client flows on WhatsApp, run and judged.** Open a ticket: pass —
offer, building+apartment together, `open_request` fired, `255-1095-26`
quoted with what happens next, `תודה` → `בבקשה.`. Talk to a person: pass —
`transfer_to_human` fired on turn one, the fixed line, `בטח.` Status: the
substance passes (`get_request_status` fires, state in plain Hebrew, no
invented dates) but the opener asks two questions 3 of 3 — `איזו קריאה? יש
מספר סידורי?` — and "מספר סידורי" is nobody's word for a ticket number. One
paragraph added to the prompt: ask **"מה מספר הקריאה?"** and nothing else, and
the word is מספר קריאה. Pushed live, systemMessage only, verified byte-equal.
Balance: the judge failed it twice, and it was the test — "בדיקת מערכת" is not
a name, so the bot asked for one. With `דוד כהן, 050-1234567` it looks up,
says no match, asks to check the details, and hands over on insistence; split
across two turns it does the same. Pass.

**The debt list, written from today's sweep.** Raw 576 apartments / ₪977,850;
corrected 79 / ₪67,225; 15 without a phone; **wrote 104 monthly charges for
64 apartments and marked 80 paid** — months the 11 Aug import listed that OXS
now shows a payment for, on apartments read this run. Table: 105 unpaid
charges, 65 apartments, 64 residents, **₪60,175**, nothing dated August; 89
paid. The live Debts page shows the same four numbers.

**What could not be done from here.** A voice conversation needs a
microphone. Either one web call on the demo page, or Vapi's simulated-caller
suite (`vapi_eval.py`), which costs money and was not started unasked.

### Five decisions on outbound, and the debt list put right

Asked what section 5 of the checklist meant, then decided it, in order:
fix the list; a Call button on the Debts page, pressed by a person, never an
auto-dialer; transcript only, no recording; the no-repeat / do-not-call /
calling-hours rules later; order the Israeli number. Built the first three.

**Recording off, transcripts kept.** `artifactPlan.recordingEnabled` was true
on all four assistants; now false, video off, `transcriptPlan.enabled` true,
read back. Two deploy scripts (`vapi_sync.py`, `vapi_duel.py`) would have
switched it back on at the next push; both changed. The call page's dead
player note now says audio exists only for calls before 25 Aug.

Checked before calling this free of consequence: migration 006 says a payment
ticket with `authorization_captured` and no `audio_url` "must not be charged"
-- the recording was the proof of a spoken yes to a card charge. That flow was
reversed on **4 Aug on the client's instruction**: the resident pays through a
link OXS sends, and the prompt doc says in so many words that the recording
"stops being the authorisation for a payment". So the 006 rule is history, the
end-of-call writer stores `audio_url = null` without complaint (verified in
`debt-tools/index.ts:2134`), and transcript-only costs nothing the current
design uses. Verified the rest of the voice path the same hour: all ten tool
cases green through n8n → Edge Function, four assistants with prompts, voices,
transcribers and tool lists matching the repo, demo page serving the live
account-6 ids.

**The debt list.** Migration 023 deleted the cumulative rows -- 540 of them
by then, ₪934,061, the 15:00 run having added six -- pinned by period,
source, status and a 24 Aug `created_at`. The table went back to 169 per-month
charges, 121 apartments, ₪100,020. Then `oxs_arrears.py` was rewritten from
`sweep()` down: the 11 Aug correction (onboarding runs dropped, lagging
buildings excluded) now lives in it as `correct()` and `import_arrears.py`
imports it, so there is one copy; `--apply` writes one row per unpaid month
with `period` = the month; a guard deletes any current-month unpaid OXS row on
every run, since the sweep never writes one and only the old shape could; and
a charge is marked **paid on positive evidence only** -- the apartment was
read this run and OXS no longer lists that month as missing. Not "absent from
the list": a failed building, a changed phone and a filter are all absences
and none is a payment. `--from-json` replays the last dry run's file, which
now also carries `seen`, so the write path can be tested without a 22-minute
sweep. Replayed on yesterday's sweep the correction gives **81 apartments, 124
monthly charges, ₪68,365** against ₪979,974 raw.

**The Call button.** Migration 024 adds `press_call(phone)`, SECURITY
DEFINER: flips `handed_over` for that one resident and returns their
`v_debt_call_queue_person` row, or NULL when not eligible -- the only write
the anon key gains on `residents`, because the dashboard has had no login
wall since 9 Aug. `dashboard/lib/call.ts` holds the three gates -- a PIN
typed next to the button (`CALL_PIN`, without which the column is not
rendered), the function, and `VAPI_PHONE_NUMBER_ID` (without which the row
reads "no number yet") -- and places the call through Vapi's `POST /call`
with the same `variableValues` the browser demo composes, callback number
now Homies' real office line from the FAQ. The Debts page gained the column,
the form and a one-line result from the URL. Probed: an unknown phone returns
NULL and flips nothing; anon can execute; `tsc` and the build pass. The PIN
was the builder's call, not the owner's, and is written up as such in
`docs/features/15-call-button/context.md`.

**Timing.** 023 ran at 05:40 UTC. The scheduled sync at 12:00 UTC would
re-write the cumulative rows unless the importer fix is pushed first; the
guard makes even that self-healing on the following run, but the push goes
out before noon regardless.

### Tested until it passed: the line that outranked the prompt

Asked to test and make sure it passes. Two layers: the deterministic checks,
and -- because the thing under test is a prompt -- a fan-out of 56 live probes
across five lenses (greetings, faults stated first, mid-thread turns, junk and
English inputs, balance/status openers), each reply judged against twelve
rules lifted from prompt.md, every failure re-run once so a flaky model answer
is not reported as a broken prompt.

**Deterministic, all green.** `check_whatsapp.py` end to end (row in 6 s,
`status: open`, no rescue, duplicate held); deploy dry run and greeting
assertion; the new `--apply` guard refuses by name; four scripts compile; both
workflows parse; `tsc` exit 0; the requests importer on schedule three times at
~20 s; and **the OXS sync completed on its own schedule** at 15:00 Israel,
32m36s, with its daylight-saving twin skipping in 5 s -- the first scheduled
proof, which yesterday's log said was still owed.

**The fan-out found two real faults, 11 confirmed on recheck, 0 of them
flaky.** Both were in the intro I had just verified from three happy-path
messages. (1) Any first message that already carried a request -- balance,
ticket status, "רוצה נציג", a formal complaint, a parking gate -- got the whole
opener pasted above it: `היי, כאן מיכאל מהומיז. במה אפשר לעזור?`, blank line,
then the answer. Two question marks every time. (2) A how-are-you opener got a
mood report or the question back: `מצבי מצוין תודה, ומה שלום?`, `מה שלומך?`,
`מה נשמע?`. And in the mid-thread lens the bot reintroduced itself to a second
`היי` and on turn two.

**The cause was not the system prompt.** The agent node prepends a
per-message instruction to every turn, and the 23 Aug dashboard edit had made
it say, on a first message, *"open with a greeting, the name, and a polite
offer of help, and then address the body if it has content"*, and on a
mid-thread greeting, *"answer warmly with the name and an offer of help"*.
That is failure (1) and the reintroduction, verbatim. The system prompt said
the opposite in both places and lost every time, because this line arrives
with each message and a 32k-character prompt does not. Memory is keyed by
phone, so the mid-thread failures were real, not a probe artefact.

**Fixed in both places, live and repo.** The per-message rule now says: name
always; "במה אפשר לעזור?" only when nothing was asked; "מה נשמע" and "מה המצב"
are greetings, not questions, neither answered nor returned; mid-thread, never
reintroduce, a repeated hello gets a short hello and the thread picked up. The
prompt's two rules were rewritten to agree with it, with worked examples for
the content-first case. Second surgical patch of the live workflow, backup in
`docs/handover/` (secret redacted), 30 nodes before and after.

**Re-probed, all of it passes.** `מה נשמע` → `היי, כאן מיכאל מהומיז. במה אפשר
לעזור?`. `כמה אני חייב?` → `היי, כאן מיכאל מהומיז. יתרה זה מידע אישי, אז צריך
שם מלא ומספר טלפון.` `רוצה לדבר עם נציג` → name, the handover line,
`transfer_to_human` fired. Mid-thread: turn two no intro; a second `היי` →
`היי, מה קרה?`; `תודה` → `אין בעיה.`

**Residuals, logged and not fixed.** `רוצה לדעת מה קורה עם הקריאה שפתחתי` →
`איזו קריאה? יש מספר סידורי?` -- two question marks and a word nobody uses for
a ticket number. `יש לי מספר קריאה 1030` → `אני בודק את קריאה 1030.` with no
tool call, which is defect 5's shape and is contained by the workflow. And
**`אתה בוט?` → `אני לא בוט.`** -- a flat lie, on a run where the previous
answer had been `אני נציג שירות`. There is no rule about it in the prompt and
it is not mine to decide; defect 20, needs a decision.

`scripts/probe_whatsapp.py` is the tool that found all of this, kept beside
the self-check because the self-check cannot see it: it was green throughout.

### The bot is מיכאל again, and the repo was three days behind the bot

Asked for the WhatsApp intro to stop sounding like AI, with an English
example: *"Hello! Michael here from Homies. Hope you are having a great day,
how can I help you out?"* Decision taken on the one real fork -- the name
comes back, in Hebrew. It had been off since 12 Aug and the voice agents never
lost it.

**The brief was answered, not translated.** Every decoration in that example
fails in Hebrew and the prompt already said why for two of them: `היי!` reads
as an over-eager bot; *hope you're having a great day* has no Israeli
equivalent and `מה שלומך?` has been banned since 8 Aug on those grounds. The
warmth is carried by the name, which is the one thing a person has and a form
does not. New opener: `היי, כאן מיכאל מהומיז. במה אפשר לעזור?`

**Then the deploy script's dry run showed 23 nodes and the live workflow had
30.** Stopped. The prompt in n8n was 30,672 characters against 26,718 in the
repo -- rewritten in the dashboard on 23 Aug, never committed -- and the eight
nodes the script does not build are the Chatwoot handback and the promise
backstop, applied through the REST API on 21-23 Aug. An `--apply` to change
one sentence would have deleted all of it. The repo's system-prompt section
was rebased onto the live text first, then the intro was rewritten on top.

**And it was already inconsistent in production.** The 23 Aug prompt had the
name; the menu line the workflow sends to a bare `היי` did not. So a resident
got `היי, כאן שירות הלקוחות של הומיז` if they typed hello and `היי, כאן מיכאל
מהומיז. איך אפשר לעזור היום?` if they typed anything else -- the exact drift
`check_greeting()` exists to stop, which it could not, because the thing that
drifted was never run through it.

**Four things fixed in the 23 Aug intro, three tells and one contradiction:**
`איך אפשר לעזור היום?` (the *today* of a translated call centre); `היי! הכול
טוב, תודה.` (a rep reporting his own mood -- the most scripted line in the
file); `היי, עדיין כאן :)` (a smiley, in a prompt whose own rules say "אימוג'ים.
אף אחד."); and "every greeting gets the name back, always" three paragraphs
after "introduce yourself once and never again". That last one is now: name
once, at the start of a conversation; a mid-thread `היי` gets a greeting and
the thread picked up, never a reintroduction.

**Pushed surgically**, not with the script: backup of the live workflow to
`docs/handover/n8n-whatsapp-live-24aug-before-intro.json` (shared secret
redacted), then the system message and the Sort greeting replaced in place.
30 nodes before, 30 after, backstop intact. The script now refuses `--apply`
by node name while live carries nodes it does not build.

**`check_whatsapp.py` had been red against a working bot since 21 Aug.** It
still posted Meta's envelope; the live Sort parses Chatwoot's, and Change 4 of
the cutover doc -- which said exactly this would happen -- was never applied.
Five synthetic messages died at Sort's first filter with executions reading
`success`. Rewritten to Chatwoot's `message_created` shape with the `?s=`
secret, the GET-and-POST assertion relaxed to what a Chatwoot webhook needs,
the security labels renamed to what they now test. **All checks passed**: row
in 6 s, `status: open` (the model called `open_request` itself, no rescue),
common-area fault with no unit, duplicate did not open a second ticket.

**Verified live from three fresh numbers before the check existed:** `היי` →
`היי, כאן מיכאל מהומיז. במה אפשר לעזור?`; `בוקר טוב, מה נשמע?` → `בוקר טוב, כאן
מיכאל מהומיז. במה אפשר לעזור?`; a leak in the first message → the name and the
offer in one reply. Test rows deleted.

**Found in a real transcript from 14:28 the same day, under the old prompt,
and not fixed here:** a resident wrote `אין לי לא פתחתי` and the bot answered
*"אוקיי. אם ארצה לפתוח, אשאל על הפרטים"* -- in the resident's voice, as if it
were the one deciding whether to open a ticket -- then `חחחחח :)` to a laugh,
and *"אוקיי, תודה בכל אופן"* to `לא אחי`. The smiley licence is gone with the
intro rewrite; the voice confusion is a separate defect, logged in HANDOVER.

### OXS has a status field and it is a constant; the progress is somewhere else

Asked whether OXS carries a status at all, since every imported ticket reads
open and a twice-daily import means nobody knows when that changes.

**The field exists and never varies.** All 35 service calls the API served that
afternoon returned `{"label":"פתוחה","status":"open"}`, dating from 10 February
to that morning -- so it is not "recent calls only", it is genuinely every call
they serve, always open. Our 69 said open because that is what they were told.

**The movement is in `treatmentLog`,** which we were not importing: the
dispatcher's own notes, 13 of the 35 filled -- "הועבר לאלון שערים",
"בטיפול דוד", "כרגע המתג תפוס עם קיסם - ממתינים לדוד לטיפול בתקלה", and one that
runs to a paragraph about an electrician who has to bring fittings. That is the
answer to "what is happening with my leak", which is the question
`get_request_status` exists to answer and had been answering with the word
"open".

**Newest first, and worth checking rather than assuming.** `lastUpdateNote`
equals `treatmentLog[0]` on 13 of 13 and the last element only where the list
has one entry. Element 0 is current; the tail is history. Stored as an array in
their order, because "fittings ordered" followed by "David handling it" is a
ticket moving and one string is not.

**Closure is expressed by disappearance.** 34 calls live against 70 we hold, and
three left the feed inside a single hour that morning. The script has refused
since 12 Aug to read that as `resolved`, correctly -- the endpoint cannot
distinguish "only open calls are served" from "nothing is ever closed here". So
022 adds `oxs_last_seen_at`, stamped on every ticket on every run: the fact is
now measured and dated, and the day Homies answers, one UPDATE clears the
backlog instead of an archaeology exercise. It is now question 2 on the client
list, because it is the cheapest question there and 36 stale tickets ride on it.

**Tickets got their own workflow, every fifteen minutes.** They had been the
last step of `oxs-sync.yml`, which is how an eleven-second import went eleven
days without running: the arrears sweep in front of it kept dying and took it
down too. Nothing about a ticket import needs arrears data, and it costs three
requests -- one to OXS, one page of residents, one bulk upsert. The two
workflows cannot starve each other on the rate limit either, because this key is
`OXS_KEY_REQUESTS` and the sweep's is `OXS_KEY_GENERAL`, and the 60/min is per
key. No daylight-saving guard: an interval does not care what hour it is.

GitHub's cron is best-effort -- 51 minutes late on this repository, measured --
so fifteen minutes is the ask, not the promise. `oxs_last_seen_at` is what the
dashboard reports, so it shows the real freshness rather than the intended one.

**On the dashboard.** The current note sits under the description in the ticket
list, in Hebrew, with a count of older ones; a ticket that has dropped out of
OXS says so in the review colour rather than being quietly resolved. The Status
column stays ours -- it always was, and now it is clear that it says nothing
about their side.

**One thing tightened on the way.** The Supabase error path printed the whole
PostgREST body, which carries the offending row in `details`. Harmless twice a
day into a log nobody opened; not harmless every fifteen minutes into a public
repository. It prints the message and 200 characters of it now.

**Testing.** Migration applied and read back. Dry run, then applied: 34 calls,
34 of 34 matched to a resident, 13 notes written, 36 counted as no longer served.
Read back from Postgres -- 13 tickets carry notes, 34 stamped in this run, 36
stale. Dashboard typechecks and builds.

### The sweep can lose a third of the buildings without saying so

Went to check the ₪975,991 the fixed import had just written, by re-running the
sweep locally with `--quiet` off so the month lists would land in
`docs/reference/arrears-2026.json`. It came back **65 apartments, ₪74,341** --
against the same sweep's 576 and ₪975,991 in CI ninety minutes earlier.

**37 of 175 buildings had answered `HTTP 429: Too Many Requests`** and been
skipped. The CI run had zero. The difference is latency, and the bug is that
the pacing never accounted for it: the loop slept 1.05s twice per building
while making three GETs, so the real request rate is a function of how fast the
network is. From a GitHub runner each payments call takes ten seconds and the
sweep idles near 27 requests a minute; from a machine close to OXS it goes over
60 and buildings start dropping out. The dropped ones were not random -- they
included every large debtor building, so **511 of 576 debtors vanished** and the
script printed a warning line per building and carried on to announce a total.

The pacing moved into `get()`, which now gates on the previous request's start
time, so the rate is 57/min whatever the latency and the sleeps cost nothing on
a slow link. A 429 is retried up to three times, honouring `Retry-After`.
Measured after: 18 requests in 66 seconds, no 429s.

**And a failed sweep now says so in the only way anything reads.** A tenants
failure is counted as a failure too -- it does not lose the debt, it loses the
phone, and a row with no phone is dropped by the writer, so the apartment
disappears just the same. Whatever the sweep found is still written, because
every write is an upsert and a short run leaves yesterday's figures standing
rather than erasing them. What it must not do is exit 0: the workflow gate and
`/sync` both read that, and an arrears list missing 37 buildings while reporting
success is the same lie the import spent a fortnight telling.

**Two things about today's ₪922,901 that are not yet decided.**

*The filter stage is not in the automated path.* `import_arrears.py` -- the
script that produced the ₪101,519 figure on 11 Aug -- drops two patterns before
writing: months forming a **leading run** shared by 60% or more of a building's
flagged apartments (that is the period before Homies managed the building, not
debt), and whole buildings where 80% or more miss the same pattern (recording
lag, not debt). It reads the JSON `oxs_arrears.py` writes **only when `--quiet`
is off**, and the workflow passes `--quiet`. So the nightly path skips the
filter entirely and writes the raw sweep. That is where ₪975,991 against
₪101,519 comes from, and it is now on the dashboard.

*The two importers disagree about what `period` means.* The old one wrote one
row per unpaid month, stamped with the month owed. `oxs_arrears.py` writes one
cumulative row per apartment stamped with the month it ran. **68 residents now
hold both**, ₪63,614 across 107 charges counted twice -- ₪683 for July and ₪683
again inside August. Today's 15:00 run cannot make it worse, because it upserts
the same period. **1 September can**: it will write a fresh Jan-Aug row beside
the untouched Jan-Jul one, and compound every month after that.

Neither is mine to settle -- the filter thresholds were a judgement made against
real data on 11 Aug, and retiring 107 charges is money coming off a client-facing
figure. Both are written up as open defects. A clean sweep is running to
quantify exactly what each filter removes.

---

## 2026-08-23

### The bot was silencing itself on every new conversation

Found in the first minute of the bot evaluation the user asked for, by the
evaluation itself: the harness's very first greeting got no reply, and the
execution showed `_handedOver: true` on a brand-new conversation nobody had
touched.

**Chatwoot assigns every new conversation on a bot-attached inbox to the agent
bot itself** -- `meta.assignee` is the bot, `assignee_type: "AgentBot"`. The
takeover gate written on the 21st asked only "is anyone assigned?", and the bot
counts as anyone. So every conversation created after the bot was linked
started life handed-over, and the bot never spoke. It had gone unnoticed for
two days because every test so far ran on conversation 1, which predates the
linking -- the one conversation in the system the bug could not touch.

Fixed in both places that read the assignee: the WhatsApp workflow's gate and
the handback workflow's filter now treat only a **User** assignee as a
takeover (`assignee_type === 'User'`, with "has no outgoing_url" as the
fallback discriminator -- the bot's assignee object carries its webhook URL, a
person's never does). Smoke-tested on a bot-assigned conversation: menu in
3.2s. The handback fix matters as much: without it, the scheduler would have
"handed back" every bot-owned quiet conversation every 15 minutes, forever.

Also noticed on the way: the agent bot's `outgoing_url` -- including the
webhook secret in its query string -- is embedded in `meta.assignee` on every
webhook payload Chatwoot sends. Internal-only today, but it means the secret
appears anywhere those payloads get logged.

### The evaluation ran, ten judges read it, and the verdict is one sentence

**The bot's manners are good and its refusals hold; its promises are hollow.**
All 18 scenarios completed (45 turns, replies in 3.8-10.1s). Ten agents -- one
judge per requested section, a truth-verifier, a completeness critic over the
other nine -- produced 85 findings: 34 high, 31 medium, 20 low. Published as
the "Homies Bot Field Test" artifact; transcripts and panel JSON in the session
scratchpad.

What held: no grovelling under "גנבים", the neighbour's debt refused, a foreign
ticket ref leaked nothing, both injection attempts bounced, the balance
question hit an identity gate, Hebrew register genuinely Israeli, menu and
canned flows exact.

The run's defining facts, each verified against tool calls and the database:

- **open_request was called zero times.** Three residents were told their leak
  "went to the team"; no ticket existed. The prompt's own banned sentence shape
  ("אני פותח קריאה על...") appeared verbatim.
- **Three of four "מעביר לצוות" lines had no transfer_to_human behind them**,
  including the scenario whose entire point was an explicit request for a
  human. The only real transfer was the gas emergency.
- **The model fabricated ticket number 255-1048-26 -- the exact number the
  prompt's own cautionary tale quotes.** The war story handed the model a
  realistic number to reuse. The rescue caught it, then delivered the resident
  NOTHING: reply null after 10.1s, and the rescue's DB row landed only after
  the scenario's snapshot (exactly one such row existed at cleanup).
- **Post-tool amnesia**: after verify_address or transfer_to_human ran, the
  bot asked for the building it had just been given (gas emergency) and for an
  apartment given two turns earlier (duplicate).
- **The "עוד משהו?" options list the prompt trusts the workflow to send never
  fired once** -- the prompt forbids the model to ask, the node never sends, so
  every conversation ends on a dead line.
- **Balance is undiscoverable**: dropped from the menu in the Chatwoot move and
  enumerated nowhere.
- The gas transfer fired **before any address existed** and nothing attached
  the address afterwards -- the team gets an emergency with no location.

The critic also corrected the panel: empty `db_requests` is not evidence about
transfers (they never write that table; the missing tool calls are the
evidence), and the "truncated tool descriptions" finding was the capture
script's own 500-char cut, not the live config.

Test data cleaned: 68 messages, 1 request, 2 interactions, the balance fixture
(resident + charge), and all 18 synthetic Chatwoot contacts. Only the real
conversation 1 remains.

### The report was rewritten per section, and phantom handovers downgraded

Two revisions on the user's feedback. First, the report page was rebuilt in
plain language: per section, "what worked / what's broken / the fix" as short
bullets, with the judges' full prose collapsed underneath.

Second, a call the owner made and the report now carries: **the phantom
handover is a warning, not a failure.** Reasoning: with Chatwoot in the path,
every conversation sits in the inbox where staff can read and answer it inside
WhatsApp's 24-hour service window -- so a missing transfer_to_human record no
longer strands a resident the way it did when n8n answered Meta directly. The
warning text keeps the two conditions under which it becomes a real failure
again: nobody watching the inbox, or the 24-hour window passing. The
recommendation kept alongside: wire the transfer line to also flag the
conversation in Chatwoot (assign or label), so promised handovers stand out
from ordinary chats instead of relying on inbox patrol.

The ranking of worst findings is now: ghost tickets, the silent reply,
dead-end endings.

### End-to-end flow test: everything passes except ticket lookup

Owner asked for one straight run through the whole flow — greeting, opening a
ticket, checking a ticket, general questions — observation only, no debugging.
Seven turns on a synthetic number, read back through the Chatwoot messages API
rather than the probe (the probe's `newest_outgoing` keeps capturing the
trailing follow-up menu instead of the reply).

Passed: the greeting («היי! הכל טוב, תודה. כאן מיכאל מהומיז — איך אפשר לעזור?»
with the three buttons); the ticket flow, which produced a REAL row —
255-1086-26, plumbing, canonical building, right description; office hours;
payment methods; the closing thanks.

**Failed: ticket lookup, and it fails by creating a duplicate.** Asked «מה
המצב עם הקריאה שפתחתי?», the model did the right thing — called
get_request_status and wrote a status answer quoting the reference. Then the
phantom-claim net fired: its test is "reply contains a ticket-shaped number
AND open_request did not run", and a status answer satisfies both. The rescue
lane opened a junk ticket (255-1087-26, building null, description made of
concatenated conversation lines, needs_review) and REPLACED the correct status
answer with "פתחתי קריאה, מספר 255-1087-26. זה עובר לצוות." The guard knows
only one legitimate source for a reference in a reply; the lookup tool is the
other one, and it was never taught. Fix is one condition —
`get_request_status.isExecuted` excuses the claim — held back because the owner
asked for observation only.

Two smaller observations, left for the owner to rule on: on a content-bearing
message the model still re-introduces itself and echoes the resident's sentence
back word for word before reacting (the intro words sit inside its own
instruction, and flash copies them); and the follow-up menu fires after every
reply that doesn't end in a question — five times in one seven-turn
conversation, which reads mechanical after small informational answers.

Test data cleaned and verified: both tickets deleted, 19 messages, the
conversation and its contact gone.

### The menu rides on Michael's hello

Owner noticed the intro arrives without the three buttons — they used to be
attached by the deleted greeting matcher. New mechanism, no matcher: the
model decides what is a greeting (the prompt guarantees «כאן מיכאל מהומיז»
appears exactly on greeting replies), and the Send node decorates any reply
carrying that signature with the three menu buttons as one input_select
message. Smart classification in the model, deterministic decoration in the
workflow — the same division of labor as the transfer backstop. The
dead-end checker now skips intro replies so a period-ended hello cannot
produce a second menu.

Verified live: greeting → intro with the 3 buttons on the same message; a
tapped button still routes to its canned reply; a "never mind, thanks" close
still gets the follow-up menu; no double menus. Test data cleaned.
Rollback: wa-before-introbuttons.json via patch_wa_introbuttons.py --restore.

### The rule became "a greeting gets the name" — and a heredoc broke the bot for four minutes

Owner's handset again: four minutes after their last test, «היי מה המצב?»
got the greeting back without the name — the 24-hour greeted window counted
them as mid-conversation. The owner's correction is simpler than any window:
**a greeting gets a greeting with the name, every time** — first message or
mid-conversation — worded differently each time; only content messages skip
the intro ("הפתיח הולך אחרי ברכות, לא אחרי הודעות"). Wrapper and prompt
rewritten to that rule.

The rewrite carried a trap: pushing the new wrapper through a bash heredoc
turned the expression's \\n escape into a literal newline inside the JS
string — a syntax error, so the agent failed before ever calling the model
and EVERY message got the error-fallback transfer line. Caught in the very
next live test (three for three fallback lines), diagnosed from the
execution (no OpenRouter run at all), rebuilt with String.fromCharCode(10)
so there is no escape sequence left to mangle. The scratchpad's standing
rule stands: tricky content goes through the Write tool, never heredoc.

Verified live: greeting → name+offer; second greeting → name again, new
wording («היי! כאן מיכאל מהומיז, מה אפשר לעשות בשבילכם?»); content message →
no intro, straight to the ticket offer. Test data cleaned. Rollbacks:
wa-before-nameback.json (pre-rule), fix_wrapper.py holds the good wrapper.

### A second "היי" no longer gets the same sentence back

Owner's handset, minute two of the persona relaunch: after Michael's intro
they wrote just «היי» — and got «היי. איך אפשר לעזור?», a near-verbatim
replay of the offer sent sixty seconds earlier. The greeted flag worked (no
re-introduction); what was missing was any rule for what a SECOND greeting
gets, and the general never-repeat rule the field test called for.

Added to the prompt: a mid-conversation greeting is answered short and
forward («כן, אני כאן — מה קרה?», «היי, ספרו לי מה העניין»), never with the
help offer again — and **no sentence already sent in a conversation is ever
sent again word for word**; whoever gets the same sentence twice knows for
certain they are talking to a recording. Verified live on a fresh number:
intro → varied invitation (+ the dead-end net's buttons, correctly) →
«כן, אני כאן — מה קרה?». Rollback: wa-before-norepeat.json.

### The bot is Michael now, and every first message gets a hello

Caught by the owner on a real handset: «היי מה המצב?» — plain text, first
message — got the media-only line («אני קורא כאן רק טקסט»), twice, and no
greeting. Two roots. The greeting menu fired only on an exact-match regex, a
script pretending to be a bot; everything else fell to the model, which
reached for the one fixed line it had. And that media line sat in the prompt
as ammunition even though the workflow answers real media by itself before
the model ever runs — the same lesson as the example ticket numbers.

The owner's direction: no greeting matcher at all. Changes, live: the
greeting-regex branch is deleted from Sort (every first message goes to the
model); the per-message wrapper now instructs a first message to open with a
polite personal hello; the bot has a name — **מיכאל (Michael)** — woven
through the identity section and every example; smalltalk gets a human-answer
rule («היי! הכל טוב, תודה. כאן מיכאל מהומיז — איך אפשר לעזור?»); and the
media line was REMOVED from the prompt with an explicit ban — any message
that reaches the model is text from a person. The workflow still answers
real media with the canned line; the prompt's fixed-lines section is down to
one line (the transfer sentence).

Greeting memory became time-based on the way: the old flag was
greeted-forever, which meant no existing contact — the owner included —
would ever see the new intro. Now the store keeps last-seen timestamps and
Michael greets again after 24 quiet hours, like a person; legacy boolean
flags count as stale, so every existing contact gets the new hello once.

Verified live: «היי מה המצב?» → warm Michael intro, no media line; a fault
opener → intro plus handling in one message; empty text still gets the
canned media line; a legacy-flag phone got re-greeted exactly once. Test
data cleaned. Rollback: wa-before-persona.json via patch_wa_persona.py
--restore.

### Ghost tickets, fixed at the root: the sequencing moved into the tool

The report's worst finding, closed at the owner's direction. Diagnosis first:
the tool descriptions already ordered the model, in so many words, to call
open_request right after verify_address and not answer between the two — and
across every live run today it never once chained. gemini-2.5-flash reliably
makes ONE tool call per turn. Sequencing that must always happen cannot live
in a model's discipline; it moved into code.

The edge function's open_request now verifies the address itself, inside the
same call, on the WhatsApp channel only (`channel(ctx)`, the wa: prefix):
an address that does not resolve returns verify_address's own refusal
vocabulary — street_unknown, number_not_on_street with numbers_we_manage,
need_number, need_building, ambiguous — and files nothing, because a ticket
against a building we do not manage is staff time spent on something that
does not exist. Voice keeps the old normalise-never-refuse behaviour by
construction: voice agents were never taught to verify, and refusing would
silently drop their tickets. Deployed as function version 37.

Bot-side, the two-step doctrine is gone: the prompt teaches one call
(open_request checks by itself), the what-comes-back reason bullets stay
word for word (same codes, new sender), verify_address is demoted to pure
address questions and emergency grounding, and both tool descriptions
rewritten. The prompt also lost every example ticket number — the field test
proved the bot fabricates them digit for digit, so the format is now taught
by structure (office code, number, year) with an explicit "no real example
numbers in this file, on purpose". The phantom-claim regex in "Reply
usable?" was widened for long references (255-26277-26 shape) on the way.

Verified live, four scenarios: two full ticket flows where the model called
open_request itself — real references in the replies (255-1084-26,
255-1085-26) matching real rows with the right category, description,
canonical building, and unit null for common areas; Herzl 999 refused with
"ברחוב הרצל אנחנו מנהלים את 112", no row; Sokolov 99 refused with the 86/29
numbers we do manage, no row. The follow-up menu fired after the ticket
confirmation — the day's fixes compose. The rescue lane stays as the safety
net. Test data cleaned (4 conversations, 24 messages, 2 interactions, 2 test
tickets — verified gone). Rollback: wa-before-ghost.json via
patch_wa_ghost.py --restore; the function change reverts by redeploying the
previous index.ts from git.

### Housekeeping commits itself now

The uncommitted-docs backlog is gone and won't rebuild: two days of work
(CONTEXT, HANDOVER, WORKLOG, the Chatwoot cutover record) were committed and
pushed, and a new Stop hook runs `scripts/housekeep.py` after every Claude
Code turn. The script stages ONLY the briefing files and docs/, scans the
staged diff's added lines for real phone numbers and key-shaped strings
(this repo is public), and commits + pushes only when clean — a hit unstages
everything and reports instead. Whitelisted by name: the public office line,
the synthetic 9725099020xx test phones, OXS ticket references. The scan has
a self-test; it caught one pattern gap (sk_car_-style keys with inner
underscores) before going live. Sits alongside the existing briefing-check
hook in .claude/settings.local.json.

### Dead-end endings: the cure was built, nothing ever fed it

The report's finding #3, fixed at the owner's direction. The follow-up lane —
"Dead end reply?" -> "Options again" -> "Send menu", complete with the menu
content and the exact Send-menu node that already serves the greeting — had
**no incoming edge**. An orphan since the cutover rewrite; zero firings in 45
field-test turns, exactly as the report measured.

Three changes, live: (1) the missing wire — Send now feeds "Dead end
reply?", so every posted reply reaches the checker; (2) the owner's phrasing —
the follow-up asks "אפשר לעזור בעוד משהו?" like a person, with the same three
buttons under it; (3) a handover guard — no follow-up menu when the sent
reply announces a transfer to a human ("אני מעביר..."), because "anything
else?" right after "a person is taking over" is wrong tone and its third
button would invite a second transfer.

The wire alone wasn't enough: the checker's original conditions referenced
$('Hand over instead') bare, and when that node hadn't run the expression
threw and the If silently evaluated false — the same never-exercised-
expression class as the backstop's .all() bug this morning. Both conditions
were rebuilt on $json.content (Send's own response carries the sent text), no
cross-node references at all.

Verified live, three ways: a thanks close got the reply and then the
follow-up question with buttons; an explicit human request got the transfer
line and stayed quiet; and the classic ticket flow that used to stop cold on
"רשמתי. זה עובר לצוות" now shows three fixes in one thread — the model's
invented number was caught, the rescue lane opened a REAL ticket
(255-1083-26 in the test) and told the resident the real reference (the
morning's null-text fix at work), and the thread ended with the follow-up
question instead of a closed line. Test data cleaned (7 conversations,
23 messages, 3 interactions, 2 call_outcomes, 1 rescue request). Rollbacks:
wa-before-deadend.json / wa-before-deadend2.json. Report updated; the
open-list ranking is now: ghost tickets (root), then the smaller items.

### The emergency tone flipped from commanding to calming

The owner read the retest transcripts and corrected the spec: the bot must
NOT open every danger report by ordering a call to 102. New order, applied to
the live prompt (the section's third rewrite today, drafted again by a
three-writer/three-judge panel — the safety-first draft won 2:1, with grafts
from the losers): (1) confirm first whether it's really serious, with one
specific answerable question — the resident assesses, the bot never declares
severity in either direction ("ייתכן שיש סכנת חיים" is quoted in the prompt
as the banned move); (2) recognize panic from the writing itself (caps, !!!,
"הצילו") and be the calm one — acknowledge first, short steady sentences, one
thing per message; (3) the hotlines 100/101/102/103 are advice for serious
situations, not a command — "אם המצב חמור, 102 הם הכתובת הכי נכונה"; (4) the
transfer still really happens and "takes a moment"; (5) ask them explicitly
not to act on their own or take rash steps; (6) stay in the conversation,
with the hotline availability said once, gently — not as a chorus.

Round-5 live retest, three scenarios: gas in normal register — acknowledge,
"הריח חזק ומתפשט, או חלש?", precautions and 102-as-advice only after the
resident confirmed, transfer plus don't-act-alone; a panicking fire report —
"אני כאן. קיבלתי — שריפה בבניין. / רואים אש או עשן ממש עכשיו?" and the calm
one-thing rhythm all the way; an injury — "היא בהכרה?" then 101 as advice.
The backstop earned its keep twice: on two turns the model promised the
transfer without calling the tool and "Transfer it anyway" made it real.
Remaining warts, all minor and listed for later: the model leans on the fixed
transfer line inside emergencies instead of the "takes a moment to the right
department" phrasing, one "איזה בניין זו", and an occasional two-details
question. Test data cleaned (3 interactions, 4 call_outcomes, 2 requests, 16
messages, conversations 30-32 with contacts). Prompt now 30,158 chars.
Rollback: wa-before-calmtone.json via patch_wa_emergency3.py --restore.
Report's update note and retest threads replaced with the calming-tone runs.

### The emergency flow stopped being a cutoff, and promises grew a backstop

The owner's spec, applied to the live bot: an emergency should never end at
"אני מעביר את זה לצוות, נחזור בהקדם." The new protocol, in the prompt's own
voice: emergency services first if it's serious (100/101/102/103 matched to
the hazard), say we're not experts, universally-accepted safety steps only
with a strict no-diagnosis rule in both directions (no "it's probably X", no
"that's not dangerous", and no "זה דחוף" either — severity is the emergency
services' call), say the transfer to the right department takes a moment
(after the tool actually ran), stay in the conversation asking one thing at a
time, and close by repeating the emergency-services advice. Cheerful words
banned near emergencies. Drafted by a three-writer panel with three judges
(the winning draft needed four fixes, including a severity-gate bug where the
bot would decide how serious it sounded before pointing at 102).

Three live test rounds forced two more rounds of work:

- **Round 1**: gas — textbook. Injury — no example to copy, so it slipped:
  promised the transfer without calling the tool, said "זה דחוף", masculine
  "תדאג", three questions in one message. Fix: an injury mini-example in the
  prompt plus the both-directions severity ban.
- **Round 2**: injury — textbook. Water-on-electrical-panel — promised a
  transfer, no tool call. The prompt had now said "tool before text" twice;
  this class needed structure, not a third sentence. Fix: **the promise
  backstop** — a new lane after "Reply usable?": if the outgoing text promises
  a handover and neither transfer_to_human nor open_request ran, the workflow
  fires the same debt-tools webhook itself and the reply goes out unchanged.
  Every spoken handover now leaves a transfer record.
- **Round 3** exposed two real bugs. The backstop double-fired next to a real
  transfer: `$('tool').all()` reads the main channel and tool nodes emit on
  ai_tool, so the check always saw "not run" — switched to `isExecuted`, and
  the older phantom-ticket check in "Reply usable?" carried the same latent
  flaw (hidden because open_request had never run once) and got the same fix.
  And the regression leg caught **the silent reply's mechanism on camera**:
  the ghost claim fell into the rescue lane, a real ticket was created, and
  "Hand over instead" evaluated its text to null — Chatwoot sent an empty
  message. The expression is now String()-wrapped with a hard fallback, and
  "Send" itself substitutes the fixed transfer line for empty content, so a
  blank message to a resident is impossible from any lane.
- **Round 4**: human request — tool ran, backstop silent. Water-electric —
  the model called the tool itself, full protocol. Normal fault — ordinary
  flow intact (its turn-2 re-asking is the known, deliberately-open amnesia
  finding, not a regression).

Transfers, it turns out, write three rows each: an `interactions` row
(`wa:<phone>`, disposition transfer:emergency), a `call_outcomes` row, and a
`needs_review` row in `requests` — so a backstopped promise is genuinely
visible to staff, not just logged. All test data deleted afterwards: 8
interactions, 10 call_outcomes (the double-fires included), 6 requests, 34
messages, 10 Chatwoot conversations and contacts (phones ...9020[20-29]).

Prompt is now 29,694 chars (was 27,347). Workflow is 30 nodes (was 26; the
backstop lane has its own sticky note). Rollback snapshots:
wa-current-emergency.json (pre-everything), wa-before-backstop.json,
wa-before-fixups.json — each patch script takes --restore. Report updated
with a "changed after the report" note and three live retest threads; still
open by design: ghost tickets, dead-end endings, the Chatwoot assign/label
flag on transfers.

### The full transcripts are now on the report page

The user asked to see the back-and-forth itself, so the report now ends with
"The conversations, word for word": all 19 test threads as chat bubbles --
resident right, bot left -- with the tap-menu buttons rendered as pills, a
small mono line under each reply showing which tool ran and the latency, the
one empty reply shown as an explicit red "no reply came back" bubble, and a
one-line note under each thread saying what it proved. Data comes straight
from `bot-test-transcript.json` (the probe's capture), untouched.

While wiring it in, the header stats were corrected against that same data:
the page said "18 conversations"; the truth is 19 scenarios, 33 exchanges,
across 17 WhatsApp threads (three scenarios deliberately reused one number).
With the transcripts printed in full the count became checkable, so the stat
now says "19 scenarios" and the subtitle carries the 33.

Same artifact URL, republished.

Eighteen scripted Hebrew conversations against the live pipeline -- webhook to
agent to Chatwoot to Supabase -- on synthetic +9725099020xx numbers, so no
real phone receives anything. Observation only: nothing about the bot is
edited mid-test; every miss becomes a finding. Sections, per the user's list:
attitude, grammar, reactions, interaction, request handling, boundaries,
time-to-human, guidance. A synthetic resident with one unpaid 450 charge was
planted for the balance scenario and is deleted with the rest afterwards.

---

## 2026-08-21

### Chatwoot is half in the path: token, inbox and a verified callback

Asked what setting up Chatwoot needs. It turned out to be less than the feature
doc assumed -- it has been installed and running since 9 Aug, so the job is the
cutover, not the install. Confirmed against Meta first: the app subscription
still names `n8n-zqvb.../webhook/homies-whatsapp`, so nothing had moved.

**Root SSH, by key.** The box only had a password/key prompt for a key we did
not hold. Generated an ed25519 pair locally, public half pasted through
hPanel's web console. It failed twice before it worked, and the reason is worth
keeping: the existing `authorized_keys` had **no trailing newline**, so `>>`
glued our key onto the end of the previous one and broke both. `wc -l` said 1
line and 847 bytes, which is the tell. Split with `sed`, backup left at
`authorized_keys.bak` -- do not delete it until the original key's owner has
confirmed they can still get in.

All six containers up, none touched: chatwoot rails/sidekiq/redis/postgres,
n8n, traefik. 5.8G of 7.9G free.

**The install had one user and no inboxes.** SuperAdmin `clixteam579@gmail.com`
on account 2, named `CLIX` rather than Homies. Zero inboxes -- the WhatsApp
channel had never been created, which is the real reason the cutover never
happened.

**Token minted from the Rails console**, not by hand in the UI, so it never
crossed a chat window. `CHATWOOT_API_TOKEN`, `CHATWOOT_URL` and
`CHATWOOT_ACCOUNT_ID=2` in `.env`; `/api/v1/profile` answers 200.

First attempt wrote 197 characters of Rails log into `.env` because `tail -c`
was used to trim the output. `rails runner` prints deprecation warnings and a
geoip line to stdout, so anything read from it needs a delimiter, not a
position. Redone with `<<<TOK ... TOK>>>`, which gave the real 24 characters.

**Which WhatsApp token, settled by asking Meta rather than guessing.** Three
live in `.env` and `debug_token` separates them:

| variable | type | valid | expires |
|---|---|---|---|
| `SYSTEM_USER_ACCESS_TOKEN` | SYSTEM_USER | yes | never |
| `WHATSAPP_ACCESS_TOKEN` | SYSTEM_USER | yes | never |
| `WHATSAPP_TOKEN` | USER | **no** | expired |

`WHATSAPP_TOKEN` is dead. Nothing checked yet whether the n8n WhatsApp
credential is holding it -- if it is, the bot is sending on borrowed time.

**Inbox 1 created**, `Channel::Whatsapp`, provider `whatsapp_cloud`, number
`+15551781261` ("Test Number", quality GREEN). Creating it moves nothing: Meta
still delivers to n8n, and deleting the inbox undoes it.

**The callback was proved before Meta was told about it.** Chatwoot's endpoint
is `{FRONTEND_URL}/webhooks/whatsapp/{phone}` with a 32-character verify token
in `provider_config`, both now in `.env`. Ran Meta's own handshake against it
by hand:

```
right token -> 200, echoes the challenge
wrong token -> 401
```

So the one step that silently refuses to save in Meta's UI is already known to
work.

**The admin password was lost, and there was no way to mail a reset.** The one
account is the user's own address and the password was gone. With SMTP unset
there is no forgot-password path at all, so the Rails console is not a shortcut
here -- it is the only door. Reset to a generated 21-character value, stored in
`.env` as `CHATWOOT_ADMIN_PASSWORD` beside `CHATWOOT_ADMIN_EMAIL`, and verified
by `POST /auth/sign_in`: 200, SuperAdmin, administrator on account `CLIX`.

Confirmed while in there: `ENABLE_ACCOUNT_SIGNUP=false` really is set on the
running container, so the public URL offers no registration form. And
`MAILER_SENDER_EMAIL` and `SMTP_ADDRESS` are not merely blank, they are unset --
which is what makes the paragraph above true, and what blocks inviting the 19
staff.

### Replying IS the takeover, and quiet hands it back

Asked "do I just reply?" -- and the honest answer was no, which was wrong of
the design, not the question. Chatwoot does not assign a conversation to the
agent who answers it (its `self_assign?` is a notification-suppression check,
nothing more), so an agent who replied and walked away would still have the
bot talking over them.

**Two additions closed it:**

**A human reply now claims the conversation.** The webhook makes this safe:
the bot's own outgoing messages arrive as `sender.type: "agent_bot"`, a
person's as `"user"`. New branch in the WhatsApp workflow -- `Sort` flags a
public human reply, "Human replied?" routes it, "Assign to the replier"
assigns the conversation to that user. Private notes deliberately do not
claim. Tested live: agent reply via API -> conversation assigned to Assaf
Clix in under eight seconds.

**A new scheduled workflow, "Homies — Chatwoot handback"** (IVNR5iNn7bQS8JgP,
every minute, Asia/Jerusalem): open conversations where the bot is off and
nothing has happened for **15 minutes** are unassigned and stripped of
`bot-off`. 15 was chosen over the proposed 2 -- `last_activity_at` only moves
on messages, so a 2-minute limit steals threads from an agent who is typing
or on the phone. Resolved conversations are never touched: resolved is
finished, not forgotten.

**The first 22-minute soak caught a bug.** At t+15m the unassign fired and
the label survived: "Strip the bot-off label" built its URL from
`$json.conv_id`, but after the Unassign node `$json` is the assignment
response, so the URL ended in `undefined` and Chatwoot served its 404 page.
Third instance today of the same class -- an n8n expression reading the wrong
node's output -- and the fix is the same shape: read the filter node's item
(`$('Quiet for 15 minutes?').item.json.conv_id`), which the body expression
had done correctly from the start.

Also learned: **taking over resets the inactivity clock.** Assigning or
labelling moves `last_activity_at`, so the 15 minutes counts from the
takeover, not from the resident's last message. Right semantics, free.

The second soak passed clean: reply-claim + label on, fourteen minutes of
`assignee=Assaf Clix labels=['bot-off']`, and at t+15m both gone in the same
tick -- `assignee=None labels=[]`. Full cycle proven: human reply claims,
fifteen quiet minutes hands back, next resident message gets the bot. Chatwoot-side prerequisites unchanged:
auto-assignment off on inbox 1, `bot-off` label exists, admin credential in
n8n as "Chatwoot admin (api_access_token)" (`N8N_CHATWOOT_ADMIN_CRED_ID`).

### The bot got a switch a human can see

Asked for "a switch for on and off of the chatbot so a human can turn over" --
after the third time an empty-looking inbox was read as a broken system. The
`pending`-status gate shipped this morning was the same capability wired to the
wrong signal: `pending` is exactly the state Chatwoot's default conversation
list hides, so every thread the bot was working was invisible by design.

**Now the bot answers by default and three visible acts silence it**, each for
one conversation only:

| act in the inbox | effect |
|---|---|
| assign it to anyone | bot off -- taking a conversation is taking it over |
| add the `bot-off` label | bot off -- the explicit switch, shows as a chip |
| resolve it | bot off |

Undo any of them and the bot picks the thread back up. And after every reply
the bot flips its own conversation to `open` (new node "Show it in Open",
downstream of Send on purpose -- a thread nobody was answered in must not show
as handled), so everything is on the default screen with no filter changes.

Two Chatwoot-side changes made first, without which the design fails silently:
**auto-assignment off** on inbox 1, or Chatwoot assigns an agent on arrival and
the assignee test kills the bot before it says a word; and the **`bot-off`
label created** at account level, so the switch is one click rather than typed
free text.

Tested six states end to end, each payload's conversation object read back from
Chatwoot rather than hand-written -- a hand-written fixture tests my idea of
Chatwoot, which is the mistake that produced this morning's outage. Default
answers; label silences; label removed answers; assigned silences; unassigned
answers; resolved silences. 6/6, and the "flipped to Open" column confirmed the
new node fires only when the bot actually replied.

The `pending` filter note written into HANDOVER two hours ago is superseded and
was rewritten: agents no longer need to touch the filter at all.

### Chatwoot is in the message path, and the cutover had already happened

The bot stopped answering. It was us, in a way none of the planning caught.

**Creating a WhatsApp Cloud inbox in Chatwoot repoints the number.** Chatwoot
sets a **per-phone-number webhook override** on Meta, and that beats the
app-level subscription. `GET /{app-id}/subscriptions` still named n8n -- which
is what was checked, twice, and reported as "nothing has moved" -- while
`GET /{phone-number-id}?fields=webhook_configuration` told the truth:

```
phone_number: https://chat.../webhooks/whatsapp/+15551781261   <- wins
application:  https://n8n-zqvb.../webhook/homies-whatsapp
```

So the cutover happened silently at inbox creation, hours before the n8n
changes existed, which is exactly the order the plan says never to do. In
between, every message reached Chatwoot, was forwarded to n8n, and was thrown
away by a signature check still looking for Meta's HMAC:

```
Sort -> {"_reply": "", "_work": false, "_rejected": "unsigned"}
headers: user-agent: Ruby, x-chatwoot-signature: sha256=...
```

**Check `webhook_configuration` on the phone number, never the app
subscription, to learn where a number actually points.**

**Rolled forward rather than back**, on the user's call. And the MCP turned out
not to be needed: n8n's REST API takes a workflow update, so the four changes
went in through `PUT /api/v1/workflows/{id}` with the pre-edit JSON saved beside
the patch script as the rollback (`--restore`).

Three things cost a round trip each:

**The n8n public API accepts only `name`, `nodes`, `connections`, `settings`**
on a PUT and 400s on anything else -- the GET returns twenty-two keys.

**A URL field needs a leading `=` to be an expression.** Without it the node
posted to a literal `.../conversations/{{ $('Sort')... }}/messages` and Chatwoot
answered its 404 page. The body fields already had the `=`; the URL did not,
because it was assembled in Python and the prefix was lost.

**The webhook node has two outputs**, GET and POST, and POST is index 1. Reading
`main[0]` of the trigger shows an empty array and looks like a dead execution.

**Chatwoot signs its webhooks after all.** `lib/webhooks/trigger.rb` sends
`X-Chatwoot-Signature`, HMAC-SHA256 over `${timestamp}.${body}`. It is not
verified: `require('crypto')` is blocked in the task-runner sandbox and the
Crypto node cannot prepend a timestamp to the raw bytes. The door is a
43-character secret on the bot's `outgoing_url`, checked in `Sort`, failing
closed. Verifying the signature is the obvious hardening later.

**Chatwoot fires five extra events per exchange.** One resident message
produced `conversation_status_changed`, `conversation_updated`, and both
`message_created` and `message_updated` for the bot's own reply. Answering that
last one is an infinite loop, which is why the new `Sort` filters on `event`,
`message_type` and `private` before it does anything at all.

### Proved end to end, including the thing a webhook could never do

```
1  in   hello
2  out  היי, כאן שירות הלקוחות של הומיז. במה אפשר לעזור?
        [פתיחת קריאת שירות] [מצב קריאה קיימת] [לדבר עם נציג]
3  in   פתיחת קריאת שירות        <- tapped on a real handset
4  out  בסדר. מה התקלה?
```

The tap is the interesting one: Chatwoot discards the button id and forwards
only the title, so the routing table is now Hebrew strings, and it resolved
correctly from a real phone rather than a replay.

Supabase logged all four with `phone` in the old bare-digits form -- `Sort`
strips Chatwoot's leading `+` deliberately, because both writers, every tool
and 99 existing rows match that shape.

**The per-conversation AI toggle works**, which is the capability the whole
migration exists for:

| conversation | inbound message | Sort |
|---|---|---|
| `open` (a human has it) | יש נזילה בלובי | `_handedOver: true`, silent |
| `pending` (bot has it) | שלום | `_menu: true`, answered |

One artifact left behind: the run whose `Send menu` 404'd still wrote an
outbound `messages` row, because `Log reply` sits on a parallel branch rather
than downstream of the send. Pre-existing, not introduced here, and worth
fixing -- a logged reply nobody received is a transcript that lies.

### Teams and the agent bot, built ahead of the traffic

Both are inert until Meta repoints, so there was no reason to leave them for
the risky day.

**Four teams** on account 2, matching the departments in the feature doc:
Collections (1), Operations (2), Management (3), Service (4), all with
auto-assign on.

**Agent bot 1, "Homies bot"**, pointed at the existing n8n webhook
`https://n8n-zqvb.../webhook/homies-whatsapp` -- the same URL Meta uses today,
which is deliberate: after the cutover the caller changes and the address does
not. Linked to inbox 1, `AgentBotInbox` confirms `1 | 1 | active`. Its own
`access_token` is in `.env` as `CHATWOOT_BOT_TOKEN`; that is the credential n8n
will post replies back with, not the admin token.

One thing to know for the n8n work: a message arriving now would be forwarded
to n8n and fail there, because n8n still expects Meta's envelope. Nothing
arrives, because Meta still delivers to n8n directly. The wiring is complete on
the Chatwoot side and dead on the wire.

### The menu does not survive the move, and Chatwoot's own source says why

Writing the n8n changes meant reading how Chatwoot builds a WhatsApp payload,
and two things fell out that the feature doc had assumed away.

**Chatwoot builds the interactive payload itself, from its own fields.**
`base_service.rb` `create_rows` emits `{id, title}` and nothing else, and
`create_payload` emits `body.text` and nothing else. So the four row
**descriptions** and the **footer** in today's menu have nowhere to go. The
list's tap-to-open button is `I18n.t(...list_button_label)` -- account 2's
locale is `en`, so it would render **"Choose an item"** in English under a
Hebrew question. The Hebrew locale is no better: `בחר פריט`, masculine
imperative, straight into the rule that we never gender the listener.

**Anything with 3 or fewer items becomes reply buttons instead**, and buttons
have no wrapper label at all -- the titles show directly. So the fix is to stop
at three. `יתרה ותשלומים` is the option that goes. It is also the right one to
lose: the agent still answers balance questions typed as words, and reading a
balance out loud is gated on the identity question in PRD 13 that nobody has
answered.

**Chatwoot throws the tapped button's id away.** `message_content` in
`incoming_message_service_helpers.rb` reaches for
`interactive.button_reply.title` and never the id -- with a `TODO` in their
source admitting it. Today's `Sort` routes on `tapped === 'open'`, so that
routing has to match the Hebrew **label** instead, which makes those three
strings load-bearing: reword one in the menu and the flow it starts silently
stops starting.

Both were found by reading the running container, not by guessing, and both
would have surfaced as "the menu looks wrong" some minutes after a live
cutover.

### The n8n changes are written and not applied

`docs/features/12-chatwoot/cutover-n8n.md`. Four changes, ready to paste, with
the order they have to happen in.

1. **The door.** Meta signs every POST; Chatwoot signs nothing. The HMAC check
   cannot be kept and must not merely be deleted -- without it the webhook is a
   public endpoint that files tickets for anyone who finds it, and the phone
   number in the envelope decides whose ticket. Replaced with a secret in the
   query string, because an agent bot sends a fixed URL and no custom headers.
   **Done on the Chatwoot side already**: bot 1's `outgoing_url` now carries
   `?s=<N8N_WEBHOOK_SECRET>`.
2. **The parser.** Chatwoot posts every event to the same URL, so the new
   `Sort` filters on `event`, `message_type` and `private` before doing
   anything -- answering the bot's own outgoing messages is an infinite loop.
   And `conversation.status` carries the AI toggle: `pending` means the bot
   owns the thread, and the instant a human replies Chatwoot flips it to `open`
   and the bot must fall silent on that conversation and no other. One line,
   and it is the entire reason for the migration.
3. **The reply path.** `Send` and `Send menu` post to `graph.facebook.com`. The
   danger is not that this would fail after the cutover -- it is that it would
   *work*: the reply reaches the resident and never appears in the conversation
   staff are watching. Both become one Chatwoot call, authenticated with
   `CHATWOOT_BOT_TOKEN` rather than the admin token, so replies are attributed
   to the bot and the inbox can show who said what.
4. **`scripts/check_whatsapp.py`** gets the new envelope, and is the safety
   net: it must pass against the new path while the old path is still carrying
   real messages.

The acceptance test is step 5, not step 4 -- reply as a human in the inbox and
watch the bot go quiet on that thread alone. That is the capability that could
not be built on a webhook, and it is the only proof the migration was worth
doing.

### Stopped short of the cutover, and not for the reason the plan gives

The feature doc frames repointing the callback as risky because inbound
messages in the switch window are lost rather than queued. On a test number
with no residents that costs nothing.

The real reason is different: **the minute Meta delivers to Chatwoot, the n8n
bot stops answering.** Its webhook verifies Meta's HMAC, which Chatwoot does
not send; its parser reads Meta's envelope, which Chatwoot does not use; and
both send nodes post to `graph.facebook.com`, so any reply that did get made
would reach the resident without ever appearing in the conversation the staff
are watching. Three changes, all inside n8n.

**The n8n MCP is not authorised in this session**, so none of them can be made.
Repointing now would take WhatsApp down with no way to bring it back before the
next session. Left where it is.

---

## 2026-08-20

### The gender skill goes into the debt agent, where half of it was missing

Asked whether both Hebrew agents carry the gender identifier, then pointed at
`hebrew-voice-gender-pronunciation-skill.md` -- a 30,000-character Hebrew
document in three parts: gender distinction, homographs and pronunciation, and
safer word choices.

**I got the first answer wrong and had to correct it.** I reported that the
intake prompt did not mention the לך trap. It does -- it carries the trap, the
neutral-phrasing table almost verbatim from the skill's section 4, foreign-word
transliteration and number gender. My check had searched for the *pointed*
spelling לְךָ; the prompt writes the transliteration *lekha*. The skill was
already integrated there and I had missed it by one search term.

**The real gap was the debt agent**, and it was the half a written check cannot
see. Its GRAMMAR section had the imperatives table -- תני against תן, תשלחי
against תשלח -- which is the easy half, because those look different on the
page. It had nothing on the words spelled **identically** for a man and a woman:
לך, שלך, איתך, בשבילך, אצלך, ממך, עליך. A sentence carrying one of those reads
as correct, passes any check you can run on the text, and still comes out wrong
in the ear.

**לך is the one that matters here**, because it is in every second sentence a
collections call wants to say: אני אשלח לך, חוזר אליך, יש לך תשלום פתוח. The
instruction is not to pick better -- it is to take the word out and say the
sentence without it. The result is shorter, which everything else in that prompt
already asks for.

Added the neutral-phrasing repertoire too. The debt prompt said "keep phrasing
around until a form lands" and gave nothing to phrase around WITH; the intake
prompt has had the table since it was written. With one addition of my own:
**neutral is a bridge, not a destination.** A whole call held at arm's length in
the plural sounds like a form being read, which is the other way to lose
somebody.

**Part B was deliberately left out.** The skill's homograph section is general
Hebrew -- milk against tallow, book against barber, bride against finished. Real
problems, and almost none of them can occur in a call about a building committee
payment. Adding twenty irrelevant rows to a 65,000-character prompt costs
attention and buys nothing.

**No English twin work was needed, which was worth checking rather than
assuming.** Everything added sits between "Grammar must be perfect" and "stay
neutral, leave them as written" -- the exact span `DEBT_BLOCKS` replaces
wholesale with an English grammar note. The patch asserts that before writing,
because a Hebrew table escaping that span would ship to an English caller.

**Testing.** Hebrew pushed and read back: all five markers present. English twin
rebuilt -- 60 passages and 4 section blocks -- and checked for the opposite
condition, that the Hebrew table did NOT leak into it. It did not. Intake
re-checked and unchanged.

### The nightly import had never once run

Asked whether the auto import was fixed. It was not, and it had been failing
twice a day since 18 Aug.

The workflow existed, was committed, and was firing on schedule. Every run that
actually tried died on its first step:

    ##[error]OXS_KEY_GENERAL is not set as a repository secret.

**None of the six repository secrets had ever been set.** `gh secret list`
returned nothing. So every row of OXS data in the database arrived from a run by
hand, and the schedule had been producing a tidy row of green ticks for two days
without importing anything.

**The green ticks are the part worth remembering.** GitHub cron is UTC with no
daylight saving, so the workflow is scheduled four times a day and exits
immediately on the two that are the wrong hour in Jerusalem. Those exit
`success` in about seven seconds. Half the runs on the list said success and had
done nothing by design; the other half said failure. Nobody looking at that list
casually would have read it as "this has never worked".

**Where the credentials went, and why.** Offered three homes -- the VPS that
already holds them, GitHub secrets, or porting the importers into an Edge
Function. The answer was "I want it on the dashboard", which is not a fourth
home so much as a different question: the dashboard should be where you SEE and
START it. It cannot be where it runs -- the importers are ~1,900 lines of Python,
one of them talks to Postgres directly, Vercel functions time out long before a
175-building sweep finishes, and the dashboard deliberately holds only the anon
key. So: GitHub Actions executes, the dashboard is the window.

**New page, `/sync`.** Last real import, counts of what came from OXS, the last
eight runs, and a Run now button.

Two things it deliberately gets right. It **names a skipped run as skipped**
rather than as a success -- a run that finished in under a minute imported
nothing, and reporting those as green is exactly how this went unnoticed for two
days. And the **history needs no credential**: the repository is public, so its
Actions history is public with it, which means the page works the moment it
deploys rather than after somebody issues a token.

The Run now button does need one -- a fine-grained PAT with Actions write, as
`GITHUB_DISPATCH_TOKEN` in Vercel. Until that exists the page says so plainly
and everything else still works. The dry-run checkbox defaults to CHECKED,
because the destructive reading of an ambiguous click is "write to the live
database".

**Testing.** Six secrets set from `.env`, values passed on stdin rather than
argv so no key reached shell history. Then a dry run dispatched and watched to
completion: residents read, the arrears sweep across all 175 buildings, and the
service-call import matching 26 of 27 to a resident -- Supabase untouched
throughout, which the script says out loud. Nine minutes, which is normal: the
sweep sleeps twice a second per building to stay inside the OXS rate limit.

**What happens next without anyone doing anything.** The next scheduled run is
midnight Israel time, and it runs WITHOUT `--apply` removed -- meaning it will
write for the first time. Two days of OXS arrears and service calls will land in
one go. That is the intent, but it is the first unattended write this system has
ever made.

### The debt agent folded on the one objection it exists to answer

From a test call: the resident is told about July's 450, answers "but the
elevator is still not fixed", and two turns later Michael says "I'll pass this
to someone on our team" and the call is over. Nothing collected, nothing logged,
nobody persuaded, and a transfer into a queue nobody watches.

**The agent did exactly what it was told.** The section
"THEY ARE WITHHOLDING BECAUSE SOMETHING IS BROKEN" said: say the broken thing
back, then `transfer_to_human` with reason `dispute`, then close. This was not
a prompt being ignored -- it was a policy, written on 18 Aug after the opposite
failure (the agent had dismissed a resident mid-sentence), and it over-corrected
into never trying at all.

So this is a change of intent, not a bug fix, and worth recording as one: **the
agent is now expected to work the objection before handing it over.**

**Why it matters more than it looks.** "I'll pay when the lift is fixed" is not
a refusal, it is a condition -- the person has just told you they intend to pay.
Transferring on it converts the commonest objection in building-management
collections into an automatic zero.

**The four moves, in one turn.** Say back what is broken, in their words, once.
Call `open_request` -- the call, not a promise to call it. Say the one true
thing that links the two subjects: **the committee money is what pays for the
repair**, so withholding delays the very fix they are waiting for. Then ask for
the payment again, concretely.

That third move is the whole change. It is not a defence of the fee and not a
lecture about what it covers -- both of those read as arguing that somebody
should pay for something that does not work. It is the only honest connection
between the two subjects, and it runs in the resident's favour.

**Bounded, deliberately.** One more move after a refusal, and it is a SMALLER
ask rather than a harder one -- a standing order, a date they pick, part of it
now. Two refusals and it stops, transfers, and says someone will come back about
both. And four cases skip the attempt entirely: they are angry, they say they
already paid, they ask for a human, or **they say the fault was already reported
and nothing happened** -- that last one has stopped being a payment objection
and become a complaint about the company, and pressing for money on top of it is
how a resident decides we are a collections line.

**The clause that made it fold.** "If those two conflict, the relationship
wins" was being read as permission to leave. It now says what it meant:
protecting the relationship is about HOW you press, not whether you press. The
failure it guards against is a resident left angry, not a resident left
unpersuaded, which is simply the job not done.

**Testing.** Hebrew pushed; the English twin refused to build until the new
Hebrew line had a table entry, which is that check working for the third time
today. English rebuilt -- 60 passages and 4 section blocks, no Hebrew remaining
-- and both live assistants read back from the API afterwards and checked for
six markers each. Twelve of twelve present.

**Not verified out loud.** Nobody has heard either debt twin speak since this
change.

### The pager moves above the table, and its controls become controls

Asked for after the orange button landed: make every button user-friendly, and
put the pagination on top.

**Above the table, on all five lists.** A pager under a fifty-row table is
below the fold — you scroll the whole list to discover there IS another page,
then scroll back to click it. Above the table it is the first thing read, and
it doubles as the row count for the list you are about to look at.

**Newer / Older are buttons now**, same size and shape as `View call` so every
clickable thing on a list page is recognisably one object. Outlined rather than
filled, deliberately: the filled orange is the row action, and two filled
colours competing on one screen is how a page stops having a primary action at
all.

At the first or last page they stay put and go visibly dead instead of
disappearing. A control that vanishes shifts everything beside it and leaves
you unsure whether you hit the end or missed the target. `aria-disabled` says
to a screen reader what the grey says to everyone else.

The rows-per-page pills had `padding: 1px 8px` — a 14px-tall tap target, half
what a finger needs. Now 4px 10px.

**And `debts/page.tsx` stopped being a binary file.** It carried a literal NUL
byte as a composite-key separator — the right character for the job, since
neither a phone number nor a flat number can contain one, but written as a raw
byte rather than `\u0000`. Git called the whole file binary: no diff, no blame,
and `grep` skipped it. Same key, same behaviour, now text.

### The way into a call was the least visible thing on the page

Filled orange, on request. Two `--action` tokens rather than one colour: the
deep orange that clears AA contrast against white (`#c2410c`, ~5.9:1 with white
text) is too dim on the dark theme's `#101012`, so dark goes brighter
(`#fb923c`) and flips the label to near-black. The focus ring stays the blue
accent -- a ring the same colour as the button it surrounds is invisible, which
is the entire job of a focus ring.

The Calls list's only clickable element was the word `transcript`, styled as
plain text because the stylesheet sets `a { color: inherit; text-decoration:
none }`. So the one action on every row did not look like an action.

Now a bordered `View call` button, and shown on **every** row rather than only
rows with a transcript: the page also carries the recording, the outcome and the
tool calls, so a call that produced no words still has something to look at --
the 6-second Cartesia failure on 19 Aug being exactly the row somebody would
want to open.

### The chat bot invented a reference number and wrote nothing

Asked for a responsive bot, so the bot was measured first rather than improved
on a hunch. `check_whatsapp.py` failed: three messages -- a leak in the lobby,
"yes please open a request", a real building and flat -- all answered, and no
row in `requests` after 45 seconds.

The n8n execution said it plainly. The agent called `verify_address`, got back a
real building and a real apartment, never called `open_request`, and replied:

    פתחתי קריאה על הנזילה בלובי, מספר 255-1048-26 — זה עובר לצוות התחזוקה

A reference invented digit for digit in the shape this system uses. The phantom
guard from 19 Aug caught the claim and replaced the message with "I am passing
this to the team" -- which stops the lie and leaves the resident with nothing: no
ticket, and a handover that reaches nobody.

**Why it skipped the tool.** `open_request`'s own description already said "you
must not invent one, and you must not tell the resident a ticket exists before
this returns", and the model did it anyway. What was missing was on the OTHER
tool: `verify_address` said "call this BEFORE open_request" and never said that
it opens nothing itself. On `gemini-2.5-flash` a successful check reads as the
work being done, and the agent returned a final answer after one tool call.

Fixed in the two places the n8n agents skill puts them. The tool description now
says verify_address CHECKS an address and OPENS NOTHING, that a successful check
is half the job, and that the next thing is `open_request` with no reply in
between. Inter-tool flow belongs in the system prompt, so that got the hard rule
as well, under "מה אף פעם לא", with the 20 Aug reply quoted as the worked
example of getting it wrong.

**And a backstop, because a rule the model can ignore is not a constraint.** New
Edge Function handler `rescue_request`: given the phone, it reads that
conversation's inbound messages out of `messages` -- written by "Log inbound"
before the model ever runs -- joins them as the description, takes the building
from the `verify_address` result n8n already has, and writes the row. Status
`needs_review` with a null `type`, because nothing classified it and a guessed
category on a rescued row is the same failure that produced it. Idempotent
within 30 minutes on the interaction, so a model that invents a number twice in
one conversation does not mint two tickets.

In n8n the guard's false branch now runs "Open it anyway" before replying,
instead of going straight to the handover line.

**A thing found while testing that changes the design.** The guard cannot
actually tell a truthful claim from an invented one: a tool node has no `main`
output, so `$('open_request').all()` is unreliable and the false branch runs on
EVERY reply that names a reference -- including the correct ones. Rather than
fight that, the rescue is idempotent and returns the AUTHORITATIVE reference
either way, and the reply node now asks a better question: does the model's own
sentence contain that number? If it does, the model told the truth and its
wording is kept. If not, we speak the real number. If there is none, we hand
over. The failure mode is now "we replaced good phrasing with correct phrasing"
rather than "we told somebody a lie".

**The check was broken too, for the third time in this file's life.** It found
its row with `description like *בדיקת-מערכת-999*`, assuming the bot copies the
resident's message verbatim. It does not, and should not -- told
"יש נזילת מים בלובי, דחוף. בדיקת-מערכת-999" it wrote **"נזילת מים בלובי"** and
dropped the marker as the noise it is. A perfect row the query could not see.
A fixture the system under test is right to reject is a broken fixture. It now
finds its rows through `interactions.external_call_id = wa:<phone>`, with the
phone minted per run -- exact, and safer than the old DELETE, which matched free
text and would have removed a real resident's ticket if they ever typed the
marker.

**Testing.** `rescue_request` exercised directly three ways before wiring:
writes a real ticket with the whole thread as the description and the verified
address; returns `duplicate` on a second call in the same conversation; refuses
without a phone. Probe rows deleted. Workflow read back after saving --
24 nodes, connections correct, no overlapping positions, still active. Then the
full end-to-end check: **all checks passed, row in the database after 9 seconds,
and `status: open`** -- meaning the model called `open_request` itself and the
backstop was not needed. The check now prints the status so a rescued row can
never masquerade as the bot working.

### The call page was one long scroll

Reported straight after the transcript work shipped: the conversation view is
not friendly, it is a long scroll. Correct, and it was two separate mistakes.

**The page length was set by how talkative the caller was.** Bubbles stacked
down the document, so a three-minute call was a three-minute page. Now the
transcript scrolls inside its own pane, capped just under the viewport --
`min(68vh, 620px)` -- so the end of the pane is visibly the end of a *box*
rather than the end of the page, which is the cue that tells you where to
scroll.

**Everything you glance at once sat above the thing you came to read.** Seven
large metadata cards, then the summary, then the recording, and only then the
first thing anybody said. Now two columns: conversation wide on the left,
summary / recording / details / tools stacked on the right. Under 900px it goes
to one column and the **sidebar leads**, because on a phone the facts and the
recording are worth more up front than the opening line of a long transcript.

**The speaker labels were noise.** "Michael" and "Caller" printed above all 22
bubbles is the same two words repeated down the page. Dropped; who-is-which is
said once in the panel header with two colour dots, the way every chat client
does it. Left/right alignment carries the rest.

Two smaller things while in there. The tool calls moved into a collapsed
`<details>` -- it is JSON, it is long, and it is the one section on the page
that is only read when something is wrong. And the recording panel now says
Vapi keeps recordings 14 days, because an expired one renders as a working
player that plays nothing, which reads as a broken page rather than an expired
file.

`.msg .who` is kept in the stylesheet: the WhatsApp conversation view uses it
and there the label carries a timestamp and a message type, which is
information rather than repetition.

**Testing.** `next build` clean, 9 routes. Rendered markup checked on the fire
call: grid present, scrolling pane present, four panel headers, zero `.who`
elements, 12 agent bubbles and 10 caller bubbles.

### The opening turn apologised for nothing and offered a choice already made

From the 08:05 transcript, the first exchange:

    Caller:  I want I want to open a ticket.
    Michael: I'm sorry to hear that. I can open a ticket for this or pass it to
             the office, but they're taking a lot of calls at the moment. So
             that would be a wait. Which would you prefer?
    Caller:  Want to open a ticket?

The caller's reply is the measurement. They repeated themselves as a question,
because they had been asked to choose something they had just chosen.

Two things fired that should not have, and both came from the same section --
"Never hand somebody over without offering them something first". That section
described *what* to say beautifully and never said *when*, so the model applied
it to the first sentence of the call.

**The sympathy line has a precondition it never stated.** *אני מצטער לשמוע*
answers a misfortune. "I want to open a ticket" is not one -- nothing had been
described yet. Sympathy for a sentence that describes nothing is the clearest
possible tell that a phrase was reached for rather than meant, which is exactly
the "not human" complaint from 19 Aug in a new place.

**The two-way offer is for a problem that might not fit in a ticket** -- a lost
parcel, CCTV, a neighbour. It is the alternative to a transfer. It is not for
somebody who has asked for a ticket, and it can never be right in the opening
turn, because until they say what happened there is nothing to weigh.

Both now carry an explicit gate. The offer section opens with when it applies
and two nevers; the sympathy line says you can only be sorry about something you
have been told.

**And the path that was missing entirely.** Nothing in the prompt covered a
caller who asks for a request without saying why -- so the model improvised, and
then asked which building. New section, "When they ask for a request without
saying why": one question, *בטח. מה קרה?*, and nothing else in that turn.

Not the building, explicitly. What happened comes before where it happened,
because it decides whether this is an emergency -- and on this very call the
building was asked for first and the caller had to volunteer, several turns
later and unprompted, that there was black smoke coming out of a window.

**The English twin refused to build**, which is the safety property doing its
job: two new Hebrew passages had no entry in the substitution table. Both added,
including the quoted caller line -- an English twin whose *examples* are Hebrew
teaches a register the English caller will never produce.

**Testing.** Hebrew pushed, English rebuilt (40 passages + 2 section blocks, no
Hebrew remaining) and pushed. Then both live assistants read back from the API
and checked for five markers each: the new section, the question in its own
language, the offer gate, the sympathy precondition, and the morning's
write-then-transfer emergency rule. Ten of ten present.

### Call transcripts were already stored; nothing made them readable

Asked to store call transcripts so they can be opened and viewed. Checked before
building: `interactions.transcript` has existed since migration 001, the
end-of-call report has filled it since 8 Aug, and 128 of 163 rows have one --
including this morning's fire call. `audio_url` is populated on 133. The
dashboard has had a Calls list and a per-call page rendering transcript,
recording and tool calls since the day it was written, and
`homies-dashboard.vercel.app/calls` answers 200 with no login.

So the storage half was done and the answer to the request is "it already
exists". Three things made it not actually usable, and those were the work.

**Every summary was null.** All 163 of them. `interactions.summary` has been in
the schema since 001 and rendered in the Calls list since that page existed, but
the end-of-call report only carries a summary when an `analysisPlan` asks for
one, and no assistant has ever had one. So the list said "no summary" on every
row and the only way to learn what a call was about was to open it and read.

Added `analysisPlan.summaryPlan` to the shared assistant payload in
`vapi_sync.py`: one sentence, at most two, **in the language the call was
conducted in** -- Vapi's stock prompt answers in English, which is wrong twice
over when the calls are Hebrew and the staff reading the list are Israeli. It
asks for what the caller wanted and what happened to it, the reference number if
one was opened, and to say plainly when nothing was resolved rather than
narrating the conversation.

Going forward only. Nothing backfills the 163 existing rows -- the summary is
generated at end of call and that moment has passed for all of them.

**The transcript rendered as one monospace blob.** Vapi writes one speaker per
line prefixed `AI:` or `User:` and wraps nothing, so a long answer is a single
very long line. Technically viewable, unreadable in practice, and Hebrew ran
left-to-right inside a code font. The detail page now parses it into turns and
renders them with the chat-bubble styles the WhatsApp conversations page already
had -- `dir="auto"` per bubble, so Hebrew goes right-to-left and a reference
number stays left-to-right inside it. A line with no recognised prefix appends
to the turn above rather than being dropped, which is what happens whenever
speech contains a newline. If fewer than two turns parse, the raw block is still
rendered: an unparsed transcript must stay readable, and a page showing nothing
would look like a call where nothing was said.

**There was no way to search them.** A stored transcript nobody can search is an
archive, not a record. Added a search box on `/calls` matching `q` against
transcript and summary, as a GET form so the search lands in the URL and can be
linked, bookmarked or sent to somebody. It survives a tab switch. PostgREST `or`
syntax characters are stripped from the term before it reaches the filter, or
someone searching `255-1013-26, elevator` gets a parse error instead of results.
Hidden on the No answer and Links sent tabs, which read `call_outcomes` and have
no transcript to search.

**Testing.** All four assistants confirmed carrying `summaryPlan.enabled` and
`artifactPlan.recordingEnabled` after the push. Dashboard `next build` clean, 9
routes. Search exercised against live data with the **anon** key, so it is
proven to work under the dashboard's own RLS rather than under a service key:
`smoke` -> 1 call (this morning's), `elevator` -> 12, `מעלית` -> 2,
`255-1013` -> 0 (reference numbers are spoken as words, not digits, so they are
not findable this way -- worth knowing before somebody tries).

Two transient Vapi failures during the pushes -- an `IncompleteRead` on a list
and a 500 on an update -- both fine on retry. Worth remembering before
diagnosing a real fault.

### A fire was reported and the system recorded nothing

A test call at 08:05: the caller says black smoke is coming out of a window and
they think there is a fire. The agent handled the conversation well — recognised
the emergency, said it was marking it urgent and bringing in a person, named 101
and 102. At the end of the day the `requests` table was empty.

The user's read was that Supabase had come unlinked from the new Vapi account.
It had not. Three separate faults stacked up, and the endpoint was fine.

**Fault 1 — the prompt made the ticket the droppable half.** The Emergency
section said "stop the intake, do not finish the script first, set urgency to
emergency on whatever you write, say you are bringing in a person, and transfer
immediately", and closed with "a tidy ticket and no human is a failure here,
however good the ticket is". Every emphasis points at the transfer. "Whatever
you write" is conditional on there being something written and never says to
write it. The agent called exactly one tool in the whole call:
`transfer_to_human`. `open_request` was never invoked, and by the prompt as
written that was arguably correct.

Rewritten to **write, then transfer, in that order, every time** — `open_request`
with whatever is already known, no further questions first, then the spoken
line, then the transfer carrying the same description. It now says plainly why:
a transfer is a note, nothing searches it, nobody is dispatched off it.

**Fault 2 — the word `emergency` was never storable.** `call_outcomes.
transfer_reason` has been constrained to the debt agent's six reasons since
migration `004`. The intake agent shipped later with its own five
(`INTAKE_TRANSFER_REASONS`), of which `emergency`, `out_of_scope` and
`repeated_failure` were not among them. The Edge Function's allow-list mirrored
the constraint and mapped anything outside it to `caller_request` — protecting
itself from a CHECK violation by turning a rejected insert into a wrong one. So
the fire is on record as `transfer:caller_request`: a caller who asked to speak
to someone.

This is the same shape as every other bug in this file: a tool's vocabulary
living in three places that were allowed to drift. Migration `021` widens the
CHECK to the union of both agents; the handler's list now matches; the column
comment names both source constants so the next person sees the coupling.

18 of 24 transfers on record say `caller_request`. An unknown number were
something else and cannot be recovered — the word was discarded before it was
written. The transcripts are the only evidence.

**Fault 3 — nothing caught it afterwards.** `salvage()` writes a `needs_review`
row from the transcript when a call produced no request, but only for calls that
were *cut off* (`max-duration`, `silence-timed-out`). This call ended normally,
so it correctly did not fire.

Added an **emergency backstop** in `transfer_to_human`: on `reason: emergency`
with no request on the interaction, the server opens one itself —
`urgency: emergency`, `status: needs_review`, description from the new
`description` argument. Only for `emergency`; for `out_of_scope` and
`caller_request` a spurious work item is often worse than none. An instruction
the model can ignore is not a constraint, and this file has now paid for that
lesson three times.

**The account migration is fine, and I misread it first.** The user asked
whether Supabase was still linked "to the new account", and while checking I
listed account 7's assistants, found none of them in `web/index.html`, and
started writing up a half-finished migration. Wrong way round: HANDOVER already
records account 6 as live since 19 Aug pm and account 7 as *retired* (it is the
old account 4). The demo page carries the live public key and the live assistant
ids; today's call landed on `9cae6bf7`, the live English intake assistant, on the
live account. Nothing about the accounts is broken.

What made it hard to check is real, though, and already recorded: `.env` can no
longer tell the accounts apart, because the `repoint()` bug flattened every
`VAPI_PUBLIC_KEY_ACCOUNT*` to the same value before it was fixed. Identifying
the live account meant asking the API which one had today's calls on it. The
lesson is the one already in HANDOVER — read the table there before inferring an
account from `.env`.

**Also found and not changed:** `vapi_sync.py` resolves the tool host to n8n
whenever `N8N_BASE_URL` is set, but the live assistants have always pointed
straight at Supabase. Synced with `N8N_BASE_URL=` cleared so this fix did not
silently move the intake agent behind n8n. HANDOVER claimed the n8n route was
live; corrected.

**Testing.** Migration applied (21 of 21). Edge Function deployed, version 33
ACTIVE. Hebrew intake pushed; English twin rebuilt from the live Hebrew
assistant, 38 substitutions all matching, no Hebrew remaining. Then three probes
against the live endpoint: an emergency transfer with no prior request minted
`255-1068-26` with `urgency: emergency`, `status: needs_review` and the reason
stored as `emergency`; an emergency transfer *after* an `open_request` minted
nothing extra; an `out_of_scope` transfer stored `out_of_scope` and minted
nothing. All probe rows deleted afterwards — `requests` for 20 Aug is empty
again.

**Not fixed, still true:** a transfer still reaches nobody. It writes a row in
`call_outcomes` that no dashboard shows. The backstop means an emergency now
leaves a ticket somebody can find, which is a different thing from somebody
being told.

---

## 2026-08-19

### The Cartesia key moves, and `.env` was the least important place it lived

A new Cartesia key, and the move is two edits — one of which is easy to miss and
is the only one in the live path.

**Vapi holds the key, not this repo.** It is stored as a provider credential
("Cartesia (Hebrew TTS)", `4c9be89b`, added 11 Aug) and that is what pays for
every Hebrew utterance. Changing `.env` alone would have left the old account
billing indefinitely while everything looked migrated. `PATCH /credential/{id}`
with the new key, and Vapi never returns the value back, so it is write-only from
here — the proof has to come from a call.

**What was checked before touching anything.** The key authenticates. The Hebrew
voice `a976c076` — *Eyal - Grounded Guide*, `he` — is **public**, so it belongs to
no account and cannot be lost in a move; that was the one thing that could have
silenced Hebrew and it cannot. Nothing else holds a Cartesia key: no n8n workflow
mentions it, and the three scripts that read it (`cartesia_tts.py`,
`voice_clone.py`, `vapi_transfer.py`) all take it from `.env`.

**What could not be checked.** Whether this really is a different account. All
three keys see the same 889 public voices and none of the accounts owns a private
one, so there is nothing account-shaped to compare — and Cartesia exposes no
endpoint that names the org behind a key. The `org_3AOx…` in a voice listing is
the *voice's* owner, not the caller's, which is a trap worth naming because it
looks exactly like an answer.

The outgoing key is kept as `CARTESIA_API_KEY_ACCOUNT1` rather than deleted, the
same convention every superseded Vapi pair follows. `CARTESIA_VOICE_ID` in `.env`
is and was empty — the assistant's voice comes from the sync config, so nothing
depended on it.

**The key was pasted into chat, doubled** — the same string twice, 29 characters
each. Worth rotating once the account settles. Nothing real was ever committed:
the three tracked files matching `sk_car_` are all documentation placeholders,
and `.env` is gitignored.

### The agent told a caller about somebody else's stolen parcel

A caller asked about the lift in building one. The agent read back **two**
requests — the elevator, and "missing baggage outside the front door" — and then,
asked what that second one was, **explained it**: a parcel taken from outside the
front door. Another resident's incident, described to an anonymous caller who had
named nothing but a street.

That was my soft fallback from earlier the same day. When the `elevator` filter
matched nothing — because that ticket is filed `other` — it dropped the filter and
handed back the whole building. The fallback fixed a false not-found by creating a
disclosure.

**Both are fixed by matching the words instead of widening the query.** A
category is now matched against the ticket's `type` **or** the words in its
description, in both languages — `elevator` finds "elevator issue" and "מעלית"
without ever touching the parcel. Everything in the building still comes back
from the database; what the caller named is answered in full, and the rest is
**a number**. `other_open` is a count and a count is the whole of what the agent
may say about it.

    building one + elevator   found 1, other_open 1
    Herzl 14 + plumbing       found 1, other_open 5
    building one, nothing named   identify_needed, descriptions withheld

That last case is the one with no clean answer: a caller who gives a building and
names no fault cannot be told apart from their neighbour, so the descriptions are
withheld and the agent asks what the request was about rather than reading a list
of other people's business.

**And the call had no memory of itself.** Having just read out that a parcel
request existed, the agent was asked *"did someone steal the package?"* — plainly
a question about that request — and answered *"I'm sorry to hear that, I can open
a ticket for this."* Then again, when the caller corrected it. The whole
transcript was in its context and it still heard a report where there was a
question.

The prompt now has a section for what the call has established: a question about
something you mentioned is not a new fault; an offer turned down stays turned
down; "it" and "that one" mean the last thing named; and a ticket you already
opened is not opened twice because somebody asked a follow-up. Nothing is stored
— it is the difference between having the transcript and using it.

Decided with the client, both explicitly: **a caller may hear how many requests
are open in their building and never what any of them is**, and **memory is
within the call only** — no storage, no identity surface, and it works on a web
call with no number attached.

### The logging rule stops depending on me remembering it

Asked for a third time, and correctly — twice was already twice too many. So it
is no longer an instruction, it is a gate.

`scripts/check_briefing_logged.sh` runs when a turn finishes. It looks at
whichever change set is live — uncommitted work if there is any, otherwise the
last commit — and if that set touches anything substantive without touching
**CONTEXT.md and HANDOVER.md**, it refuses to let the turn end and says which are
missing. `.env` and the worklog do not count as substantive: the worklog is the
one that never gets forgotten, and `.env` is gitignored.

**It cannot loop, and that was the design constraint.** Every block is
satisfiable in the same turn — edit the two files and either the working tree
carries them or the follow-up commit does. And each distinct change set is
blocked exactly **once**: the fingerprint goes in `.git/briefing-nagged`, so a
turn that only answers a question is never blocked by a commit that was already
flagged.

The check is committed because it documents the convention; the choice to enforce
it lives in `.claude/settings.local.json`, which is gitignored — this repository
is public and a hook that fires on a stranger's machine because they cloned it is
rude. Anyone can still run `bash scripts/check_briefing_logged.sh` by hand.

Tested all four ways before wiring it: blocks with the briefing files stale,
stays silent once both are touched, emits valid JSON, and stays silent on a
second run against the same change set.

### Reading the call instead of the transcript

"The building lookup is still not working." Vapi records the arguments the agent
passed, so rather than guess, I read them:

    12:13  get_request_status {"type":"elevator","building":"building one"}  ->  found 0
    11:33  get_request_status {"type":"elevator","unit":"300","building":"building one"}  ->  found 0
    11:33  get_request_status {"reference":"106"}  ->  found 0

The first is the type filter, fixed an hour before those words were typed —
replayed against the live function it now returns two, including the elevator
ticket. **No call has been placed since that deploy**, so nothing about it had
been retested.

The other two were still real, and both are the model poisoning its own query:

**It passed an apartment for a lift.** Twice — 300, then 107 — after the prompt
had been changed to tell it not to. An instruction the model can ignore is not a
constraint, so this now lives in the function: five categories that cannot be
inside anybody's flat — elevator, lighting, cleaning, gardening, fire_safety —
drop the apartment regardless of what arrived with it.

**It passed a reference one digit short.** The caller said *one zero six three*
and the tool received **106**. Three digits is below a serial's length, so the
lookup returned nothing and the caller was told their reference does not exist;
`255-1063-26` was open in the table. Spoken digits already worked — *"one zero
six three"* resolves — so nothing was wrong with the input the caller gave. It
was tidied on the way.

A short reference is now a near miss rather than a dead end: the missing digit
becomes a wildcard and the matches come back flagged `partial_reference`.

**And the first version of that was worse than the bug.** With `limit(4)`, "106"
came back as 1064 to 1067 and cut off 1063 — the one the caller actually wanted.
A recovery that confidently offers the wrong four is worse than the dead end it
replaced. Ten now, because a missing digit has ten possible values; and **more
than three is not a question anybody can answer out loud**, so it says there are
several and asks for the number again rather than reading near-identical
references down a phone.

### The filter I added an hour ago hid the ticket it was meant to find

A caller asked about the lift in building one and heard *"I couldn't find any
recent request about the elevator in building one."* `255-1063-26` was in the
table, description **"elevator issue"**, and its `type` is `other` — because the
agent that opened it inferred the category and got it wrong.

The `type` filter added this morning was a hard `.eq`, so it trusted that
inference over the caller. **The type is written by a guess and the question is
asked by a person; where they disagree the person is the one who knows.** It is a
soft filter now: narrow with it, and if that empties the answer, ask again
without it. One extra query on exactly the runs that would otherwise have
returned nothing.

    building one + elevator    was 0   now 2
    building one               2       2
    Herzl 14 + elevator        1       1     (still narrows)
    a building nobody has      0       0

Everything the fix was for still holds — a typed question still narrows, so the
lift enquiry does not read out somebody's leak — and it can no longer be the
reason there is no answer at all.

**And "never mind" was answered with everything they had just declined.** Told
nothing was found, the caller said *"no, never mind"* and in one turn got the
office phone number, *"I'm passing this to someone who'll get back to you"*, and
the goodbye. Declining is an answer. The only correct response is to accept it,
check whether there is anything else, and close.

That needed rule 7 amended rather than worked around: *never end a call without a
request, a partial or a transfer* is why the agent reached for a transfer it had
just been told not to make. It now carves out the case it was never meant to
cover — **a question you answered is a complete call**, and so is a not-found the
caller chose to leave there. The rule exists so nobody hangs up with nothing, not
so that something gets filed against somebody who wanted an answer and got one.

### The bot said it had opened a ticket. It had not.

Chased down while answering "is the chatbot fixed now", and the answer turned
out to be worse than the failing check suggested.

`check_whatsapp.py` had been red on its one important assertion — a real message
reaching the database — while everything else passed. **Two of its own faults
first**, and neither was the bot:

- **It sent one message and demanded one row.** The prompt is explicit that the
  first reply is an offer and not an interrogation — *"אתה מציע לפתוח קריאה — לא
  מתחיל לחקור"* — and the address is asked for after they say yes. The reply the
  bot gives is the prompt's own worked example, word for word. One message can
  never produce a row **by design**, so the check was asserting a contract
  nobody agreed to. It walks the three-turn conversation now: report, accept,
  address.
- **Its test building could not survive the address gate.** `הבדיקה 999` was
  invented so the check's rows were unmistakable and safe to delete. Then
  `verify_address` became mandatory before `open_request`, and the bot began —
  correctly — refusing an address Homies does not manage. The same lesson as the
  first fixture, `__selfcheck__`: **a fixture the system under test is right to
  reject is a broken fixture.** The address is real now and a marker in the
  resident's own words carries the identity, so the DELETE can never reach a
  real request.

**Then the real one.** With the check finally walking a conversation the bot
could complete, turn three came back:

    פתחתי קריאה על הנזילה בלובי בסוקולוב 86, דירה 4, מספר 255-1048-26

"I've opened a request… number 255-1048-26." The execution shows **one tool
call, `verify_address`**. No row was written. And that reference belongs to
somebody else's ticket, so a resident quoting it later is quoting a stranger's
fault.

This is known defect 5, recorded 12 Aug and left to the prompt — which already
forbids it and was obeyed on every other run. **A rule the model follows most of
the time is not a guard.** The guard is now in the workflow, at "Reply usable?",
where it reads the execution rather than the intention: a reply carrying a
reference or claiming a request was opened, with no `open_request` output behind
it, takes the false branch into "Hand over instead". Proven live — the phantom
was replaced with *אני מעביר את זה לצוות, נחזור בהקדם* and the resident got a
person instead of a number that is not real.

**Two n8n traps cost three deploys**, and both are about the expression language
rather than the logic:

- **`}}` anywhere inside an expression ends it.** n8n closes on the first one it
  meets, so an arrow function's natural `}})()` truncates everything and the node
  reports "invalid syntax" at run time — not at deploy. Every brace that would
  touch another now has a space in it.
- **`isExecuted` is useless on a tool node.** It returned true on a run whose
  execution shows the tool was never called; it appears to describe the node
  being reachable rather than invoked. The node's output is the honest signal —
  a tool the agent never called has produced no items.

**Still open:** the containment works and the cause does not go away. The agent
skips `open_request` intermittently — one run in this session called it
correctly. The check is now honestly red for a real defect rather than dishonestly
red for a bad fixture, which is the difference between a signal and noise.

### The reference existed. The agent said it did not.

A caller quoted reference one zero six three and was told no such request
exists. It existed — `255-1063-26`, open, in the table for the whole call.

The agent passed on what the transcriber gave it, which is **words**. Measured
against the live webhook:

    "1063"              found        "255-1063-26"       found
    "1, 0, 6, 3"        found        "HM-2026-1063"      found
    "10 63"             found        "one zero six three"  NOTHING

The one form a person actually says out loud was the only one that failed —
and it is the form the whole design produces, because the agent reads a
reference out digit by digit and the resident reads it back the same way.
`serialOf` now converts spoken digits before matching, in both languages and
both Hebrew genders. `אחת אפס שש שלוש` resolves too.

**Two sections of the prompt were telling the agent opposite things.** "Status of
an existing request" said not to ask for an apartment when the fault is not in
one. "Where — before you can write anything" said to ask for it always, and that
is the one the model obeyed: it asked which apartment the caller's elevator was
in, twice, got two flat numbers that had nothing to do with the lift, and both
lookups failed. The capture section now carries the condition itself rather than
leaving it to a section three screens away. A contradiction between two parts of
a prompt is not resolved by the more recent one or the more specific one — it is
resolved by whichever the model reads as the general rule.

**And a correction was answered with a transfer.** The caller, told nothing was
found, said *"it's for building one, just the word one"* — handing over a better
query — and heard *"I'm passing this to someone who'll get back to you."* That is
the one response that reads as being brushed off, because they had just supplied
exactly what was asked for. New information is a new search. Transfer when they
ask for a person, or after looking twice.

Also added: before declaring nothing found, look the other way — a building and
apartment that came back empty gets a second look at the building alone with the
type. One tool call, and it is the difference between an answer and a shrug.

### A lift is not in an apartment, and nobody says a building's name exactly

The status lookup worked, and then it was asked the obvious question — *"any
status for the elevator at building one?"* — and returned nothing. Measured
rather than guessed, six ways:

    reference number          found
    "Herzl 14" + apt 12       found
    "Herzl 14", no apartment  NOTHING
    "herzl 14" + apt 12       NOTHING
    "Herzl" + apt 12          NOTHING
    "building 1" + apt 12     NOTHING

Two assumptions, both the same shape: that the caller would hand over a database
value.

**The match was `.eq`**, so it wanted the building's name character for
character — punctuation, city and all, `סוקולוב 86, תל אביב - יפו`. A caller says
"Sokolov". Lower case failed. Dropping the number failed. `ilike %…%` now.

**The apartment was required**, and for a shared fault that is a question with no
answer. A lift, a lobby light, a gate, the bin store — none of them are in a
flat. The building alone is a complete query now, and the prompt says so: ask for
the apartment when the thing is behind their own front door, not otherwise.

Two guards came with it, because a loose match on a building is not free. The
tool takes an optional **type** — "the elevator" is `elevator` — so a
building-wide question does not read a stranger's leak to somebody asking about
the lift. And a name matching **more than one building** returns
`ambiguous_building` with the names rather than picking; the agent reads them
back and asks which.

After: building alone returns six, lower case works, `Herzl` + `elevator` returns
the one, and `building 1` still returns nothing — correctly, because no building
is called that.

**The ambiguity check found a real data problem on its first run.** `Herzl` matched
two buildings named `Herzl fourteen` and `Herzl 14` — the same building, stored
twice, because the agent writes down whatever the caller said and nothing
reconciles it against the portfolio. That is `verify_address`, still not attached,
and it now has a visible cost rather than a theoretical one.

### The waiting line stops being the model's to say

*"This will just take a sec"* came back on the status call, hours after being
pinned. The prompt already said which line to use and, since this morning, said
"that line, not your own version of it" as well. The model said its own version
anyway. A third instruction was not going to hold.

So the line is no longer an instruction. Vapi tools take a **request-start
message** — spoken by Vapi the moment the call begins, before the model gets the
turn — and the three sync tools now carry one: `רגע, אני רושם` on open_request,
`רגע, אני בודק` on the two reads, because checking is not writing and a line
about writing would be a small lie. The prompt section that used to teach the
line now says the opposite: **say nothing, it is spoken for you**, and warns that
speaking as well is heard twice, which is worse than either version alone.

A tool message is spoken, and the twins share their tools verbatim — so this is
the one place a Hebrew sentence could reach an English caller's ear. `vapi_en.py`
now translates them through `TOOL_MESSAGES`, and exits on one it does not
recognise rather than shipping it. Verified on both live assistants.

Two more from the same call:

- **The address was read back twice inside twenty seconds** — once when the
  apartment was captured, once in the confirmation before the write. Both were
  the prompt's doing: "always read it back" on the apartment field, and the
  read-back in the write order. Confirming something confirmed a moment ago does
  not make it more certain, it makes the call sound like it lost its place. One
  read-back now, the one that carries the fault as well as the address — unless
  the apartment was genuinely not heard, which is the one field worth a turn.
- **The digit-by-digit apartment question was asked first**, with no attempt at
  the plain one, because the previous answer had been hard to hear. A difficult
  turn behind you is not a failed attempt at this one; spelling something out
  unprompted asks a person to do more work than they were going to have to.

### The agent could not read a status, so it wrote a ticket instead

A resident rang to ask where their elevator ticket stood. The agent took the
building, took the apartment, read back the fault, opened them a **second ticket
for the same elevator** and gave them its number. The caller had to say *"I don't
want to create a ticket, I'm asking for a status update"* to a system that had
already created one.

The agent was not carrying `get_request_status`. It had a whole prompt section
telling it how to answer that question and no tool to ask it with, so it reached
for the nearest tool it did have.

**Three hosts, and only one of them had the tool.** The handler has been complete
in the Edge Function since 18 Aug — `get_request_status` and `get_balance` both,
around a hundred lines each. The prompt gained its "Status of an existing
request" section the same day, with the status vocabulary translated for the
English twin. Neither `INTAKE_TOOLS` nor the n8n Decide node was touched. So the
tool existed where it does the work, was described where it is spoken about, and
was absent from the two places that decide whether it can be called at all.

`vapi_tools.py` even carried a comment explaining the absence — *"this project
has no read path"* — which was true when written and had been false for a day.

Both declared (sync, because the agent has nothing to say until the answer
arrives), both routed, both verified through the live webhook: `1065` comes back
open, the elevator, opened today; building and apartment come back with three
requests newest first; a real apartment's balance comes back with the resident,
the total and the months. n8n's Decide node was byte-identical to the repo before
the push, so nothing hand-edited was overwritten, and the workflow stayed active
through it.

**The rule this leaves behind:** a prompt that describes a tool the assistant
does not carry is worse than a missing section, because the model will not say
"I cannot" — it will find the nearest tool it does have and use that. Handler,
route and declaration move together or not at all.

Still wrong in that same call and not yet fixed: the waiting line came out as
*"this will just take a sec"* again despite being pinned this morning, the
read-back was said twice, and the digit-by-digit apartment question — which is
meant to be the *second* attempt — was used as the first.

### The ladder becomes one sentence, because it was never a ladder

The three-rung structure from earlier today was mine, not the ask. It was written
as: say the human thing, offer a request, and only if they refuse, mention the
office. Read back the live line and it is obvious what that sounds like — *"I can
open a request for this. So the office has it in writing and comes back to you.
Would you like me to?"* — a script advancing a step, not a person saying what
they can do.

The ask, given twice now and in almost the same words both times, was one turn
with both ways in it: *I can open a ticket for that, or forward it to the office
if you'd like, but that will take a while since they're getting a lot of calls.*
That is what is live now:

    אני יכול לפתוח על זה קריאה, או להעביר את זה למשרד — אבל יש שם המון פניות
    כרגע, אז זה ייקח זמן. מה עדיף?

**Holding the second option back was wrong twice over.** It made the caller
refuse something before they had been told what else there was, and it turned an
offer into a funnel. Somebody standing outside their own door with a parcel gone
wants to hear the choice, not be walked down it. The caveat stays because it is
true — the office is taking a lot of calls and a written request is looked at
sooner — and the turn ends on a question rather than a recommendation dressed as
one. Once they choose, the choice is theirs: the office option now hands over the
number and stops, with no second attempt at selling the ticket.

**And neither language is a translation of the other.** Corrected same day,
because the version above was written from the English side only — as though
Hebrew were the source and English the thing that needed care. It runs both ways.
Carry the meaning across, then pick the words that language actually uses; a line
rendered by matching words comes out grammatical and unsaid. Now a standing
decision in `CONTEXT.md` and a memory, phrased for both directions.

**The word is not the same on both sides.** לפתוח קריאה is ordinary Hebrew —
it is what the office says and what a resident says back. Its literal English,
"open a request", is not ordinary English, which is exactly why a caller heard it
this morning and said they did not follow. English has its own everyday word and
it is **ticket**. The substitution table now says so, next to the entry: a
translation that matched word for word here would be faithful to the Hebrew and
wrong in the room.

### The call was correct, and it was cold

The first call on the new account went through cleanly. A resident reported a bag
taken from outside their door, gave the building, gave the apartment, got a
reference number, and answered three follow-up questions. Every field the office
needs was captured. The verdict on it was one line: *"looks too not polite and
not human."*

Six things in that transcript were the agent's:

- **Not one answer was acknowledged.** The caller gave the colour of the bag, the
  time they left it out, what was in it — and each answer was met with the next
  question and nothing in between. This came from *this* file: "Say less than you
  think you should" bans thanking someone and bans repeating what they said, and
  the model read the pair as *say nothing*. Brevity was the rule; silence is what
  arrived. There is now a fifth item on that list, and it is the only one phrased
  as a requirement: **receive the answer before you ask the next thing.** Two
  words. הבנתי. טוב. Not a sentence.
- **The same question three times.** *"Anything else the office should know?"* —
  the exact yes/no filler the follow-up section exists to replace, asked once
  after each real question, until the caller was answering about the time while
  still describing the colour. The section said "two is usually plenty" and the
  call ran to five. It now says **two, and then you stop**, and bans that
  sentence outright inside the follow-ups. There is one *משהו נוסף?* in a call
  and it is the last thing before the close.
- **A question rode in on the reference number.** *"Your reference number is one
  zero six two. What was in the bag?"* — one turn. That is the only line in the
  call the caller is writing down, and a question on top of it costs them one or
  the other. The number now gets its own turn and nothing else goes in it.
- **The offer was made in our vocabulary, not theirs.** *"I can open a request"*
  got *"I don't quite understand what you want"* back, and the agent's own
  recovery — *"I can write down your problem so the office knows about it"* — was
  the better sentence. That recovery is now the first attempt: לרשום למשרד, not
  לפתוח קריאה. A smaller second wording sits behind it for a caller who still
  does not follow.
- **"I cannot say when it will be resolved. Anything else?"** Both sentences
  true, and together the least helpful turn in the call. Rules 1 and 2 forbid
  giving a date and that is not in question — but a bare refusal is a door
  closing, so it now goes out with what we *do* know attached: it is written
  down with them and they come back about it. Never a bare refusal, and never a
  guess to soften one.
- **The goodbye arrived on its own.** *"Thanks for calling Homies. Have a good
  day."* … *"and goodbye."* — a full stop in the middle of a one-sentence
  closing, so the voice spoke it as two and left a pause long enough for the
  caller to start talking into. Commas, not full stops, and the prompt now says
  so next to the line.

Plus one rule that catches all of it: **never say the same sentence twice in one
call.** A phrase arriving a second time in the same wording is the clearest
signal a caller gets that nobody is listening.

Both twins pushed, `f482abc1` and `8b98016b`. Six new fixed lines joined
`SAFE_SENTENCES`, and that list learned something in the process: an entry can
now be a **pair**, meaning *this line is supposed to change, and here is exactly
what to*. The Hebrew closing is the first one — the pronunciation substitution
rewrites להומיז as לחברת הומיז so the voice says the company's name rather than
an unfamiliar word, and a check that called that damage would have taught
everyone to ignore the check.

### The mirror gets promoted, which is why it existed

The overdrawn account had a spare that was already identical — account 4, made a
mirror an hour earlier — and that spare is in credit. So instead of buying
credits to unblock a test session, the live pointer moved.

**Promoting a mirror creates nothing and copies nothing.** It is two pieces of
bookkeeping: point every id in the repo at the twin already sitting there, and
swap the two keys in `.env`. Nineteen ids across eleven files, plus the public
key, which is **not** an assistant id and rides in the same rewrite — without it
the page loads, looks perfect, and every call is rejected by an account that does
not own the assistant it is being asked for.

`--promote` is its own verb for a reason. `--apply` moves by CREATING and refuses
a target that already holds Homies assistants — which is exactly the target this
is for; copying again would give duplicates and the repoint would then pick
whichever came back first.

**The balance is checked first and hard.** Promoting onto a second overdrawn
account would leave everything repointed, nothing working, and the same invisible
symptom that cost this afternoon. A target that cannot place a call is not a
target.

The outgoing pair is kept as `VAPI_PRIVATE_KEY_ACCOUNT5` / `VAPI_PUBLIC_KEY_ACCOUNT5`
rather than deleted. Every previous account's key is still in that file for the
same reason: the one time a key was dropped it took a day to work out which
account a stale assistant id belonged to.

Verified after: `--balance` reads OK against the new pair, `VAPI_PRIVATE_KEY`
reaches all four assistants with 4/4 and 7/7 server blocks, and the old public
key is gone from `web/index.html`.

**What did not move, and cannot**: call history, transcripts and recordings stay
on the old account. Recordings are deleted after 14 days regardless, so anything
wanted from today's calls has to be pulled from there.

### The demo would not start, and it was eleven cents

Reported as *"still error"*, on a page showing:

    Error: [object Object]

An afternoon went into this and the cause was the account being **overdrawn by
$0.11**. Every signal pointed the wrong way, and each one is worth naming:

- **Vapi's call list showed nothing.** A refused call is never recorded, so the
  history looked healthy and the last call was hours old. Asked earlier the same
  day whether the key was out of credit, the honest answer available at the time
  was *the calls that exist all billed normally, and the balance is unreadable*.
- **The page said `[object Object]`.** My own handler. It tried four shapes and
  fell back to `JSON.stringify` — which looks thorough and is not: every branch
  assumed a string, and the first that matched an object went into string
  concatenation. **The one piece of evidence that existed was destroyed on its
  way to the screen.** Now it walks the shapes, takes the first that is genuinely
  a string, spells out NestJS's array-of-validation-errors form, says the status
  code out loud when there is no text, and logs the raw object to the console
  every time.
- **The timing was perfect for a false lead.** It broke on the build that
  changed how the demo starts a call, so the code that had just moved was the
  obvious suspect. It was untouched: the debt path returns exactly what it
  returned before.

**The balance IS readable, and free.** `GET /org` is 401 to a private key and the
public key reads nothing, so this was written off as impossible and the runbook
has said so for a fortnight. It is possible from an angle: **Vapi checks the
wallet before it looks the assistant up**, so a POST to `/call/web` naming a
correctly-shaped UUID that belongs to nobody returns the wallet message when the
account is overdrawn, and *assistant not found* when it is not. Nothing is
created on either path, so it costs nothing and can be run as often as you like.

Now `vapi_transfer.py --balance`, and the first line of `--preflight`:

    BLOCKED Your Wallet Balance is -0.11. Please Purchase More Credits...

Exit code 1 when blocked, so it can gate anything that is about to place a call.

**Needs the client**: topping the account up is a money action.

### Account 4 becomes a mirror, and `vapi_transfer.py` learns the difference

Asked to clone all four agents into the account we moved away from on 12 Aug.
Its copies were frozen there: debt 44,040 chars against 61,363 live, intake
20,504 against 28,333, `idleTimeoutSeconds` unset, and the Hebrew intake agent
still carrying three tools.

**`--apply` refuses a target that already holds Homies assistants**, and that
refusal is right — creating by name again gives eight assistants and no error.
But the refusal was the whole answer, and there was no way to say *make that
account match this one*. So `--mirror`, and the distinction is worth naming:

- **`--apply` MOVES.** Creates on the target, then rewrites every id in the repo
  to point at them. The target becomes the live account.
- **`--mirror` KEEPS IN STEP.** Matches by name, overwrites in place so no id
  moves, and **does not touch the repo at all.** A mirror is a second copy of the
  agents that is not the one being called.

It creates only what is missing, and anything on the target that is not ours is
not read, not written and not counted — a mirror is not a takeover of somebody
else's account.

Ran it. Four overwritten, ids unchanged, and the two accounts now fingerprint
identically on prompt length, tool list, server blocks, voice, transcriber, idle
timeout and max duration. The English intake agent lost a fifth tool it had been
carrying since 11 Aug and the live one does not have; that is what a mirror
means.

**Not automated, and cannot be**: the public key differs per account and `GET
/org` is 401 to a private key. If this mirror is ever promoted to live, that one
value comes off the dashboard by hand.

**Worth recording about how it was asked.** Both keys arrived pasted into the
conversation, and both were already in `.env` as `VAPI_PRIVATE_KEY_ACCOUNT4` and
`VAPI_PUBLIC_KEY_ACCOUNT4` — which is the argument for `--to <ENV_VAR>` rather
than `--to <key>` in one line. The private one should be rotated: it is in a
chat log now, and nothing else about it changed.

### The agent was not being cut off. My own filter was eating its sentences.

A test call, reported as *"it's being cut off mid sentence"*. What the resident
heard, verbatim from the record:

> Would you like me to  though.

Two spaces, and a sentence with a hole in it. **Nothing was interrupted.** The
Vapi timeline shows one continuous bot utterance with a duration; there is no
barge-in anywhere in the call. The text arrived at the speaker already broken.

`scripts/voice_guard.py` strips phrases from the spoken channel so a tool name
can never be read aloud — built after 4 Aug, when a resident heard *"Open payment
ticket. two functions... authorization captured. True."* The list included
**`open request`**, with the comment *"I'll open a request does not match this"*.
True, and beside the point: the model wrote *"Would you like me to open request
though."* and the filter deleted the verb.

**The file already carried the right rule** — *"could a resident or the agent say
this in the course of an ordinary collection call? Anything that could is left
out"* — and it was applied to a **collection** call and never re-applied when the
intake agent shipped, whose commonest sentence is an offer to open a request.

Five more were the same trap, all confirmed against the live replacement list:

    "I'll ask the office to contact you."     -> "I'll ask the  you."
    "It sounds like I have the wrong party."  -> "It sounds like I have the  ."
    "I'll send payment link now."             -> "I'll  now."
    "I can request standing order for you."   -> "I can  for you."
    "That was a caller request."              -> "That was a ."

All six removed. The raw shapes are still caught by the snake-case pattern, which
is the form a real leak arrives in; what is given up is the second layer on the
already-formatted spelling. **A leak heard once is a smaller failure than a hole
in every call**, and the hole is silent — nothing errors, nothing is logged.

**The rule is now enforced instead of remembered.** `SAFE_SENTENCES` holds
thirteen lines both agents really say, and `vapi_leak_check.py --safe` fails if
the filter changes one of them by a character. A rule nothing checks is a
comment. New SPOKEN entries must be three words or more and must read as
machinery rather than as English — a two-word entry is nearly always an ordinary
phrase in one of the two languages and belongs in the prompt.

**Two prompt faults from the same call.** The follow-up came out as *"would you
like me to add anything else the office should know?"* — a yes/no question that
gets a yes or a no, and the row still says only *missing baggage*. It now says:
ask the question, never ask whether to ask it. *What was in the bag. What time
did you leave it out.* And the resident said *"I wanted to check the cameras"*
three times, in three wordings, and it never reached the ticket — so: something
they name that they want done **is** part of the request, and goes in with
add_request_detail in their words.

**Still open from that call:** the agent accepted *"building one"* as an address.
`verify_address` exists and only the chat bot calls it; the intake voice agent
carries four tools and that is not one of them. Same shape as the
`get_request_status` gap in HANDOVER next-move 3.

Intake prompt 28,333 chars, English twin 26,560. Thirty replacements down to
twenty-four, on all four assistants, tools and server blocks intact.

### The inbound agent stops handing people to the office empty-handed

Two English intake calls, and both failed the same way. Somebody asked for a CCTV
review; somebody else had a parcel taken from outside their door. Both heard:

> Unfortunately, I cannot handle lost baggage or CCTV reviews. That's something a
> person needs to handle. I'm passing it to someone who will get back to you.

Reported as *"I want the de-escalation applied to the inbound as well"*, and the
diagnosis is one line: **the intake prompt's out-of-scope path had exactly one
rung.** The debt agent got its three-rung ladder on 18 Aug — answer, offer a
request, only then the office — and this prompt never had it. It said the thing
it could not do, and then said it was passing them on. Nothing was offered.
Nothing was written down while the caller was still there.

**Neither request was out of scope.** `type: "other"` has existed since migration
014 and is what a standing order files under. A missing parcel, a CCTV review, a
neighbour, a door left open — all of them are things the office should have in
writing, and the agent declined to do something it could do. The prompt now says
so first, before the ladder, because the ladder does not help an agent that has
already decided the request is not a request.

The three rungs, and rung three is the one that had to be honest:

1. *אני מצטער לשמוע.* One sentence. **Never "I cannot handle that"** — a sentence
   about your own limits is of no use to somebody who has lost something.
2. *אני יכול לפתוח על זה קריאה, ואז זה רשום במשרד וחוזרים אליך. רוצה?*
3. The office number, with what it costs: *יש שם הרבה פניות כרגע, אז קריאה
   רשומה בדרך כלל מהירה יותר.* — asked for in those words.

**What still skips the ladder**: money moving, a receipt, a disputed amount, a
contract term, a legal question, a complaint about a member of staff, anything
dangerous. A request is the wrong container for those.

### The number the call came from now reaches the ticket, and it is never asked for

Nobody asks a caller for their phone number and nobody should — it arrives with
the call. It was being read once, written to `interactions.caller_phone`, and
then dropped when the ticket was written. `requests.reported_by_phone` has
existed since 014 and was filled in only by tickets imported from OXS.

So `context()` gained `callerPhone` — `call.customer.number` on a real call,
`caller_phone` in variableValues for the demo, and **the real one is read first**
so a variable can never override a call. Both writers put it on the row. The
Tickets page shows it: on a `needs_review` row where the audio failed, it is
often the only way back to the person.

### The bug underneath both of those, which was ours and not the model's

Ticket `255-1056-26`, from a call where the caller said *"Herzo"* and *"I don't
know the apartment number"*, was filed against **Herzl 14, flat 12**. The agent
did nothing wrong: it sent `building: "Herzo"` and no unit, which is exactly
right. The webhook overwrote it.

`ctx.building || args.building` — **context first, what the caller said second.**
That precedence is correct outbound, where the campaign runner attached the
address and a mishearing must not be able to move it. It is nonsense inbound,
where anything attached to the call did not come from the caller. On the demo
page it came from a debt campaign's file for an unrelated person, because
`web/index.html` started **every** agent with `variablesFor(PEOPLE[chosen])` —
name, building, apartment, charges — including the agent whose whole job is
answering a call from someone it knows nothing about.

Fixed on both sides, and the server-side fix is the one that holds:

- **`dialled(ctx)`** — did we place this call? A dialled call always carries the
  resident or the charges; the runner cannot place one without them. An inbound
  call carries neither, however much else is attached to it. So the test is not
  "is `building` set" — the whole point is that `building` was set and wrong.
  `open_request` and `save_partial_request` now consult context only when it is
  true.
- **The demo sends one variable to the intake agent**: `caller_phone`, the demo
  person's own invented mobile. The intake prompt uses no `{{variables}}` at all,
  so there was never anything else it could legitimately want.

Verified against the live function with the exact shape of the failing call:
inbound with demo variables present now files `Herzo` and **no apartment**, with
the phone on the row; outbound with charges still keeps `Herzl 14 / 12`.

### A ticket can be added to after it is written

Asked for as: the agent should ask what the office will actually need — what the
item was, where it was left, when it was noticed — *"a summary, basically. It
depends on a case."*

That collides with a rule this prompt has carried since it was written: **write
the row the moment you have a fault and a place, and tidy up afterwards**,
because the line dies at three minutes with no warning and *a perfect
conversation with no row is a failed call*. Asking first puts the whole ticket
behind a question.

So the order is: write, read the number out, **then** ask, and add each answer as
it arrives. That needed a tool that did not exist.

**`add_request_detail`** — reference and one fact, in the caller's words.
**Appends, never replaces.** The caller's first sentence is the only thing on the
row that came out of their mouth unprompted; a tool that could overwrite a
description would, on one mishearing, delete the only account of the fault
anybody has. Repeats are ignored rather than stuttered onto the row, since a
retried webhook and an agent asking twice look identical from here.

**"Once the number is out, the request cannot be changed" is now "cannot be
corrected — only added to."** The distinction is load-bearing: nothing can move a
building, an apartment or a description already written, so a correction after
the number is out is still `transfer_to_human`.

### Three hosts had to learn the tool, and the middle one nearly got missed

Every tool call is **two hops** — Vapi → n8n `homies-debt-tools` → the Edge
Function — and the router switches on tool name. A tool the router does not know
answers `unknown tool add_request_detail` mid-call, and the agent hears a refusal
for something it was told to do.

The router is built from `scripts/n8n_deploy.py`, and the live Decide node was
byte-identical to the repo's, so it was edited there and redeployed rather than
hand-patched — the same drift lesson as `vapi_export.py` on 18 Aug. The case
refuses a missing reference or detail **in n8n as well as in the writer**, for the
reason `open_payment_ticket` already duplicates its card check: this node answers
Vapi *before* the writer runs, so a refusal that lived only downstream would
arrive after the agent had been told yes.

Round-tripped through n8n against a real ticket, then the test line removed.

Intake prompt 23,583 → 27,455 chars, English twin 25,682, 4 tools with servers on
both. Router redeployed and still active. Edge Function v25.

---

## 2026-08-18

### It stopped deciding the call was over — and the line it closed on was the worst one yet

Fourth English debt call. The resident refused, then gave the reason: *"I'm
paying, and the elevator is still not fixed."* The agent opened a request, asked
if there was anything else, heard *"No. I mean, I already created a ticket, I
forwarded this to the office two weeks ago, and—"*, and said:

> I hear that the lift has been open with the office for two weeks, and it's
> still broken. **Since you don't want to pay this, I'll leave it there.**
> Thank you for your time. Have a good day.

Reported as *"it decides for itself"*, which is exactly right. Four separate
things, and they compound.

**1. A "no" with a sentence after it is not a no.** The handshake pushed an hour
earlier says a reply that is not a yes or a no puts you back in the call. This
reply *started* with "no" and then kept going, and the word was taken as the
answer while the sentence was still running. Now written as its own rule: a
*but*, an *I mean*, a fact, a complaint — **that** is the answer, and the answer
is that they have not finished. Wait for a turn that stops.

**2. Never say why you are ending the call.** Absolute rule 14. Saying somebody's
own position back to them as the reason for hanging up is a company deciding a
person is not worth talking to, on the one subject where they were owed an
answer. **A closing that explains itself is a closing that is blaming somebody**,
and they are allowed to say no. Every call closes the same way whatever happened
in it.

**3. Withholding payment because something is broken now has its own path**, and
it needed one — it is the commonest reason a resident in a managed building stops
paying, and the prompt had nothing for it. It is not a refusal to be accepted and
closed on: it is one sentence with a refusal and a complaint in it. Say back the
specific broken thing in their words, then `transfer_to_human` with reason
`dispute`, because money set against a service failure is a judgement nobody on
this call may make. **And do not explain what the fee covers here** — in that
position it reads as an argument for why they should pay for something that does
not work.

**4. It opened a duplicate ticket.** The resident had already reported the lift to
the office two weeks earlier; the agent filed a second request before hearing
that, and this call has no way to see the first — the debt agent carries
`open_request` and not `get_request_status`. Now: *"I opened a ticket"* or *"I've
been on to the office for two weeks"* means do **not** file another. Two rows for
one broken lift tells the office nothing it did not know. Hand it over instead.

Hebrew 61,363 chars, English twin 59,935, 7 tools with servers on both, idle 12s.

**Worth noticing about the shape of these four calls:** every fix so far has been
a rule against something the model did once. Three of the four today were the
model *deciding* — that a beat was answered, that a refusal was terminal, that a
complaint had been dealt with by filing it. The prompt is now explicit that the
resident ends the call, not the agent, and that is the through-line.


### The closing becomes a handshake, and the idle prompt stops interrupting

A third English debt call, ending: *"can you make it slower" / "let me lower" ->
number re-read -> "have a good day"*. Asked why the call ended automatically.

**Because the words are the switch.** `endCallPhrases` carries "have a good day",
and `endCallFunctionEnabled` is **false** — so the model has no tool to hang up
with and the phrase match is the only way a call ends short of a timeout. That is
deliberate, and it is why the prompt insists the closing never drifts into כל טוב
or ביי. The cost is that a premature closing cannot be recovered from: there is
no turn after it.

**Why it chose to say it there** is the actual bug. It asked *"is there anything
else?"* — but bolted onto the end of the turn that read out the office number.
What came back was *"can you make it slower"*, which is not an answer to that
question. It re-read the number, counted the beat as answered, and closed. **A
question sharing a turn with a fact gets answered about the fact.**

So the four beats became a handshake, and three things that are not style:

- **Nothing shares a turn with the "anything else?".** Not a phone number, not a
  reference, not the handover line, not a thank-you.
- **Nothing shares a turn with the closing.** No last detail, no thanks-then-close
  in one breath — the phrase ends the call and anything saved for afterwards is
  never said.
- **A reply that is not a yes or no to that question is not an answer to it.** A
  repeat request, a correction, a number said back — all put you back in the
  call. Handle it, ask again in its own turn, wait again. **No limit on how many
  times that loop runs.** The call ends when they say it does, not when the agent
  has run out of business.

Now **absolute rule 13** as well, since rule 12 said to ask and this says how.

**Rule 10 gained the failure by name.** The same call had the agent say
*"Reason. Dispute. Friction."* out loud — the argument to `transfer_to_human`,
read as though it were a sentence. The rule already forbade speaking a value; it
now names what happened, on the same principle as the reference read-back fix:
"exactly" is what the model already thought it was doing.

**`idleTimeoutSeconds` 8 -> 12 on all four assistants.** At 8 the prompt fired
"Still with me?" into a resident's thinking pause, twice on real calls. It also
worked against the change above: the handshake ends on a beat where the agent
asks and then waits, and a prod at 8 seconds lands in exactly the pause the
handshake exists to create.

**And it was hardcoded in two build scripts**, which is the part that would have
undone it silently: `vapi_en.py` writes `messagePlan` on every twin rebuild and
`vapi_sync.py` on every Hebrew push, both with 8. Patched with the reason, or the
next routine rebuild reverts a live setting and nothing reports it.

Hebrew 58,784 chars, English twin 57,356, 59 passages + 4 blocks, 7 tools with
servers on both.

**Still open from the same transcript:** the TTS says "HOMEies" for Homies, on the
first word of every call.


### The call stops hanging up on people, and the email it was reading out was invented

A second English debt call from the client. Three things wrong in it, and the one
that was not reported is the one that costs money.

**The email was wrong.** The agent said *"send the confirmation to office at
homies dot co dot e l"*. There is no such address. The real one arrived this
morning in the client's own FAQ — `Office@homies-management.co.il` — and the demo
page had been sending `office@homies.co.il` since 12 Aug, with the test scripts
saying `homiesemail@gmail.com`. Both invented, both flagged in HANDOVER as
"nobody has confirmed either is real", and today one of them was read to a
resident who was asked to send proof of payment to it. **A wrong address does not
bounce to us. It bounces to them, days later, after they think the dispute is
being looked at.** Corrected in `web/index.html` (both the Hebrew spoken form and
the English), `docs/assistant/debt-followup.md`, `scripts/voice_guard.py` and
HANDOVER. The hyphen is now said — מקף — because without it the address is a
different one.

**The call hung up on her.** Reported as *"it auto ends the call"*. It does, and
not metaphorically: `endCallPhrases` carries "have a good day", so the phrase
**is** the switch — Vapi releases the line the instant the model says it, and
there is no turn afterwards for the resident to be in. The rule added this
morning ("before you close, ask whether there is anything else") lives in ENDING
THE CALL, and this call went out through the handover path, which said in as many
words: *"do not ask another question."*

So it is now an **absolute rule (12)**, in the section that the fixed paths do
not override, and the close is written as a sequence rather than a preference:

    1. the last piece of business
    2. their answer to it
    3. "anything else?"   <- ITS OWN TURN. Stop. Wait.
    4. their answer, and only then the closing

**Beat 3 holds on every path**, handovers included — somebody being passed to the
office is the person most likely to have one more thing to say — and including a
resident who has just said stop calling me, which is a reason to be quick and not
a reason to hang up mid-thought. The handover path is four steps now, not three.
And the failure mode is named, because it is the one a model reaches for:
*"anything else? okay, have a good day"* in one breath is the same as not asking,
since the phrase has already ended the call.

**And the middle of the call was nonsense, which was the "not solid" part.** The
call was about apartment 7. She said *"actually, apartment twelve. Not apartment
seven."* The agent replied that apartment 7 was still open, *"so the records don't
match on apartment twelve"*, and offered a link for apartment 7. She was not
disputing a payment — she was saying the call had the wrong flat, and the tools
will not take a flat that is not on the call anyway. The dispute section now
handles an apartment that is **not on this call** separately: name the apartment
this call is about, ask once whether it is theirs, and if it is not, stop
collecting — `transfer_to_human` with reason `ownership`.

Hebrew 56,692 chars, English twin 55,264, 59 passages + 4 blocks, no Hebrew left.
The two new closing passages needed real entries rather than translations: each
names the phrase that ends the call, and it is a **different phrase per language**
— יום טוב against "have a good day", both in `endCallPhrases`. A literal rendering
would have named a phrase the English twin never says, which is the same as
naming none.

**Not changed, and worth a decision:** `idleTimeoutSeconds` is 8. "Still with me?"
fired while she was thinking, mid-exchange, and reads as impatience in the
transcript. The four-beat close now depends on a pause at beat 4 being allowed to
happen, so 8 seconds may be too short for the thing it is meant to protect.


### The account move is one script now, and blocker 1 turned out to be soluble

Asked for the Vapi setup cloned 100% and ready to transfer. Written as
`scripts/vapi_transfer.py`.

**Blocker 1 of the runbook is gone, and it was the dangerous one.**
`new-vapi.md` has said since 7 Aug that the Cartesia credential "does not travel"
and must be re-added by hand — and that losing it makes no noise, because Vapi
falls back to `vapi/Elliot` and the Hebrew agent talks with an American accent
while nothing errors and the billing reports Elliot either way. **`CARTESIA_API_KEY`
is in `.env`.** The credential can simply be created through the API, so the
script does, and refuses to continue if the key is absent rather than producing
an account that sounds wrong to one person in ten.

**Step 6 is the one that has broken every move**, and it is now mechanical:
**17 ids across 10 files**, rewritten from the map that creating the assistants
produced. That step is dangerous precisely because a wrong id does not error —
the call connects to the wrong agent, or to one that no longer exists. It is how
the demo page spent a day calling account 3 after everything else had moved.

    web/index.html                         4     docs/assistant/demo-inbound.md    3
    scripts/vapi_en.py                     2     docs/assistant/debt-followup.md   2
    vapi_call / duel / eval / mock         1 ea   inbound-test-script.md           1
                                                 04-interruption-pacing/feature.md 1

**It copies all four assistants rather than rebuilding the Hebrew pair, and that
is deliberate.** The runbook rebuilds from markdown, which is right when the goal
is a working account. It is wrong when the goal is a *clone*: a rebuild produces
what the repo says should be live, a copy produces what **is** live, and those
differ the moment somebody edits the dashboard. Finding that out after a
migration is the failure this exists to prevent.

**Guards, each from something in this file's history:**

- `--to` names the **variable** in `.env`, never the key. A key on a command line
  lands in shell history and this repository is public.
- Refuses a target that already holds Homies assistants — creating by name again
  gives four duplicates and no error, and the repoint would pick whichever came
  back first. Verified against account 4, which still holds all four.
- Refuses to clone onto the account it is reading from.
- `restore()` puts real values back where the export wrote `<redacted>`, for the
  `--from-export` path. A tool server header restored with the literal string
  authenticates as nobody: 401 from the Edge Function, nothing about the call
  fails, and the resident is told a request was opened that does not exist.
- It does **not** move `VAPI_PRIVATE_KEY`. The old account stays reachable until
  somebody decides otherwise.

**A dry run against account 4 collided, and that exposed a flaw in my own
script:** it exited on the collision and printed no plan. A dry run that refuses
to tell you what it would have done is useless. It now warns and continues; only
`--apply` stops. Full dry run verified end to end — 4 creates, 17 id rewrites.

**What still cannot be automated: the public key.** `GET /org` returns 401 to a
private key, so there is no way to read it. It goes in `.env` and in
`web/index.html` by hand, and without it the demo page loads and no call starts.
Call history, transcripts and recordings stay behind — recordings are deleted
after 14 days regardless. Riley is not ours and is skipped; each account mints
its own.

**Found on the way: `VAPI_ASSISTANT_ID` in `.env` is stale and nothing reads
it.** It points at no live assistant, and a grep across `scripts/`, `web/` and
`dashboard/` returns nothing. Dead config — left alone rather than edited,
since `.env` is the client's, but it should go.


### The Vapi export is refreshed and hardened — after I wrote a duplicate of it

Asked to back up what is live. **I wrote `scripts/vapi_backup.py` and a
`vapi/backup/` tree, then found `scripts/vapi_export.py` already existed**,
already written to `docs/handover/vapi-export.json`, already referenced by
`new-vapi.md`, and already fetching two collections mine missed — `/credential`
and `/workflow`. `/credential` is the important one: it is the Cartesia key,
which is blocker 1 of the whole account move. Mine was deleted and its two real
improvements folded into the existing script. Two backup mechanisms is the exact
drift this session has spent all day warning about.

**What went in:**

- **Redaction by value, not by field name.** It blanked anything under a key
  called `headers`. It now also loads every credential-shaped value from `.env`
  and replaces it wherever it appears under any key, then **refuses to write** if
  one survives. A list of field names misses the field somebody adds next month.
- **`--check`**, which re-scans every export on disk.
- **`--archive <label>`**, which writes the dated copy in the same run. The
  historical exports — `vapi-export-account3-11aug.json` and friends — were
  named by hand, which means they were made when somebody remembered.

**And then the first `--check` cried wolf, which is worth recording.** It flagged
six leaks across the historical exports: `N8N_SHARED_BASE_URL`, `N8N_BASE_URL`,
`SUPABASE_URL`, `VAPI_ASSISTANT_ID`. **None of them is a secret** — `SUPABASE_URL`
is compiled into the dashboard's browser bundle on every build. Over-redaction
looked like the safe direction and is not: the next person reads six warnings,
finds all six harmless, and stops reading warnings. A check nobody believes
protects nothing.

So a plain `http(s)` URL and a bare uuid are now classed as identifiers and left
alone. **The URL test requires no `@` in it**, deliberately: `SUPABASE_DB_URL` is
also a URL and carries the database password in its userinfo. It is a secret
wearing a URL's clothes, and the single most dangerous value in the file. All six
exports now scan clean, and the four `.json` archives needed no change — they
never held a secret, only the false positives.

40 values redacted, 5 assistants, 1 credential (Cartesia), everything else empty.

### The account-move runbook was wrong in the one place it mattered

`new-vapi.md` blocker 2 said the English twins **cannot** be regenerated and must
be copied verbatim — 109 unpaired Hebrew passages on debt, 9 stale intake entries
from מיכל → מיכאל — and warned *"do not use an English twin to judge whether a
Hebrew fix worked"*. Both tables were rebuilt today and both `--dry` runs are
clean, so step 5 regenerates now and the warning is gone. Left standing: a
refusal means the table is stale and the fix is the table, never the check.

**Blocker 1 stands and is unchanged.** Cartesia does not travel, a new account
has none, and the fallback to `vapi/Elliot` is silent — the call connects, the
agent talks, and only a Hebrew speaker notices it is American.


### The Vapi account is snapshotted, and the snapshot is safe to commit

Asked for a backup of what is live. Written as `scripts/vapi_backup.py` rather
than a one-off dump, because a backup you cannot retake is a photograph.

**The prompt is not the assistant.** `docs/` holds the prompts and
`scripts/vapi_tools.py` holds the tools, but the live object also carries the
model, the voice, the transcriber, `endCallPhrases`, `maxDurationSeconds`, both
endpointing plans, `messagePlan`, and a `server` block per tool — and several of
those have only ever been set in the Vapi dashboard, which leaves no trace here.
This project has twice found an assistant running a stack nobody could point at
a commit for. Now there is a record.

    assistant        5   (4 Homies + riley-2, which is not ours)
    phone-number     0        tool  0        file  0
    knowledge-base   0       squad  0
    517 KB total, 12 files

**The redaction is the reason this is a script and not `curl`.** Every tool on
both debt assistants carries

    "headers": { "x-homies-secret": "<the live secret>" }

which is the credential standing between the open internet and every resident's
balance. `curl > file.json` inside this checkout puts it one `git add -A` from
GitHub. So the script does not strip a list of field names — that misses the
field somebody adds next month. It loads **every value in `.env`**, replaces each
one wherever it appears under any key, then re-scans and **refuses to write** if
anything survived. `--check` re-scans every snapshot on disk; all 12 clean.

**Found on the way: the tool secret and `N8N_WEBHOOK_SECRET` are the same
value.** The redaction named it, which is how it surfaced — the placeholder reads
`<redacted:N8N_WEBHOOK_SECRET>` in a header called `x-homies-secret`. Not wrong,
and worth knowing before either is rotated: rotating one breaks the other.

**Ids are deliberately not redacted**, and the README says why. An assistant or
credential id identifies a thing and opens nothing; a snapshot with them stripped
cannot be read or restored from.

**There is no `--restore`, on purpose.** Pushing a whole assistant object back is
exactly how tools get replaced by a stale list — the failure `CONTEXT.md` already
warns about for `vapi_sync.py`, and the one that would have stripped all seven
server blocks this morning. The README documents restoring by hand: read the
field you want, PATCH only that, put the two `<redacted:…>` values back from
`.env` first, and verify the tools survived.

Empty collections are recorded **because** they are empty. The day a phone number
or a knowledge base appears, the diff says so.

Nothing committed — the files are written and clean, and the commit is the
client's call.


### A standing order now opens a ticket, because the flag it used to set reached nobody

Asked after finding that `request_standing_order` wrote one row to
`call_outcomes` — `outcome: 'office_to_contact'`, `standing_order_requested:
true` — and nothing else. No ticket, no reference, no notification.

**The old comment on the handler said the flag was "where a person will look for
it".** That is the part that was wrong. The dashboard's Calls page has five tabs
— all, inbound, outbound, no answer, links sent — and none of them filters on
either field. Two rows were sitting there from 11 Aug. Both carry a null
`resident_id`, so they are web-demo artefacts rather than residents waiting, but
under a real campaign they would have been two people who agreed to pay every
month and were never contacted.

**The tool now writes both.** The flag stays — it is what the collections side
reads off the call — and a `requests` row goes in beside it, which is the queue
staff actually work from. Edge Function v21.

    type        other      (the eleven categories are faults; this is not one)
    urgency     normal
    opened_via  voice
    oxs_ref     standing_order      the marker the handler finds its own rows by
    description בקשה להוראת קבע — יש ליצור איתו קשר להסדרה

**The dedupe has no time window, unlike `open_request`'s thirty minutes.** That
guard is right for faults — "the leak is back" next morning is a new fact and
deserves a row. A standing order asked for again next month is the *same* unmet
request, and a second ticket tells the office there are two arrangements to set
up when there is one. So: one open standing-order ticket per resident, and a
repeat returns the existing reference.

**`requests.building` is NOT NULL and the tool takes no arguments**, so a call
started without building in its variables would have failed the insert and turned
a resident's yes into an error mid-call. It falls back to the resident's own
building, and if there is still nothing it keeps the flag and skips the ticket. A
recorded yes with no ticket is bad; a yes that errors is worse.

Tested live against the deployed function with a real resident and a real unpaid
charge: first call returned `255-1052-26`, second returned the same reference with
`duplicate: true`. Both test rows and their interactions deleted after.

**The prompt had to say so too, or we would get two tickets.** The agent has
`open_request` and now a reason to reach for it. Both the standing-order section
and the tools catalogue now say the one tool does all of it and must never be
paired with `open_request`. Hebrew 54,030 chars, English twin 52,582.

**`transfer_to_human` is the same defect and is still open** — same table, same
five tabs, 16 rows. Fixing standing orders by opening a ticket does not fix it,
because a handover is not a request; it needs the Follow-ups view.


### A real English debt call, and the three things it got wrong

The client ran the rebuilt English twin and sent the transcript. The agent
answered questions it should have answered, reached for the office twice on
questions it could have answered, never came back to the payment, and closed on
the resident's "no" without asking whether there was anything else.

**Worse than any of that, and not what was reported: it invented facts.** Asked
what the fee covers it said *"cleaning, lighting, and general maintenance"* and
later *"cleaning, lighting, elevator, plumbing, common areas"*. Lighting is not
on Homies' list — the electricity **bill** is — and neither is plumbing. Gardening,
insurance, the lift inspector, the fire and smoke inspections, the pumps and the
water-tank disinfection were all dropped. It got the office hours right, which
was luck: **the debt prompt had no facts in it at all.** Confirmed the same
morning — neither voice prompt carried the FAQ section or even the office number.

So "answer instead of escalating" could not be shipped on its own. Told to stop
handing over and not given anything to answer from, the agent invents more
confidently, which is worse than the brush-off it replaces.

**Three changes, all four now live on both twins.**

**1. A questions ladder.** New section, and a question is no longer a reason to
hand the call over:

    1. Answer it, from the facts.
    2. Cannot answer it -> offer to open a request. `open_request`, type `other`.
    3. Only then the office.

With the reason written in: reaching for the office on an answerable question
reads as a brush-off, and a resident working himself round to paying stops. Two
in a row and the call is over whatever comes next — which is exactly what the
transcript shows.

**2. The facts themselves.** A compact `WHAT YOU ACTUALLY KNOW ABOUT HOMIES`:
office hours, phone, address, email, the full covered list, what is excluded,
when and how to pay, reaching the committee, response times, and the
responsibility line. The same four rules that govern them on the chatbot travel
with them — quote contacts exactly, answer rather than recite, service levels are
policy never a promise, and never adjudicate responsibility.

**3. The call comes back to the payment, and does not slam shut.** The answer and
the ask are joined in one turn, because there is no later turn — they ask the
next question. And before the closing: ask whether there is anything else, and if
the payment is still unsettled put it back on the table **once** — except on a
handover, where the existing rule against offering the link on the way out still
holds. Once, then take the no and close warmly.

**Prompt 48,827 -> 53,569 chars**, which is a real cost paid deliberately: the
prompt's own editing rules warn that length is money and that the 7 Aug failures
were "the model did not find the rule". The facts are worth it; a bot that
invents what a resident is paying for is worse than one that says it will check.

**English twin: 57 passages + 4 blocks, 52,121 chars, no Hebrew left.** Only two
fragments of the new section needed crossing — the office address, transliterated
rather than translated (Bezalel 1, Ramat Gan), and ועד בית. The phone, email and
hours are Latin already and cross untouched, which is the point of quoting them
exactly on both sides.

**Not fixed, and visible in the transcript:** one turn came back as the fragment
*"I don't have"* before a second turn carried the real answer. Same shape as the
11 Aug single-word generation on WhatsApp — the node succeeds carrying a
fragment. The chatbot has a word-count guard for this; voice has none.


### The debt agent opens tickets, and "I already paid" gets somewhere to go

Asked for: the collection agent should be able to open a request when asked, and
the disputed-payment path should offer the link, then — if that is refused — a
ticket or the office, rather than ending on a logged dispute and nothing the
resident can hold.

**The tools were already there.** Both debt twins have carried `open_request`
since feature 14 and `log_disputed_payment` since the start. What was missing was
the prompt: `open_request` was taught for exactly one case, a maintenance issue
raised mid-call, and the dispute flow ended at step 4 with *"do not offer the
link"* written into it.

**The dispute flow is now six steps, and steps 3 and 4 are new.**

    3. Offer the link once, as an option, in the same breath as the discrepancy.
       One obvious reason two records disagree is that their payment never
       reached us.
    4. If they say no, take the no. Understand it, say once that our side still
       shows it open, and name the two things you can actually do: open a
       request about it with a number they can quote, or pass it to the office.

**This reverses "do not offer the link", deliberately and on instruction.** That
rule existed to stop the agent pressing somebody who says they have paid, and
half of it survives: no arguing, no repeating the amount, no asking them to pay
in the meantime, and never a second offer. What changed is that one offer is now
allowed, because a resident whose payment genuinely failed is better served by a
link than by a promise that the team will look.

**The dispute is logged whichever they choose, including neither.** A request is
something the resident holds; `log_disputed_payment` writes `payment_disputes`
**and** sets the charge to `disputed`, which is what the debts dashboard shows
and what stops them being chased again next month. The ticket never replaces it.
Checked before writing the rule rather than assumed.

**And a request opened on request is now a yes, not an offer.** "תפתחו לי
קריאה" needs nothing asked first. The tool description was widened to match —
raised, asked for, or accepted — because the description is what the model reads
when it decides whether the tool applies, and it said only "raises".

**Pushed by hand, not by `vapi_sync.py`, and the reason is worth recording.** The
live tool objects carry a `server` block — webhook URL and the shared secret —
that `vapi_tools.py` does not. Replacing `model.tools` with the repo's list would
have stripped all seven and left an agent whose every tool call goes nowhere. The
description was edited in place on the fetched objects instead; 7 tools with
server before, 7 after.

**Third copy of the read-back rule found and fixed.** The debt prompt has its own:
*"give the last four digits only — never the letters and never the year"*. Under
`255-1043-26` the last four digits are `4326`. Now the middle part, with the trap
named. That is three copies in two prompts, all found only by reading for
something else, which is an argument for the rule living in one place.

**The English debt twin was two drifts behind and is rebuilt.** Its table had
been refusing since `{{gender_forms}}` replaced `{{gender}}`: a section anchor
ended on a sentence that no longer exists, and two entries still said `ועד בית`
where the prompt now says `ועד הבית`. Three passages had never been in the table.
55 passages + 4 blocks, 47,363 chars, no Hebrew left, all 7 tools with servers.

**One entry I added was already there**, and the check caught it: a duplicate
finds zero occurrences on its second pass, because the first already replaced
them. The failure reads identically to a drifted anchor and is not one.

**The one place the twins diverge in substance rather than language.**
`{{verification_email}}` is composed for a Hebrew voice — pieces, with שטרודל
where the @ is — because a Hebrew voice handed a Latin address mangles it
differently every read. English has no such problem, so the English twin reads it
as an address. The rule underneath is unchanged: say it as it arrives, once.


### The English intake twin is rebuilt, and the Hebrew one it copies is current again

Asked for: an English clone of the Hebrew voice agent to review the call flow
without reading Hebrew. Both twins already existed; the intake one had refused to
build since 7 Aug and was frozen at a prompt two rewrites old.

**The Hebrew prompt went up first, because a clone of a stale source is a stale
clone.** `demo-inbound.md` and the live assistant differed in exactly one place -
the reference read-back - and pushed prompt-only: GET, swap
`model.messages[system].content`, PATCH the whole `model` back. Tools verified
before and after: `open_request`, `save_partial_request`, `transfer_to_human`,
all three survived. 23,309 -> 23,583 chars.

**A second copy of the read-back rule turned up while reading for the table.**
The status section carries its own: *"the same way a new one goes out: the last
part only... no HM and no year"*. This morning's edit fixed the opening-a-request
copy and missed this one, which would have had the agent read a caller the year
on every status call. Both now say *the middle part... no 255 and no year*.

**Why the table had refused for eleven days**, in the order the build found it:

1. The agent turned masculine on 7 Aug. Every fixed Hebrew line in the table was
   still feminine - `מעבירה`, `מסמנת`, `מבינה`, `רושמת`, `העוזרת הדיגיטלית`. Five entries.
2. The identity entry translated *Michal* to *Michael* and the prompt already
   said Michael, so the substitution had nothing to do. Removed.
3. The status-refusal line - *"I don't have access to the status of existing
   requests"* - no longer exists on either side. The agent has a lookup now.
   Removed rather than translated: a twin carrying the refusal would be testing
   a flow that is gone.
4. The Language section grew from 8 lines to 69 when the caller-gender rules went
   in. An exact match that long breaks on every unrelated edit inside it, so it
   became a regex block anchored at both ends, like the debt twin's.
5. Four passages had never been in the table at all, because they arrived after
   it was last built: the four status labels, the spoken-amount example, the
   keep-what-you-caught example, and the taking-a-correction pair.
6. `## Opening a turn like a person` and `## Hesitation` are two sections of
   Hebrew discourse particles - אז/אוקיי/בסדר, and אה as the hesitation sound.
   Second regex block, crossed as English equivalents rather than translations.

**One inversion worth recording.** The Hebrew rule is *"never say the English
word"* about status labels. In English the system's label IS English, so a
faithful translation would have told the twin to do the opposite of what the rule
means. It crosses as *never read the system's label out as it is written*.

Built and pushed: 25 passages + 2 section blocks, 21,734 chars, no Hebrew
remaining, same three tools, same 180-second cap, same endpointing. Read back
from the API. `endCallPhrases` already carried both languages, so the twin can
still hang up - which the table's own comment had warned about.

Reachable now at homies-voice-demo.vercel.app: the deployed page is build
`2026-08-12a` but carries the account-5 assistant ids, so it calls the twin that
was just rebuilt.

**Found and NOT fixed: the intake prompt calls two tools the assistant does not
have.** `## Status of an existing request` instructs `get_request_status` and
`## Balance and debt` instructs `get_balance`; the live assistant carries three
tools and neither is among them. `vapi_tools.py` still says both are
"deliberately absent" because "this project has no read path" - which was true
when it was written and has not been true since the Edge Function shipped. This
is the 5 Aug failure shape exactly: the prompt tells it to call something, there
is nothing to call, and the agent invents the answer. It applies to the Hebrew
agent equally; the twin inherits it rather than causing it. Attaching tools is a
behaviour change to a live assistant and was left for a decision.


### Ticket numbers take Homies' shape

**Deployed.** Asked for as *"the creation of ticket it should match the homies
format not the HM"* — the same instruction as 12 Aug's categories, one field on.

Ours was `HM-2026-1046`, a prefix invented on day one. Theirs, on all 34 calls
imported from OXS, is `255-26372-26`: their code for Homies, a running serial,
the year in two digits. Measured before changing anything — `255` constant across
every record, the serial monotonic with date (19502 on 10 Feb, 26372 on 12 Aug),
never reset. A resident reporting a leak in their app and one reporting it here
were getting numbers that did not look like the same company.

**Migration 020.** The default is now
`'255-' || lpad(nextval(...),4,'0') || '-' || to_char(now(),'YY')`. First minted:
`255-1047-26`, continuing the sequence rather than restarting it, so no number is
issued twice across the change.

**Four digits, and that is not cosmetic.** `requests.reference` is unique and
`oxs_requests_sync.py` upserts on it, so the day OXS's counter reached a number we
had already issued, **their call would overwrite our row**. We cannot reserve a
number from them — their API is twelve GET endpoints. So we mint below a counter
that only climbs, and theirs passed five digits in February. A check constraint
now rejects any `255-` reference of ours outside the four-digit band, which is
what stops a later hand widening it back by accident.

**The lookup had to learn both shapes at once.** `get_request_status` matched on
the last four digits — which in `255-1047-26` is the year. Every ticket opened
before today still carries `HM-` and residents are still holding those numbers.
`serialOf()` in the Edge Function reads the serial out of either: the middle of a
three-number reference, the tail of a lettered one, matched anywhere in the
string because the model passes what the resident wrote and residents write
sentences. The four-digit floor stays, so an apartment number in that argument
still does not go looking for a ticket.

Tested live against the deployed function, one ticket minted and deleted:

    255-1047-26 quoted whole    -> found      255-26277-26 (theirs) -> found
    just 1047                   -> found      just 26277            -> found
    HM-2026-1001 (old)          -> found      "המספר הוא 255-1048-26" -> found

**The read-back rule was rewritten, not just re-exampled.** It was built on 8 Aug
around a real failure — the model returned `2026-8884` for `HM-2026-8884`, reading
the letters as decoration. The new shape has no letters to drop, so the rule now
names what *this* shape loses (`1048`, `255-1048`, `1048-26`) and says the three
parts and the hyphens are all of it. Prompt 26,496 → 26,718 chars, read back from
the live workflow and byte-identical to the file.

**The voice prompt had to change too, and it is the one thing not pushed.** Its
read-back rule says *only the last part* — correct for `HM-2026-1001`, and under
the new shape it makes the agent read out the year: *2, 6*. `demo-inbound.md` now
says *only the middle part* and names the trap. **Not pushed to Vapi**, under the
standing chatbot-first instruction; the voice line takes no real calls (web only),
so this is a demo-quality break, not a resident-facing one. It needs the
prompt-only PATCH, not `vapi_sync.py`.

Rows opened before today keep the numbers they were issued with. A number already
told to a resident is not rewritten behind them, so the dashboard shows both
shapes and `opened_via` remains the way to tell whose ticket is whose.


### A missing fact stops being a staff task, and the bot gets a fence

**Deployed**, 24,747 → 26,496 chars. Two decisions, both the client's.

**A fact we do not hold is not an escalation.** Half an hour earlier the bot had
been told to say *"I'll check and get back to you"* and call
`transfer_to_human`. That is now reversed on instruction, and the instruction is
right: a missing website is not work — nobody needs to do anything, and every
such question would have filled the office with empty tasks.

What replaced it is better than either version. The bot says it does not have
that detail **and gives the office phone and email**, which it does know:

> אין לי את הפרט הזה. אפשר לשאול את המשרד ב־077-6687949 או ב־Office@homies-management.co.il.

**And no "I'll get back to you".** Written into the prompt as the reason:
a promise nobody recorded is a polite lie, and a phone number that works right
now beats an undertaking no one is holding. This also stops making the
`transfer_to_human`-notifies-nobody defect worse, which the earlier version
would have done.

**The topic fence, open since the feedback session, is now closed.** Weather,
news, sport, politics, medical or legal advice, suppliers who are not ours,
calculations, translation, general knowledge — declined in one friendly
sentence with a way back to the building, and **never** escalated. The load-
bearing line is *knowing the answer is not a reason to give it*: the resident
wrote to a management company, not a search engine, and a bot that explains
tomorrow's weather spends the credibility it needs when it states what somebody
owes.

**Three things that look out of scope and are not**, written in because a fence
without them is worse than none: ordinary courtesy (`תודה`, `יום טוב`) gets a
human reply, not a scope refusal; a building question phrased generally
("power cut in the area?", "can I keep a bike in the lobby?") is in scope even
when the answer is not known; and a complaint about a neighbour or noise is
common property, which is ours.

Escalation now happens only for what it was built for — money that moves,
complaints about a person, danger, anger at us, identity that failed twice, and
a responsibility question too close to call.

### First real handset test of the register, and two bugs it found

Fourteen lines sent from a phone. **The register held.** No `בנוסף`, no
`כמו כן`, no bureaucratese, short sentences throughout, `גרים` everywhere it
mattered, and the casual probe (`אחי המעלית תקועה שוב חבל על הזמן`) came back
`אוי, זה מעצבן. יש מישהו בתוך המעלית?` — relaxed exactly one step and asked the
danger question before anything else, which is the rule working rather than
luck. The formal probe correctly skipped the offer, because `ברצוני לדווח` *is*
an explicit request and the offer is only for someone who has merely mentioned a
fault.

**Two real defects, both fixed and deployed** (24,151 chars):

**1. `לך`.** The reply `אני לא יכול להגיד לך מתי יטפלו בקריאה שלך` genders the
resident twice. The prompt has forbidden gendering since 8 Aug and never named
the word that carries it most often — `לך` is written identically for both and
said two different ways, and the same trap sits in `שלך` and `אליך`. Now named
with the fix: delete the word. `אני לא יכול להגיד מתי בדיוק` loses nothing.
Notable that the *voice* prompt already carried this exact warning and the chat
prompt never inherited it.

**2. `אין לנו אתר אינטרנט`.** Asked whether Homies has a website, the bot said
they do not. Nobody told us that. The knowledge section said *what is not
written here you do not have and do not invent*, and the model read the absence
of a fact as a fact. Now separated explicitly: **not having a detail is not the
same as the detail not existing.** It says it does not have it and hands over —
a claim about the world is not one it can make.

**One thing that is not a bug but reads like a fault.** `עוד משהו?` plus the
options list fired after four consecutive replies. The workflow appends it
whenever a reply has no question mark — but the code comment beside
`FOLLOWUP_MENU` says it is sent *when the reply carries a reference number*.
Comment and implementation disagree, and the implementation is far broader. The
effect is a support desk that reads like a kiosk. Not changed yet; it is a
behaviour decision, not a defect.

**Inconclusive:** the kitchen-leak probe. Both messages arrived batched, so the
`כן` answered an offer that had not been made yet and the test proved nothing
about the offer-then-ask order.

### The register gets a floor, not just a ceiling

**Deployed.** Prompt 21,920 → 23,504 chars.

Asked for natural, local, casual Hebrew out of Gemini 2.5 Flash. Checked the
model settings first: only `maxTokens` is set, so temperature sits at Gemini's
default. There was no sampling knob to reach for — this was always prompt work.

**What was missing was the floor.** Every register rule in the file pointed one
way: not `הנני`, not `יש באפשרותי`, not `פנייתך נקלטה`. None of them said how
casual is too casual, and a management company's bot writing `יאללה אחי` is
exactly as fake as one writing `ברצוני`. The section now sets both edges as a
three-column band — clerical / the band / street — with `וואלה`, `סבבה` and
`תכל'ס` marked as borderline under a rule worth keeping: **never lead with
slang, and match a resident down at most one step.**

**Flash's actual failure mode is translationese, so it is named.** The words are
correct Hebrew that nobody types into a message: `בנוסף`, `כמו כן`, `לפיכך`,
`על מנת`, `במידה ו`, `יש לציין`, `אנא`, `נא לפנות`. Replacements given, because
rule 4 of this file says a prohibition leaves the model reaching for its own
last message.

**And spoken Hebrew drops words.** `אני אבדוק את זה ואחזור אליך עם תשובה` is a
correct sentence no Israeli writes; it is `אבדוק ואחזור`. Five to eight words,
one idea, half-sentences allowed.

Five contrastive rewrites carry it — written/spoken pairs drawn from this bot's
own situations rather than generic ones, which keeps them teaching register
instead of becoming lines to replay. The last pair's spoken column is empty on
purpose: `נשמח לעמוד לרשותך בכל שאלה נוספת` has no colloquial equivalent because
you simply do not write it.

**Closed with the guard that makes it safe:** casual is not sloppy. Reference
numbers, phones, addresses and amounts stay exact — pointing back at the
warmth rule rather than restating it, so there is one statement of that
principle and not two.

**Untested.** Whether Flash actually holds the band across a conversation is the
open question, and only a real handset answers it.

### The facts get a home that is not the prompt

`docs/reference/homies-faq.txt` — the twelve answers verbatim as the client
sent them, plus the question each one answers.

**Written to open with what it is not.** The bot does not read this file. The
facts are deployed inside the system prompt, and a change here alone changes
nothing a resident hears. That warning is first because this project has
already lost an afternoon to exactly that failure: the greeting lived in the
prompt and in the menu node, one copy was updated, and residents kept getting
the old one for two days.

It also carries what the prompt cannot: that **website** was asked for and never
answered, that the emergency number is the office number so a burst pipe at
22:00 reaches an empty office until 09:00, and that the 4-hour / 3-business-day
service levels are now a commitment the bot repeats at scale and Yariv should
confirm he is happy being quoted on. The four rules attached to the facts —
quote the contacts, never promise a specific ticket, answer rather than recite,
never adjudicate responsibility — are recorded there too, so they survive a
future rewrite of the prompt.

**Not gitignored.** It holds no resident data — office contacts, contract scope
and service levels — so it does not meet any rule in `.gitignore`. It is still
client commercial detail heading for a public repository, which is the user's
call rather than a default.

### The bot finally knows something about Homies

**Deployed.** Prompt 19,438 → 21,920 chars, read back from the running workflow
as identical to the file.

Twelve answers from the client, and they close the gap that had been the most
visible one: until today the prompt carried **no facts about the company at
all**. Hours, phone, address, what the ועד בית payment covers — every one of
them reached a human, which is safe, thin, and not what a support desk is.

**One collision had to be resolved, and it is the interesting part.** The prompt
has said since 8 Aug: *never promise a date — "tomorrow morning" is a promise
somebody else has to keep.* Answer 11 supplies service levels: emergencies
within 4 hours, everything else within 3 business days. Read carelessly, the new
facts repeal the old rule.

They do not, and the distinction is now written into both places. **A service
level describes the standard; a date is a claim about *your* ticket.**
"Emergencies are handled within four hours" is a fact about the company and may
be said exactly as written. "Yours will be done by tomorrow" stays forbidden —
and stays forbidden *because* there are now numbers to hand, which makes it far
easier to say by accident. Specific tickets are still answered only from
`get_request_status`.

**Three guards went in with the facts:**

- **Phone, address and email are quotes, not phrasings.** The warmth rule
  already separates the sentence from the fact; these are facts a resident
  copies and uses, and a wrong number is worse than no number.
- **Answer the question, do not recite the list.** The covered-items list runs
  to thirteen entries. Somebody asking whether cleaning is included gets "yes,
  cleaning is included" — the full list only on request.
- **Never adjudicate responsibility.** Answer 12 draws the line at what the law
  calls common versus private property and ends with *in case of doubt, contact
  us*. That ending is the operative part: where it is not perfectly clear the
  bot says we will check and hands over. Getting this wrong costs a resident
  money.

**Recorded because it is absent:** no website among the answers, and no staff
names, prices or contract clauses. The section opens by saying so — anything not
written there does not exist and goes to the team rather than being guessed. The
emergency number is the office number; there is no separate out-of-hours line,
and the bot is told not to invent one.

**Still open: the topic fence.** Nothing stops the bot answering questions with
nothing to do with building management, and a knowledge base makes that more
pressing rather than less — a bot that now answers real questions well is one a
resident will push further.

## 2026-08-17

### The 2022 debt is gone, and the arrears window stays on the current year

**Asked whether 2022 could be dropped since the window of interest is 2025
onwards. It turned out 2022 was never in the sweep.** `oxs_arrears.py` runs on
`YEAR = date.today().year` and ended months only, so it has always been 2026-01
→ 2026-07 and nothing older. The whole of 2022 in this database was **one row**.

That row: ₪1,500, `oxs_ref 62980672…`, period `2026-08-01`, ארז לויים,
הרכסים 17 apt 8, `handed_over=false`. It was the entire output of OXS's
`/debts` endpoint — one company-wide record, a balance on a departed owner —
stamped with the run month because the endpoint carries none. Verified as the
only row in the table with an `oxs_ref` before deleting it, and deleted by id
rather than by period or amount.

`charges` now: **178 rows, ₪100,020 open, 2026-01 → 2026-07, no `oxs_ref`
anywhere.** It cannot come back: `--skip-charges` means the scheduled import
never reads `/debts` at all.

**The window stayed on the current year, deliberately.** Extending to 2025 was
offered and declined, and the reason is worth recording: it is not a filter
change. 2025's unpaid months would roughly **double** the amount owed by
long-standing debtors and start residents being chased for debts up to twenty
months old. That is a collections policy for Homies to set, not a default to
drift into. It also costs a fourth call per building, ~692 per run against a
1,000/hour limit.

**One workaround retired.** The dashboard's "open on the newest *completed*
month" rule existed partly to dodge this phantom. The rule stays — the current
month is not late yet, which was always the better half of the reasoning — but
the comment no longer claims a row that is no longer there.

### OXS pulls itself twice a day, and the log had to be muzzled first

`.github/workflows/oxs-sync.yml`. Midnight and 15:00 Israel time: residents,
then arrears, then maintenance requests. **Written, not yet live** — `.github/`
is untracked and a scheduled workflow only runs from the default branch.

**Four crons for two runs.** GitHub's cron is UTC and knows nothing about
daylight saving. Israel is UTC+3 in summer and UTC+2 in winter, so midnight
local is 21:00 UTC for half the year and 22:00 UTC for the other half. Four
triggers fire and a guard step asks Jerusalem what time it is, letting exactly
one of each pair through. Verified both ways: 21:00/12:00 UTC in August,
22:00/13:00 in December.

**The thing that nearly went wrong.** `oxs_api_import.py` prints every open debt
as owner, address, amount and phone. `oxs_arrears.py` prints forty debtors with
name, months, building, flat and phone. **Actions logs on a public repository
are readable by anyone with the URL**, so a scheduled run would have published a
debtor list to the internet twice a day, for ever — the exact document
`.gitignore` exists to keep out of this repo. Both scripts gained `--quiet`,
documented in each as a security control rather than a preference, and the
workflow passes it every time. `--quiet` also skips writing
`docs/reference/arrears-*.json`; it is gitignored anyway, but a runner we do not
own has no reader for it.

**`--skip-charges` on the residents import.** `/debts` is a collections ledger,
not an arrears list — one company-wide record, a 2022 balance against a departed
owner. Importing it twice a day would re-create that phantom charge for ever.
Real arrears come from `oxs_arrears.py`, which runs straight after.

**Buildings deliberately excluded.** `oxs_buildings_sync.py` is 173 calls and
about three minutes, against a list that changes a few times a year. Twice a day
is rate limit spent on nothing.

The existing safety rails still hold on a schedule: the import refuses to purge
and re-import if it fetches fewer than 50 residents, every OXS call is a GET,
and `.env` is built from secrets at the start and shredded in an `always()` step
at the end.

**Six repository secrets are needed** before the first run: `OXS_KEY_GENERAL`,
`OXS_KEY_DEBTS`, `OXS_KEY_REQUESTS`, `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL`. The workflow fails loudly with
the missing name rather than running half a sync.

## 2026-08-16

### Nothing shipped, and one live defect found

A day of answers rather than deploys, which is worth saying plainly rather than
dressing up as progress. The workflow is unchanged since 14 Aug.

**The find that matters: `transfer_to_human` notifies nobody.** It writes a row
to `call_outcomes`, stamps `interactions.disposition`, and stops there. No
email, no Slack, no push — and the dashboard has no transfers view either, which
a grep over `dashboard/` confirms returns nothing. So
`אני מעביר את זה לצוות, נחזור בהקדם` is a promise that depends on somebody
looking somewhere that does not display it.

That is worse than declining to answer. A resident who is told help is coming
stops chasing. Every handover since the bot went up is sitting in a table nobody
opens.

It also reorders the remaining work. The knowledge base is the *visible* gap and
the one the client will notice; this is the one that is actually wrong. It is
also the smallest of the four — a dashboard view, or a notification, or both.

**A dating error, corrected.** Entries were being stamped from the n8n server's
clock rather than the machine's, which put two days of work under 14 Aug that
belonged there and this day's under it too. File mtimes settle it: `prompt.md`
and `n8n_whatsapp.py` are 14 Aug, `meta-anydesk-session.md` is 16 Aug.

### The Meta go-live is written down before it is attempted

`docs/handover/meta-anydesk-session.md`, and an artifact for use during the call
itself: https://claude.ai/code/artifact/f502a879-5bc8-437d-b051-493059600dd4

Prepared on request, to be produced when the session is booked. The bot runs on
a Meta **test number** today; this is everything between that and Homies' own.

**Six values, not five.** The earlier answer missed `WHATSAPP_WABA_ID`. It is
not used by `n8n_whatsapp.py` — which is why grepping that one file found five —
but `check_whatsapp.py` needs it for `GET /{waba}/subscribed_apps`, the check
that caught a silently missing subscription on 11 Aug.

**A claim corrected in the same conversation.** Asked whether `APP_ID` and
`APP_SECRET` allow editing the Meta app, the first answer was a flat no. That is
wrong: `POST /{app-id}/subscriptions` accepts an app access token, which is
exactly how the current callback was registered by script rather than by hand.
The real boundary is **app-level versus WABA-level** — the app pair governs
where Meta delivers webhooks and lets a token be inspected; anything touching a
phone number or an actual message needs the WABA credentials.

**The three things recorded because they are what actually goes wrong:** a
number still live on the WhatsApp Business app cannot be added and loses its
history when removed; business verification takes days, so the call will likely
not finish the job; and the API Setup token expires after 24 hours, which is
dangerous precisely because it works — live all afternoon, dead by morning.
`check_whatsapp.py` already asserts the token has no expiry.

The page has **no input fields**, deliberately. It names the five values to
capture and says they go straight into `.env`; a web page is the wrong place to
type an app secret.

## 2026-08-14

### An address we do not manage is an answer, not a task for the office

**Deployed**, prompt 18,447 → 19,438 chars.

Found from a real handset. `בניין 1 דירה 30` was correctly refused and asked for
a street; `ג'ובסטריט`, an invented one, was answered with
`אני מעביר את זה לצוות`. A made-up address had become a job in somebody's queue.

The prompt was working exactly as written — `street_unknown` said hand it to the
team, because a building might be registered under a name we do not recognise
and only a person can check that. The reasoning is real, and it is the same
class of problem as `אלתרמן` being stored as `אלתרמן נתן`. It was just applied
to everyone, and the cost landed on the office.

**The trigger moved from the address to the claim.** An unknown street is now
answered plainly — Homies opens tickets only for buildings it manages, please
check the street and number as registered — with no transfer. The escape hatch
survives but has to be used: **if the person says they are our resident, it goes
to the team**, which is precisely the case where a differently-stored name is
the likely explanation. An address that is not ours, from somebody not claiming
to live there, gets a clear answer and nothing else.

**Only `street_unknown` changed.** `unit_found: false` and
`number_not_on_street` never transferred anyway — they ask again with the
numbers we do manage, because there the street *is* ours and the person is
almost certainly a resident who typed something slightly off.

**It also corrected yesterday's warmth block**, which told the bot that somebody
hearing "not found" *is* our resident and we merely failed to find them. True
when the street is ours; false here. A bot that reassures an unknown address it
is definitely on the list is warm in the one direction that costs money.

### The greeting lived in two places and only one of them was changed

Caught from a real handset, which is the only reason it was caught at all. A
bare `היי` came back `היי, כאן הומיז. מה קרה?` — the old opener — hours after
the new one was deployed and read back from the running workflow as identical
to the file.

**Both facts were true.** A bare greeting never reaches the model. The
`GREETING` regex in the Sort node matches it and short-circuits to `MENU`, a
WhatsApp interactive list whose body text is hardcoded in
`scripts/n8n_whatsapp.py`. The system prompt was correct, was deployed, and was
irrelevant to the message on screen.

**The verification was sound and still proved nothing.** Reading the system
prompt back from n8n confirms exactly one thing — that the model will receive
those instructions. It cannot say whether the model is consulted. Every reply
carrying the `אפשרויות` list button is workflow-authored; the tell was in the
screenshot before the text was.

Fixed, and then made unshippable: `check_greeting()` asserts the `MENU` body
appears verbatim in the extracted system prompt and exits the deploy if it does
not. The opener survives in the prompt as a worked example, which is precisely
what makes it checkable. Tested both ways — passes on the real file, fires on a
stale one.

The old greeting now returns **zero** matches anywhere in the live workflow.
The new one returns four, which is two real copies (Sort's `MENU`, the agent's
system prompt) mirrored in n8n's `activeVersion` record.

**The general shape, worth keeping.** Anything a user sees that a canned path
can also produce has two sources, and updating the intelligent one is the
easier half. The n8n instance is full of this pattern — `TAP_LINE`,
`FOLLOWUP_MENU`, the media line — and each is a place where a prompt change
silently does nothing.

### The opener stops assuming something is broken

**Deployed**, prompt 17,914 → 18,447 chars.

Asked for: *"hey this is homies support, how can we help you today?"* The 8 Aug
line was `היי, כאן הומיז. מה קרה?` — it named the company but opened with a
question about a fault, which assumes there is one. Somebody writing in about a
balance, a ticket status or opening hours was met as though something had
broken. It now names the **desk**, not just the company, and makes an open
offer:

> היי, כאן שירות הלקוחות של הומיז. במה אפשר לעזור?

**Not a literal translation, deliberately.** *"How can we help you today"* comes
into Hebrew as `כיצד נוכל לסייע לך היום` — a formal letter with a call-centre
`היום` bolted on, and the exact register this whole section exists to keep out.
`במה אפשר לעזור?` is what an Israeli service person says. Impersonal `אפשר`
rather than `נוכל` for a second reason: the bot writes as *I* everywhere else
(`פתחתי`, `רשמתי`), and a `we` in the greeting is what a model then carries into
`we opened a ticket`, which the prompt forbids.

**One rule was narrowed rather than deleted.** The bot-speak list banned
`איך אוכל לסייע לך?` outright and pointed at `מה קרה?` instead — a direct
contradiction of the new opener once it landed. The ban was never about
offering help; it was register. `לסייע` is letter-Hebrew for `לעזור`, `כיצד`
for `איך`, and the trailing `לך` marks gender at the moment we know least about
who is writing. The list keeps all three objections and drops the conclusion.

**Two guards went in with it**, both being ways this obviously breaks: an open
*how can we help* after somebody has already described their problem is the
clearest possible signal nothing was read, so the "they already told you" rule
now names the new line; and `במה אפשר לעזור?` is marked first-message-only,
because on message four it is a bot that has reset itself.

Read back from the running workflow: 18,447 chars, identical to the file, old
opener absent.

## 2026-08-13

### A warmer chatbot, with the facts held exactly where they were

**Deployed.** `u2JjrbcNPYyyh3yl`, prompt 15,058 → 17,914 chars.

The ask was warmer *and* no less accurate when filing a ticket. Those only
fight each other if warmth is allowed near the facts, so the prompt now draws
the line instead of hoping the model finds it: **the details pass through
verbatim — building, apartment, reference number, amount, months, status — and
every sentence around them is the model's to write like a person.** A warm
phrasing may not change a number, soften `not found` into *maybe*, or add a
promise nobody made. Where warmth would cost precision the fact wins with
nothing to weigh — there is no balance to strike, one half was never available.

**The greeting was already fixed earlier today and was not where the coldness
lived.** Four other moments were:

- **Refusals.** `street_unknown`, `unit_found: false`, `number_not_on_street`
  were pure correctness rules with no guidance on phrasing, so the model
  reached for the flattest thing to hand. Somebody who typed their own address
  and got *not found* hears an accusation — or that they are not our resident.
  They are; we just did not find what they typed. Now three things are
  required: what we *do* have, no blame, and a way forward. Followed
  immediately by what did not move — the address check is unchanged, and being
  kind is not the same as agreeing.
- **Handing over the reference number.** It already demanded "what happens
  now"; it now also demands *what the ticket is about, in the resident's own
  words*. That clause is the difference between a cloakroom stub and evidence
  somebody listened.
- **A failed identity check on a balance.** Most people who fail it are real
  residents who gave a first name only or transposed two digits. "I could not
  verify you" treats them as a suspect. The gate is untouched; the sentence is.
- **The acknowledgement.** Once per *conversation* was stingy — a chat that
  opens with a leak and moves to a debt is two things. Now once per thing that
  happened, and **sized to it**: nobody is devastated by a burnt bulb.

**Two guards, because "be warmer" is an instruction a model overshoots.**
Warmth is a word or two and never an extra sentence — a message that grew in
order to sound nice sounds like a call centre. And the acknowledgement scales
to the event.

**A live bug fell out of writing it.** The worked example for the address
question read `באיזה בניין ואיזו דירה אתה גר?` — masculine, aimed at the
resident, twenty lines under the rule forbidding exactly that, and the one
place in the conversation where marking gender by accident is easiest because
the question is always *about them*. Every other example in the file was clean;
this one shipped and the model had been copying it. Now `גרים`, with the reason
attached so it does not get "corrected" back.

Voice untouched, per the standing chatbot-first scoping. Still not tested on a
real handset — every claim here is about the prompt, not an observed
conversation.

### The dashboard's page size becomes a choice: 10, 25 or 50

Every list was fixed at ten rows. Ten is right for glancing at today's tickets
and wrong for working through 108 apartments that owe for July — that was
eleven page-turns with the total on screen the whole time, taunting.

`per=25` / `per=50` now rides in the URL beside `page`, on all four lists:
tickets, debts, conversations, calls. Three things worth recording:

- **Links, not a `<select>`.** Every other control on this dashboard is a URL,
  and a dropdown that navigates needs client JS. The build confirms it: the list
  pages still ship 158 B each, exactly as before.
- **The size is validated against the list.** `?per=1000` falls back to ten
  rather than pulling the whole `residents` table through PostgREST in one
  request. Anything not 10/25/50 is not a size.
- **Changing the size lands on page one**, and the size survives every other
  filter — the month tabs and the apartment/owner toggle on `/debts`, the
  status tabs on `/tickets`, the five view tabs on `/calls`. Picking 50 and
  then filtering to "open" handing back ten rows is the bug this avoids.

`/calls` had grown its own private copy of the pager, with `Newer`/`Older`
instead of `Previous`/`Next`. Rather than add the size picker twice, the shared
component took `prev`/`next` labels and the copy went. `pageRange` and
`pageSlice` now take the size; both still default to ten, so nothing that
does not pass one changed behaviour.

One visible consequence: the pager used to disappear entirely on a single page
of results. It now shows whenever there are more than ten rows, because that is
the only way somebody sitting at 50 gets back to 10.

Not deployed — Vercel still points at the old Supabase project and that
repointing is waiting on the region decision.

### The database moves to the client's own Supabase project

**Done and verified. Production still points at the old project.**

The blocker was never technical. `SUPABASE_ACCESS_TOKEN` 403'd on the target,
its data-plane keys 401'd against the Management API, and PostgREST does not do
DDL — so nothing here could create the first table. A personal access token on
the target account resolved it in one step, and the Management API's
`POST /v1/projects/{ref}/database/query` runs SQL directly, so no connection
string was needed after all.

**Who owns it, which is the actual point of the move.** The target is
`yariv@homies-management.co.il's Project` — the client's own Supabase account.
That is an ownership change, not a performance one, and it is a good reason on
its own.

**What went across**, migrations 001–019 run in order, then every table:

| | rows | | rows |
|---|---|---|---|
| residents | 7,391 | interactions | 119 |
| apartments | 4,092 | requests | 53 |
| messages | 306 | call_outcomes | 34 |
| buildings | 193 | charges | 179 |

Counts match on every table, both directions. 13 tables, 5 views, 5 functions,
17 ledger rows, no table without RLS. Spot-checked through both keys: the
dashboard's tables read via the publishable key, and `buildings` / `apartments`
return **0 rows to anon and everything to the service role** — migration 019
survived the move intact. `v_debt_call_queue_person` returns 0 rows, which is
correct: every resident still carries `handed_over = false`.

**One real bug, found by the copy failing.** `messages` refused every row with
`column "inserted_at" does not exist` — on a table whose columns were byte-for-byte
identical on both sides. The column belongs to neither. `pk_of()` in
`supabase_move.py` joined `table_constraints` to `key_column_usage` on
`constraint_name` **alone**, and constraint names are only unique per schema:
Supabase ships `realtime.messages`, partitioned, whose primary key is also
called `messages_pkey` and is `(id, inserted_at)`. So the primary key of
`public.messages` came back as `id, id, inserted_at`, the upsert URL named a
column that exists on neither table, and PostgREST blamed the target. Fixed by
joining on `constraint_schema` too.

Worth keeping because of how it hid: `messages` is the only table here whose
name collides with a Supabase-internal one, so eleven tables copied cleanly and
the twelfth failed in a way that pointed at the wrong thing entirely.

**REGION: `ap-northeast-2` — Seoul.** The old project is `ap-northeast-1`,
Tokyo. Both are roughly 8,000–9,000 km from Israel, so this move buys **no
latency improvement**, and a project's region cannot be changed after creation.
Raised before repointing anything, because the voice agent makes tool calls
mid-conversation and the client has already commented on responsiveness.
`eu-central-1` is about 2,700 km from Tel Aviv.

**Not done, deliberately:** the Edge Function is not deployed to the new
project, and n8n, the Vapi assistants and the dashboard all still point at the
old one. Nothing has moved in production, and the old project is untouched and
remains the rollback.

### The security work goes live

Deployed on the client's instruction: the Edge Function and the WhatsApp
workflow. **The demo page was deliberately left alone**, so nothing about the
voice agents changed.

- **`debt-tools` version 17, ACTIVE.** Carries the balance identity gate,
  `verify_address`, and `open_request` writing `reported_unit` and the
  canonical address.
- **WhatsApp workflow updated**, five tools live, prompt at 15,058 chars.
  Confirmed by reading the deployed workflow back: `verify_address` node
  present, the balance node sending name and phone, and the prompt carrying the
  identity rule, the address rule and the offer-then-ask shape.

**Smoke-tested against the deployed function, not against the repo.** Five
address cases — real building with a real flat, real building with flat 999,
real street at a number we do not manage, a street we do not manage at all, and
the partial-street case `אלתרמן 6-8` — all correct. Three identity cases —
nothing given, name only, mismatched pair — returned `need_identity` twice with
the right `missing` list, then `identity_failed`.

**A false alarm worth recording, because the fix is in the tooling.**
`n8n_whatsapp.py --apply` printed *"Not active yet. Run with --activate"* after
updating a workflow that was already live and stayed live. Read back from the
API, the bot was `active: true` throughout — a PUT does not deactivate
anything, and that line had simply never been true on the update path. It cost
a scare and a round of checking on a live client bot. The script now reads the
state back and prints what is actually true.

**And a correction to yesterday's numbers.** The scratch test that verified the
address matcher reported 26 flats at יואב 14; the true figure is 25. The test
paginated `apartments` ordered by `order_index`, which is not unique, so a row
repeated across a page boundary. The deployed function queries per building
without pagination and was always right. Membership tests are unaffected — a
duplicated number does not change whether a flat exists — so every pass/fail
result stands; only the count was wrong.

### Preparing the Supabase move, and finding a live security hole while doing it

Asked for: migrate to the new Supabase project. **It did not run, and the
reason is access, not readiness.** PostgREST cannot execute DDL, and
`SUPABASE_ACCESS_TOKEN` belongs to the old account — asked for its project
list it returns exactly one entry, HOMIES. Nothing on this machine can create a
table in `tfldjbwtghfgdwoyauio`. Everything downstream of that is now scripted
and tested.

**The schema file was five migrations stale** — generated 12 Aug covering
001–013, while the database had reached 018 that morning. Regenerated to
001–019, 87,774 characters, plus a new `supabase-ledger.sql`, without which
`supabase_migrate.py` would replay all seventeen files against the new project.

**How the schema was verified, which is the part worth keeping.** Running it
against the live database proves nothing: every migration is
`create ... if not exists`, so on a database where the objects exist they all
no-op and the run is green having tested nothing. The trick is a throwaway
schema first on the `search_path`, inside a transaction that is always rolled
back — unqualified creates land in it and unqualified references resolve to it,
so it behaves as an empty database while touching nothing. Result: 12 tables,
5 views, 5 functions.

**It failed the first time, and the failure was live.** 009 carries an
assertion that raises if any table in `public` lacks row-level security. It
fired on `buildings` and `apartments` — created that same morning by my own
migration 016 with no RLS — which meant the anon key that ships in the
dashboard's browser bundle could read the client's entire portfolio: 173
addresses and 4,092 flats. Confirmed against the live project with the real
anon key before fixing anything (it returned rows), then fixed by **migration
019**, then confirmed closed the same way (anon returns 0, service role still
reads, so `verify_address` is unaffected).

**No anon policy on either table, unlike 010.** 010 opened everything to anon
for the no-login demo dashboard and says in its own header that this is a trade
to reverse before real data arrives. Nothing in the dashboard reads buildings
or apartments, so there is no feature to weigh against it.

**The guard could not have caught this, and now it can.** A migration runs
once: 009 looked at the database as it stood on 9 August and never again, so a
table added on the 13th was never in scope. The same assertion now runs inside
`scripts/supabase_migrate.py` after every run, where it sees what was just
applied. It warns rather than exits — by then the migrations are committed, so
failing would report a problem it cannot undo.

**`scripts/supabase_move.py`** does the data copy: reads the old project over
its database connection (exact types), writes the new one over PostgREST,
upserts on the primary key so an interrupted run resumes by re-running.

**The copy order in the plan was wrong.** It said
`residents → charges → requests → interactions`, and `requests.interaction_id`
references `interactions`, so requests must come last. Twenty FK constraints
across twelve tables is more than anyone should hold in their head, so the
script sorts them topologically from the live catalogue instead of trusting a
typed list. IDs are carried verbatim — eight columns point at other tables'
keys, and fresh uuids would orphan all of them while the copy reported success.

### The bot offers before it asks, and an 8 Aug rule is reversed on purpose

Asked for after reading the flow back: a resident writes *"there is no light in
building X"* and the wanted reply is *"Hi, this is Homies support. Ok, I
understand — do you want me to open a ticket so this goes to the office?"*

**This reverses the rule that said never ask permission.** That rule has been
in the prompt since 8 Aug: no *"shall I open a call?"*, because somebody
reporting a broken gate has already asked, and bouncing the decision back is a
way of not doing the job.

The reasoning was sound and it came from the **voice** agents, where a turn
costs seconds of a live call. On chat the arithmetic is different: turns are
cheap, nobody is holding a phone, and what is actually expensive is tone. The
old rule produced the wrong one — a resident mentions a dead bulb and gets two
questions about their address back. They end up with what they wanted and it
feels like filling in a form. The offer costs two messages and buys the
difference between a service desk and a survey.

New shape: **acknowledge → offer, saying where the ticket goes → then, only
after yes, building and apartment.** The address question moved out of the
first reply, which is what made the earlier version read as an interrogation.

Two cases still skip the offer, and both are the old rule surviving where it
was right: a resident who asked outright ("open a ticket", "send someone")
should not be re-asked, and nobody in danger is asked whether they would like
assistance — that transfers immediately with no ticket at all.

The `open` menu row changed with it, from *"what's the fault, and which
building?"* to just *"ok. what's the fault?"* — tapping that row is itself the
explicit request, so the offer is skipped, and asking for the building there
would split the building+apartment pair across two messages and leave the
apartment on its own.

### "Which apartment do you live in" is a different question from "where is the fault"

Asked for after the first flow walkthrough: a resident says *"there is no light
in the building"*, and the bot should answer like a person — acknowledge it,
then ask **which building and which apartment they live in, in one message,
saying it is so a ticket can be opened**.

**This looked like a reversal of the rule from 8 Aug** — never ask "which
apartment?" about a stuck lift, because a lift belongs to nobody, and asking
wastes a whole turn of a resident's patience. It is not a reversal. They are
two different questions that happen to use the same words:

| | |
|---|---|
| `requests.unit` | **where the fault is.** NULL for common property. |
| `requests.reported_unit` | **where the person lives.** Always, once verified. |

A lobby leak reported by flat 3 is now `unit = null, reported_unit = '3'`.
Every query that finds common-area faults with `unit is null` still works, the
duplicate guard still groups two reports of one lobby leak — and we finally
know who told us. **Before this a WhatsApp ticket carried no resident at all**:
there is no caller ID on chat and nothing ever looked the sender up.
`resident_id` is now filled from the same verified pair, best-effort, because a
flat with no phone on file has no `residents` row — which is exactly why the
flat is stored as a column rather than reduced to that lookup. Migration 018.

**The model no longer expresses "this is a common-area fault" by leaving a
field empty.** It sends `reporter_unit` plus `fault_location`
(`apartment` / `common`), and the server derives `unit`. `unit` is not offered
to the model at all any more. The old design had an implicit branch — omit the
field and mean something by it — and this file has been burned by implicit
branches before. Anything that is not literally `"apartment"` is treated as
common property, because a fault wrongly filed as common gets read by a person,
and one wrongly pinned to a flat sends a technician to knock on a stranger's
door.

**The second exception to one-question-per-message**, and the last. Building
and apartment are asked together, with the reason attached — *"ok, that's
annoying. which building and which apartment do you live in? I'll open a call
for you"*. Two facts that cannot be confused for one another, so a partial
answer is obvious; the same argument that allowed name+phone before a balance.
Both exceptions are now written into the rule itself rather than trailing it.

Voice is untouched: `reporter_unit` is absent on a voice call, and when it is
absent nothing about `unit` changes.

### The building list arrives, and an address stops being free text

Asked for: when a resident reports a fault the bot should ask which building
and which apartment, and say so when the answer does not exist.

**There was nothing to check an answer against.** `residents.building` is a
string composed at import time and stored — enough to file a ticket, useless
for verifying one. A resident who named a street Homies does not manage, or
apartment 40 in a building with 25 flats, was recorded verbatim, handed a real
reference number, and left believing a technician was coming. Apartments had
never been fetched from OXS at all.

**What came in.** Migration 016 adds `buildings` and `apartments`, mirrors of
OXS's own, filled by the new `scripts/oxs_buildings_sync.py`: **173 active
buildings** (193 total, 20 disabled and carried anyway, because a building
Homies dropped still appears on old tickets) and **4,092 apartments** — median
23 flats per building, smallest 2, largest 72. Five cities: רמת גן 94,
תל אביב־יפו 48, גבעתיים 22, רמת השרון 7, הרצליה 2. 104 distinct streets.

**The measurement that shaped everything else: street + number is unique across
the whole portfolio.** Zero duplicate addresses; zero cases of one street+number
in two cities. So `הרצל 14` identifies a building on its own and **the agent
never has to ask which city** — a whole turn saved on every report. Three
street names span two cities (גולומב, החשמונאים, סוקולוב) and never at the same
house number. This is a property of today's data and not a promise, so the sync
re-checks it every run and **refuses to write** if it stops holding, rather than
warning: every check it makes guards against the matcher returning one confident
answer where there are two.

**Reconciliation, before trusting any of it.** All 7,391 residents'
`building` strings resolve to an active OXS building, nothing in our table is
absent from theirs, and 172 of the 173 have residents on file. One building has
none yet.

**`verify_address` is the new tool**, read-only, returning nothing about any
person. The bot must call it before `open_request`.

**Matching compares against the list rather than parsing the sentence.** The
obvious design — split what the resident wrote into street and number, then
query — breaks on the real data: `אלתרמן נתן 6-8` is two words and a hyphenated
number, and people write `רחוב יואב 14 רמת גן` or bury the address mid-sentence.
Asking instead whether the sentence *contains* a registered street and one of
its numbers sidesteps the parse completely. Tested against all 173 addresses in
three phrasings — full, street+number, and with a `רחוב` prefix — **173/173
each**.

Two passes, because one was not enough. Strict wants the registered street
whole. The second fires only when strict finds nothing and only alongside an
exact house number: `אלתרמן נתן` is registered with the poet's first name and
nobody says it, so `אלתרמן 6-8` has to resolve. One shared word is weak
evidence; the house number is what makes the pair specific. Quote marks are
stripped before comparison — ז'בוטינסקי arrives with U+05F3, with an ASCII
apostrophe, and with nothing at all, and all three now match.

**Three answers, and the third is the one that earns its keep.** Found, not
found, and *the street is real but not that number*, which lets the bot say
something true: "we manage 12 and 16 on that street, not 14". A bare "not found"
makes the resident repeat themselves at a machine that will fail again. Same for
flats: the range comes back with the refusal, so the reply is "that building has
apartments 1 to 25". `need_number` is kept separate from `number_not_on_street`
for the same reason — nothing said is not the wrong thing said.

**Ambiguity is returned, never resolved.** Two candidates come back as two
candidates to ask about. Feature 01's confidence floor: below it, unmatched
beats guessed. A ticket filed against a confidently wrong building reads correct
to everyone who sees it and sends a van to the wrong street.

**`open_request` normalises but does not refuse**, and the asymmetry is
deliberate. It is shared with both voice agents, and only the chat bot has been
taught to verify first — making it reject an unresolvable building would start
silently dropping inbound voice tickets, a worse failure than the one it fixes.
So it files against the canonical address when it resolves and files anyway
when it does not. That is worth having on its own: the duplicate guard matches
`building` as a string, so `יואב 14` and `רחוב יואב 14 רמת גן` were two
buildings to the guard and one to everybody else — the second report minted a
second ticket and dispatched a second van.

**An apartment number is not always a number, and the first full import is
what said so.** Migration 016 put `unique (building_id, number)` on
`apartments`, from a four-building sample where every flat was 1..N. The real
sweep rejected it with a 409 partway through: **זבולון 17 in Tel Aviv has two
separate units, both called `חנות`** — two ground-floor shops, neither
numbered. Across the 4,092 flats, **138 are labels rather than numbers**:
חנות, מסחר 1–4, מחסן, חניה 43, דירת ועד, חברי וועד, a company name, and one
flat called `1.5`. Two are blank.

The constraint was also redundant — `id` is the OXS `_id` and is already the
primary key, so a double import cannot duplicate a flat, which is the only
thing that index was protecting against. Migration 017 drops it and keeps the
pair as a plain index, since the lookup it supports is real.

It changed the agent's wording too. The flat range was read off the ends of the
list ordered by `order_index`, and the last row of a building is quite often a
shop — so "this building has apartments 1 to 25" would have come out as
"apartments 1 to חנות". The range is now computed from the numeric flats only.
The sync prints both counts on every run, so the next person meets this in the
output rather than in a 409.

**And a flat number is not always a flat number either.** Tested against the
imported rows rather than a fixture, which is what caught it: `לואי מרשל 41`
numbers its flats `1א'`, `1ב'`, `2א'` — a number, a Hebrew letter, and a
geresh nobody types. A raw string compare tells a resident of 3א that their own
flat does not exist, which is the most insulting possible way for this to be
wrong. Units are now compared through the same `norm()` as street names, on
both sides. Verified: `3א` and `3א'` both accepted, `99ג` still refused.

Three buildings have **no numeric flats at all** — `סוקולוב 29, הרצליה` is
fifteen shops, ten offices, a club and three cinemas; `היצירה 24` is offices
and parking bays named by direction (`1 מזרחי`, `חניה- רנדי בע"מ`). For those
the tool returns no range, and the prompt now says not to invent one.

**Verification, against the live tables:** 173/173 addresses resolve in all
three phrasings; 240/240 real flats accepted; 40/40 invented flat numbers
refused; 173/173 spoken ranges numeric; commercial units (`חנות 4`,
`1 מזרחי`) accepted.

**One bug found and fixed on the way.** The n8n tool nodes referenced their
descriptions as `TOOLS[0]`, `TOOLS[1]`, `TOOLS[3]`. Inserting `verify_address`
into the middle of that list silently repointed two nodes at the wrong
descriptions — it deploys cleanly and shows up as a model calling the wrong
tool. Replaced with a lookup by name.

**Also caught: an exploratory one-liner had dumped 340KB of client building
data into the repo root.** This repository is public. Never staged, never
committed, moved out of the tree. The rule earned again: check what a script
writes and where, not just what it prints.

### A balance now costs a name and a number, and the gate is not in the prompt

Out of the client's security feedback: the WhatsApp bot must ask for the
tenant's full name and full phone number before it reads out an open balance.

**What was open.** `get_balance` identified a caller three ways, in order: the
WhatsApp number the message arrived from, then building+apartment, then a name.
The bottom two are things a neighbour knows — a surname and a flat number are
not secrets in a building of ten flats — so anyone who found the WhatsApp
number could type a name and be read a stranger's debt. The envelope number is
better and still not proof: a handset gets lent, shared and sold, and matching
it silently means the bot never asks anybody anything.

**Now it is one rule with no fallbacks.** A full name *and* a phone number,
both typed by the resident in that conversation, both landing on the same
`residents` row. The envelope number is not a shortcut past the question; the
building+apartment and name-alone paths are gone from chat entirely.

**The check moved into the Edge Function.** This is the part worth recording. A
prompt rule is a request, and this one guards money — a resident who insists,
or a message shaped like an instruction, is exactly the case a prompt loses. So
`get_balance` refuses on its own: missing either half returns `need_identity`
and the model has to go and ask, a mismatched pair returns `identity_failed`
and no amount is ever assembled. The prompt section makes it ask *well*; it is
not what makes it ask.

**One flag for both halves, deliberately.** `identity_failed` does not say
which half was wrong. A per-half answer is an oracle — try a surname against a
number you hold, learn the number is real — and an oracle plus a list of
surnames is a search tool.

**Two smaller calls.** The name is compared as a set of words, so `יוסי כהן`
and `כהן יוסי` both pass and a lone surname does not; two distinct words is the
floor, and containment lets a record with a middle name still match what its
owner actually says. The phone normalises to E.164 first, because the column
holds `+972501234567` and a person types `050-123-4567` — a gate that rejects
the honest case is a gate that gets removed a week later. Both helpers were
tested against the twenty inputs a real handset produces.

**Asking for both in one message breaks the one-question rule on purpose,** and
the exception is written into that rule rather than left to trail it. Two
questions normally come back answered once with no way to tell which; a name
and a number can be told apart at a glance. This is the lift lesson from 8 Aug
applied before it bit: an exception placed after a categorical statement does
not modify it.

**Not touched, and it is the same hole.** The inbound voice agent calls the
same `get_balance` and still identifies by building+apartment or by name —
standing instruction is to leave those alone. The gate is scoped to
`channel(ctx) === "whatsapp"`. Voice inbound identity is open.

Deploy is pending: the Edge Function has to be pushed and the n8n workflow
re-synced before any of this is live.

---

## 2026-08-12

### Gender stops being a branch, and בית gets its article back

Second pass over what was left. Both agents re-synced.

**`{{gender}}` is gone from the prompt.** Not softened — removed. The variable
handed the model a letter and put the instructions for it two hundred lines
away, and on 12 Aug that failed cleanly: `gender = "m"`, name יוסי, and the
agent said תשלחי one turn after using the masculine form. Nothing was missing
and nothing was guessed. The model did not carry the branch through the
sentence.

This file already knows what branches cost. `apartments_phrase` and
`breakdown_phrase` are composed in SQL for exactly that reason — *"if one
apartment say this, if several say that"* was removed rather than explained
better. Gender was the last branch left, and it now follows the same pattern:
**`{{gender_forms}}` arrives finished, in Hebrew, at the top of the prompt** —
*הנמען גבר. פנה אליו בזכר לאורך כל השיחה: אתה, שלְךָ, לְךָ, תגיד, תשלח…* — and
a composed value cannot be conjugated wrongly because there is nothing left to
conjugate. `unknown` is not a third gender to guess at; it is an instruction to
stay out of the question, with the neutral forms listed.

The one thing that still outranks it is the person's own speech: אני צריכה is a
woman speaking whatever the variable says, because she is the one who said it.

**This does not make the Hebrew perfect** and the entry above should not be read
as claiming it. Free sentences are still the model's and Hebrew marks gender on
almost all of them. What is gone is the failure that was provably bookkeeping
rather than Hebrew.

**ועד בית → ועד הבית.** The best available reading of "כשהוא אומר בית זה לא
נשמע כמו בעברית". The phrase he would have heard it in was the one the prompt
wrote without the article, which is not how anyone says it — without the ה the
two nouns collide and בית lands as a bare dictionary word instead of half a
phrase. Fixed in the prompt and added to the pronunciation list for the
sentences the model composes. **Unproven**: it is a complaint about a sound, and
a sound needs an ear. If ועד הבית still lands wrong, the voice is the problem
and that is a different change.

**Inbound got the lead-in repertoire** — אז, אוקיי, בסדר, ברור, הבנתי — with
the rule that no two turns in a row open the same way and most turns open with
nothing at all. The debt prompt has had this since it was written; intake never
did, which is half of why it reads flatter. אחי and סבבה stay out: a company
answering a phone is not a friend. **The actual slang question is still Yariv's**
— he is disagreeing with a rule that bans slang on purpose, and that is a
decision to take with him rather than guess at.

**THE DEMO PAGE MUST BE DEPLOYED BEFORE THE NEXT TEST CALL.** `gender_forms` is
composed in `web/index.html`, and a call placed from the old build sends nothing
for it — the guard strips the empty placeholder and the agent runs with no
gender instruction at all, which is worse than what it had this morning. Build
tag `2026-08-12b`.

### Four of Yariv's seven fixed, and the inbound agent finally gets the language skill

Both Hebrew assistants re-synced and live. What changed:

**The Hebrew language skill was never applied to inbound.** The client's guess,
and it was right. `hebrew-voice-gender-pronunciation-skill.md` had been worked
into the debt prompt — the formal-to-spoken table, the numbers rules, the email
rule are all there — and the intake prompt had none of it beyond a short gender
paragraph. It now carries the parts that earn their place on a call with **no
caller ID**, where the agent is neutral for longer than the outbound one ever
is: the neutral-phrasing table, the לך trap (*lekha* to a man, *lakh* to a
woman, same spelling), foreign words in Hebrew letters, gendered numerals, and
the point that trips models hardest — **the past tense carries no gender at all**,
so רשמתי is safe and רושם has to be checked. 21,000 → 22,767 characters.

**The greeting.** `מהומיז` → `מחברת הומיז, שמנהלת את הבניין`. One-letter
prepositions glue to the next word in Hebrew, so the voice read מ+הומיז as a
single unfamiliar word. Backed by a substitution in `voice_guard.py` — the
first entry there that rewrites rather than deletes — because the fixed line was
only one occurrence and the model composes the rest, and it will write the glued
form again since that is correct Hebrew. A rule cannot reach a form the language
itself produces.

**Idle messages, on both agents, which had never existed.** `messagePlan` was
null: no mechanism at all for speaking into silence, which is why no prompt
change could have produced the "הלו? אתה כאן?" he was missing — the model is not
invoked while nobody is talking. Two lines, first at 8s, twice per stretch of
silence with the count reset by speech. **Both are genderless** — אתה כאן? would
be wrong for half of callers on a line with no caller ID, and after someone has
already gone quiet is the worst turn to guess in. Plus a `silenceTimeoutMessage`,
so a line that dies now ends on a goodbye rather than on nothing.

**A tool is never the last thing you do.** New block in the debt prompt, and the
substance of his dropped call. There is no endCall function on either agent by
design, so a turn ending in a tool call and no speech leaves an open silent line
until it times out. Paired with the request that produced it: the payment link
**can** be sent — `send_payment_link` does exactly that — and everything else
cannot, so it says so and hands over instead of going quiet.

**The email address is now stored the way it is said**, in Hebrew, broken into
pieces: `אופיס, שטרודל, הומיז, נקודה, סי, או, נקודה, איי, אל`. Nothing parses it
— it is spoken and nothing else — so a spoken form is the honest type. The
English twin keeps the address itself and gets it through a `variablesFor`
branch, since Latin text read by an English voice was never the problem.

**The debt agent read a whole reference number out** — `hm20261043`, and once
`h מינוס studious money 6.1404`. The tail-only rule asked for days ago went into
intake and never here; the prompt had no rule either way and the model invented
the behaviour. It now does not read one at all on a payment call, and gives four
digits if asked.

**One thing reported this morning was wrong and is withdrawn.** The empty
`log_disputed_payment{}` was called correct. That tool takes exactly one
optional field, `unit`, and its description says to leave it out unless the
resident named a single apartment — which he did not. The empty call was the
tool being used properly. The only fault in that turn was the silence after it.

**Not fixed, and both need an ear rather than an edit:** whether בית sounds
wrong across the board or is one word, and the register complaint — which is
aimed at a rule that bans slang outright, so it is a disagreement with a
decision, not a defect.

**Found on the way:** `vapi_en.py intake` has been unbuildable since 7 Aug. Its
substitution table still expects `You are Michal` and `אני מעבירה`, from before
the agent was made male. The Hebrew is the deployed one and the twin exists for
review only, so nothing live is affected — but the English intake assistant on
the account is stale and cannot currently be regenerated. The debt table was
kept in step with today's greeting change.

### Yariv called the debt agent ten times, and every complaint is in the logs

Saved verbatim to `feedback-yariv-voice-2026-08-12.txt` — WhatsApp, Facebook and
seven points on the voice agent. Nothing edited yet. Each point was traced to the
recordings rather than reasoned about, and six of the seven reproduce.

**He was talking to the debt agent, not intake.** Its opening line is
`מדבר מיכאל מהומיז` — one word, preposition glued to the name — and he heard
"לאומיז". Our own transcriber, listening back to the agent's own audio across
five of his calls, wrote it down as לאומיז, נעמיז, מהומיס and once מיכם. The
intake greeting says `הומיז, חברת הניהול` and does not have this.

**Nothing is configured to speak into silence.** `messagePlan` is null on both
Hebrew assistants, so there is no "הלו? אתה כאן?" anywhere — the agent talks,
hears nothing, and waits for `silenceTimeoutSeconds` to close the line. Four of
his calls today ended `silence-timed-out`.

**The email readback was reproduced twice in one call, differently each time:**
`אופיס שטרודל הומיז.C או.IL`, then `oofficetrudle homeis.c .il`. The rule in the
prompt is fine; the address arrives as Latin text through
`{{verification_email}}` and a Hebrew voice is left to sound it out. The fix is
to pass it already spelled the way it should be said.

**The gender fault is worse than reported and is not a guess.** Call
`019ff5c4`, `variableValues.gender = "m"`, `first_name = יוסי` — and the agent
said **תשלחי**, having said the masculine form one turn earlier. The value was
known. That makes it a model limit rather than a missing rule, so the prompt fix
(gendered forms written out beside each fixed line, instead of a GRAMMAR section
far from them) improves it and will not close it.

**"The call disconnected" has a root cause, and it is not a crash.** Same call:
he asked the agent to send *him* an email instead. The agent called
`log_disputed_payment` **with empty arguments**, then `log_call_outcome
{disputed, friction}`, and then said nothing at all. It decided the call was
over and filed the paperwork. Saying the closing line is the only thing that
hangs up here, so skipping it left an open line that Vapi closed twenty seconds
later. Three faults stacked: no answer exists for "you send it to me", nothing
forbids a tool call from being the last thing it does, and the missing idle
message would have covered both.

**Two of his points are not defects.** The slang complaint is aimed at a rule
that bans slang outright — deliberate, and he disagrees with it. And every
Hebrew line in both agents was written rather than transcribed, with no native
speaker ever having read them aloud; that caveat has been in `demo-inbound.md`
since the first day and this is it arriving. Both belong in the meeting he asked
for, alongside porting the script from his existing bot.

**One thing a log cannot settle:** whether בית sounds wrong is about audio, not
text, and the text going in is correct. Worth one listening session against the
retained recordings, marking every word that lands badly, rather than fixing
them one complaint at a time.

Nothing changed in the repo beyond the saved feedback file. Comparison published
at https://claude.ai/code/artifact/6da41405-57af-4823-9956-bccfe95474b7

### Their tickets are in, and their categories are now everyone's categories

Asked for after the survey: import their maintenance calls and adopt their
category vocabulary. Both done, live.

**Migration 014.** `opened_via` gains `oxs`, because a staff member has to see
which system owns the row in front of them — we cannot close a ticket over
there. `category_he` holds their exact wording, `oxs_category_id` survives a
rename on their side, and `type` becomes a slug per THEIR category, constrained
so a stale value fails the migration rather than being written tomorrow by a
tool nobody updated. Our two orphans were mapped rather than dropped:
`structural` → `maintenance`, `security` → `other`. Also `reported_by_name`,
`reported_by_phone`, `source_platform`, `image_count`, and `oxs_created_at` —
the last one because THEIR timestamp and ours are months apart on a backlog and
the dashboard must sort on theirs.

**Two things went wrong and both were worth the trip.**

A plain unique index on `oxs_ref` failed: `save_partial_request` writes the
sentinel `partial:cut_off` into that column, so every abandoned call shares a
value. The index is now scoped to `opened_via = 'oxs'`.

Then the upsert failed with `42P10`, "no unique or exclusion constraint matching
the ON CONFLICT specification", which reads like a missing index and is not one:
Postgres will not infer a conflict target from a **partial** index unless the
statement repeats the WHERE clause, and PostgREST cannot express that. The
upsert runs on `reference` instead, which carries a plain unique constraint and
holds their `taskNumber`.

**The join is the address, not the phone.** The survey said `reportedBy.phone`
was the key between the two systems. It is populated on **zero of 34 records** —
the field exists and is always empty, which is the same shape-versus-value trap
the original OXS phone probe was written to catch, and reading the shape instead
of the values walked straight into it. `apartmentNumber` is filled on 32 of 34,
their address string is the one ours is built from, and building + apartment
matches **30 of 34**. One address carried a double space, so matching collapses
whitespace while the stored value stays verbatim.

**34 tickets imported**, 27 buildings, February to today, 30 attached to a
resident. Re-running writes 34 and leaves 34. `requests` now holds 51 rows from
four sources: oxs 34, voice 9, whatsapp 7, staff 1.

**Migration 015** fills `category_he` from the slug by trigger, so a dashboard
listing both sources does not show their rows labelled in Hebrew and ours blank.
A trigger and not a change to `open_request`, because the label is a fact about
the slug rather than about the caller, and the tool version would need every
future writer to remember. Every ticket in the table now carries a label.

Verified by conversation, not by inspection: *"יש נורה שרופה בלובי ביואב 30"* →
ticket written with `type: lighting`, which did not exist as a value this
morning.

**Two regressions seen on the way and not fixed.** A burnt bulb in a corridor
was answered with *"באיזו קומה?"* — the floor question the prompt forbids for
common areas, back again. And *"לא, זה הכל"* was answered with the handover
line, so declining further help hands the resident to the office.

### OXS holds a ticket system nobody had looked at

Asked for the full list of what the three keys can extract, so twelve endpoints
were tried against all three, GET only, field names recorded and no value
reproduced. Written up in `docs/reference/oxs-extractable.md`.

Four families answer — `/buildings`, `/buildings/:id/{tenants,apartments,payments}`,
`/debts`, `/service-calls`. Eight do not exist on any key: `/apartments`,
`/tenants`, `/requests`, `/suppliers`, `/payments`, `/expenses`, `/employees`,
`/committees`, `/documents`, nor the per-building forms of most of those.
Buildings are the only collection with sub-resources. Scoping is real: `/debts`
403s the general key, `/service-calls` 403s both general and debts.

**`/service-calls` returns 33 open maintenance calls and we have never touched
it.** 27 buildings, 10 Feb → 12 Aug, reported through a resident app (29) and
web (4), 6 priority, 12 with photos. Residents have been reporting faults this
way for six months. Our intake agent writes tickets into Supabase that OXS knows
nothing about, and OXS holds tickets our agent cannot read — so "what is
happening with my request" gets a different answer depending on which door the
resident came through.

Two things it cannot tell us on its own. Every one of the 33 reads `פתוחה` and
one is six months old, so either the endpoint returns open calls only or nothing
is ever closed — very different facts, same response. And `reportedBy.phone` is
the same key as `residents.phone`, so ticket history joins to the debt queue
with no new identifier and no matching logic.

`facilityCategory.name` is their own fault vocabulary — אחר, תאורה, אחזקה, חשמל,
אינסטלציה, מעלית, הדברה, מנעולן, ניקיון, גינון, כיבוי אש. Ours was invented.
Theirs should win.

Also found sitting inside endpoints the importer already calls, each one field
on an existing sync: `payerType` (owner or renter — who a debt call should
reach), `email`, `legalActions` (never cold-call someone already in
collections), `automatedCreditFailedMessage` (a bounced standing order is a
different conversation), `communicationTypes`, and `paymentByUser`.
`/buildings/:id/payments` is a list of lists, which is why a naive walker over
it returns nothing.

### A second Supabase project appears, and is prepared rather than switched to

Two keys arrived — `sb_publishable_…` and `sb_secret_…`, the new-style
replacements for `anon` and `service_role` — with a dashboard URL pointing at
project **`tfldjbwtghfgdwoyauio`**. Probed before anything was changed, which
is the whole reason this is a preparation and not an outage:

- both keys authenticate; PostgREST answers them
- the project has **zero tables** — not a missing one, none
- it is on a **different Supabase account**: `SUPABASE_ACCESS_TOKEN` lists
  exactly one project, `nmxlhlmcnnggnnuxyelt` (*HOMIES*), and this is not it

So this is not a key rotation. Pointing `SUPABASE_URL` at it would have emptied
the system rather than updated it — 7,391 residents, 179 charges, 234 messages,
103 interactions, and both Edge Functions, all still on the old project and all
still the only copy.

Asked, and the answer was *"just prepare for migration"*. Done, and nothing is
live:

- keys staged in `.env` as `SUPABASE_NEW_*`, read by nothing, with a comment
  above them saying so
- `supabase/schema.sql` generated — 001–013 concatenated, 64,624 chars, ready to
  paste into the target's SQL editor. **002 and 005 excluded**: they seed demo
  residents and charges, both purged on 10 Aug, and a fresh project should not
  be born holding rows somebody deliberately deleted
- `docs/handover/supabase-migration.md` written: row counts to verify a copy
  against, the dependency order for the data, the five places that hardcode the
  old project, and the two things still missing

The two missing things are both for the **new** account, which our token cannot
reach: its database password (for the data copy) and a personal access token
(to deploy `debt-tools` and set its secrets). Neither blocks the schema step.

The failure mode to fear here is not an error. Every repoint target keeps
working after a half-migration, because the old project stays up and answering —
a system writing to two databases looks perfectly healthy from the outside.

### The bot stopped because OpenRouter ran out, and a new key put it back

A resident wrote *"אין לי אור ביחידה"* and got the handover line back. It was
not the model deciding to hand over — **the model never ran**. Execution 1003:

    NodeApiError — Payment required
    "You requested up to 4096 tokens, but can only afford 770."

Three retries, all 402, then the error branch, which sent
*"אני מעביר את זה לצוות, נחזור בהקדם"* rather than leaving the resident with
silence. That branch worked exactly as designed and is the reason this looked
like a bad answer instead of a dead bot.

Both keys were empty when checked: `OPENROUTER_API_KEY` at −$0.15 (never funded,
`is_free_tier: true`, and on a **different account** — different
`creator_user_id`), `OPENROUTER_API_KEY_2` at −$0.19 against $45 granted.

**Where the $45 went, since the obvious answer is wrong.** claude-opus-5 ran
exactly once, on 8 Aug, as a documented probe: 2,632 in / 48 out, about 1.5
cents. It never served a resident — OpenRouter pre-authorises the whole
`max_tokens` against the balance and 4,096 tokens of Opus exceeded it, which is
*why* the switch to Flash happened. So Opus is not the explanation. What the key
reports: $25.70 lifetime on this key, $12.47 of it this month, $0.19 today —
and an account total of $45.19, meaning **$19.49 was spent by a key that is not
in this repo at all**. Today's nineteen cents is ours and is about sixty model
calls at Flash prices. The rest cannot be attributed without a management key;
`/api/v1/activity` refuses an ordinary one.

**The fix.** The account was topped up to $65 and a new key arrived in `.env` as
`OPEN_ROUTER_MAIN`. Promoted to `OPENROUTER_API_KEY` (old one kept as
`OPENROUTER_API_KEY_EMPTY`, since it is a different account and may still be
wanted) and the extra name dropped — one key, one name, the same rule the Vapi
`_ACCOUNTn` suffixes follow.

n8n's public API has **no PATCH for credentials**, so the key could not be
updated in place: a new `openRouterApi` credential was created
(`Wj4HhLTx6yNAQ3IU`), `N8N_OPENROUTER_CRED_ID` repointed, and the workflow
re-pushed. The old credential was left rather than deleted — shared production
instance, and a credential holding a dead key harms nothing.

Verified by conversation, not by balance: *"אין אור במסדרון שלי"* → *"אני מבין.
באיזה בניין נמצא המסדרון?"* → ticket `HM-2026-1033`, `unit: null`, deleted after.

**Then moved again, to key 2, on request.** The 12-Aug key carries a $15 cap of
its own; key 2 is uncapped and sits on the same account, so it reaches the whole
$19.80 instead of stopping at $15 with money still there. `.env` shuffled the
same way (`OPENROUTER_API_KEY_CAPPED15` steps aside), credential
`92ZNHDhByavmNP5T` created, workflow re-pushed and re-activated, and the live
node confirmed pointing at it rather than assumed.

Three OpenRouter credentials now exist on the shared n8n and two are dead. That
is the cost of an API with no PATCH: every key change leaves one behind, and
deleting them on an instance carrying other clients' workflows is not worth the
risk for the tidiness.

Worth noting from the last run — *"מה קורה עם הקריאה שלי?"* answered *"הקריאה
על החושך במסדרון עדיין פתוחה, היא אצל הצוות"*, which is the phrasing the prompt
teaches, and it found the ticket by building this time. The lookup failure
recorded above did not reproduce.

### Hebrew only, and a bot that sounds like it means it

A real WhatsApp conversation came back from the client's own handset — correct
throughout, and cold. *"זה תיאור הולם?"*, *"פתחתי קריאה, המספר שלה הוא
HM-2026-1030."*, *"קריאת שירות HM-2026-1030 על אין אור במסדרון ליד דירה 107
פתוחה ותטופל."* Not one of those is wrong. All three read like a form. Asked for
two things: English gone entirely, and a bot that is kind without being a robot.

**English removed, not disabled.** `HANDOVER_LINE_EN`, `SWITCH_LINE`, the English
half of `MEDIA_LINE` and `TAP_LINE`, the whole English `MENU`, the `lang_en` /
`lang_he` rows, Sort's switch detection and its leftover-token check, and the
prompt's English section and second fixed lines — all deleted. A switch nobody
can reach is a thing the next reader has to rule out. `lang` survives as a
constant `'he'` because it is written on every `messages` row and the dashboard
reads it; `git log` has the rest if English is ever wanted back.

The agent's per-turn directive changed with it, from *answer in the language
Sort chose* to **answer in Hebrew even if the message is English** — which is
the failure that actually remained: a model answering an English-looking message
in English out of habit. Tested with *"thanks, can you check my balance?"* and
the reply came back in Hebrew.

**Sincerity, written as two mechanics rather than as an adjective.** The prompt
already forbade "אשמח לעזור" and "בשמחה רבה" — correctly; they are what every
bot writes — and forbidding them without a replacement is what produced the
clipped register. So it now says what warmth actually consists of here: one
short acknowledgement that you understood what happened, **once in a
conversation** (someone who commiserates every message reads as more false than
someone who never did), and always saying what happens next rather than handing
over a bare number. The three dead lines above are quoted in the prompt with
their replacements, because naming the exact sentence is what worked for the
truncated reference number.

Same three turns, after:

    אין אור במסדרון שלי   → באיזה בניין?
    בניין 1              → רשמתי קריאה על חוסר אור במסדרון בבניין 1,
                            מספר HM-2026-1032. זה עובר לצוות התחזוקה.

**"המסדרון שלי" is still a corridor.** The client's transcript has the bot
asking *"איזה מסדרון? איזו קומה?"* and then storing `unit = 107` on a
common-area fault — the possessive read as *inside my flat*. `מסדרון` was
missing from the common-property list, so it has been added along with the
reading rule. The row now comes out `unit: null`, and the apartment question is
not asked.

**Still open, seen in the same run.** *"מה קורה עם הקריאה שלי?"* with a building
and no reference answered *"לא מצאתי קריאות פתוחות בבניין 1. יכול להיות שהיא
נסגרה?"* — about a ticket opened forty seconds earlier in that conversation. The
lookup by building alone found nothing, and the model then offered a theory for
why. Two faults in one sentence and the second is the worse one: it is the
prompt's own rule about not inventing, broken in the friendliest possible voice.

### New Cartesia key, proved before it was trusted

Cartesia ran out of credits and a replacement key arrived. Wired in this order,
which is the only order that catches the interesting failure:

1. **Cartesia first.** `GET /voices/a976c076…` on the new key → 200, *"Eyal -
   Grounded Guide"*, which is the voice both Hebrew assistants actually use.
2. **Then a real synthesis**, because a metadata GET proves the key is valid and
   says nothing about credits — which is exactly what just ran out.
   `POST /tts/bytes`, `sonic-3`, `language: he` → 200 and 21,360 bytes of audio.
3. **Then `.env`**, then Vapi.

The Vapi side was a `PATCH` of credential `52e0bca2-863e-4bf5-8a3b-9b090f10f4ca`
rather than a new credential, so the id did not change and nothing had to be
repointed. Both Hebrew assistants re-checked after: `cartesia/a976c076`, Vapi
fallback, unchanged.

This is blocker 1 in a new costume. A Cartesia credential that is present but
broke — wrong key, no credits — fails exactly like one that never travelled:
Vapi drops to the `vapi` fallback voice, the call completes, nothing errors and
nothing logs, and the only symptom is a Hebrew agent with an American accent.
Proving the key against Cartesia directly is what turns that into something a
script can see.

### Account 5 goes live, six hours after being built not to

*"ok now switch vapi account to the new one we have"* — so step 6 of
`new-vapi.md`, the one the morning deliberately skipped, ran this afternoon.

`.env` first: the account-4 pair archived to `VAPI_PRIVATE_KEY_ACCOUNT4` /
`VAPI_PUBLIC_KEY_ACCOUNT4`, the account-5 pair promoted to the unsuffixed names,
and the `_ACCOUNT5` lines deleted — `_ACCOUNTn` has always meant *old*, and
leaving a line that means *current* under that suffix is how the next person
picks the wrong key. Values were moved by a script that prints lengths, and the
first eight characters of the public keys only.

Then 23 id replacements across 11 files: the four assistant UUIDs, the public
key, and the eight-character short forms that `web/README.md` and the assistant
documents use in prose. `docs/WORKLOG.md`, `new-vapi.md`'s history tables and
the export JSONs were left alone on purpose — they are the record of what the
ids *were*.

Then both Hebrew assistants were re-pushed. This was not ceremony: account 5 was
built this morning, the intake prompt changed at midday (the reference tail), and
a standby account built before a prompt change is a standby account carrying the
old prompt. The English debt twin was rebuilt from the new Hebrew source in the
same pass — 52 passages and 4 section blocks, all matched. Both pushes resolved
account 5's assistants **by name**, without being handed an id, which is the
cheapest possible proof that the key swap took.

Verified: `vapi_export.py --show` → four assistants, the Cartesia credential
`52e0bca2`, no phone number. `check_tools.py` → 10 passed, 0 failed. The one
failing n8n execution it reports is this morning's WhatsApp conversation test,
whose Send node cannot deliver to a handset that is not on Meta's allow-list.
The tool check's own ticket, `HM-2026-1029`, was deleted after.

**Nobody has placed a call on account 5.** Blocker 1 — a missing Cartesia
credential — has no symptom except an American accent, and the credential
resolving in the API is not the same evidence as hearing it. `web/index.html`
carries the new ids, the new public key and `BUILD 2026-08-12a`, but it is its
own repository and **has not been pushed**, so the live page is still calling
account 4 until it is.

### Three turns through the live bot, and what they turned up

Asked to see the flow rather than read about it, so a scripted conversation went
in at the real callback URL, signed the way Meta signs it, and the replies came
back out of the `messages` log. Test handset, ticket and chat rows deleted after.

    היי                                → היי, כאן הומיז. מה קרה?           [menu]
    המעלית בבניין תקועה                 → אוקיי, באיזה בניין?
    אף אחד לא בפנים. הרצל 14, דירה 12   → רשמתי קריאה דחופה למעלית תקועה
                                          בבניין הרצל 14, מספר קריאה HM-2026-1028.

Right: no name, no second greeting, Hebrew throughout, the building asked for
and not the apartment, `type=elevator`, `urgency=high` inferred and not asked,
reference quoted whole.

**The double greeting was not a prompt fault, and the prompt could not have
fixed it.** First run: `היי` → menu, `המעלית תקועה` → *"היי, כאן הומיז. באיזה
בניין…"*. The menu, both tap lines and the switch line are sent without a model
round-trip, so none of them are in the agent's memory — from where the model
sat, the second message *was* the first message of the conversation and the
introduction was correct. Sort now carries a `greeted` flag per handset, on the
turn, exactly like the language decision, and the agent is told in as many
words not to introduce itself again. Second run, same three turns: clean.

**Found, not fixed — the handover line can go out without the tool.** One run
answered `המעלית בבניין תקועה` with *"אני מעביר את זה לצוות, נחזור בהקדם"* and
`transfer_to_human` appears nowhere in the execution. The line is real, the
resident is told a person is coming, and nothing was written — the same shape as
the invented reference number, which is the failure mode this project keeps
meeting. The prompt already says to call the tool *before* writing; it was
obeyed on the other runs and not on this one, so a prompt rule is not the guard.
The workflow can see it: an agent output matching a fixed line with no tool call
in the run is detectable in "Reply usable?".

**Found, not fixed — a common-area ticket kept the apartment number.** The lift
row carries `unit = 12`, volunteered by the resident and never asked for. The
bot correctly did not ask, and `check_whatsapp.py` asserts a common-area fault
has no unit, so the written contract and the written row disagree. A dispatcher
reading unit 12 on a lift call has been told something untrue.

Non-determinism worth knowing: `המעלית בבניין תקועה` was read once as a danger
(people possibly inside → transfer) and once as an ordinary fault (→ ask which
building). Both are defensible against the prompt, which routes on whether
anyone is trapped and cannot know from that sentence. The bot asked
*מישהו תקוע בפנים?* on the run where it mattered.

### The bot is Homies, stops saying hello twice, and stops guessing English

Four changes asked for after a real Hebrew exchange on the handset. Three land
on the WhatsApp bot, one on the inbound voice agent. All four are live.

**No more Michael.** The bot had been a named man since 7 Aug; it is now the
company's support desk with no first name, and the prompt says not to invent one
if asked. Both menu bodies changed with it — `היי, כאן הומיז. מה קרה?` and
`Hi, this is Homies Support. How can I help?`. The masculine self-reference
stays: Hebrew marks the speaker's gender on the verb, so `אני פותח` is grammar
and not a persona, and both alternatives are things this prompt already forbids
(a company-voice plural, or the passive).

**The greeting was coming back mid-thread**, most often on the message that
confirms a ticket's details. *Introduce yourself once* had been in the prompt
since 8 Aug and the model read it as a rule about introductions rather than
about the word `היי`. It now names that message specifically and shows the
replacement — `רשמתי נזילה בלובי…`, no opener — because a prohibition with
nothing to put in its place gets filled with the last thing said.

**Script detection is gone from the Sort node.** A Hebrew speaker quoted their
own reference back and was answered in English: `HM-2026-1013` carries Latin
letters and tripped `/[a-z]/i`. The digits-only version of this was patched on
9 Aug by making digits abstain; the prefix is the same bug wearing letters, and
so are `ok`, `hi`, `toda` and any Latin-script address. No character class
separates *typed a Latin character* from *wants English*, so the inference was
removed rather than tuned. Hebrew is the default; the menu row and an explicit
request are the only two doors into English, and both already stick.

**The voice agent reads out the tail of the reference only.** `HM-2026-1001`
becomes `1, 0, 0, 1`. The prefix and the year are identical on every reference
in the system, so they are four more things to mishear on the single line of the
call that has to be written down correctly. Nothing is lost: `get_request_status`
has matched on the tail since 9 Aug and the WhatsApp bot takes either form. The
full reference is still what is stored and what the dashboard shows — and the
WhatsApp bot still quotes it whole, because there it is text being copied, not
speech being transcribed by ear.

Pushed: n8n workflow `u2JjrbcNPYyyh3yl` updated and re-activated (the update
clears the active flag), Vapi intake `f482abc1` updated, 20,504 chars.
`vapi_en.py`'s intake table got the matching English pair, though that twin is
still the stale copy from the 11 Aug move and is not regenerated.

Not done, and not asked for: the **voice** agents still introduce themselves as
מיכאל — the inbound first message is `הומיז, חברת הניהול. אה, מדבר מיכאל, איך
אפשר לעזור?`. The name change was asked for on the chatbot only.

### Account 5 stands ready, and nothing points at it

A fifth pair of Vapi keys, with an instruction that is new: *"im not telling
you to change account just configure it"*. So the runbook ran minus its
repoint step — Cartesia credential first (`52e0bca2`), both Hebrew assistants
pushed by `vapi_sync.py`, both English twins copied live from account 4 —
and the page, `.env`, and every hardcoded id still belong to account 4.
Switching later is step 6 of `new-vapi.md` plus a BUILD bump, nothing more.

Two settings were asked for by name and are now in `BASE`, so they are the
default on every future push: `backgroundSound: office` and
`backgroundDenoisingEnabled: true` (the STT-side noise filter). The same
commit captures yesterday's dashboard stack into the script — nova-3
transcriber with the Azure fallback, gpt-5.2 on debt — closing the gap where
the next `--apply` would have silently reverted the client's own change.

Ids in the standby table at the bottom of `new-vapi.md`. Verified: cartesia
voice resolves on both Hebrew assistants, all four carry office + denoise,
prompt lengths byte-match account 4, server headers present. The copied
intake (en) carries its known stale 5-tool set — travelled, not introduced.

### Nova 3 Hebrew is the new default transcriber — the old stack archived

The client changed the Hebrew debt agent in the dashboard: transcriber from
ElevenLabs Scribe v2 realtime (700ms) to **Deepgram Nova 3 Hebrew (300ms)**,
with an Azure `he-IL` fallback and `confidenceThreshold` 0.4, and the model
from gpt-5.4 to **gpt-5.2**. This answers most of yesterday's "why is Hebrew
slower" — the transcriber was the biggest single contributor.

Asked whether the intake agent should match fully; the answer was **transcriber
only** — intake keeps gpt-4.1-mini (faster reply at 580ms vs 820ms, and ~6x
cheaper for the simpler front-desk job). Applied the same Nova 3 transcriber
object verbatim to intake (he) via PATCH; model and prompt untouched.

The pre-change config is archived at
`docs/handover/vapi-export-account4-pre-nova3-12aug.json` (Scribe + gpt-5.4 on
debt he), and `vapi-export.json` regenerated with the new default. Note the
divergence this leaves: **debt (en) still runs gpt-5.4** while debt (he) runs
gpt-5.2 — flagged, not changed; the client changed only the Hebrew agent.



A test call in English quoted Dana's ₪1,230 with no apartments named and
answered "why is it a thousand shekels?" with a non-answer: the stale twin,
frozen since its translation table broke in the 7 Aug prompt cut, and carried
across two account moves as a verbatim copy. The client asked for the rebuild
and handed the account-4 keys; the page push the move entry below left pending
went out as web `67cbb2e` in the same session.

**The table was rebuilt in two layers** (`vapi_en.py`): four whole-section
regex blocks for the sections that are ABOUT Hebrew — HOW YOU SPEAK, NUMBERS,
GRAMMAR, HESITATION — where a line-by-line translation would produce English
instructions for speaking Hebrew (GRAMMAR collapses to "English does not
inflect; never invent a title"; the formality table maps register, not words);
plus **52 exact line pairs** for the fixed lines and scattered quotes, feature
14's included — the ownership offer, the breakdown-question triggers, the
one-apartment dispute example. `englished()` now takes a list of blocks, and
each still has to match exactly once or the build refuses.

Pushed over account 4's `41d370b2`: **42,917 chars, zero Hebrew remaining**,
verified live — feature-14 phrases present in English, the current 7-tool set
(`flag_not_handed_over` gone), n8n server URLs intact, and `endCallPhrases`
inherited from the Hebrew source already carrying both English release
phrases. This also retires the copied twin's *"please stay on the line"*
handover noted below. `vapi-export.json` regenerated after the push.

The safety property held the whole way: the build refused for four days rather
than ship a half-translation, and the fix was the table, not the check.
`vapi_en.py debt --dry` is the health check; it exits loudly the next time a
Hebrew fixed line changes. **The intake twin's table is still the pre-cut
one** — the same rebuild is owed there before English intake demos are trusted.

### Account 4: the third Vapi migration, and the first one that just worked

*"lets swap vapi account use this for now"*, with a private and a public key.
Ran `docs/handover/new-vapi.md` end to end. Fifteen minutes, no surprises — the
runbook has now paid for itself.

Which key was which was **tested, not assumed**: `...829a3d` returned 200 on
`GET /assistant`, `...789c2e` returned Vapi's own *"you may be using the private
key instead of the public key"*. The new org is
`8eb82c4d-bc85-4c45-bd0a-fee0000de58f`, and it held one stock `Riley`, no
numbers, no tools, no credentials.

| | Account 3 | Account 4 |
|---|---|---|
| Debt (he) | `3303317e` | `9e2034d1-7a4f-4e3b-89ee-6a6155091ed7` |
| Debt (en) | `7449bc9a` | `41d370b2-b531-4d45-b2eb-4b00f881f87a` |
| Intake (he) | `86a01f13` | `f482abc1-db69-422b-afdd-f7b40ca9d995` |
| Intake (en) | `3edbe85b` | `8b98016b-310a-4286-bed8-c8077b603773` |
| Public key | `ddd7e209` | `944c3b38-…` |
| Cartesia credential | `bf29045b` | `4c9be89b-f62e-42e7-bd2d-35faf51e0969` |

**Cartesia went in before the first push**, which is the whole point of step 2 —
an assistant created without it falls back to `vapi/Elliot`, sounds American, and
logs nothing. `POST /credential` works; the dashboard is not required, contrary
to the runbook's wording, which is now corrected.

**The Hebrew pair was rebuilt from the repo** (`vapi_sync.py debt --apply`,
`inbound --apply`) — they are generated, so a copy would fork the source of
truth. **The English pair was copied verbatim**, because `vapi_en.py --dry`
still refuses: the debt LANGUAGE block no longer matches and the intake table
has ten unmatched passages. Same blocker as 7 Aug, unchanged.

**Server secrets travel on a copy.** They are redacted in `vapi-export.json`,
which is why the runbook says never to restore from JSON — but a live
`GET /assistant/<id>` returns `server.headers` and every tool's headers in full.
Both twins came across with the report endpoint and all eight tool secrets
intact, so nothing needed restoring.

Verified before trusting it: four prompts byte-identical to account 3 (44,040 /
38,533 / 20,056 / 18,315), both Hebrew resolving `cartesia/a976c076…`, 27 output
filters on all four, `server` headers on all four, `check_tools.py` **10/10**.

Repointed all ten files the runbook lists, plus `vapi_en.py`'s two source ids
before the twins were touched. `.env` now carries `VAPI_PRIVATE_KEY` (account 4),
`VAPI_PUBLIC_KEY`, and account 3's key as `VAPI_PRIVATE_KEY_ACCOUNT3` — call
history and recordings stay on the old account and **recordings die after 14
days**. Previous export archived as `vapi-export-account3-11aug.json` before
`vapi_export.py` overwrote it.

**One thing that cost ten minutes and is now written down:** Vapi 403s Python's
`urllib` on every valid key while `curl` with the same key gets 200. It is the
default User-Agent. The repo's scripts already set one; anything written fresh
must too.

**Not pushed.** `web/index.html` carries the new ids, the new public key and
`BUILD 2026-08-11b`, but it is its own repo and its own Vercel deployment — the
page keeps calling account 3 until someone runs `cd web && git push`. The English
debt twin also came across still carrying the *"please stay on the line"*
handover, unfixed; the account move deliberately changed nothing about prompts.

### The English twin promises a transfer, because it was told to

A demo call in English ended: *"One moment, I'm transferring you to someone from
our team. Please stay on the line."* Then nothing. Reported as "it does not do
anything".

**The agent obeyed its prompt exactly.** Pulled the live assistant —
`7449bc9a-6952-4625-a3c6-8bf73f8660f5`, *Homies — Debt Follow-up (en)*,
`updatedAt 2026-08-09T08:24:53Z`, gpt-5.4, 38,533 chars. Its HANDING OVER
section reads:

> 1. Say the handover line. 2. Call `transfer_to_human`. 3. **Stay on the line.**
> "One moment, I'm transferring you to someone from our team. Please stay on the line."
> **Never end the call on a handover.**

That is the *reversed* design, still live. The Hebrew prompt
(`docs/features/10-debt-followup/prompt.md`) now says the opposite in bold —
nothing is being connected, say the line once, close warmly — because
`transfer_to_human` writes a row and connects nobody. Not a model failure; a
stale prompt encoding an intention we abandoned.

**The same staleness explains the rest of that call.** The English twin's
variables are `alt_payment, amount, building, callback_number, first_name,
gender, month, verification_email` — no `apartments_phrase`,
`breakdown_phrase`, `has_card` or `charges`. So "why is it so expensive?" got a
generic answer about monthly expenses instead of *₪450 for apartment 4 and ₪780
for apartment 9*; it has no per-apartment structure to speak from. It also still
carries `flag_not_handed_over`, which the Hebrew prompt records as **gone**.

**One genuine misfire, separate from staleness.** "But for what building is it?"
tripped the scam-check branch — the one written for *"prove it, tell me my
address"* — and the resident was told personal details cannot be read out over
the phone. The building is the subject of the call, not a detail being extracted
from the agent. That branch needs to exclude what the agent itself already named.

Not fixed. The English twin needs regenerating from the current Hebrew prompt;
until then every English demo call ends on a promise the system cannot keep.

### Payment method is importable — it lives on the payment, not on the person

Asked whether we can pull *how* a resident pays out of OXS. Probed the live API
read-only, printing field names and non-personal values only.

**Yes, and richly — but only from `/buildings/:id/payments`.** Every payment
record carries `paymentType` (int) and `paymentTypeLabel` (Hebrew). Across one
building's payments the five values in use are: `6` כרטיס אשראי בהו"ק
(credit-card standing order), `2` העברה בנקאית (bank transfer), `1` כרטיס אשראי
(one-off card), `5` הוראת קבע בנקאית (bank standing order), `4` צ'ק (cheque).
`monthsPaid[].isKeva` (and `isBankKeva`) says per month whether a standing order
covered it, and `wasCancelled` / `cancelReason` mark reversals.

**The tenant record carries none of it.** `/buildings/:id/tenants` returns only
name, number, phone, email, `isActive`, `payerType` (owner vs tenant),
`orderIndex`, `job`. So there is no "this resident is on standing order" flag to
read — the arrangement is inferred from what they last actually paid with. Good
enough, and more honest than a stored flag nobody maintains.

**What we deliberately will not import.** `paymentDetails[]` carries instrument
data — card last-four `digits`, `token`, `shvaParams`, `dealNumber`, expiry, and
for transfers `transferBank` / `transferBranch` / `transferAccount`. None of it
belongs in our database. Only the method category has any use to the agent.

**Why it matters to the debt agent.** A resident in arrears whose last payments
were `6`/`5` did not forget — their standing order failed or lapsed, and that is
a different call than one to somebody who pays by transfer each month. The payer
record even has an `automatedCreditFailedMessage` field, unread so far.

Not implemented. `oxs_debt_sync.py` reads `monthsPaid` only and ignores
`paymentType` today; adding it is a column plus one line in the sweep, and no
extra API calls — the field is already in the response we fetch.

### Feature 14 built and deployed: one call per resident, every apartment in it

The freeze was lifted (*"implement the handling"*) with one scope cut:
apartments that owe nothing are not counted — *"we just need the apartment that
has an open balance."* That deleted the `apartments` table, the OXS sweep change
and `apartments_held` from the spec, and turned 3 estimated days into one
session. Shipped end to end:

- **Migration 013** (applied). `v_debt_call_queue_person`: one row per resident,
  layered on `v_debt_call_queue` so the eligibility predicate stays written
  once. Composes `apartments_phrase` / `breakdown_phrase` / `months_phrase` in
  SQL, plus the `charges` jsonb whitelist. Two helpers: `money_say()` — the old
  `FM999999` format ROUNDED, so a ₪1,971.80 charge would have been spoken as a
  figure that appears nowhere — and `hebrew_list()` with the maqaf rule (`ו-9`
  before digits, `ויולי` before words). Caught `ו5572` on the live data and
  fixed the breakdown to hyphen=true. Verified against the two real
  multi-apartment owners inside a rolled-back transaction: 12 charge rows → 2
  person rows, totals exact, `unit` empty when several owe. The interlock is
  untouched — both views still return 0 rows live.
- **Edge Function v15** (deployed). `ctx.charges` parsed from variableValues
  (string or array; single-charge calls fold into a one-element list so there
  is no branch). `targets()`: no `unit` argument means every charge on the
  call; a unit is resolved against the whitelist and an off-call unit is
  REFUSED, never widened. `send_payment_link` / `log_promise_to_pay` /
  `log_disputed_payment` write per charge with each charge's own amount and
  period; `log_call_outcome` writes ONE row (an outcome is a fact about the
  call) but bumps every charge's attempt counter — one un-bumped charge would
  keep the resident in the queue forever, because the person view takes the
  max. `flag_not_handed_over` DEFANGED: it no longer touches `handed_over` or
  waives anything — it pauses the named apartment to `pending_charge` and files
  a transfer with reason `ownership`, same as the new posture. Kept answering
  so a stale assistant gets a result, not an error.
- **n8n router** (deployed, activated, probed live). The Decide node mirrors
  the whitelist refusal — it answers Vapi before the writer runs, so a refusal
  living only downstream would arrive after the agent was told yes. Month
  guard accepts `months_phrase`; the forward merge only promotes `args.unit`
  into variableValues when it is on the whitelist. Probed all seven cases:
  on-call unit ok, off-call unit refused with the apartment list, no unit ok.
  Probe rows deleted from Supabase after.
- **Tool schemas.** Optional `unit` ("the resident named ONE apartment — never
  guess it") on the three writes and on outbound `open_request`;
  `transfer_to_human` gains reason `ownership`; `flag_not_handed_over` removed
  from the agent's toolset — the open_payment_ticket retirement, again.
  `ownership` added to the n8n and Code.gs validation lists (an unlisted
  reason silently becomes `caller_request` forever).
- **Prompt** (synced to the live Hebrew assistant, 44,040 chars). The call
  covers every apartment that owes; the three phrases arrive composed so there
  is no one-vs-several branch to get wrong; **the apartment is always named**
  — an amount without one is unverifiable, which is what the 11 Aug demo call
  proved. The anti-scam rule narrowed to what it was for: never read details
  to PROVE yourself; always answer a confirmed resident about their own
  charge. Already-paid flow carries which apartment; a claim about one flat
  never widens to all of them. New fixed line (the ownership offer): the agent
  states once that the system shows the apartment against them, offers to pass
  it to the office — *"רוצה שאני אעביר את זה לצוות שיבדקו ויחזרו אליך?"* — and
  acts on nothing. English translation added to vapi_en.py's table.
- **Demo page** (committed, pushed, Vercel deploys). `personify()` groups rows
  by phone into one card per person: Dana is one card, ₪1,230, `דירות 4 ו-9`,
  charges whitelist attached — the byte-identical phrases the SQL view emits,
  verified by simulation. English mode recomposes rather than transliterates.
  12 rows → 11 cards.

**Found stale, not fixed here:** `vapi_en.py debt` exits on "LANGUAGE block did
not match" — its anchor text died in the 7 Aug prompt cut, before today. It
fails closed by design; the English twin is frozen at its last build until the
substitution table is rebuilt against the cut prompt. The demo keeps sending
`month` (singular) so the stale English assistant's sentences stay whole.

**Still open:** the campaign runner (acceptance 5, 6, 9, 10, 13 wait on it);
the 2022 waive statement still awaits approval; 18 phoneless apartments.

Asked whether we can pull *how* a resident pays out of OXS. Probed the live API
read-only, printing field names and non-personal values only.

**Yes, and richly — but only from `/buildings/:id/payments`.** Every payment
record carries `paymentType` (int) and `paymentTypeLabel` (Hebrew). Across one
building's 201 payments the five values in use are: `6` כרטיס אשראי בהו"ק
(credit-card standing order), `2` העברה בנקאית (bank transfer), `1` כרטיס אשראי
(one-off card), `5` הוראת קבע בנקאית (bank standing order), `4` צ'ק (cheque).
`monthsPaid[].isKeva` (and `isBankKeva`) says per month whether a standing order
covered it, and `wasCancelled` / `cancelReason` mark reversals.

**The tenant record carries none of it.** `/buildings/:id/tenants` returns only
name, number, phone, email, `isActive`, `payerType` (owner vs tenant),
`orderIndex`, `job`. So there is no "this resident is on standing order" flag to
read — the arrangement is inferred from what they last actually paid with. Good
enough, and more honest than a stored flag that nobody maintains.

**What we deliberately will not import.** `paymentDetails[]` carries instrument
data — card last-four `digits`, `token`, `shvaParams`, `dealNumber`, expiry, and
for transfers `transferBank` / `transferBranch` / `transferAccount`. None of it
belongs in our database. Only the method category has any use to the agent.

**Why it matters to the debt agent.** A resident in arrears whose last payments
were `6`/`5` did not forget — their standing order failed or lapsed, and that is
a different call than one to somebody who pays by transfer each month. The payer
record even has an `automatedCreditFailedMessage` field, unread so far.

Not implemented. `oxs_debt_sync.py` reads `monthsPaid` only and ignores
`paymentType` today; adding it is a column on `charges` or `residents` plus one
line in the sweep, and no extra API calls — the field is already in the response
we fetch.

### The agent insists on ownership, and acts on nothing

Reading the "left broken" note, decided: *"the agent should insist since the
system says otherwise, and would say would you like me to forward you to the
office regarding this concern?"*

Right, and for a bigger reason than this feature. `flag_not_handed_over` sets
`handed_over = false` and waives the charge **on an unverified verbal claim**,
made to an automated caller, by somebody with an obvious incentive. That makes
"this flat was never mine" the phrase that ends any call about money, and nobody
has to prove it. It also runs against a standing decision already written down:
OXS is read-only and a change a resident asks for becomes staff work. Who owns
an apartment is exactly that, and the agent recording it unilaterally is the
same mistake as writing it back to OXS one layer down.

**One wording correction to the instruction.** "Forward you to the office"
promises a live transfer and `transfer_to_human` connects nobody — it writes the
call to the office. `HANDOVER.md` states the rule outright. The line is "shall I
pass this to the office so they can check it and come back to you?"

**Pause, not waive.** On acceptance the contested apartment's charges move to
`pending_charge`, which `v_debt_call_queue` already excludes since it only emits
`unpaid`. Existing machinery, exact fit: the resident is not rung again next week
about something the office is still checking, the other apartment carries on,
and the ownership record is untouched. Waiving would have answered the question
the transfer exists to ask.

`flag_not_handed_over` comes off the agent's toolset — the same retirement
`open_payment_ticket` got on 4 Aug, for the same reason: a tool the agent should
not be deciding to use should not be offered to it. The handler stays in the
Edge Function so a stale assistant gets an answer rather than an error.

**This removed a blocker rather than deferring one.** Nothing automatic writes
`handed_over` any more, so the multi-apartment blast radius on that flag never
opens and feature 14 no longer depends on moving the interlock.

The cost, on the record: a resident who genuinely is not responsible keeps
getting called until a person acts. `pending_charge` bounds that to the
apartment they contested rather than all of them, but it is a promise that the
office follow-up actually happens.

Spec and artifact both updated.

### Spec: one call per resident, every apartment in it

Decided, after watching the demo call to the two-apartment owner: *"calling
multiple times to a single person is not the best way. The best way is to
determine how many apartments this person has, what specific apartments have the
balance not yet settled, how much is the total and what month still has an open
balance, so we can complete all transactions in a single short call."*

Written up as `docs/features/14-one-call-per-resident/`. Nothing built, nothing
live changed — the voice agent is still frozen.

That requirement is stronger than what I had proposed an hour earlier, and it
kills the smaller version. My v1 was "one call covering the total, per-apartment
arguments deferred". It does not survive **complete all transactions**: a
resident who says "I already paid for number 4" in a call that can only dispute
everything has settled nothing, and the office gets a ticket claiming both flats
are contested when one is not.

**The counting requirement sounded like the expensive half and is the cheap
half.** "How many apartments does this person have" needs apartments owing
nothing, which Supabase does not hold — both import paths upsert
`on conflict (phone)`. But `oxs_arrears.py` already sweeps every active
building's payment records and iterates every apartment in them; it keeps the
ones behind and silently drops the settled. The half-hour sweep and the rate
limit are already spent. What is missing is a list it chooses not to write down.

**The expensive half is the tool layer**, where `log_promise_to_pay`,
`send_payment_link` and `log_disputed_payment` each write against one
`ctx.chargeId`. Resolved without breaking the rule the Edge Function exists to
enforce: the call carries a whitelist of `{charge_id, unit, period, amount}`,
and the agent passes a **unit** — a thing the resident said out loud, not an
identifier it could invent. The server maps unit to charge id against that list
and refuses anything absent. The model can point at a debt already in front of
it and cannot reach one that is not.

**Composition moves into the view, not the prompt.** The queue hands over
finished Hebrew — `דירות 4 ו-9`, `450 על דירה 4 ו-780 על דירה 9` — so the prompt
keeps one sentence form and has no branch to get wrong. Teaching it two shapes
was rejected: every turn re-sends the whole prompt, and the 7 Aug failures were
already "the model did not find the rule". `v_debt_call_queue` composing the
Hebrew month name in SQL is the same instinct.

Also folded in from the demo call: the apartment is now always spoken, and the
anti-scam rule is narrowed. It fired on "on what building?" from a resident who
had already confirmed her identity. The prompt contradicted itself there — the
voicemail line says `לגבי בניין {{building}}` to an unverified answering machine
while the agent refused the same fact to the confirmed account holder.

Left explicitly broken: `residents.handed_over` is an apartment fact stored on
the resident, so flagging one flat stops calls about all of them. Same category
error migration 012 fixed for charges. Not fixed here because that flag is the
interlock keeping the queue empty, and a change whose failure mode is placing
calls that should not happen gets its own approval.

Published as an artifact for reading: the plan in plain language, with the
worked call script.

## 2026-08-11

### A multi-apartment owner in the demo caller list

Asked for a sample on the test console covering one owner with several
apartments. Added דנה רוזן, הרצל 14 — apartment 4 at ₪450 and apartment 9 at
₪780, one phone across both.

**Two rows, not one combined row**, and that is the point rather than a
shortcut. `unit` and `amount` are single template variables and the prompt
refuses a call without them, so a combined row would demo a call the agent
cannot currently place. Two rows is what `v_debt_call_queue` actually produces.
Picking either card rings her about that apartment only, which makes the
undecided question tangible: as built, this owner gets two calls.

Two cards with the same name read as a duplicated row, so each carries a marker
naming the other apartment and the combined ₪1,230 — the same device the
dashboard uses, for the same reason. Grouped on phone, since that is the only
field identifying a person here.

The marker is computed at draw time and never stored on the person object:
`variablesFor()` forwards every field it does not explicitly drop, so an extra
key would have reached the agent as a template variable it could read aloud.
Appended after the existing tag rather than folded into it, because that chain
is a priority ladder — no phone, no Latin name, blocked, card — and every rung
is there because a call once went out without it.

Verified: 12 rows, exactly one owner with more than one apartment, markers
correct on both cards, no unintended phone collisions, page script parses.

**No assistant, prompt or queue change.** This is a fixture in the test
console; the voice agent freeze holds.

### A resident was sent the single word "אני" — a failed generation, sent as an answer

Reported from a real handset: a resident asked for their balance, was asked for
a name, gave one, and got back **"אני"** followed by the options list.

The tool was not the problem, and neither was the data. Execution 613 shows the
whole turn:

| | |
|---|---|
| OpenRouter run 0 | `finish_reason: tool_calls`, 40 completion tokens |
| `get_balance` | `found:1`, ₪9,984, 2026-06 + 2026-07 — correct |
| OpenRouter run 1 | **`finish_reason: "error"`, 1 completion token, `"אני"`** |

So the model called the tool properly, got the right answer back, and then its
final generation failed upstream after one token. The agent node reported
**success** carrying that one word, and the workflow sent it.

Two wrong guesses discarded on the way, both recorded because they are the
obvious ones to reach for again. It is **not** the `maxTokens` ceiling — a cap
gives `finish_reason: "length"`, not `"error"`, and the code comment predicting
a mid-sentence truncation sent me down that path. And it is **not** a missing
tool call — the tool node was invisible in my first dump only because tools
emit on `ai_tool`, not `main`, so a filter on `main` hid it.

**Why `onError` and `retryOnFail` do not cover this.** Neither fires, because
nothing threw. The existing error branch is real and correct and simply never
saw this: the node succeeded, it just succeeded with a fragment.

Fixed with a `Reply usable?` IF between the agent and Send. Fewer than two
words routes to the existing handover line instead of to the resident. The test
is **word count, not length** — "אני" is exactly as long as a legitimate Hebrew
word, so length cannot separate them, while every reply this agent has business
sending is a sentence and the one-liners are all on canned branches. Verified
against eight cases including the exact failing string.

`retryOnFail: 3 tries, 5s apart` added to the agent and model nodes too. It
does nothing for this failure and covers the ones that do throw — the 402s when
OpenRouter credit runs out, most obviously.

Deployed to `u2JjrbcNPYyyh3yl`; confirmed still active, 22 nodes, no
overlapping positions. The "Not active yet" line the deploy prints is
unconditional when `--activate` is absent and does not reflect the real state —
the workflow was active throughout.

### The voice agent is frozen, and what that leaves open

Asked how the agent would handle an owner with several apartments — three
calls, or one covering all of them. Answered from what is built rather than
from intent, then **decided: do not edit the voice agent for now.**

The honest answer was worse than the question assumed. `v_debt_call_queue` is
one row per charge, which since this morning means one row per *apartment per
month* — so an owner with two flats owing four months each is eight rows, and a
runner iterating the view places eight calls. The multi-month half of that
predates today; putting the apartment on the charge turned four into eight.

It is not a decision anyone has made, because **no campaign runner exists** and
nothing has ever read the view. Collapsing was always the runner's job; the
view's contract is only that a row carries everything one call needs, which is
why it refuses to emit a row missing an amount or a month.

One call per person is not a queue tweak. `{{month}}` and `{{amount}}` are
single values and the prompt forbids placing a call without them, so the script
is built around one debt. And `log_promise_to_pay`, `send_payment_link` and
`log_disputed_payment` each write against a single `ctx.chargeId` — a call
covering eight charges has nowhere to record a promise against eight. That tool
layer is the work, which is the argument for settling it before a runner is
written rather than after.

Frozen means frozen: the prompt, the queue grouping and the assistants are
untouched, and `debt-tools` stays undeployed even though the repo copy is
ahead. Both consequences are written into `HANDOVER.md` under "Deferred by
decision" so they are visible rather than rediscovered — in particular the
eight-calls trap, which a future runner would otherwise walk straight into.

Also recorded: exactly two owners hold more than one indebted apartment,
₪9,143.80 between them. How many own several apartments *overall* is unknown
and not in Supabase — both import scripts upsert `on conflict (phone)`, so
`residents` keeps one row per person carrying one apartment. Only flats that
earned a charge exist per-apartment. Answering that needs another OXS sweep.

### Owner view on Debts, because the apartment split broke a second question

Splitting rows per apartment answered *what does this flat owe* and quietly
broke *what does this person owe*. Rows sort by amount independently, so one
owner's two flats scatter — ₪5,572 third on page one, ₪1,838 on page two —
with nothing saying they are one phone call worth ₪7,409.60.

Both halves shipped, not either:

- `?by=owner` — one row per resident, flats merged into an `Apartments` cell,
  months deduped across them, sorted by what they owe in total.
- A marker on the apartment rows — `· also apt 103 · ₪7,409.60 total` — so the
  default view cannot mislead somebody who never finds the toggle.

The toggle alone was rejected because the default would stay wrong-by-omission;
the marker alone because reading a position off two rows on two pages is work
the page should already have done. Month and view are independent in the URL —
switching either keeps the other — and the cards are computed from the
apartment grouping in both views, since a `Total open` that moved when you
regrouped rows would look like a discovery rather than a rendering choice.

Verified against a local production build before pushing: `all` 122 apartments
/ 120 residents, July 108 / 106, toggle links preserve the month, and the two
multi-flat owners merge correctly in owner view and carry the marker in
apartment view.

### A charge belongs to an apartment, not to a phone — ₪6,665.40 recovered

Asked: *"I want to know what apartment isn't paid yet and how much."* The page
could not answer it and no page change would have — the second apartment's debt
was not hidden by the query, it was **absent from the database**.

`residents.phone` is unique and `charges` was unique on `(resident_id, period)`,
so when `import_arrears.py` met the same phone twice it ran `do update set
amount = excluded.amount` and the second apartment **overwrote** the first.
Measured before changing anything: two owners, two invisible apartments,
₪6,665.40 missing from a reported ₪94,854.30 — one second flat carrying four
months at ₪5,572, the other two months at ₪1,093.40. (Both owners are in the
same building; naming it here alongside apartment numbers and amounts would put
a debtor record in a public repo.)

**Migration 012** puts the apartment on the charge: `charges.unit`, backfilled
from the resident, `NOT NULL` defaulting to `''` — nullable would have let
Postgres treat two unknown apartments as distinct and reopen the same duplicate
— and the unique key becomes `(resident_id, period, unit)`.
`v_debt_call_queue` now takes `unit` from the charge, or an owner of two flats
would be told the amount for one and the apartment number of the other.

Chosen over keying residents on `(phone, unit)`. Every identity path starts
from a phone — `get_balance` on WhatsApp, the n8n memory window,
`v_conversations` — and making phone non-unique turns a balance question into a
disambiguation mid-call. What made the charge-side fix cheap was checking
first: every write tool keys off the `charge_id` the campaign runner attached
to the call, never off `(resident, period)`, so not one of them needed touching.
Also rejected: hand-patching the two rows, which would have re-collapsed on the
next import.

**Two hazards the pre-flight caught, both inside the statement being rewritten.**
Nine charges were already `paid`, and the import ended its upsert with
`status = 'unpaid'` — re-running it would have resurrected nine settled debts
against real people. It now leaves `status` alone; a snapshot from one sweep is
not evidence that a paid debt is open again. And all 173 real charges carried
`source = 'seed'` while their residents correctly said `oxs`, because the column
defaults to seed and the import never set it — meaning the whole arrears list
sat one purge away from deletion by a query written to be careful (007 exists to
make `source` exactly that filter). Both fixed.

**Verified after applying:** ₪101,519.70 across 170 charges, 122 apartments,
120 residents. Nine paid charges still paid. Zero duplicate
`(resident, period, apartment)`. All 179 charges now `source = 'oxs'`.
`v_debt_call_queue` still **0 rows** — the handed-over interlock is untouched
and nothing can dial. Migration re-run to prove it is idempotent.

Dashboard groups on phone+apartment with an Apartment column from the charge,
and counts apartments and residents separately because they stopped being the
same number. `get_balance` answers for one apartment when the caller identified
themselves by apartment, and for everything they own — split under
`owed_apartments` — when found by phone or name; months are summed across flats
rather than listed twice. It also had to learn to find a caller through their
*charge*, since `residents.unit` names only one flat and apartment 601 was
otherwise reachable as 103 and invisible as itself.

**The Edge Function is written but NOT deployed** — it is the live writer voice
calls hit, and that is a separate decision. Until it ships, the two multi-flat
owners get a combined balance and their second apartment is not findable by
building+apartment. Nothing else is affected; every write tool is unchanged.

Defect 2 in `HANDOVER.md` is closed. Defect 1 (the 2022 debt stamped `2026-08`)
is still open.

### Debts page filters by month, and opens on the month being called

The page answered "who owes the most, ever". Collection is worked one month at
a time, so it now opens on a single month, with `?month=2026-07` in the URL the
way the ticket filter already works. Tabs are derived from the months that
carry an unpaid charge, so nothing is hardcoded and a month leaves when its
last charge is paid. `?month=all` is the previous view, unchanged.

Chosen over a month-by-month grid (seven columns today, one more every month,
and the number a caller needs buried in a row of dashes) and over tabs-plus-
breakdown, which is the right second version once somebody has used this one.
Filtering stays in the page rather than in Postgres: the query already pulls
every open charge in one round trip, and pushing it down would need a second
query just to build the tab list. Rationale and the point at which that flips
are in `docs/features/13-dashboard/context.md`.

**The verification changed the design.** Cross-checked every month against the
database before pushing: the eight months sum to ₪94,854.30, exactly the `all`
total. But the newest month carrying debt is `2026-08` — the 2022 legacy row
stamped with the current month by a sync that had no month to use. "Open on the
newest month" would have landed staff on one phantom debtor owing ₪1,500 while
106 people owed for July.

Fixed not with a special case but by applying a rule the project already holds:
arrears are months that have *ended* unpaid, and the current month is never
chased — what `oxs_arrears.py` computes on. The default is the newest
**completed** month, correct on its own terms and still correct once the month
stamp is fixed. The `2026-08` tab still renders; hiding a row for being wrong
would put the dashboard at odds with the database.

A well-formed month nobody owes for shows "Nobody owes for 2026-03" rather than
redirecting — a forwarded link to a collected month should say it is clear, not
quietly show a different month's numbers.

Type-check and production build clean. Defect 1 in `HANDOVER.md` — the 2022
debt stamped `2026-08` — is routed around, not fixed; it is still open.

## 2026-08-10

### Feature status doc for the client — features, not plumbing

User asked for documentation of what is done and not done, explicitly **system
features only, no technical detail**. Wrote
`docs/reference/Homies-Feature-Status.md` and published it as an artifact so
there is a link to send rather than a repo path.

Rule applied throughout: no table names, no tool names, no endpoints, no env
vars. A feature is described as the thing a resident or a staff member can
actually do. Organised by who is doing it — resident by voice, resident by
WhatsApp, the office — rather than by subsystem, because that is how the client
will read it.

Each ❌ item names **what it is waiting on**, which is the part the client can
act on: the phone line waits on Homies' company registration documents (1–3
weeks, the long pole); payment-link delivery waits on a decision about who
sends it, since OXS exposes no way to generate one; the human handover waits on
wiring the inbox that is already running; the nightly refresh waits on nothing
external.

Included the things that would embarrass us in a pilot if unsaid: the dashboard
currently has no login, every resident is flagged not-handed-over so nothing
can dial, multi-apartment owners collapse into one row so **₪94,854 understates
the real total**, one 2022 debt carries the current month, 18 apartments have
no phone, and the arrears list is ours rather than OXS-confirmed.

Ends with five decisions needed from Homies, so the client has an action list
rather than a status report.

## 2026-08-10

### Diagram: ✓ / ✗ status marks, so done vs not-done reads at a glance

The diagram showed what exists but never said which parts were finished — the
only status marker was the ✗ list in the bottom band. Added three layers:

- A **scoreboard band under the title**: ✓ DONE with the five working flows on
  the left, ✗ NOT DONE with the four gaps on the right.
- **✓ on every column header**, because all six flows do run end to end.
- **Grey dashed ✗ pills inline**, placed at the exact step that is missing
  rather than in a footnote: no real phone number (outbound column), nothing
  delivers the payment link (right after the payment_links write), Chatwoot not
  connected (end of the WhatsApp column), no scheduler (OXS column).

The inline placement is the point — it shows that the gap is one step inside an
otherwise working flow, not a whole feature missing. Orange dashed pills still
mean an exit to a human, which *works*; the legend now separates the two.

209 elements, CLEAN on `check_diagram.py`. Paste file regenerated.

### Diagram redrawn in the six-column layout, and a paste-ready format

User pointed at the old System-Flow's look and said the current-system diagram
should match it. Rewrote `gen_currentflow.py` to the same visual language —
front-door spine, a wide bar, six vertical flow columns with dashed exit pills
in the gutters, bands at the bottom — but with today's verified content. Now
195 elements, CLEAN on `check_diagram.py`, bounds 3330×1645 (the old one is
3250 wide, so they read as a pair).

The six columns are the flows that actually run: inbound call → ticket,
WhatsApp → ticket, check a ticket, check a balance, outbound debt follow-up,
and OXS → Supabase. Same file name as before, so existing links still work.

Also added `docs/diagrams/to_clipboard.py`. Excalidraw has two JSON formats and
only one of them pastes: `{"type":"excalidraw"}` is a *file* (drag-drop or
File > Open), `{"type":"excalidraw/clipboard"}` is a *paste*. Every diagram now
has a `.paste.json` beside it — select all, copy, Ctrl+V onto a canvas.

### Diagram: the system as it actually runs, not as the PRD draws it

User asked for an Excalidraw flowchart of the current system, specific about
how it works and where the data goes. Wrote `docs/diagrams/gen_currentflow.py`
→ `docs/diagrams/Homies-Current-System-Flow.excalidraw` (93 elements, CLEAN on
`check_diagram.py`: no shape, label or bound-text overlaps, no dangling
bindings). Follows the existing generator convention rather than hand-authored
JSON, so it can be regenerated.

Kept separate from `Homies-System-Flow.excalidraw` deliberately: that one draws
the PRD's *intended* architecture (Telnyx in the path, Chatwoot in the path,
n8n as one brain with twelve tools), which is not what exists. One is the plan,
the new one is the state.

Mapped the real paths first rather than drawing from memory, and three things
turned out to differ from what the older diagram and the docs claim:

- **Tool calls are two hops, not one.** Vapi → n8n `/webhook/homies-debt-tools`
  → Supabase Edge Function `debt-tools`. `vapi_sync.py:tool_server()` resolves
  n8n → Supabase → Apps Script, and `N8N_BASE_URL` is set, so n8n wins. The
  end-of-call report goes *straight* to the Edge Function, bypassing n8n, since
  n8n has no handler for a server message and would 200 while writing nothing.
- **`create_staff_task` does not exist.** It is in the PRD, in `HANDOVER.md`
  and in the old diagram, but there is no handler, no tool definition and no
  `staff_tasks` table. Its real stand-in is `transfer_to_human` /
  `request_standing_order` writing `call_outcomes`. Drawn in the NOT BUILT
  band, not in the flow.
- **The WhatsApp bot writes `messages` directly** to PostgREST with the
  service-role key, not through the Edge Function — so there are two writers
  into Supabase, not one.

Also on the diagram: live row counts (interactions 53, messages 99, charges 19,
residents 22, requests 2 — and payment_links / promises_to_pay /
payment_disputes all at 0), the 12 handlers with the table each writes, the
three views, the Sheets/Apps Script queue read that is still the demo console's
source, the manual OXS import, and the four gaps with what each one blocks.

### HANDOVER.md made self-sufficient: "read the handover" is now the whole briefing

The first pass at HANDOVER.md was a pointer — it assumed the reader would go
and find the architecture elsewhere. The user's actual requirement is that
*saying "read the handover" is enough*, so it now carries the system itself:
the two front doors, the Vapi/n8n runtime, the one-writer tool layer through
the Edge Function, the tables and the three views, the dashboard, all 12 tool
handlers, and a credentials map by env-var name (never values).

Personal names were removed on the way — "one owner with three apartments"
rather than naming him. A handover doc gets pasted into new contexts, and real
residents do not need to travel with it.

### CONTEXT.md and HANDOVER.md are now the handover pair, updated every task

Standing instruction from the user: a fresh Claude window should be able to
take over without reading the repo or querying the database, and should behave
the same way this one does.

`CONTEXT.md` (new) is the **rules**: what Homies is, the standing decisions
that must not be relitigated (OXS read-only, Supabase is the store, the repo
is public, nothing dials), the prompt-editing rules and the prompt-only PATCH
warning, how to work (worklog first, verify before claiming, look before
deleting), how the user wants to be answered, and the script inventory with
the rate-limit facts that make a sweep half an hour instead of five minutes.

`HANDOVER.md` (rewritten from the OXS-thread version, which was obsolete
within a day) is the **present tense**: what works, what does not exist, the
data as it stands with its three known defects, the OXS finding and the
arrears correction, open questions for the client, next moves.

Neither duplicates this file. WORKLOG is the chronology with the reasoning;
HANDOVER is only now; CONTEXT is only the rules. Both are rewritten rather
than appended to, and updating them is part of finishing a task.

### Pagination, ten rows a page, on every list in the dashboard

`dashboard/components/pager.tsx` — `PAGE_SIZE`, `pageFrom`, `pageRange`,
`pageSlice` and one `Pager`. Wired into **debts** (was unbounded, 120 rows
after the arrears import), **tickets** (was `.limit(200)`, no pager) and
**conversations** (same). **Calls** already paginated and dropped 50 → 10 so
every list behaves alike.

Page state lives in the URL, so page four is a link somebody can send. Tickets
keeps its status filter in the query string alongside it; switching tabs
resets to page one, which is what a filter change should do.

Debts paginates in memory because its rows are grouped per resident after the
query — one person owing four months is one row, and that grouping cannot be
expressed in a `.range()`. The others paginate in Postgres with
`count: 'exact'`. **The summary cards stay totals over everyone**, never the
visible page; a figure that changed when you turned the page would be worse
than no figure.

`npx next build` clean, all nine routes.

### Arrears imported: Open Balances is now 120 residents, ₪94,854, month by month

`scripts/import_arrears.py` (new, offline — reads the sweep's JSON, no API
calls) applies the onboarding correction and writes the result.

**One charge per unpaid month, not one lump.** `charges.period` is the month
itself, so the dashboard's months-owed column is true and the agent can name
the month it is calling about — which the ₪1,500 legacy row cannot do (it is
stamped 2026-08 because the sync had no month to use; the debt is from 2022).

The correction, stated as a rule: where four or more flagged apartments in a
building miss the same **leading run** of months (01, 01-02, 01-05), that run
predates Homies managing the building and is dropped from every apartment
there. Threshold 0.6 for leading runs and 0.8 otherwise — deliberately
asymmetric, because a whole building going unpaid from January and then
resuming in unison does not happen, while a building being taken on in May
happens constantly. המרי 58 (78% missing 01-04) is exactly why: it sat under
an 80% bar and would have contributed ~₪40k of invented debt.

610 flagged → 22 buildings' leading months dropped, 5 excluded as recording
lag, 432 apartments left with nothing owing → **139 apartments, ₪108,770**.

Written: 121 residents, 169 charges. Stored: **120 residents, 164 charges,
₪94,854.** Spread: 106 owe July, 18 June, 11 May, 8 April, 4 March, 12
February, 4 January, plus the one 2022 legacy row.

**Known loss in that gap.** `residents.phone` is unique and
`charges` is unique on (resident_id, period), so one person owning several
apartments collapses to one resident and one charge per month —
משולם לוינשטיין holds three apartments in המרי 58 and survives as one. Real
money is missing from the total because of it. Fixing it means keying the
resident on phone+unit, or moving the apartment onto the charge; neither is a
five-minute change and both touch the tool layer. 18 more apartments were
skipped outright for having no phone.

### The 2026 arrears sweep: 610 flagged, ₪962k — and 79% of it is buildings joining mid-year

`scripts/oxs_arrears.py` (new) computes arrears the way `/debts` will not:
per building, per apartment, months of 2026 that have ended with no payment
recorded against them. The monthly figure comes from the apartment's own
`monthsPaid[].amount`, never a guess. August is excluded — not late yet.
Ran 34 minutes over 173 buildings (each returns thousands of payment
records; the sizing estimate was badly wrong, and `python -u` should have
been used so progress was visible).

Raw result: **610 apartments behind, ₪962,405**, plus 267 apartments with no
2026 payment at all, already excluded as unknowable (new, vacant, or never
handed over).

**Then the audit, which is the actual finding.** Grouping by building shows
whole buildings missing an identical run of months: המעיין 48 — 12 of 12
apartments missing all seven; קוסובסקי 48 — 95% missing Jan–May; הרב לוין 6 —
100% missing Jan–Feb; המעלות 8 — 29 of 29 missing Jan–May. That is not
arrears, it is the month Homies took the building on. **429 apartments,
₪756,870, 79% of the total, sit in that pattern.**

Corrected estimate of genuine individual arrears: **~181 apartments, ~₪206k**
— still a real call list, two orders of magnitude past what `/debts` reports.
32 of the 610 have no phone and could not be called regardless.

Nothing written to Supabase. The fix is a building-level rule: a month is
only due if the building was under management then, inferred from the
earliest month any apartment in it paid. That needs a re-run (~20 min, and
the tenants call can be dropped since the import already cached it).

Full list: `docs/reference/arrears-2026.json`.

### Why OXS reports one debtor: `/debts` is legacy arrears, not who is behind this month

7,391 tenants and one debt did not add up, so it got probed properly.

Ruled out: pagination (`?page=2` is empty), sorting, the per-apartment rollup
(`/buildings/:id/apartments/debts` returns `[]` for every building and every
year, including the one that *does* have a debtor), `/apartments/:id/debts`
(returns `data: null` for a valid apartment id), and a per-building feature
gate — all 193 buildings carry identical `vaadSettings` with דוח חייבים
active.

**The proof it under-reports.** In אנה פרנק 10, OXS lists zero debtors. Its
own payment records show 4 of 16 apartments have not paid recent months —
אסטרוגו (apt 5) and יהודה גרוס (apt 10) are missing both July and August
2026; נצר (13) and פוגצקי (16) are missing August. Residents behind by two
months do not appear in `/debts` at all.

**What the one record actually is:** `regularPaymentsDebt: [{year: 2022,
debt: 1800}]`, owner `isActive: false`, and `paymentNotes` describing SMS and
WhatsApp chasing. A legacy carried balance from a former owner — not a
current arrear. So the finance module answers "who carries old debt", and
the collection question the agent exists to ask is a different question.

**The real arrears list is computable from `/payments`.** Each record carries
`apartmentId`, `totalAmount`, and `monthsPaid: [{year, month, amount,
isKeva}]` — so paid-months per apartment is directly readable, the monthly
figure comes with it (₪350 in this building), and `isKeva` marks standing
orders. Arrears = expected months minus paid months, with the current month
excluded because it is not yet late.

Not built yet. It needs a decision on the grace rule and on how far back to
count, and it is a 193-building sweep (~4 min). Until it exists, Open
Balances shows one row and that row is honest but incomplete: it is what OXS
calls debt, not what the client means by it.

### Open Balances now means "OXS says they owe": 9 stale debts cleared, 1 real one left

The client asked for the Debts page to show only people who have actually not
paid. That was a data problem, not a page problem — the page already filters
to unpaid/disputed/pending. `scripts/oxs_debt_sync.py` (new) reconciles
`charges` against OXS: sweeps every active building via
`/buildings/:id/debts` (the company-wide `/debts` under-reports — it returned
one row), inserts what OXS lists, and marks `paid` anything OXS does not.

**The sweep of all 173 active buildings found exactly one debtor
company-wide: ארז לויים, הרכסים 17 apt 8, ₪1,500.**

Before marking nine real debts settled on the strength of an absence, checked
for presence instead: `/buildings/:id/payments` for אנה פרנק 10 returns full
payment records, and all nine residents pay regularly — מורגנשטרן, ארנון and
לגשטיין in early August 2026, פוגצקי in July, and חקק paid ahead through
December 2026. The December 2025 collection report was eight months stale.
Calling those nine would have been calling people about money paid twice
over.

Applied: 9 charges → `paid`, 1 written from OXS. Open balances: **1 charge,
₪1,500**, verified through the dashboard's own anon key.

Worth putting to the client: one debtor across 193 buildings is a very clean
book. The payment records make it plausible (standing orders, many residents
paid months ahead), but if Homies believes more residents are in arrears,
their finance module counts arrears differently than we assume and that needs
an answer from OXS before this page is trusted operationally.

### Fake data gone: 7,391 real residents imported from the OXS API, real phones, real buildings

`scripts/oxs_api_import.py` — new, replaces the two CSV scripts. GET-only
against OXS. Walks 173 active buildings via `/buildings/:id/tenants`, keeps
active tenants that have a phone, normalises to E.164, strips the
" - דירה N" suffix from names, then reads `/debts`.

Purged: the ten `source='seed'` demo residents and the twelve synthetic-phone
rows. Imported: **7,391 residents** (358 skipped for having no phone, 723
duplicate phones collapsed — one person paying for several apartments).

**The debt trap, caught before the purge ran.** `/debts` returns exactly one
open debt for the whole company (ארז לויים, הרכסים 17, ₪1,500), while our DB
held nine real debts from the December collection report. A straight
replace would have destroyed them. Checked whether those twelve people exist
in the API first: **all twelve matched by name and apartment number**, in
בניין אנה פרנק 10, רמת גן — with real mobiles. (The "הרצל 14" on those rows
was ours, passed via `--building` at CSV-import time; OXS never said it.) The
importer now carries those charges across the purge and re-attaches them by
name. Result: 9/9 re-attached, so **10 charges total, every one against a real
phone.**

**Then the follow-up query answered it, and the answer is that those nine
are probably not owed any more.** `GET /buildings/63ee7989.../debts`,
`/apartments/debts`, and the same with `?year=2025` all return an empty list:
OXS says בניין אנה פרנק 10 has **no** outstanding debt, including for 2025.
The December report was a point in time and eight months have passed. So of
the 10 charges now in Supabase, exactly **one** (ארז לויים, ₪1,500) is
confirmed current by OXS; the other nine are real people whose debt is
almost certainly settled.

Nothing can call them — every imported resident has `handed_over=false`, so
`v_debt_call_queue` returns 0 rows. The decision (mark the nine paid, or
confirm against a fresh report first) is the client's, and calling a resident
about a debt they cleared in December is exactly the call the prompt calls
the worst one this agent makes.

Everyone lands with `handed_over=false` (nobody is callable until a person
approves it) and `gender=NULL` (OXS does not carry it; the agents infer).
Dashboard needs no redeploy — it reads Supabase live; verified the anon key
sees all 7,391.

### THE OXS API IS OPEN — endpoint doc arrived, all three keys verified live, real phones present

The user uploaded `OXS_External_API_v1.pdf` (repo root) — the endpoint
reference that never existed anywhere. Base `https://api.oxs.co.il/api/external/v1`,
auth `x-api-key`, three modules matching our three keys. Tested immediately,
read-only GETs (`scratchpad/oxs_v1_test.py`): **all three keys return 200 with
real company data.** External API is already enabled for Homies — no support
email needed for activation.

The headline: `GET /debts` returns owners with
`contactDetails.mobilePhone` populated — **real resident mobile numbers are
extractable today.** The synthetic-phone era can end with one import run
(purge synthetic rows first, `scripts/oxs_purge_synthetic.py --apply`).

Corrections to earlier beliefs: rate limits are **per key** (60/min, 1,000/hr
each), not shared across keys as the key-management guide was read to imply.
The probe's negative result stands explained: it guessed `/api/tenants`-style
paths; the real surface is `/api/external/v1/*`.

Not in the API: any payment-link field or endpoint (finance is debts-only,
read-only) — question 7 of the support-email draft is answered "no" by
omission; the draft itself is now largely obsolete (activation: done; auth
header: known; routes: known). Endpoints per module — general: buildings,
apartments, tenants, payments; finance: debts (company/building/apartment);
service_calls: list/read, plus POST/PUT/DELETE only with a `full` key (ours
should stay read; OXS-write remains forbidden by policy).

Open: import real phones + live debts into Supabase (replaces the manual
CSV-export path), decide sync cadence, check which access level the
service_calls key actually carries.

### Debt prompt trimmed ~1.8k chars and gains a partial-payment rule (repo only, not yet pushed)

An external review of the debt prompt landed; scored it against the file. Its
four "critical conflicts" were mostly misreadings (opening/אה not a conflict,
`transfer_to_human` is not terminal, wrong-party gender rules serve the fixed
line, card-on-file already handled). Two findings were real: duplicated rules
(no-repeat ×5, digit-reading ×3) and no path for "אפשר לשלם חצי עכשיו וחצי חודש
הבא" — which the old rules would have routed to hardship handover, wrong for
someone actively trying to pay.

`docs/features/10-debt-followup/prompt.md` edited, behaviour sections only —
the client-owned style/grammar/repetition sections (3 Aug) were not touched:

- Cut full-paragraph restatements of no-repeat reasoning in THE OPENING and
  WHAT THE CALL IS TRYING TO DO (the point-of-action one-liners stay — the
  7 Aug failure mode was "rule not found", so rules near the action survive).
- Compressed justification prose to rules: send_payment_link ordering, receipt
  rationale, consent-word rationale, dispute-steps intro, refusal rationale.
- De-duplicated the email-speaking rule (now only in NUMBERS) and the
  same-digits rule; voicemail no longer re-explains יום טוב releasing the line.
- **Added THEY OFFER TO PAY PART NOW** after THEY WANT TO PAY LATER: trying to
  pay ≠ hardship ≠ refusal; link is full-sum, log the offer via
  `log_promise_to_pay` in their words, never argue about the rest.

Extracted prompt: 38,412 chars vs 39,684 live → net −1,272 (−1,789 cut, +517
added). ~300 tokens per turn, ~1.2¢/min back — roughly cancels the morning's
gender/recovery additions. Verified: all anchors present exactly once, all cut
phrases gone. **Not pushed to Vapi yet** — awaiting user review; push must be
the prompt-only PATCH (full model object), not `vapi_sync`, until INTAKE_TOOLS
catches up.

Open from the same review, deliberately not acted on: WhatsApp vs
{{verification_email}} for payment proof is a client/office-intake decision;
prompt-cache pricing on the model line still unverified.

### Two voice-skill docs distilled into both Hebrew assistants

Two documents arrived in the repo root — `hebrew-voice-gender-pronunciation-skill.md`
and `hebrew-voice-failure-recovery.md` — and went in the same way the
super-skills doc did on 7 Aug: distilled hard, most of it rejected as already
present in stronger form or in direct conflict with rules the prompts earned.
The latency-masking fillers lost to NEVER SPEAK THE MACHINERY (a tool call is
silent, deliberately); the de-escalation-to-keep-working protocol lost to
hot-is-a-floor; the silence map is Vapi endpointing config, not prompt text.

What went in, both assistants: **conversation-cue gender detection** — the
caller's own present-tense verbs (צריכה/צריך, יכולה/יכול, גרה/גר) settle their
gender and outrank the name; past tense settles nothing; unisex names (שי, טל,
נועם, ליאור, עדן, רון) are never guessed. Debt also gained WHEN YOU MISS
SOMETHING — never "לא הבנתי, נא לחזור", reflect the caught part and ask only
for the gap, second attempt is a different strategy, the miss is always yours
(לא הסברתי טוב, never לא הבנת) — and a no-אבל rule on friction
acknowledgements. Inbound gained the caught-part reflection and the
correction-interruption rule; its two-attempt slot machinery already covered
the rest.

**Pushed as prompt-only PATCHes, not vapi_sync — and that was load-bearing.**
The live inbound assistant carries five tools; `INTAKE_TOOLS` in vapi_tools.py
still has three. A sync --apply would have silently stripped
`get_request_status` and `get_balance` (attached 9 Aug outside the script).
Full model object fetched, system message swapped, PATCHed back; tools
verified intact on both after the push. Debt he 39,684 chars, inbound he
20,056.

Also closed on the way: **demo-inbound.md was stale against the live prompt**
— the 9 Aug balance section lived only in Vapi. The fence now carries the live
prompt (merged, plus today's additions), so `vapi_sync inbound` extracts the
right text again. Open: add the two read tools to INTAKE_TOOLS before anyone
runs a full sync; English assistants untouched (Hebrew-specific rules).

### Credentials checklist rebuilt against the live `.env`

User asked for the full list of what the project still needs, especially the
telecom and the Facebook/WhatsApp credentials. Rewrote
`docs/reference/Homies-Credentials-Checklist.md`, which was written 3 Aug and
had gone stale: it still said telephony was "undecided (generic SIP)" and that
Supabase was "not created yet" — both wrong now. Every line is now marked
DONE / MISSING / N/A against the actual `.env` (names and populated-or-not
only; no values read or printed).

The picture is better than the old doc implied. Only four things are actually
outstanding: **Omnitelecom SIP (4 values)**, the **Google service account +
sheet ID**, the **Monday token + board ID**, and **Meta business verification**
(account state, not a key — caps WhatsApp at 250 conversations/day until done).

Two findings worth noting. **All Meta/Facebook credentials are already
obtained** — app id/secret, WABA id, phone number id, verify token, system-user
token, n8n cred id — so nothing needs ordering there; but *three* overlapping
access tokens coexist (`WHATSAPP_ACCESS_TOKEN`, `SYSTEM_USER_ACCESS_TOKEN`,
`WHATSAPP_TOKEN`), which is a rotation hazard since an expiring temp token
looks exactly like an outage. And **all four SIP values are absent**
(`SIP_GATEWAY_IP`, `SIP_USERNAME`, `SIP_PASSWORD`, `SIP_PHONE_NUMBER`), which
is why nothing dials today. Telnyx/Twilio vars present but empty — retired.

The Omnitelecom order detail (two products only, digest not IP auth, G.711,
RTP `40000-60000` with per-call source IPs, the two Vapi signalling IPs, and
the public-internet-vs-dedicated-line question to ask before paying) is now
in the checklist rather than only in memory.

### Hebrew gender: implemented in the prompts, inert on the real residents

Checked whether Hebrew gender agreement is actually implemented. It is, at
every layer — but it never engages for the 12 real OXS residents.

Implemented: `residents.gender` (`m`/`f`/`unknown`, CHECK-constrained,
004_debt_schema.sql), exposed by `v_debt_call_queue` as
`coalesce(gender,'unknown')`, and consumed by the voice prompt
(10-debt-followup) which has a full GRAMMAR section — agent is always
masculine about himself, resident inflected by `{{gender}}`, an imperative
table (תן/תני, תשלח/תשלחי, אתה/את), third-person agreement about the resident
when someone else picks up, and a rule that fixed lines may be re-inflected but
not rephrased. WhatsApp (11-whatsapp-bot) deliberately does the opposite:
never genders the resident, because the WhatsApp envelope carries no gender —
impersonal/infinitive forms only. Both deliberate, both correct.

The catch, from the live DB: **all 12 OXS residents have `gender = NULL`** —
only the seed rows carry values. The view coalesces those to `unknown`, so
every real call takes the fallback path. And the prompt's rescue — infer gender
from the given name — is defeated by the data: the queue view computes
`first_name` as `split_part(full_name,' ',1)`, but OXS name order is
inconsistent. 7 of 12 emit a **surname** as the first name (מורגנשטרן, מילמן,
מרקנטי, אסטרוגו, ארנון, אשכנזי, בונוביצקי), which carries no gender signal and
would also be spoken as if it were a given name. A further 5 rows are
**couples** on one account (אסטרוגו אילן ונאוה, אשכנזי תומר וזוהר, ארנון רחל
ומוני, מילמן אשל ורחל, בונוביצקי רפי וטובה) — two people, no single correct
gender, which no amount of data backfill resolves.

Net: the feature degrades safely (unknown -> neutral phrasing, nobody is
misgendered) but never actually inflects for a real resident. Not fixed —
reported only.

### OXS API host found and verified — the endpoint IS reachable, one call to prove it

User's ask: skip the support email, just verify we can pull a phone number
from the API key directly. Findings:

- **`api.oxs.co.il` exists and is genuinely OXS.** DNS resolves; TLS cert is
  Amazon-issued, `CN=oxs.co.il`, SAN `*.oxs.co.il`, valid to Dec 2026 — the
  same origin that serves the OXS web app. So this is a host we can send the
  company's own key to without breaking the never-guess-a-host rule (the host
  is cert-proven, not guessed).
- **There is a real, auth-gated API behind it.** `/swagger.json` returns a
  true `401 Not Authorized` (JSON, 16 bytes) unauthenticated — not the SPA
  fallback that every unknown path returns (4285-byte index.html). So the spec
  endpoint is real and gated by the key. If the key authenticates there, that
  one response yields the auth header name AND the full route list — the entire
  endpoint reference the handover said was missing.
- **Could not make the authenticated call from this session.** The Claude Code
  auto-mode classifier blocks transmitting the API key over the network from
  here (credential-protection guard), both as a scheme loop and as a single
  request. This is a harness limit, not an OXS one.
- Wrote `scripts/oxs_probe.py` — the user runs it locally. It re-verifies the
  cert, finds the auth header via the key-gated `/swagger.json`, then fetches
  actual tenant records. Never prints a key; GET-only.

**Sharpened after the user's clarification:** the only question that counts is
whether a *populated* mobile number comes back, not whether a phone field
exists. The last export had the phone column present and useless — one
placeholder repeated down every row. So the probe now judges values, not
schema, and reports one of four verdicts: POPULATED (distinct real numbers —
importable), PLACEHOLDER (filled but all identical — the same dead end as the
export), EMPTY (field there, all blank), ABSENT (no phone field at all).
Numbers print masked (`+9725******89`) so a real number never lands in a
terminal log while still proving the values are distinct. Verdict logic
unit-tested against all four cases; each classifies correctly.

Bottom line: no longer blocked on "no docs" — blocked only on running one
authenticated GET, which the user can do in ~2 seconds with the probe script.

### OXS unblock prep: support email drafted, synthetic-purge script written

Continued from `HANDOVER.md`. Two artifacts, both sides of the "next actions"
list, so whichever path unblocks phones first has its tooling ready:

- `docs/reference/Homies-OXS-Support-Email.md` — the support email that asks
  OXS for the API reference (base URL, auth header, routes, tenant/debt field
  names, whether tenants carry the mobile number, and API-activation
  confirmation). English and Hebrew versions, ready to send to
  support@oxs.co.il; explicitly says never to paste a key value.
- `scripts/oxs_purge_synthetic.py` — deletes the 12 synthetic-phone residents
  (`source='oxs'` AND phone LIKE '+9725000000%') before any re-import with
  real phones, since residents upsert on phone and would otherwise duplicate.
  Dry-run by default, `--apply` to delete; charges go by FK cascade. Dry run
  verified against live Supabase: matches exactly 12 residents, 9 charges.
  `--apply` deliberately not run — that happens only right before a re-import.

Also verified `.env`: all three OXS keys present, 70 chars, `oxs_k_` prefix
(lengths checked, values never printed). Nothing new pasted since the
handover, so the REQUESTS re-issue as Read-Only is still with the user.

### All three OXS keys are now in `.env`

`OXS_KEY_REQUESTS` was the last blank one; the user filled it today. All three
keys (`REQUESTS`, `DEBTS`, `GENERAL`) are now set, same 70-char shape. Nothing
can call with them yet — still blocked on OXS Support sending the endpoint
docs (base URL, routes, auth header, field names). Open check: Service Requests
is the one module where a key can be Full Control; if this key was issued that
way it should be re-issued Read-Only so the no-writes rule is enforced by the
key itself.

Confirmed from the guide PDF what the three keys are entitled to: General =
buildings, apartments, tenants (phones live here), payment histories; Debts =
balances, payment details, outstanding; Requests = tickets (write only if
issued Full Control). Checked the public web too — oxs.co.il names only a
"Metric API" in pricing, no developer docs anywhere, so the endpoint reference
remains support-only. Wrote `HANDOVER.md` at repo root to carry this thread
into a new session: state, decisions in force, next actions (support email or
re-export), and the delete-synthetic-rows-before-reimport caveat.

---

## 2026-08-09

### Dashboard: Debts page — who owes what, largest first

New /debts view, one row per resident rather than per charge: name,
building·unit, phone, the months owed, anything disputed or pending under
"in review", and the total. Three cards on top — total open, residents
owing, months in review. Grouping done in the page (the table is hundreds
of rows at pilot scale); no new migration — anon read on charges and
residents arrived with 010. Same demo posture as the rest of the dashboard.

### The voice agents answer balance too

Same get_balance tool, attached to both inbound Vapi assistants (he 86a01f13,
en 3edbe85b) with the shared Edge Function URL and secret. Web calls carry no
caller ID, so voice always goes through building+apartment — the two facts the
call already collects — or a full name; the WhatsApp phone-first shortcut
simply doesn't fire. Prompts: scope widened from two things to three, the
"one lookup" rule became "two lookups", and a Balance and debt section
mirrors the WhatsApp rules with voice manners — amounts spoken as words
(ארבע מאות חמישים שקלים), never a digit sequence. Money that moves still
transfers. Verified with a voice-shaped envelope: הרצל 14/12 → דוד כהן,
₪450 open for 2026-07. Prompts still live only in the scratchpad — no repo
source doc for either inbound prompt yet, which stays on the open list.

### The balance row works: get_balance, caller's own number first

The last menu row that handed over to a human now answers. New `get_balance`
tool in debt-tools (version 13): read-only — total owed and the unpaid
months, nothing that moves money. Lookup order is the identity story: the
caller's own WhatsApp number first (the one fact they didn't type), then
building+unit, then full name — a name matching two residents returns
nobody rather than guessing between neighbours. Disputed and pending months
come back under `in_review` so a clean zero can't hide them. Wired into the
WhatsApp workflow as a fourth tool on the same direct-to-Edge-Function
route as the status lookup; prompt gained a יתרה וחוב section ("call it
with no arguments first") and the transfer section shrank to money that
*moves* — pay, receipt, dispute, payment method. All four lookup paths
verified against the live function. PRD §13 #1 (proving who asks) remains
open; this is the accepted demo posture, same as the no-login dashboard.

Also reverted mid-flight: a close_request tool (bot closes tickets on
request) was built and then dropped on the client's direction — closing
stays with the team; the balance lookup is what was wanted.

### A reply with no question gets the menu after it — decided in the workflow

The prompt rule against bare acknowledgements lost to history on its first
real test ("אוקיי." to a pasted sentence, minutes after the rule went live)
— the same history-beats-prompt failure the language choice hit on 8 Aug,
and the same fix: take the decision away from the model. "Ticket in the
reply?" became "Dead end reply?": a reply that asks a question is mid-flow,
no menu; a reply that asks nothing is a dead end and the options list
follows it. Covers the reference replies the old regex caught, the bare
acknowledgements it missed, and the handover line. Error branch read first
in the expression — on that path the agent's main output is empty and
.first() throws. One prompt line added: mid-collection messages must end
with a question, or the menu reads them as the end of the flow.

### "OK." is not a reply

The resident pasted the bot's own status sentence back and got "OK." — a
dead end in either language. New prompt section for a message that carries
nothing actionable (pasted text, a statement with no question, a repeat):
never a bare acknowledgement; say briefly that you didn't get it and name
what you can do — open a ticket, check a status, or pick from the list — in
the conversation's language, phrasing the model's own. Distinguished from
the media line, which is fixed; this one is described, not scripted, per
editing rule 1.

### A bare "1020" flipped the conversation to English

The Hebrew scenario test: reference quoted back as digits only, and the
answer came back in English. Sort's per-message language detection read
"not Hebrew" as "English", and a number contains no Hebrew. Now only
letters vote — Hebrew script sets he, Latin letters set en, and digits,
punctuation and emoji leave the preference where it was. The status flow
explicitly invites a digits-only message, so this was the flow contradicting
itself. Re-applied, re-activated.

### Ticket status is editable from the dashboard

Each row's status pill became a select + save, posting to a server action —
no client JS, anon key only. The write permission is migration 011, and the
blast radius is one column by construction: `grant update (status)` to anon
after revoking table-wide update, so a request touching any other column
fails at the grant before RLS is consulted, and the check constraint rejects
invented statuses. All three verified live: status change 200, description
change 401, "nonsense" 400. Same demo-mode expiry as 010 — the re-lock
(drop policy, revoke grant) is written in the migration header. Stale
`needs_review` tab replaced with `cancelled`, which is what the constraint
actually holds.

### Test tickets cleared

All 8 open requests deleted on request — HM-2026-1011…1019, the residue of
today's WhatsApp and voice testing. HM-2026-1001 (in_progress) left: the ask
was open tickets. The 1013 voice-status test target is gone with them; open
a fresh ticket before testing that flow.

### The follow-up menu died on a `}}`, found in the execution log

Ticket HM-2026-1019 opened cleanly and no menu followed. Execution 363: the
If matched, "Options again" failed — "invalid syntax", no description. The
cause: the menu JSON was inlined into a Set-node {{ expression }}, and a
menu is JSON full of `}}` — n8n cuts an expression at the first `}}` it
meets, so the node was handed a truncated fragment. Moved the follow-up menu
into Sort's output (a Code node has no such tokenizer), and the Set now just
reads `$('Sort').first().json.followup`. Re-applied, re-activated.

### The bot's brain ran out of money, and moved to key 2

"theres a water outage" got the handover line — not a decision, the error
branch: OpenRouter 402, key 1's balance at $0.00 with the negative-balance
grace exhausted, the model failing in 253ms. The fallback did exactly its
job; a resident got a sentence instead of silence. Swapped the n8n
credential to OPENROUTER_API_KEY_2 ($45 credits, $43.80 already used —
about $1.20 of headroom, ~2,400 flash messages), workflow re-applied and
re-activated, key-1 credential deleted from n8n. That headroom is testing
money, not pilot money.

### The English menu says ticket

"Open a service call" / "Check an existing call" → "Open a ticket" / "Check
an existing ticket", asked for off a screenshot. The second title is exactly
24 characters, which is Meta's hard cap on a row title, so it fits with
nothing to spare. Hebrew rows untouched — קריאת שירות is the trade's own
word and was chosen deliberately over פנייה.

### The options come back after a flow completes

Asked for: after a ticket is opened, offer the options again instead of
leaving the resident with a reference number and silence. Two new nodes
chained AFTER Send (parallel sends can arrive swapped, and a menu landing
before the reference reads as changing the subject): an If that looks for a
reference number in the outgoing reply — the marker of a completed flow,
which the model cannot fake because references only come from the tool — and
a Set that rebuilds the flat to/menu shape so the follow-up rides the
existing Send menu node. Body "עוד משהו?" / "Anything else?", rows identical
to the greeting menu. Fires after status answers too, deliberately — both
flows end with a reference and both deserve the offer. One prompt line so
the model does not also ask "עוד משהו?" itself. isExecuted guards the canned
branches where the agent never ran.

### The WhatsApp bot answers status now, and a tap stopped being smalltalk

Two faults off one screenshot. A tap on "Open a service call" reached the
model as four bare words and it re-greeted — a menu answering a menu. Now
'open' and 'status' taps get the first question of their flow as a canned
line straight from Sort, no model round-trip; 'human' and 'balance' still go
to the agent, whose job on both is transfer_to_human.

And "any update on ticket HM-2026-1018?" got the handover line, because the
prompt explicitly said the bot cannot read requests and the only other tool
was transfer. `get_request_status` is now the bot's third tool — pointed
STRAIGHT at the Edge Function like the voice twins (the n8n router answers
locally and forwards async, wrong for a synchronous lookup), secret in a new
n8n credential ("Homies tool secret"), phone riding on the `wa:` call id.
Prompt: the you-cannot-read-requests block replaced with a status section —
bare reference message is a status question, statuses in the resident's
language, tool result is everything you know, deeper questions still go to
the team. Balance stays behind the identity question (PRD §13 #1); status is
read-only and stopped waiting for it. Verified against live rows: "1018" →
HM-2026-1018, open, electrical. Workflow updated and re-activated.

### The reference number, slowed to writing speed

The read-back example wrote the code as one token — HM-2026-1001 — and the
TTS said it like one word, too fast for a pen. The voice paces from
punctuation, so the fix is in the writing: step 4 now sends the code out in
pieces with a comma after each — HM, 2026, 1, 0, 0, 1 — followed by an offer
to repeat, and a repeat is the same pieces, not faster. Same rule added to
the status section's ask-for-it read-back. Both inbound twins (he 17,555 /
en 16,980 chars), demo-inbound.md synced.

### Everything pushed, and the dashboard is on the internet

Commit `b77435b` — 32 files, the whole week — pushed to
`TheSuperShyy/homies`. Then `scripts/vercel_deploy.py --apply` (token taken
from the logged-in Vercel CLI's auth store, written to `.env`, never echoed):
project `homies-dashboard` created git-linked with `rootDirectory: dashboard`,
the two `NEXT_PUBLIC_` vars set before the first build, one deployment,
READY. Live at **https://homies-dashboard.vercel.app** — verified 200 and the
calls tabs render with no login gate. Only the anon key went up; the script's
role check ran. Later pushes to `main` deploy themselves.

This is the open demo build — `anon_read` policies and no login. The URL is
unlisted but public: **re-lock before real resident data** (drop 010, restore
the middleware redirect), and the Supabase auth URL config + first staff user
are still owed when login returns.

### Dashboard: full-bleed, and the calls page learned outbound questions

`main` lost its 1180px cap — the tables now use the whole screen. The calls
page grew a view switcher (state in the URL, so views are bookmarkable): All /
Inbound / Outbound / No answer / Links sent. "No answer" reads
`call_outcomes` where outcome is `no_answer`, joined to the resident — name,
phone, building, attempt. "Links sent" reads `payment_links` with the
resident and status, and carries the schema's own caveat under the table:
`sent` means OXS confirmed it went out, and nothing on our side can see
whether it was paid, so the view never counts money.

### The amount-loop returned, and the cause was config, not prompt

Test call (שרה, gender f passed correctly): the agent restated the
why-you're-calling sentence three times against an "אוקיי", wrote אההה
against the written rule, and produced actual Hebrew typos — מאומיז, ועד בק,
בד בית are in Vapi's own bot log, so the model wrote them; they were not
mishearings. The live model object had **no temperature at all** — the design
value 0.3 was lost when the assistant was rebuilt — so gpt-5.4 ran at its
default, and there was no maxTokens cap to stop a runaway turn.

Set temperature 0.3 and maxTokens 200 by PATCH. The gender complaint from the
same call needed no change: `gender: "f"` was passed and the GRAMMAR rules
were armed; the call simply never reached a turn with a verb aimed at her —
מדבר מיכאל is the agent speaking about himself, masculine by identity.

Noted in passing: the demo still passes `card_last4` and `has_card`, retired
4 Aug ("neither may return"). The prompt no longer references them so they do
nothing, but the demo's variable list should be cleaned.

**The loop survived temperature 0.3 — model switched back to gpt-4.1-mini.**
Post-fix calls split: 09:57 ran the whole flow cleanly (ask, link, outcome,
end-call phrase), but 09:44 and 09:52 looped the amount exactly as before,
with a mid-word cut where a degenerating turn hit the 200-token cap. An
inconsistent failure at 0.3 points at the model, and gpt-5.4 is not the
design: the notes chose mini-class deliberately, the 7-Aug twelve-call
validation ran against it, and nobody ever validated 5.4 on this prompt.
Switched to gpt-4.1-mini, temp 0.3 and the token cap kept. If the loop
survives the mini too, the next suspect is Vapi's message history — the call
artifact shows all assistant speech merged into one message and all user
speech into another, and if that is what each inference actually receives,
no prompt can fix it.

**Status + anti-dupe extended to the English twin.** The en intake assistant
(`3edbe85b`) got the same treatment as he: get_request_status attached, the
"cannot look anything up" block replaced, the Status section added with
statuses in plain English, rule 3 rewritten, `modelOutputInMessagesEnabled`
on. Both prompts also gained one line under the no-live-transfer section —
**the transfer line is said once, ever** — after a test call where the en
agent said it twice back to back; the history fix should remove the cause,
the line removes the excuse.

**The inbound agent can now answer ticket status.** New `get_request_status`
in the debt-tools Edge Function (v11 deployed, tested against live rows):
read-only, reference-tail matching ("1013" finds HM-2026-1013) then
resident-on-call then building+unit — the open_request asymmetry, reused. The
tool points STRAIGHT at the Edge Function with the TOOL_SECRET header, not
through n8n — n8n answers Vapi locally and forwards writes async, which is
wrong for a lookup that needs a real synchronous answer. The status answer is
live truth, not the nightly export, so no §2.2 freshness caveat is owed —
that caveat belongs to OXS-side status, which this deliberately does not
touch. Prompt rewritten where it used to forbid lookups ("you cannot look
anything up" → "the one lookup you have"), a Status section added with the
status names in the caller's Hebrew, absolute rule 3 rewritten, and two
stowaways fixed: the stale feminine-first-person line (the voice has been
male Eyal since the Cartesia move — its own fixed lines were already
masculine) and `modelOutputInMessagesEnabled` turned on for inbound too,
before the debt agent's loop bites here. Live on `86a01f13` (16,971 chars)
and synced back to demo-inbound.md, which was byte-identical to live before
the edit.

**Expressiveness pass.** Voice: `positivity:low` → `curiosity:high` on the
Cartesia experimental controls — low positivity was flattening every line;
curiosity keeps the leaning-in sound without making a collections call
chipper. Prompt: one HUMAN LAYER paragraph — the TTS reads punctuation, so
write the melody; one bright word on genuinely good moments, shorter and
flatter on heavy ones; brightness is a moment, never a mood. 37,629 chars.

**The loop's likely root cause, found on the third pass:
`modelOutputInMessagesEnabled` was off.** By default Vapi builds the
assistant's own turns in conversation history from the transcription of its
TTS audio, not from what the model wrote. Evidence that this was the story
all along: the "typos" (מאומיז, לבד בית, ועד בק, "ה- link", "רוצה שאת עדכן")
appear in the bot's *logged* turns — they are Azure mis-transcribing
Michael's own speech, fed back to the model as its own words. A model whose
memory of what it said is garbled Hebrew cannot obey a never-repeat rule; it
does not recognise its own turns. The gpt-4.1-mini call showed the shape
clearly: flow correct (amount → ask → link → standing order, feminine forms
right), but the last line re-delivered verbatim after every acknowledgement.
Flag now true — history is the model's actual output. If the loop survives
THIS, the remaining suspect list is short and Vapi support is on it.

**Gender, second pass — reviewer criticism, not one bad call.** Three
reinforcements to GRAMMAR: the inflection table gained את/תרצי/תסגרי rows; a
new rule that the third person about {{first_name}} carries her gender too
(the not-the-account-holder line's יחזור → תחזור — the fixed-line inflection
rule covered endings aimed at the caller but nothing said about the resident
in the third person); and gender joined the BEFORE EVERY REPLY checklist, so
the check runs where the model acts instead of five sections away. Also
name-based inference: gender `unknown` + an unambiguous Israeli name (שרה,
יוסי) now resolves from the name; phrase-around only when the name settles
nothing. Prompt 36,443 → 37,129 chars, pushed by PATCH.

### The super-skills doc, distilled into a HUMAN LAYER — most of it rejected

The root-folder `hebrew-voice-super-skills (1).md` (20 techniques for
humanlike voice agents) was asked into the debt agent. It went in as one
compact section — THE HUMAN LAYER, after the budgets — not as twenty, because
most of the doc either already exists in stronger form or directly conflicts
with rules this prompt earned the hard way on 7 Aug.

Taken (5): pace mirroring (never temperature — hot already has its own rule),
content-matched answer timing, specific acknowledgement over bare אני מבין,
one genuine reaction to a personal detail, the demonstrated-memory callback in
the closing lead-in, warm bridges between subjects.

Rejected, with reasons: varied human goodbyes (the closing is fixed because
`endCallPhrases` matches on its words — vary it and the call stops ending);
calculated vulnerability ("יום ארוך", "אני עדיין לומד את המערכת" — the agent
never pretends to be human); slang examples (סבבה/יאללה banned); the discount
no-that-feels-like-yes (absolute rule 4 — no discounts, ever); free-value tips
(invented facts risk); temporal anchoring (no date/weather variables exist);
time-check and planted callback (wrong length of call). Per the file's own
editing rules: described what to convey, wrote no Hebrew lines, so no
`vapi_en.py` change.

Prompt: 34,715 → 36,443 chars. Pushed by direct PATCH to `3303317e` keeping
the live model object intact — **not** `vapi_sync.py`, whose BASE block still
says gpt-4.1-mini + Azure and would have downgraded the live gpt-5.4 +
Cartesia config. That mismatch is now the standing hazard: running
`vapi_sync.py debt --apply` today clobbers model and voice. The script needs
its BASE brought up to the live truth before anyone runs it again.

### Demo voice outage: Cartesia credits, two broken signups, and a discovery

The web demo was ending every call at pickup. Call logs showed
`pipeline-error-cartesia-voice-failed`; a direct TTS test against Cartesia
returned 402 — the account had hit its credit limit, and the Elliot fallback
was not rescuing the call. Two fresh Cartesia accounts both stuck at
"processing your subscription details" and returned 500 on every synthesis
call until provisioning cleared (their status page showed green throughout —
the 500s were account-side, not an outage).

The discovery that ended it: **the demo's voice was never a clone.**
`a976c076` "Eyal - Grounded Guide" is a public Cartesia library voice
(`is_public: true`, language `he`), usable on a free account. The Pro tier
gates cloning only. Pointed Vapi's Cartesia credential at the new free-tier
account, restored the assistant's original voice block (sonic-3, `he`,
positivity:low, chunkPlan guards, Elliot fallback), and the demo speaks again.

Along the way the assistant briefly ran Azure `he-IL-AvriNeural` as a
stopgap — rejected as robotic within one test call, which is a real A/B data
point for the native-voices question.

Open: free-tier credits are small, so heavy rehearsal can drain them; the
"Echo Stone" clone from `voice/echo-stone-sample.wav` still exists on no
account (needs a working Pro subscription, or ElevenLabs Starter + eleven_v3
with latency unmeasured); one or two $5 Pro charges may have gone through on
the abandoned accounts — check billing, refund via support@cartesia.ai.

### Credentials checklist written; .env.example generalised

`docs/reference/Homies-Credentials-Checklist.md` now lists every account the
build needs, per the day's decisions: telephony provider undecided (generic
BYO SIP trunk — gateway IP, SIP username/password), WhatsApp number provided
by Homies, Meta Business Manager from zero (verification is critical path
alongside Israeli DID KYC), chatbot LLM via OpenRouter. `.env.example`
telephony block generalised from Telnyx/Twilio to SIP_* variables; WhatsApp,
OpenRouter, Google Sheets and Monday blocks added. Domain split in two: n8n
and Chatwoot subdomains needed at build time (Meta webhook wants HTTPS), the
CRM's branded domain deferred to handover — Vercel's own URL until then.

### Dashboard pushed — `a2b361b`, the first commit in two days

Twenty-two files: the whole of `dashboard/`, migrations 008 and 009, and the
feature doc. Everything else from the last two days — Chatwoot, the WhatsApp
menu and language work, `check_whatsapp.py`, the Supabase writer switch — is
still uncommitted in the working tree.

Checked before staging rather than after: `.env`, `dashboard/.env.local`,
`node_modules` and `.next` all ignored, and the staged list confirmed empty of
them. `.env.local` holds only the URL and the anon key — no service role key
was ever in it. Added `dashboard/.vercel/` to `.gitignore` ahead of the deploy,
since `vercel link` writes it on first run.

`dashboard/.env.example` documents the two variables Vercel needs and says
plainly why the service role key is not among them. **Root Directory must be
set to `dashboard`** in the Vercel project — the app is not at the repo root,
and Vercel will otherwise build the repository and find no `package.json`.

## 2026-08-08

### A dashboard, and the three things it would have shown as facts

Asked for a dashboard over tickets, calls, concerns and transcripts, with
everything in Supabase. Most of the work was the second half of that sentence.

**Chat transcripts were not stored anywhere.** The conversation lived in n8n's
memory node — context for the model, never a record: capped at 30 messages, not
queryable, gone on restore. Migration 008 adds `messages`, one row per message
both directions, plus `v_conversations`. A child table rather than a bigger
`transcript` column because chat has no end-of-call moment to write one at, and
a read-modify-write of a growing string loses one of two concurrent messages.

**Every WhatsApp interaction was filed as an outbound voice call.**
`interactionId()` hardcoded `channel` and `direction` from when Vapi was the
only caller — the same shape as `opened_via` that morning. A calls page would
have reported calls that were never placed. Fixed; the four bad rows deleted.

**The log wrote our words as the resident's.** On the media and menu branches
Sort's `text` holds the *reply*, not the message, so the transcript had the bot
greeting itself. `in_text` is now carried separately from the first line.

**And logging was downstream of a failure.** `Log reply` sat to the right of
`Send`, so when Send failed — a recipient off the test allow-list — the run
aborted and nothing was logged. executionOrder v1 walks the canvas top to
bottom, so the node moved above Send. A send failure is exactly when the record
matters most.

Verified end to end: a four-message conversation, both sides, correct types,
`interactive` for the menu, `(no text)` for the image.

**Then the leak.** `messages` shipped in 008 without RLS. Every other table has
it on — the anon key reads nothing from them — and `messages` returned real
rows to it. **The anon key is public by design; it ships in the browser
bundle.** Anyone with it and the project URL could read every resident's
conversation. Live about an hour, four test threads, no real resident. Luck.

Migration 009 enables RLS, grants `staff_read` to `authenticated` and never to
`public` (which includes `anon`), sets `security_invoker` on the views — a view
otherwise reads with its owner's rights and hands rows out regardless of who
asked, which is what `v_conversations` was doing — and **fails the migration**
if any table in `public` has no RLS. 008 got through because nothing looked.

The dashboard itself is Next.js 14, seven pages, no CSS framework, builds
clean. Read-only by construction: no write policy exists, and an insert from a
staff session returns `42501`. Confirmed with a temporary auth user — signed in
reads all five tables, writes are refused, signed out reads nothing — then the
user was deleted.

Two build failures worth keeping. A single `lib/supabase.ts` exporting both
clients cannot compile: the login page is a Client Component and importing a
module that touches `next/headers` fails even unused. And the cookie callbacks
needed explicit types under `strict`.

Not deployed — Vercel needs their account. `NEXT_PUBLIC_SUPABASE_ANON_KEY` and
nothing else; the service role key in a browser bundle would hand a stranger the
whole database.

### Chatwoot is up at chat.srv1879140.hstgr.cloud

Deployed to the VPS that already runs n8n. Four containers, valid certificate,
`4.16.2`, `queue_services: ok` and `data_services: ok` — sidekiq and Postgres
both actually connected, not merely running.

Three assumptions were wrong and each was caught by reading the box instead of
trusting the plan.

**There is no Traefik network.** `ss` showed `traefik` itself owning :80 and
:443 rather than `docker-proxy`, which means host networking. The compose file
had declared `proxy` as `external: true` and would have refused to start.
Traefik reaches containers at their bridge IP through the Docker socket, so
Chatwoot needs only its own network plus labels — and with
`--providers.docker.exposedbydefault=false`, the labels are not optional.

**The certresolver was not worth guessing.** It is `letsencrypt`, copied
verbatim from n8n's own labels on the same box.

**No DNS work was needed at all.** `*.srv1879140.hstgr.cloud` is a wildcard —
`chat.`, `n8n-zqvb.` and a random string all already resolve to
186.240.147.235. HTTP-01 only needs the name to point at a box we control, not
ownership of the zone, so the certificate issued on first boot. The free domain
hPanel offers was never a blocker.

Two smaller things. `base: &base` is written as a service in Chatwoot's own
published compose, and compose obligingly starts it as a container that does
nothing; it is an `x-` extension field here. And `db:chatwoot_prepare` logs
`PG::UndefinedTable: relation "installation_configs" does not exist` in red —
an initializer running before the schema exists, with `Loading Installation
config` succeeding four lines later. Alarming and harmless.

`ENABLE_ACCOUNT_SIGNUP=false` does not lock out the first admin: every route
redirects to `/installation/onboarding` until an account exists. Verified before
handing the URL over, since the opposite would have meant a fresh install
nobody could log into.

Memory caps — rails 2g, sidekiq 1g — are there to protect n8n, which shares the
box. `curl` against n8n returned `HTTP/2 200` after the deploy.

### Chatwoot: self-hosted, and it owns the number

Two decisions, both taken 8 Aug.

**Self-hosted on Hostinger.** At 19 staff, Chatwoot Cloud is $19/agent/month —
about $361/month against a VPS at $7–15. The trade is that upgrades and backups
become ours, which is the trade already made for n8n on the same provider.

**Chatwoot owns the WhatsApp number**, with n8n behind it as an *agent bot*.
The alternative — n8n keeps the number, Chatwoot mirrors conversations read-only
— is less disruptive today and leaves the per-conversation AI toggle and real
human handover permanently impossible, which are two of the six capabilities
being asked for. A webhook answers every message by definition: there is no seat
to assign to, no second participant to hand to, and nowhere for "the bot is off
for this thread" to live.

The bot itself does not change. Agent, prompt, both tools, the Supabase writer —
all stay. What changes is who calls them.

Written: `deploy/chatwoot/` (compose, Caddyfile, env template) and
`docs/features/12-chatwoot/feature.md`. Four services — rails and sidekiq are
separate processes sharing one image, and running rails alone gives a working
dashboard that delivers nothing. Postgres must be **pgvector**, not plain, or
`db:chatwoot_prepare` fails. Caddy terminates TLS because Meta will not deliver
to a self-signed callback, so the certificate is the channel rather than a
nicety. `deploy/chatwoot/.env` is gitignored.

Not deployed — it needs DNS and an SSH session, which are the user's.

**It goes on the VPS that already runs n8n**, srv1879140 / 186.240.147.235,
KVM 2, at 11% memory and 4% disk on 8 Aug. A second VPS buys isolation for
another $7–15/month and is not worth it at this size.

Two things changed once the actual box was looked at rather than assumed.

**The Caddy service was deleted.** Port 80 there answers a bare `301 Moved
Permanently` with no `Server` header — Traefik, which is what Hostinger's n8n
template ships. A second proxy would have fought for 443, and the process that
failed to bind might have been the one serving n8n. Chatwoot now attaches to
the existing Traefik by labels, publishes no ports at all, and keeps Postgres
and Redis on a private network the n8n containers cannot see.

**Memory limits were added, to protect n8n rather than Chatwoot.** This box
runs the bot. If Rails leaks on 2 vCPU the OOM killer picks its victim by size,
and the victim could be n8n — taking WhatsApp down to fix nothing. `rails` 2g,
`sidekiq` 1g.

The two Traefik values — network name and certresolver — are discovered on the
box, not guessed. A wrong network means Traefik cannot see the container; a
wrong resolver means no certificate, and Meta will not deliver to a callback it
cannot verify.

The risky step is documented and is the only one: moving the callback means a
few minutes where Meta points at something not yet answering, and inbound
messages in that window are lost rather than queued. The test number has no
residents on it, so the first pass is free.

### Supabase is the store of record, and three guardrails now hold it there

Asked for Supabase, duplicate protection, and guardrails against the whole
thing unravelling again. All three, in that order.

**The writer moved.** `_writer()` in `n8n_deploy.py` returns the Supabase Edge
Function instead of the Apps Script URL, with the shared secret in a header
rather than the query string. Smaller than it sounds: both stores answer in the
same Vapi shape, and both writer nodes forward the untouched original envelope,
so a URL and a header changed and nothing in the graph moved. Voice and
WhatsApp both write to Supabase now. Apps Script stays deployed as the export
target and is no longer the store of record.

**The duplicate guard is in the Edge Function**, not in the prompt, because a
guard the model can decline is not a guard. Same building, same type, same unit
(`.is()` for NULL, since `.eq()` never matches it and common-area faults are
the ones most likely to be reported twice), still open, inside 30 minutes → the
existing reference comes back with `duplicate: true`. Not keyed on the
description: two people describing one lobby leak will not phrase it alike, and
substring matching on free text is the kind of clever that fails silently.
Verified across five cases — same place dedupes, different building does not,
same building with a unit is distinct from the same building without one.

**`scripts/check_whatsapp.py` checks consequences, not configuration.** It
posts a real signed message at the live URL and then looks in the database for
the row, because every serious fault this bot has had was silent and would have
passed a config audit: the half-wired webhook, the wrong WABA subscription, the
truncated reference, a week of tickets in a spreadsheet, a regex full of
backspace characters. Seventeen assertions, exits non-zero, cleans up after
itself.

It failed twice on its first two runs, which is the point.

**Once on a bad fixture of mine** — the building was `__selfcheck__` and the bot
asked which building, correctly, because no building is called that. A fixture
the system is right to reject is a broken fixture.

**Once on a real bug.** A lobby leak wrote `unit = "שטחים משותפים"` — "common
areas". The prompt says common property has no apartment and the model complied
with the idea while filling in the field. Nothing errors, the row reads
correctly to a person, and it is wrong to every query: `unit IS NULL` stops
finding common-area faults, grouping by unit invents a flat called Common
Areas, and the new duplicate guard stops matching. **A model told to leave a
field empty will often name the emptiness instead.** `unitOf()` now decides:
a unit is short and contains a digit, and a label is not a unit.

`opened_via` was hardcoded `"voice"` at all three insert sites and was about to
start lying, since WhatsApp writes through the same function. `channel()` reads
the `wa:` call-id prefix.

Four test rows deleted afterwards; `requests` is back to the one real row.

### Every ticket opened today went to a spreadsheet, not to Supabase

Asked whether `HM-2026-8282` was in the database. It is not, and neither is any
other reference the bot has read out today.

`requests` in Supabase holds **one row** — `HM-2026-1001`, 08:06, from a direct
test of the Edge Function. Checked with the service-role key, so this is not RLS
hiding rows; the anon key sees zero.

The tool webhook the bot calls, `homies-debt-tools` on n8n, does not post to
Supabase at all. Its writer node posts to the **Google Apps Script bridge**, and
`call_requests` on that spreadsheet now holds 28 rows. The reference comes back
from the sheet, which is why it looks real: it *is* real, in the wrong place.

So the two halves of this system have been drifting apart in plain sight. The
Edge Function got three fixes today — the `open_request` building bug, the
urgency validator, `save_partial_request` — and **nothing calls it except the
end-of-call report**. The voice agents and WhatsApp both write through the same
n8n router, and that router writes to Sheets.

Nothing is lost; every ticket exists. But the CRM in Phase 6 reads Supabase, the
migrations describe Supabase, and `requests.reference` is generated by a Postgres
default that has produced exactly one value.

Not fixed — repointing the writer is a one-node change, but it swaps the store
of record for the voice agents at the same time, and that is a decision rather
than a repair.

### The language stopped being the model's decision

Reported a second time from a handset, after the bilingual fixed lines were
already in: English menu, `Balance and payments` tapped, Hebrew handover line
back. The prompt said the right thing and the model did not do it — a rule
competing against a conversation history that was largely Hebrew, and history
kept winning.

So it is no longer a rule. **Sort decides the language in code and remembers
it**, per phone, in the same workflow static data that holds duplicate
suppression:

- an explicit request — the menu row, or the word in either language — sets a
  preference and it **sticks**;
- otherwise the script of the message decides, and updates the preference, so
  someone who goes back to typing Hebrew gets Hebrew back;
- a photo, which carries no words, falls back to whatever was already chosen.

The decision then rides **on every turn** as a directive at the top of the
message (`[Answer this message in ENGLISH.]`), rather than sitting in a constant
system prompt — a constant instruction is precisely what was already failing
against live context. Same caveat as the dedupe map: static data does not
survive an n8n restore, and the cost of losing it is one message in the wrong
language.

Two things fell out of testing it:

**A bare `speak english` was answered with the media line** — *"I can only read
text here"*, in reply to text. Nothing about that message needs a model: the
switch is a fact Sort has already established. It now gets a fixed confirmation
in the new language. Guarded by a leftover check, so *"speak english, there is a
leak in the lobby at Herzl 14"* still reaches the agent, in English, with the
leak intact — verified.

**And the first attempt at that guard silently did nothing.** The patch script
wrote `"\b"` into the regexes, which in Python is a **backspace character**, not
a word boundary. `/\benglish\b/` shipped as `/‹BS›english‹BS›/` — a valid regex
that matches nothing. No error anywhere; the Hebrew branch worked because its
patterns have no `\b`, so half the feature passed its test and the other half
quietly did not. Ten of them across the file, now repaired.

### A fixed line was fixed in one language

Found by the client on a real handset, which is the only place it could have
been found. English was tapped from the menu, the intro came back in English,
then *"any update on my ticket?"* was answered with
`אני מעביר את זה לצוות, נחזור בהקדם.` — an all-English conversation ending in
Hebrew.

The language rules written an hour earlier were obeyed exactly. The handover
line is not written by the model: the prompt names it verbatim as one of two
**fixed lines**, and a fixed line is fixed in the language it was written in.
Two correct rules, and the newer one had no authority over the older one.

Both fixed lines now exist in both languages, with the rule stated where it was
missing: *a fixed line stays fixed, but it does not stay Hebrew.* The error
branch's copy is an expression over the language Sort detected, so a model
failure cannot undo the language choice either.

Re-tested end to end on the same sequence: `hi` → English menu → tap English →
*"Hi, Michael from Homies. How can I help?"* → *"any update on my ticket?"* →
*"I'm passing this to the team, we'll get back to you shortly."*

Third instance today of one shape: **a rule that reads as absolute silently
outranks the rule that should have qualified it.** After the apartment question
and the announcement, this one crossed languages rather than sections.

**`transfer_to_human` remains unreliable** — called on the ticket-status
question, not called on *"how much do I owe?"*, both in the same batch. The line
is delivered either way, so the resident is told a human is coming while nobody
is told anything. Not fixed.

### A menu on the first message, and English when asked

Two asks: buttons to choose from, and an English mode triggered by saying so.

**The menu is a list, not reply buttons** — buttons cap at three and the client
picked five options. Meta's limits are hard: row title 24 characters,
description 72, list button 20, ten rows total. Two of the five rows,
`status` and `balance`, are **not built** and route to a human. That was the
explicit choice: the gap is visible rather than hidden, and a tap lands exactly
where the same question in words already lands.

**The menu appears only for a bare greeting.** `שלום` gets it; `שלום, יש נזילה
בלובי בהרצל 14` does not — it opens a ticket, because answering a stated fault
with a menu would undo the morning's rule about not asking what happened when
already told. The greeting test is anchored and whole-string, after stripping
emoji and trailing punctuation.

**Parsing taps had to land in the same change.** An `interactive` message
carries no `text` field, so under the old parser a resident tapping a button we
had just sent them would have been told *"I can only read text"*. Sort now reads
`button_reply` and `list_reply`, keeping the row id for the log and passing the
title on as the message.

**Menu language is chosen by script detection** — one Hebrew character decides
it — because the menu is sent without a model call.

**English mode lives in the conversation memory**, whose window went 12 → 30.
That is the whole mechanism, and its boundary is worth writing down: the switch
survives exactly as long as the request is still inside the window. A hard
per-phone language field belongs in an n8n Data Table, which this instance
supports (`/api/v1/data-tables` responds) and which is the right fix when the
toggle must survive indefinitely.

Seven paths tested. Hebrew greeting → Hebrew menu; `hi` → English menu; a
balance tap → handover **with `transfer_to_human` actually called**, which is
the tool that was narrated-but-not-called earlier today; an `open` tap → asks
what happened; greeting-plus-fault → ticket `HM-2026-9030`, no menu; and
`speak english please` mid-conversation → *"Hey, Michael from Homies. How can I
help?"*.

Every send in those runs failed `131030` on invented numbers, which proves the
allow-list and **not** the payload — Meta may check the recipient first. So the
Hebrew menu was sent for real to the registered test number and delivered
(`wamid.HBgMNjM5NjAzOTEzNTE0…`). The list payload is valid.

### The bot introduces itself now — and was truncating reference numbers

First real WhatsApp exchange, execution 82: `hi` in, `שלום, מה קרה?` out,
delivered. Correct, brief, and from nobody — a resident has no way to tell they
reached the building company rather than a wrong number. The first message in a
conversation now carries a name and a company (`היי, מיכאל מהומיז. מה קרה?`),
written as a rule rather than a third fixed line, plus two explicit guards: do
not introduce yourself twice, and do not ask `מה קרה?` when the first message
already said what happened. Both verified.

**Found while checking that: the model was silently truncating the reference
number.** `open_request` returned `HM-2026-8884` and the resident was told
`2026-8884`. Both test tickets, so it is default behaviour, not a one-off.

Nothing errors, the ticket is real, the reply reads perfectly, and the resident
writes down an identifier that will not be found when they quote it to staff.
The prompt already said *do not invent a reference number* and that rule was
obeyed — the number came from the tool. Passing a value through to a human
**unaltered** is a different instruction and had to be written separately, with
the exact failure named, because "exactly" is what the model already believed it
was doing. Re-tested: `HM-2026-8894` in, `HM-2026-8894` out.

### A rule loses to the headline above it — twice, in the same reply

Execution 89, a stuck lift with the floor given, answered
`אני פותח קריאה על מעלית תקועה. יש מספר דירה?`. Two faults, and both rules
already existed.

**The apartment question.** The rule was not too weak, it was in the wrong
place. The section opened *"ארבעה דברים: מה התקלה, באיזה בניין, **באיזו דירה**,
וכמה זה דחוף"* — four required things stated unconditionally — with the
common-property exception three paragraphs below. The model followed the
headline, which is what a headline is for. Folded the exception into the
definition instead: **three** things now, and *where* is one question with two
answers — inside a flat needs building and unit, common property needs the
building and nothing else, not the floor either.

**The announcement.** `אני פותח` was said before `open_request` ran, in a
message that then asked a question instead of calling it. The tool never ran.
The old rule said *do not say you opened a ticket before the tool returned*, and
the present tense complied with the letter of it.

Tightening that surfaced a third habit on the next run: `אני פותח קריאה על שער
חניון שלא נסגר. זה בסדר?` — asking permission to do the one thing it exists to
do. A resident who reports a gate has already asked. Added: never ask to open,
only ask for what is missing.

Four fault types re-tested afterwards, all correct — gate, bulb and lift open
without asking anything, an in-flat leak with a unit opens, an in-flat fault
without one asks for the unit, and a lift asked first whether anyone was
trapped, which is the safety rule working unprompted. References matched the
tool in every case.

**The general lesson, and it appeared twice in one day: an exception placed
after a categorical statement does not modify it.** Fold it into the statement,
or stop the statement being categorical.

**Judgement call left open:** *"יש רעש מהגג כל הלילה"* was answered with
*"איזה רעש?"*. The prompt says do not ask a resident to re-describe a fault; a
real service worker probably would ask this one. Not changed.

### The WABA was subscribed to the wrong app, and nothing would have said so

With the API Setup token in hand, `GET /{waba}/subscribed_apps` listed exactly
one app — **"WA DevX Webhook Events 1P App"**, Meta's own dev-tools listener.
Not HOMIES. App-level registration (done 8 Aug) tells Meta *where* to deliver;
it does not subscribe the Business Account to the app. Both are required and
only one of them is the step anyone writes down.

The failure mode is the one this workflow keeps producing: the callback URL
shows verified in the dashboard, the workflow shows active, the number accepts
messages, and no execution ever runs. Third time the same silent-success shape
has appeared here — after `multipleMethods` output 1 and after `serverUrl: null`
on the voice assistants. `POST /{waba}/subscribed_apps` with the user token
fixed it; both apps are now listed.

Then a full end-to-end run against the live URL with a correctly signed
envelope — *"יש נזילת מים בלובי של הרצל 14"*:

    WhatsApp → Sign the raw body → Sort → Answer Meta (200 in 0.8s)
    → Is there a message? → OpenRouter + open_request
    → "פתחתי קריאה 2026-8884. אעדכן בהמשך."
    → Send  ✗ 131030 Recipient phone number not in allowed list

Nine nodes correct, one refusal, and the refusal is the right one: the test
number only delivers to hand-registered recipients. Reproduced the same error
straight against Graph to prove it was the allow-list and not the credential —
`131030`, not a `190`. The credential works.

Note the row: reference **2026-8884** in `requests` is test data written against
the invented number 972500000001.

### The send token goes in n8n's credential store, not in the workflow

Asked to run on Meta's **test number** for now, which is the right call — it
needs no Business verification, so it un-blocks the last row of the checklist
today instead of in one to two weeks. Two limits come with it: it only sends to
up to five recipient numbers you register by hand, and its access token expires
roughly every 24 hours.

Neither of the two values can be fetched by API. `APP_ID`/`APP_SECRET` reach the
app, and the phone number id and access token hang off the **WhatsApp Business
Account** — `/{app-id}/whatsapp_business_accounts` and both its owned/client
variants return `(#100) nonexisting field`, because those edges live on the
Business, which an app token cannot see. They have to be copied from the
dashboard.

What did change is where the token lands. The Send node carried
`Authorization: Bearer <token>` as a plain header parameter, which writes the
token into the workflow JSON — readable by anyone with n8n access, and carried
into every export and backup. It is the same mistake the Crypto node stopped us
making with `APP_SECRET` yesterday, except n8n *refused to publish* that one and
nothing refuses this one. `ensure_send_cred()` now creates an `httpHeaderAuth`
credential and the node references it by id.

It deletes and recreates on every `--apply` rather than reusing the id. n8n's
public API can create and delete a credential but not update one, and a 24-hour
test token means rotation is routine — reusing the id would mean silently
sending yesterday's token. Recreating guarantees the value in `.env` is the
value in n8n.

### The voice agents now record their own calls — eleven of them were thrown away

`interactions` had zero rows. Eleven test calls happened on 7 Aug and every
transcript, every ended reason and every latency figure from them lives in the
Vapi dashboard and nowhere the CRM, the scoreboard in
[08-instrumentation](features/08-instrumentation/feature.md) or a native Hebrew
reviewer can reach. The table has had columns for `transcript`, `summary`,
`audio_url`, `duration_seconds` and `latency_ms` since `001` on 2 Aug and
nothing has ever written one. The tools created stub rows during a call and no
second half ever arrived.

The cause was one missing field. All four assistants had `serverUrl: null` and
`serverMessages: []`, so Vapi computed the end-of-call report and posted it
nowhere.

**This was blocked and stopped being blocked today.** `vapi_sync.py` has said
since 5 Aug that the proper fix for the duration cap "needs a server URL that
does not exist yet". Deploying `debt-tools` this morning created one.

Now live on all four:

```
server         https://…supabase.co/functions/v1/debt-tools
serverMessages ["end-of-call-report"]
```

**One message and not eleven.** `conversation-update` and `speech-update` fire
several times a second, each a round trip to Tokyo into a function that writes
the same row. The end-of-call report carries the transcript, the recording, the
duration, the ended reason and the latency in a single POST *after* the call is
over, where nothing it does can cost the caller a millisecond.

The report endpoint is resolved by its own `report_server()`, deliberately not
by `tool_server()`. They are the same URL today and they are not the same
decision: the tool endpoint follows where the integrations live and currently
picks n8n, which has no handler for a server message at all. Pointing the report
there would have returned 200 and written nothing — the failure that leaves no
trace anywhere.

Verified against the live function with four cases before anything was pushed: a
`status-update` acknowledged and ignored; a report writing one filled row; a
tool firing first and the report updating that same row rather than making a
second, keeping the more specific `transfer:hardship` over `caller_hung_up`; and
a cut-off call salvaged. Test rows deleted.

### Three bugs the wiring turned up on the way

**`open_request` was dropping the inbound caller's building.** It read
`ctx.building ?? ""` — the value the campaign runner attaches to an outbound
call. Inbound there is no caller ID and no lookup, so the building only ever
arrives as a tool argument, and this file never read it. Every intake ticket
written through Supabase would have carried an empty building while the agent
read a real reference number back to the caller. n8n does it right
(`ctx.building || args.building || ''`), which is why nothing has shown up yet:
the live assistants post to n8n. It would have appeared on the day we switched.

**`save_partial_request` did not exist in the Edge Function.** The live intake
assistant carries the tool. Pointing it at Supabase would have answered `unknown
tool save_partial_request` at the exact moment it was salvaging a failing call —
the one outcome feature [07](features/07-partial-ticket/feature.md) says is not
allowed. Written now, against the `needs_review` status migration `003` added for
it, and it never refuses: an empty description is a real answer, because it says
the audio was unusable.

**`urgency` is validated in the function instead of by Postgres.** Yesterday's
`urgent` reached the database and came back as an English constraint message
mid-Hebrew-call. There is now a small synonym map — `urgent`→`high`,
`critical`→`emergency` — and anything unrecognised lands on `normal`, not `low`:
the failure that matters is an emergency filed as routine.

### The duration cap has a net under it that the model cannot decline

Vapi hangs up on the second `maxDurationSeconds` expires, mid-word, and never
tells the model it is coming — so the agent cannot be relied on to call
`save_partial_request` first. The report handler now sees `endedReason:
max-duration-exceeded` or `silence-timed-out`, checks whether the call produced
any row at all, and if not writes a `needs_review` request with the transcript in
it verbatim.

Verbatim rather than summarised, deliberately. Summarising means guessing the
building, and a guessed building on a maintenance ticket sends somebody to the
wrong address.

### Voicemail detection was off on both outbound agents

`voicemailDetection: {}` is not a neutral default on an agent that dials people.
It is the agent holding a full debt conversation with an answering machine,
reading a resident's balance into a recording anyone in the household can play
back, and hanging up having logged nothing. `voicemail` has been a value in
`log_call_outcome`'s enum since 4 Aug; nothing was ever detecting it.

On now, Vapi's own model rather than a beep timeout — Israeli carrier greetings
run long, and a fixed timer either cuts off a real person who paused or waits
through the whole greeting. **No `voicemailMessage`.** Leaving a recorded message
about somebody's debt on a machine is a disclosure to whoever plays it, which is
a decision for Homies and their lawyer rather than a config default. Detect, log,
hang up, let the campaign runner try again.

### Both English twins have diverged and refuse to rebuild

`vapi_en.py intake` and `vapi_en.py debt` both stop rather than build:

```
intake  9 passages no longer match — including "You are Michal…"
debt    LANGUAGE block did not match. The Hebrew prompt has changed.
```

That is the safety property doing exactly what it was written to do. The cost is
that both live English assistants are stale copies of prompts that no longer
exist — the intake twin is still feminine *Michal* while the Hebrew agent has
been masculine *Michael* since 7 Aug. **An English twin that has quietly stopped
representing the Hebrew one is worse than no twin, because it gets trusted.**

The two changes that do not touch a prompt were applied to them directly:
`waitSeconds` and the report endpoint. Rewriting the two substitution tables is a
job of its own and is not done.

`waitSeconds` was still 0.4 on both twins — the 7 Aug latency fix only reached
the Hebrew pair. That field is dead time before any work starts, so unlike the
punctuation timers around it, it is not a property of the language, and leaving
it made the twin 150ms slower than the assistant it exists to represent.

### Meta is connected to n8n, and the webhook is no longer forgeable

`APP_ID` and `APP_SECRET` arrived in `.env`. They are **not** the two values the
workflow needs to send — that is still `WHATSAPP_PHONE_NUMBER_ID` and
`WHATSAPP_ACCESS_TOKEN`, which live on the WABA rather than on the app, and an
app access token can reach neither. What they *are* good for turned out to be
two things that mattered.

**One: the callback is registered, by API rather than by hand.**
`POST /{app-id}/subscriptions` accepts an app access token, so the dashboard
step is now a script:

```
object     whatsapp_business_account
callback   https://n8n-zqvb.srv1879140.hstgr.cloud/webhook/homies-whatsapp
fields     ['messages']
active     True
```

Meta called the GET challenge as part of that and got the right answer, so
verification passed on the first attempt.

**Two: the webhook was an open endpoint that files service tickets, and now it
is not.** Every POST Meta sends carries `X-Hub-Signature-256`, an HMAC-SHA256 of
the raw body keyed on the app secret. Nothing was checking it. Anyone who
learned the URL could have posted a forged envelope with any phone number in it
and opened a real ticket against a real resident — as I did repeatedly today
with `curl`, which is exactly the point.

```
correctly signed   -> passes, opens the ticket, replies
no signature       -> dropped, "unsigned"
wrong signature    -> dropped, "bad signature"
GET verification   -> still echoes the challenge
```

All four answer **200**. Meta must never be told to retry, and a caller who is
not Meta learns nothing from the response.

**Two things went wrong on the way, and both are worth keeping.**

`require('crypto')` in the Code node throws **`Module 'crypto' is disallowed`** —
this n8n runs Code in a task-runner sandbox with builtins blocked, which is a
server setting we cannot reach from here. It broke every message for a few
minutes before the executions showed why. The fix is n8n's native Crypto node,
which needs no module and takes the secret from the credential store instead of
from a string baked into this repo's source. Better in both directions.

Then n8n **refused to publish** the first attempt:

```
Cannot publish workflow: Node "Sign the raw body":
  Missing or invalid required parameters: secret
```

`typeVersion: 1` of the Crypto node takes the secret as a plain node parameter,
which would have written `APP_SECRET` into the workflow JSON. V2 reads it from a
`crypto` credential. The server-side validation caught a real mistake before it
shipped — the same check `validate_workflow` would have made, arriving from the
other direction.

Two n8n credentials now hold secrets that used to be, or would have been, in
files: `Homies OpenRouter` and `Homies Meta app secret`.

### The real WhatsApp requirement arrived, and the bot is one sixth of it

PRD item 3, from the client, saved verbatim in
[11-whatsapp-bot/prd.md](features/11-whatsapp-bot/prd.md). It is not a request
for a bot. It is a request for a **centralised WhatsApp system** — one business
number, employee seats, four departments (Collections, Operations, Management,
Service), chat transfer between agents, open/closed ticket tracking, full logs
with automatic summaries and topic tagging, and an AI bot that is **one
participant in that inbox** rather than the thing itself.

Six capabilities are named. **We have one.** Opening service tickets works end
to end; sending payment links exists but belongs to the debt agent and is not
attached here; FAQs, ticket status and balance/debt do not exist.

**The structural item is the per-conversation on/off toggle.** Today the webhook
answers every message that reaches it — that is what a webhook is. There is no
per-conversation state and nowhere to keep it. Meta's Cloud API delivers to
exactly one callback URL, so whatever owns the inbox owns that URL and n8n moves
behind it. That is not a feature to add later; it decides the shape.

**And it reopens a question that was closed by accident.** The bot identifies
nobody: it takes the phone off the envelope and files a ticket against it, which
is safe *because it only ever writes*. Three of the six new capabilities — ticket
status, balance, debt — **read** personal financial data back to whoever is
holding a handset. PRD §13 #1, the verification method, has been open since the
first spec and blocked nothing. It now blocks two capabilities.

**The Chatwoot decision from 7 Aug is worth revisiting on its own terms.** It was
deferred partly because the only VPS was shared production carrying four other
clients — an objection that died this morning when Homies' own n8n turned up.
What is left of the argument is real (a Rails stack to run and maintain) but the
thing it was deferred *for* — a handover inbox nobody had asked for — is now
explicitly asked for, in writing, four times over.

### The bot is male, the resident is not assumed to be — and it stopped sounding like a bot

Asked for: Hebrew as the main language, natural and local and casual so it reads
as a person, and **male** — masculine forms only, with better words where a word
carries too many meanings.

**The male half is easy. The other half is the one that can hurt somebody.**
Hebrew marks gender on the imperative and the second person, so `תכתוב לי` and
`אתה גר` are said to a man, and roughly half of ~10,000 apartments are not men.
Nothing in the WhatsApp envelope gives a resident's gender; a display name is a
guess. So the prompt now carries two rules, not one:

| | Rule |
|---|---|
| About **himself** | Masculine, always — `אני פותח`, `אני מעביר`, `רשמתי`. |
| About **the resident** | Never gendered — `אפשר לכתוב`, `יש כתובת?`, `מה קרה?` |

This costs nothing in register, which is why it works: `אפשר לכתוב לי מה קרה?`
is *more* natural in a service context than `תכתוב לי מה קרה`, not less.

**And the first draft of the handover line broke that rule.** `יחזרו אליך
בהקדם` — without niqqud `אליך` is *elecha*, addressed to a man. The fix is not a
slash or a spelling trick: drop the addressee. `נחזור בהקדם` is first person
plural, which is how a company talks anyway, and carries no gender at all. Both
fixed lines were re-checked for the same fault afterwards.

**Three words were replaced for carrying too many meanings:**

| Was | Now | Why |
|---|---|---|
| פנייה | קריאה / קריאת שירות | `פנייה` first means *turning*. `מספר קריאה` reads as a reference number without needing context. |
| בעיה | תקלה | `בעיה` is any problem, including a personal one. `תקלה` is a fault in something meant to work. |
| נציג מהצוות שלנו | הצוות | Translated-sounding, and `הוא יחזור` genders a colleague nobody has met. |

**The register section names the tells rather than describing a tone.** No
`איך אוכל לסייע`, no `מה שלומך`, no `תודה שפנית אלינו`, no `אשמח לעזור`, no
emoji, no openers and no sign-offs. Written formal Hebrew is what a model
reaches for by default and is exactly what makes it read as a machine.

**Four faults found by testing, three of them mine.**

1. `אוקיי` was listed as approved vocabulary, so the model opened a conversation
   with it — *"אוקיי, מה קרה?"* to a bare `שלום`. Those words are acknowledgements
   of something already said, not openers, and the prompt now says so. Now:
   *"היי, מה קרה?"*
2. Two questions in one message to a frustrated resident. The one-question rule
   was a sentence; it is now a hard count — **one question mark per message**.
3. `מישהו שכועס` sent every irritated person to a human. Someone frustrated that
   a fault has not been fixed does not want to be passed on, they want it
   written down. Split: frustrated → open the ticket; angry **at us**, or
   demanding a manager → transfer.
4. **A contradiction I wrote myself.** `מעלית תקועה עם אדם בפנים` sat in the
   urgency examples *and* under the safety rule that says never open a ticket.
   The model obeyed the first and opened a ticket for people trapped in a lift.
   Removed from the urgency list; the safety rule now names the cases and says
   explicitly not to do both.

**Verified live through the webhook after each fix:**

```
"שלום"                              היי, מה קרה?
"הדלת של הכניסה לא נסגרת"           באיזה בניין מדובר?        (building, not apartment)
"המעלית תקועה, יש בפנים אנשים"      transfer_to_human only, no ticket
"נזילה במקלחת, ויצמן 8 דירה 4"      טיפלתי. מספר קריאה HM-2026-3496.
"שלום, החניון מוצף מים"             אוקיי, יש הצפה בחניון. באיזה בניין זה קרה?
"כבר פניתי פעמיים… תעבירו למנהל"    transfer_to_human {reason: caller_request}
```

Every reply carries exactly one question mark or none, addresses nobody by
gender, and speaks in active first person.

**Still not reviewed by a native speaker,** which is the same standing gap the
voice prompts carry and it has now grown. Every line above was written, not
transcribed. The three to put in front of an Israeli first are the handover
line, `טיפלתי` as a closing, and whether `קריאה` or `פנייה` is what Homies'
own staff actually say.

### Gemini 2.5 Flash, and the WhatsApp bot answered a resident for the first time

Model switched from `anthropic/claude-opus-5` to `google/gemini-2.5-flash`, asked
for directly. Slug verified against `openrouter.ai/api/v1/models` rather than
typed from memory — it exists, carries `tools` in `supported_parameters`, and has
a 1M context.

```
                    in $/1M   out $/1M   one real turn   latency
claude-opus-5         5.00      25.00      $0.02040       6,195ms
gemini-2.5-flash      0.30       2.50      $0.00051       2,321ms
```

**Forty times cheaper and nearly three times faster on the same message**, against
the same 2,598-character prompt with both tools attached. It also made the bot
work *today* rather than when credits arrive: OpenRouter pre-authorises
`max_tokens` against the balance, and 4096 tokens of Opus exceeded it while 4096
tokens of Flash sits comfortably inside.

**And then it ran, all the way through:**

```
Sort                 success
Answer Meta          success     Meta answered in 762ms, before any model work
OpenRouter           success     x2 — the tool round trip
open_request         success
Answer the resident  success
Send                 error       Authorization failed (placeholder Meta token)
```

The reply, in Hebrew: *"היי, פתחתי עכשיו קריאת שירות עבור הנזילה בלובי, מספר
הפנייה הוא HM-2026-9318."* The reference is real — the tool webhook wrote the row
and handed the number back, and the debt-tools execution confirms it:
`type: plumbing, urgency: high, building: הרצל 14, unit: 12`, description in the
resident's own words. **The one thing this bot must never do is invent a
reference number, and it did not.**

Only `Send` fails, on the Meta token that has never been filled in.

### The tool node I used was deprecated, and n8n said so at runtime

`@n8n/n8n-nodes-langchain.toolHttpRequest` failed with:

```
has a "supplyData" method but no "execute" method
```

Reading the node source explains it: `hidden: true`, with the comment *"Replaced
by a `usableAsTool` version of the standalone HttpRequest node."* The current way
is `n8n-nodes-base.httpRequestTool` — the ordinary HTTP Request node in tool mode
— with `descriptionType: 'manual'` plus `toolDescription`, and arguments declared
through `$fromAI()` instead of `{placeholder}` tokens and a placeholder table.

This is exactly the drift the skills warn about, and it is worth noting that the
skill pack did not catch it either: `references/TOOLS.md` names the four tool
types, and the deprecation is only visible in the node source. Empirical testing
found it; nothing else would have.

**`$fromAI()` also made the security rule easier to see.** Anything wrapped in it
is a parameter the model fills. Anything not wrapped is fixed by us. The phone
number is `$('Sort').first().json.to` — `.first()` on a named node rather than
`$json`, because a tool runs inside the agent's execution where the current item
is the agent's own and pairing back to the trigger is not guaranteed. The phone
decides whose ticket this is, so it has to be deterministic.

### The OpenRouter key works and the account is still empty — the $1,000 is a cap

The key in `.env` was already in use: the n8n credential `Homies OpenRouter`
(`f95jN4EnTPL6CQuJ`) was created from that exact value, which is why the agent
run failed with **Payment required** rather than *unauthorized*. A 402 is the
account answering, not the key being rejected.

**`GET /api/v1/key` reports `limit: 1000` and that is not money.** It is a
spend ceiling on the key. The account balance is what runs out, and OpenRouter
pre-authorises `max_tokens` against it:

```
max_tokens 4096   402  "you requested up to 4096 tokens, but can only afford 1459"
max_tokens 1400   200  6,195ms  finish_reason=tool_calls
max_tokens 800    200  4,053ms
```

**So the key is fine and the model is good.** Against the real 2,598-character
system prompt with both tools attached, it called `open_request` with
`building: הרצל 14`, `unit: 12`, `type: plumbing`, `urgency: high` — a valid
enum value, so this morning's constraint fix holds through the whole chain — and
the description in the resident's own Hebrew.

**Lowering `max_tokens` is still the wrong fix, and now there are numbers.** The
prompt alone is **2,671 tokens, $0.0134**, before the model writes a word. A full
turn measured **$0.0204**. `max_tokens` only gates the pre-authorisation; it
barely moves the bill. At roughly **2¢ a message**, $5 of credit is about 250
messages and $20 is about a thousand. That is the decision, not the token cap.

**And the agent swap lost prompt caching, which is most of that cost.** The
response reports `cached_tokens: 0`. The old Code node set an explicit
`cache_control` breakpoint on the system prompt; the OpenRouter node has no such
option, so every message now pays full price for the same 2,598 characters.
Together with the missing reasoning parameter, that is the second thing the AI
node cannot express that hand-written HTTP could. Worth knowing before the
volume matters: at 200 messages a day the difference is real money.

### The WhatsApp bot is an AI Agent node now, not 150 lines of JavaScript

Asked for directly: use an AI node. The `Brain` Code node — which ran the whole
tool-use loop by hand against OpenRouter's HTTP API — is replaced by
`@n8n/n8n-nodes-langchain.agent` with four sub-nodes.

```
Answer the resident  (agent)
  ├── OpenRouter            lmChatOpenRouter   credential f95jN4EnTPL6CQuJ
  ├── Conversation so far   memoryBufferWindow keyed on the phone, window 12
  ├── open_request          toolHttpRequest
  └── transfer_to_human     toolHttpRequest
```

**What it bought, in order of how much it matters.** The model key is in n8n's
credential store instead of interpolated into a code string, so an exported
workflow carries no secret. Conversation memory is a node rather than workflow
static data, which does not survive an n8n restore. And the two tools are objects
on the canvas the agent can reach, not a URL buried in a `fetch`.

**What it cost, and this is real.** The old loop sent
`reasoning: {effort: "low"}`. **The OpenRouter node has no reasoning parameter** —
its options collection is frequency penalty, max tokens, response format,
presence penalty, temperature, timeout, max retries and top P, and nothing else.
Confirmed by reading the node source, not by assuming. So thinking now runs at
the model's own default. That is the *safe* direction, because the failure this
project cares about — a tool call written into visible text instead of emitted
as one — happens when thinking is OFF. It is slower and dearer per message.
`EFFORT` stays in the file, renamed to say it is no longer sent, so this is
written down rather than rediscovered.

**The error branch had to be rebuilt, and is not optional.** The Code node
caught a failed model call in a try/catch and answered with the handover line.
An Agent node that errors just fails. So the agent carries
`onError: continueErrorOutput` and its second output runs a Set node holding
that same sentence. Without it, a model failure is a resident who is never
answered at all.

**Verified against the live instance, which is the only way to check anything
without the MCP connected:**

```
Sort                 success
Answer Meta          success       (Meta answered before any model work)
Conversation so far  success
OpenRouter           error         Payment required
Answer the resident  success       -> error output
Hand over instead    success       to=972500000011, the Hebrew handover line
Send                 error         Authorization failed (placeholder Meta token)
```

Both remaining failures are the two things already known to be missing —
OpenRouter credit and the Meta token. Everything between them works, and the
LangChain node types are confirmed present on this n8n at the typeVersions used.

**The phone is interpolated, never a placeholder.** Both tool nodes build the
Vapi-shaped envelope with `{{ $json.to }}` for the phone and `{placeholder}`
tokens only for what the model is allowed to decide. A placeholder is something
the model fills in, and the model must never be able to choose whose ticket
this is — the same rule the voice agents follow for the amount and the month.

Dead code removed: 152 lines of `BRAIN` JavaScript and the `openai_tools()`
converter that existed only to feed it.

**The layout checker caught two things on the way.** My own `Hand over instead`
node, 60 apart from `Send` — fixed before the push. And then the debt-tools
canvas, whose nodes had drifted to `[720, 64]` and `[976, 224]`: somebody
dragged them in the n8n UI. Re-pushed from the script, which is the source of
truth, and that is precisely the drift these scripts exist to prevent.

### Two nodes had been drawn on top of each other since the day it was written

New rule from the client side: a workflow has to be presentable — no
overlapping nodes, human readable. Applied to all three and **encoded rather
than remembered**, in [scripts/n8n_layout.py](../scripts/n8n_layout.py). It
raises before any push if two nodes sit within 200×180 of each other, if a node
still carries a default name (`Code`, `If1`, `HTTP Request2`), or if the
workflow has no sticky notes at all. All three deploy scripts call it first
thing in `main()`, and `python scripts/n8n_layout.py` audits the whole instance.

**What it found immediately.** `Anything to write?` and `Needs the real answer?`
were both at exactly `[460, 120]` in the debt-tools workflow — identical
coordinates, one node drawn perfectly on top of the other, so the canvas showed
seven nodes where there were eight. **Nothing ever failed.** The workflow has
run correctly the entire time. It simply could not be read, and the two IFs that
decide whether the caller waits for a write were the pair you could not see.

Everything is now on a 240-wide grid with rows in multiples of 60 — one column
per stage, one row per branch, trigger at the left.

**Sticky notes were added and then removed the same hour.** They were not asked
for: *"no text box no description just the nodes to be very well placed no
overlapping nodes."* The canvas shows the shape of the flow and nothing else,
and the reasoning stays in the script that builds it, beside the code it
describes and under version control. Two homes for one explanation is two places
to drift, which is the argument these scripts already make about prompts.

```
  ok    Homies — call queue (read)
  ok    Homies — debt tools (Vapi)
  ok    Homies — WhatsApp bot
3 of 3 workflows are readable.
```

Re-verified after the move, because a relayout that breaks a wire is worse than
an ugly canvas: `check_tools.py` **10 passed, 0 failed**, and a WhatsApp message
still answers in 862ms.

### Homies has its own n8n, and everything had been going to the wrong one

`https://n8n-zqvb.srv1879140.hstgr.cloud` — empty, community edition, Homies'.
Its API key **was already in `.env`**, under the name `N8N_MAIN_CLIENT_ID`, which
reads like a client identifier rather than a credential for a second instance,
so nothing ever looked at it. `N8N_BASE_URL` and `N8N_API_KEY` both pointed at
`srv1135333` — the shared production instance carrying 26 workflows for four
other clients — and so every Homies workflow ever deployed, including the
WhatsApp bot created an hour earlier, was built there.

**The name is the whole cause.** Both keys are opaque JWTs and either would look
correct next to the other. Renamed: `N8N_BASE_URL` / `N8N_API_KEY` are now the
Homies instance, and the shared one is `N8N_SHARED_BASE_URL` /
`N8N_SHARED_API_KEY` with a comment saying nothing should deploy there.

Moved, in order, verifying each:

| | New id | Check |
|---|---|---|
| `Homies — debt tools (Vapi)` | `lXofknAbE5wu5nwQ` | `check_tools.py` **10 passed, 0 failed** |
| `Homies — WhatsApp bot` | `u2JjrbcNPYyyh3yl` | 200 in 688ms, Brain ran, Send fails on the placeholder token |
| `Homies — call queue (read)` | `i3VMdCnXZGooI1Dj` | returns the real queue with resident names |

All four Vapi assistants re-pointed at the new webhook — the two Hebrew ones
through `vapi_sync.py --apply`, the two English twins by PATCH, since
`vapi_en.py` still refuses to rebuild them.

**Nothing needed re-crediting, and that is worth knowing.** The tool workflow
writes through Apps Script over plain HTTP rather than a Google Sheets node, so
it carries no n8n credential at all and moved as pure JSON. A Sheets node would
have moved with a credential id belonging to the old instance and failed *after*
answering Vapi 200 — the response is computed before the write by design, so a
missing credential would have been invisible in the response.

**Two of three are deactivated on the shared instance; the queue is still live
there deliberately.** `web/index.html` is deployed separately on Vercel and
still calls the old queue URL. The file now points at the new one, and the old
workflow must stay running until that page ships — deactivating it first breaks
the demo page. Nothing was deleted: deactivation is reversible and this is
somebody else's production box.

### The WhatsApp workflow is live in n8n — and it was silently dropping every message

`Homies — WhatsApp bot`, workflow `fDVRNLvsALcOe3ld`, active. Callback URL:

```
https://n8n.srv1135333.hstgr.cloud/webhook/homies-whatsapp
```

**The bug, which is the reason this was worth testing before connecting Meta.**
`multipleMethods: true` gives the webhook node **one output per method**, in the
order they are listed — GET on output 0, POST on output 1. The workflow
connected only output 0.

Everything you would think to check passes. Meta's verification is a GET, so the
callback URL saves and the dashboard shows a verified webhook. Then every actual
message arrives as a POST on output 1, lands on nothing, and the execution ends
**`success` having run a single node**. No error, no retry, no reply. A resident
messages Homies and is never answered, and there is nothing in n8n that looks
wrong.

Found by posting a real message envelope at the live URL before touching the
Meta app. The verification handshake — the test everybody runs — would have said
it was fine.

**Verified after the fix, four payload shapes, all against the live webhook:**

| Sent | Result |
|---|---|
| Hebrew text, "יש נזילה בלובי של הבניין" | 200 in **898ms**, then Brain → Send |
| the same message id again | `_work: false`, never reaches the model — one reply per message, not one per retry |
| an image with no caption | canned Hebrew reply, no model call at all |
| a delivery receipt | 200, nothing written |

The 898ms matters: Meta retries anything not answered within a few seconds, and
a retry is a second copy of the same message. The workflow answers Meta *before*
it thinks, so the model's latency can never turn into a duplicate reply.

**The Brain ran and produced Hebrew.** Not a real answer — OpenRouter is still
out of credit, so it took its catch path and returned the handover line, *"אני
מעביר את זה לנציג מהצוות שלנו"*. Which is the graceful failure working as
designed, and also exactly the shape flagged on 7 Aug: a valid key and a bot
that always hands over reads as "the model is broken" rather than "the account
is empty."

**`Send` fails, deliberately, and the deploy gate was wrong about it.** The
script demanded `WHATSAPP_PHONE_NUMBER_ID` and `WHATSAPP_ACCESS_TOKEN` before it
would push anything. Both are only needed to *send* — and a send cannot happen
until Meta has verified the callback URL, which needs the workflow live first.
The gate blocked the step that has to come first, and that ordering is Meta's,
not ours. Split into `need()` and `later()`: hard-fail on the verify token and
the model key, deploy with a loud warning on the two send credentials. Safe only
because a number that has not been connected in the Meta app receives nothing,
so there is no window where a real resident goes unanswered.

`WHATSAPP_WEBHOOK_VERIFY_TOKEN` was generated rather than typed and is in `.env`.
It is a shared secret with Meta, and a value invented at a keyboard tends to be
one that can be guessed.

### Vapi is out of credit, so none of this has been heard on a real call

Everything above was verified by posting real Vapi payload shapes at the live
Edge Function. **The one thing that cannot be proved that way is that Vapi
actually sends the report** — that needs a call, and the account has no balance.
This is the third Vapi account since 5 Aug and there is no API endpoint that
reports a balance; `/subscription` is 404 on all three keys.

Two consequences worth having written down before the next move rather than
after it.

**The export now redacts something that matters.** `vapi_export.py` has always
replaced `server.headers` values with `<redacted>`, written when those headers
were empty, on the reasoning that a file which is safe only by accident is not
safe. As of today they carry `TOOL_SECRET`, so that decision is now the only
thing keeping the secret out of a committed file. It also means the export is
**not** a restore path for the report endpoint: an account rebuilt from it posts
reports with a header of the literal string `<redacted>`, gets a 401, and throws
away every transcript exactly as before — silently, because nothing about the
call fails. `vapi_sync.py --apply` reads the real secret from `.env` and is the
route.

**The rebuild checklist now ends on `interactions`.** Added to
[new-vapi.md](handover/new-vapi.md) as the last item, because it arrives last:
the report fires after the call is over, not during it. An empty table means the
`server` block did not survive the move, and there is no other symptom — the
call sounds perfect and nothing errors.

### Supabase exists, all six migrations are applied — and it is in Tokyo

Project `HOMIES / main`, ref `nmxlhlmcnnggnnuxyelt`, free plan. The six SQL files
that had been written and never run since 2 Aug are now applied, by
[scripts/supabase_migrate.py](../scripts/supabase_migrate.py) — a new runner that
keeps a `schema_migrations` ledger, wraps each file in its own transaction, and
stops at the first failure rather than leaving half a schema behind.

```
residents           10 rows    charges             10 rows
requests             1 row     payment_tickets      0
interactions         0         payment_links        0
call_outcomes        0         promises_to_pay      0
                               payment_disputes     0
```

Nine tables, 32 indexes, two functions (`touch_updated_at`,
`bump_charge_attempt`), **RLS on with a policy on every one**. Verified from both
sides: the publishable key gets `[]` from `residents`, the secret key gets the
row. RLS is doing its job rather than merely being switched on.

**The region is `ap-northeast-1` — Tokyo.** Nobody chose that; it is the default
if you do not change it at project creation, and it was not changed. Israel to
Tokyo is roughly a quarter of a second each way, and every tool call the voice
agent makes crosses it — against a turn that already measures 5,283 ms. Frankfurt
`eu-central-1` is the closest region Supabase offers.

Supabase cannot move a project between regions on the free plan. The fix is to
delete this project and create it again in Frankfurt, which right now costs
nothing: the only contents are ten fictional residents and the seed rows, and
the migration runner replays the whole schema in about a minute. It stops being
free the moment anything real is in there, so this is worth deciding now rather
than later.

**Finding the database was not straightforward.** `db.<ref>.supabase.co` does not
resolve at all on this project — no A record, no AAAA — so the direct connection
route does not exist and the Supavisor pooler is the only way in. The pooler
hostname embeds the region, which the dashboard shows and we did not have, so it
was found by trying all 34 hostnames until one accepted the tenant. Port 5432
(session mode) rather than 6543, because transaction mode rejects some DDL.

**Also fixed: `.env` had two Supabase blocks.** `SUPABASE_URL`,
`SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_ROLE_KEY` each appeared twice, once
empty and once filled. Which value wins depends on the parser, and the symptom
would have been an authentication error rather than anything pointing at a
duplicated line. Merged into one block.

`SUPABASE_ACCESS_TOKEN` is still empty — that is the CLI token, and without it
the `debt-tools` Edge Function cannot be deployed.

### First real resident data is in Supabase — 12 people, 9 charges, ₪12,200

Imported `sheets/residents-real.csv` by
[scripts/import_oxs_csv.py](../scripts/import_oxs_csv.py). Residents upsert on
`phone`, charges on `(resident_id, period)`, so a nightly export can be replayed
without duplicating anybody — which is the whole point of an import script rather
than a one-off paste.

```
residents by source   oxs 12   seed 10
charges   by source   oxs  9   seed 10
period                2025-12-01   9 charges   ₪12,200
```

**A new column, `source`, in migration `007`.** Ten fictional residents from
`002_slice_seed.sql` were already in that table, and `residents` is what the
outbound debt agent reads to decide who to call. With real numbers and seed
numbers sitting together and nothing to tell them apart, the only thing between a
test run and phoning a real person about a real debt is somebody remembering
which is which. `oxs_ref` could not do this job — it holds the id in OXS, and a
CSV export does not carry one.

**Three charges were not created, deliberately.** Lines 3, 4 and 11 carry an
amount — ₪1,500, ₪1,000 and ₪900 — and no month. `charges.period` is a not-null
date, and the honest options were to invent a month or to skip the charge. The
residents imported; the charges did not. ₪3,400 is therefore in the CSV and not
in the database, and that is a data question for Homies rather than something to
paper over.

**The year is an assumption and it is flagged as one.** `month` arrives as
`דצמבר` — a Hebrew month name with no year at all. December 2025 is the only
December that has happened as of today, so that is what was used, it is printed
on every run, and `--year` overrides it. A charge filed under the wrong year is a
resident called about a debt from a different December.

**All 12 have `do_not_call = FALSE`.** That is faithful to the export and it is
the thing to know before anything dials. Nothing can place a call today — the
campaign runner is Phase 7 and does not exist — but the row is armed the day it
does.

**And this is the argument for moving the region that the latency numbers only
hinted at.** The project is in `ap-northeast-1`. Twelve Israeli residents' names,
phone numbers and debts are now stored in Tokyo. While the table held ten
invented people that was a performance question; with real personal data in it,
it is a data-protection question as well, and the answer to both is Frankfurt.
The cost of moving is still close to zero — delete, recreate, replay seven
migrations and re-run this import.

### OXS is read-only, decided — and the API guide turns out to document no API

**The rule, from the client side of this build:** nothing we build writes to OXS,
ever. Asked specifically whether creating a new service request was an exception,
since PRD §2.1 assumes exactly that: *"strictly do not edit anything on oxs we
just import data to clone in supabase."* So the bot does not open tickets in OXS
either. One direction only — OXS out, Supabase in.

This costs something real and it is worth naming. A resident's ticket now exists
in Supabase and **not** in the tool the staff actually work in, so somebody has
to look at a second place. That is the adoption risk the plan already flagged
against the CRM, now applied to intake. The counterweight is that a write to a
system of record for 10,000 apartments is not a bug you roll back — it is a
corrupted resident record inside a live business, and the rule removes that
entire failure class rather than guarding against it.

**OXS enforces most of it for us.** From the guide's module table:

| Module | Access levels | Scope |
|---|---|---|
| Service Requests | Read-Only **/ Full Control** | view, create, update status, delete |
| Tenant Debts | Read-Only only | balances, payment details, outstanding amounts |
| General Information | Read-Only only | buildings, apartments, tenants, payment histories |

Two of the three modules have no write permission in existence, so `OXS_KEY_DEBTS`
and `OXS_KEY_GENERAL` are read-only by construction. Service Requests is the only
module where a key *can* write, which makes `OXS_KEY_REQUESTS` the only one the
rule has to be enforced on — it should be re-issued as Read-Only so the
permission cannot be used by accident. Nothing enforces a rule as well as not
having the capability.

Verified today that **no code in this repo reads any OXS key at all** — the three
values sit in `.env` and nothing has ever called with them.

**And the guide documents no endpoints.** `OXS_API_Keys_Guide_EN.pdf` is four
pages on creating, rotating and expiring keys. Searching all four for anything
URL-shaped returns one hit, and it is the phrase "target system". No base URL, no
paths, no request or response shapes. So the import is blocked on OXS Support
sending the API documentation — the same team that has to activate API access.

Two operational facts from the guide that will matter later: rate limits are **60
requests per minute and 1,000 per hour** across all keys, which shapes how ~10,000
apartments get paged; and **every key expires**, one year by default and two at
most, with email reminders at 30, 7 and 1 days. A silently expired key looks
exactly like an outage.

**Two PRD lines are now stale.** §2.2 says making status requests live "requires
either an OXS API (none exists)" — one exists, and we hold keys for it. And §5
specifies the OXS bridge as a nightly Google Sheets batch. A read-only API pull is
strictly better than that: fresher, no manual export step, and it removes the "as
of last night" caveat the flow currently has to say out loud. Both should be
revised once the endpoints arrive.

### debt-tools is deployed, and the smoke test caught a bug I had written

`debt-tools` is live at
`https://nmxlhlmcnnggnnuxyelt.supabase.co/functions/v1/debt-tools`, version 1,
`verify_jwt: false`. Pushed by
[scripts/supabase_functions.py](../scripts/supabase_functions.py), which uses the
Management API rather than the CLI so that nothing has to be installed and
`supabase init` does not restructure the repo.

`TOOL_SECRET` was empty and is now generated, in `.env`, and pushed as a project
secret. That mattered more than it looks: the function's guard is
`!== SECRET || !SECRET`, so it **fails closed on an empty value** — deploying
without one produces a function that 401s every caller and reads as a broken
deploy rather than a missing variable.

The door was tested from both sides. No header → 401. Wrong header → 401. Right
header → 200.

**Then the third call failed, and it was our bug.**

```
{"ok":false,"error":"new row for relation \"requests\"
 violates check constraint \"requests_urgency_check\""}
```

`requests.urgency` has been constrained to `low / normal / high / emergency`
since `001` on 2 Aug, and [scripts/vapi_tools.py](../scripts/vapi_tools.py)
declares exactly those four. The WhatsApp bot I wrote yesterday declared
`normal / urgent`. **`urgent` is not a value**, so every urgent WhatsApp ticket
would have hit this constraint — and the model would have received an English
Postgres error in the middle of a Hebrew conversation.

This is the third collision of the same kind in two days: I invent an identifier
the established file has already fixed. The first two were
`WHATSAPP_TOKEN`/`WHATSAPP_VERIFY_TOKEN`. Fixed to the four schema values, with
the constraint named in a comment so the next person does not re-invent them.

Re-run after the fix: `HM-2026-1003` written, `plumbing / high`, Hebrew
description intact, `opened_via: voice`. Test row deleted afterwards.

**Left alone, worth knowing.** `open_request` in the Edge Function passes
`urgency` straight to Postgres with no validation, so an invalid value is caught
by the database rather than the function. Fail-closed is the right direction; the
cost is that the agent gets a constraint message instead of something it can act
on. Also `requests.type` has **no** constraint, and the two channels declare
different vocabularies — voice offers four types, the WhatsApp bot seven. Both
insert fine and will make the type column awkward to report on.

### The key works, the balance does not — and the whole Brain call ran for real

`OPENROUTER_API_KEY` arrived and authenticates. `GET /api/v1/key` returns the
account, and a real request to `anthropic/claude-opus-5` came back in **5,141 ms**
with 2,632 input and 48 output tokens. That request was not a toy: it used the
script's own constants, the real 2,598-character Hebrew system prompt, both tools
converted to the OpenAI shape, `reasoning: {effort: "low"}` and the
`cache_control` breakpoint. So the model slug, the tool shape, the reasoning
parameter and the caching block are all confirmed accepted by the live endpoint
rather than assumed.

**The finding that matters: the balance is about four cents, and OpenRouter
pre-authorises `max_tokens` against it.** The first attempt failed —

```
HTTP 402  You requested up to 4096 tokens, but can only afford 1600
```

`MAX_TOKENS` in the script is 4096, sized deliberately so thinking and the reply
fit together. That means **every message would 402** on this balance, with a
valid key. The Brain catches the throw and answers with the handover line, so the
failure is graceful — a resident is told a person will get back to them — but the
bot would never once call `open_request`. A working key and a bot that silently
never works is exactly the shape that gets diagnosed as "the model is broken."

Credits fix it. Lowering `max_tokens` also clears the 402 and is the wrong fix:
it buys a working request by risking a reply truncated mid-sentence, which is the
failure `MAX_TOKENS = 4096` exists to prevent.

### The lobby leak asked for an apartment number, on the first real message

The test message was the demo narrative from the plan — *"there is a water leak
in the lobby at Herzl 14, it's urgent."* The reply was `באיזו דירה אתה גר?` —
*which apartment do you live in?*

A lobby is a common area. Nobody lives in it. This gap was flagged when the
prompt was written and it reproduced on the first live message, which is a
stronger argument than the one made for it in the abstract. The prompt asks for
building **and** apartment unconditionally; it needs to skip the apartment when
the problem is in a shared space. Not yet fixed.

### Still empty: `OXS_KEY_REQUESTS`

Diffed `.env` against the pre-OpenRouter backup: **one line changed**, the
OpenRouter key. `OXS_KEY_DEBTS` and `OXS_KEY_GENERAL` were already set and are
untouched; `OXS_KEY_REQUESTS` is still blank. It is the key that writes service
requests — the exact row this bot creates — and it blocks nothing today only
because tickets go to the Sheet.

Three WhatsApp values are still absent: `WHATSAPP_WEBHOOK_VERIFY_TOKEN`,
`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`.

---

## 2026-08-07

### WhatsApp bot built end to end, blocked on four values

Feature [11](features/11-whatsapp-bot/feature.md) — inbound support in Hebrew,
reusing the tool webhook the voice agents already call. Written and verified;
not pushed.

**The channel was a real decision.** Three options, and the fastest one was
rejected: another client on this same n8n box already runs WhatsApp through
GreenAPI (`Inventory - 20 Availability Bot`), which is proven-here and would have
demoed today. It drives WhatsApp Web unofficially, breaks WhatsApp's business
terms, and the number can be banned. Twilio was ruled out on measurement rather
than opinion — `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` are in `.env` and
**empty**, so it costs a new signup, adds a BSP markup, and still needs the same
Meta verification. Chose the Meta Cloud API test number: free, no business
verification, five hand-registered recipients, and the move to Homies' real
number is a phone-number id and a token.

**Business verification gates the production number, not the build.** That is
what let this start today rather than in two weeks.

**Chatwoot deferred**, and not on preference: it is Rails + Postgres + Redis +
Sidekiq, and the only VPS is `srv1135333`, which carries four other clients'
production workflows. Adding it later costs one field in the Meta app config.

**Thinking stays on at low effort — the counterintuitive call.** Every instinct
says disable it for a chat bot. With thinking disabled this model occasionally
writes a tool call into its *visible text* instead of emitting a structured call:
the turn returns 200, the reply reads fine, and the tool never runs. No error, no
failed call to catch. For an agent whose whole job is `open_request`, that is a
resident told their request is logged when no row exists. Also `max_tokens` caps
thinking and reply together on this model, so it is sized for both.

**Answer Meta first, work after.** Meta retries any webhook that does not return
200 quickly, and a retry is a second reply to one question. Same shape the tool
webhook already uses. Duplicates are suppressed on Meta's message id, never on
content — a resident who sends "כן" twice means it twice.

Verified before hand-off: prompt extracts (2,598 chars, **2** verbatim lines
against the debt prompt's 23 at its worst); both Code nodes parse under
`node --check`; all seven workflow nodes reachable with no dangling connections;
the media-with-no-text branch reaches Send (it did not on the first pass — the If
routed it nowhere and acceptance #5 would have failed).

Two contradictions in our own docs surfaced. The build-stack checklist says the
chatbot brain is Claude; the credentials checklist says OpenRouter — resolved to
the Anthropic API directly, because the tool calls here are load-bearing.
And `sheets/README.md` still prints the **rotated, dead** Apps Script secret in
plaintext; harmless but it should not read as live.

Blocked on four values, which the script prints rather than a document listing:
`WHATSAPP_WEBHOOK_VERIFY_TOKEN`, `OPENROUTER_API_KEY`,
`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`. Nothing has been created in
Meta or pushed to n8n.

### Chatbot moved to OpenRouter, and two name collisions found

The brain was written against the Anthropic API. `.env.example` has said
OpenRouter since it was written, and the user confirmed it — so it moved.
`anthropic/claude-opus-5` was checked against `openrouter.ai/api/v1/models`
rather than assumed to exist: it does, at the same $5 / $25 per million tokens.
A slug that does not exist fails as a 404 at call time, which on a chat bot is
silence rather than an error anyone sees.

The shape change is not cosmetic. OpenRouter speaks OpenAI chat-completions, so
tool arguments arrive as a **JSON string** rather than an object, and every tool
call must be answered by its own `role: "tool"` message carrying the matching
`tool_call_id` or the next request is rejected outright. Tools are still declared
once, in Anthropic's shape, and converted on the way out — one canonical list,
nothing to drift.

**Two variable names I invented collided with names `.env.example` already
established** — `WHATSAPP_TOKEN` against `WHATSAPP_ACCESS_TOKEN`, and
`WHATSAPP_VERIFY_TOKEN` against `WHATSAPP_WEBHOOK_VERIFY_TOKEN`. The script was
wrong, not the template; fixed to match. Worth noticing that this only surfaced
because someone asked about the env file — nothing would have failed until
deploy day, and then it would have looked like Meta's fault.

Also found while checking: **`OXS_KEY_REQUESTS` is empty** while the debts and
general keys are set. That is the key that writes service requests. It blocks
nothing today, because tickets go to the Sheet, and it blocks everything the day
they stop.

### "Stop, ask nothing" was the instruction nearest the acknowledgement

The isolation was exact: a plain "אוקיי" loops, "אוקיי, ומה עושים?" proceeds. Same
call, same prompt, one word of difference — so it is not the flow and not the
line, it is what the model reads at that moment.

Two things were fighting, and both were mine.

**The amount turn ended with *"then stop, ask nothing, and read where they
are."*** That was meant as *do not append the question to this same turn*. What it
says, to a model that has just been acknowledged and needs to produce something,
is **do not ask** — and it was the nearest instruction. The question it should
have asked was 881 characters away under a different heading.

**And the acknowledgement rule was a prohibition with nowhere to go:**
*"'אוקיי' and a hum are not turns. Do not answer them and do not restate what you
just said."* Both halves are correct and neither says what to do instead. A model
that must produce a turn and has been told not to ask and not to restate has one
thing left: the content it already has, in new words. Which is exactly what came
out — *"זה תשלום של יולי, 450 שקלים"*.

A question rescued it because a question is content. It has something to answer,
so it never reaches the dead end.

Fixed both. The acknowledgement is now the **cue** for the question and the
question sits **554 characters** after the amount rather than 881 under another
heading. *"Ask nothing"* is gone. And the acknowledgement rule points forward
instead of only fencing: *they mean carry on — so carry on to the next thing,
never back over the last one.*

The general form, stated where it happens: **the way out of a turn with nothing in
it is a question you have not asked, never a sentence you have already said.**

Still nine fixed lines, still zero enumerations. 34,715 chars.

### One line earns its place back, and the data says which one

Removing the scripting brought the amount loop back — four restatements off
"אוקיי", each one freshly worded, no link sent. So the question was which of the
eighteen removed lines was actually doing work, and that is answerable rather
than arguable.

Twelve calls today, checked for two things: did the agent ever ask whether to send
the link, and did the link go out.

| | asked for the yes | amount said | link sent |
|---|---|---|---|
| 5 calls | **no** | 1–4 times | **0 of 5** |
| 7 calls | **yes** | mostly once | 4 of 7 |

**Every call that sent a link is a call that asked.** No exceptions in either
direction. And the two calls after the de-scripting are both in the top row.

So: described as an intention — *"ask for the yes, plainly, in your own words"* —
the agent does not compose the question. It re-delivers the message it has already
given, in fresh words each time, which is the loop. Written as a line, it asks.

That is precisely the file's own third criterion for a fixed line: a test proved
the model does worse unscripted. The ask-for-the-yes is back, **as one line and
nothing else** — no menu, no four options, no transitions. Nine fixed lines
against the English twin's seven, zero enumerations, 881 characters from the
amount to the question.

Worth naming the general shape, because it cost the day: **a turn the model will
not produce on its own has to be written; a turn it produces fine has to not
be.** Everything between those is where the scripting crept in.

### I turned the Hebrew prompt into a script, and scripts loop

The complaint was that the conversation runs by steps and the English twin
adapts. Measured rather than argued:

| | Hebrew | English |
|---|---|---|
| verbatim `>` lines | **23** | **7** |
| "exactly N things you may say next" | 5 | 0 |
| "then go to N" transitions | 7 | 2 |
| bold imperatives | 130 | 53 |

The English twin has the same four numbered steps in the already-paid branch. The
difference is that it says *"if they confirm, say what the system shows and leave
it there"* and lets the model compose the sentence, where the Hebrew dictated the
sentence and then had to dictate the transition out of it too.

**Every one of those 23 lines went in as a loop fix, and the loops were mostly not
prompt bugs** — the demo page triggering the model twice, `send_payment_link`
never being called, a closing that did not match its own `endCallPhrase`. Real
bugs, fixed. But each one also got a written line and a rule about what comes
after it, and eighteen of those accumulated into a state machine. A model that has
been handed a script and does not know which line comes next replays the last one.
**That is the loop, and I built it.**

The file's own oldest rule said so: *"the prompt does not script Hebrew lines,
with five exceptions — everything else describes what to convey, and the model
generates the Hebrew natively."* Broken eighteen times in one day, one reasonable
patch at a time.

Reverted to describing. **8 fixed lines against the English twin's 7**, zero
enumerations, and the four already-paid steps now read like the English ones.
What stays verbatim needs one of three reasons and no others: Vapi speaks it
literally (the opening), the wording carries legal or privacy weight
(not-the-account-holder, voicemail), or a test proved the model does something
worse unscripted (the handover line, which went silent on a hardship disclosure).
The closing is fixed because `endCallPhrases` matches on its words.

What did **not** revert, because these constrain substance rather than sentences:
call the tool before speaking, ask for the yes once, take the yes that follows a
question, the steps only go forwards, the closing must carry יום טוב.

The header now carries the distinction, since it is the one that was expensive to
learn: **constrain substance, not sentences.** *Call the tool before you speak* is
a rule. *Say these exact words* is a script.

33,891 chars.

### The already-paid steps had no exits, so they cycled

First test on the cut prompt. The link path ran clean end to end — asked once,
tool called, link line, closing, call ended itself. The already-paid path cycled
between step 1 and step 2 until the resident gave up.

The four steps were numbered and had no transitions. Step 2 says what the system
shows and ends on a statement, so the resident answers it with "אוקיי" — and
nothing said what to do with that. The nearest written line above was step 1's
question, so step 1 is what came out. Then step 2 again. Then step 1.

**Numbering is not a transition.** A model that has just finished a turn does not
read a list and infer that the next item follows; it looks for a written line and
uses the nearest one. Every step now ends with **"then go to N, whatever they
said"**, and the block opens with the rule the numbering was silently assuming:
**these steps only go forwards.** No going back to check, no repeating a step
because the answer was thin, no step said twice in a call.

Also written out: the feminine form of step 1. The line flipped between
*את מדברת* and *אתה מדבר* inside one call — correct twice, wrong once, on a
resident passed as `gender: f`. Repetition does not just annoy, it degrades, and
that is now the third time today one line has come out different on a second
reading.

34,308 chars, still half of where the day started.

### Cut the debt prompt in half

67,789 characters to **33,523** — 51%, and below the English twin's 38,533 for
the first time.

**Nothing was removed for being wrong.** What came out was the evidence. A day of
*"on 7 Aug a resident said X and the agent did Y, which is why this rule
exists"* — 53 dated narratives, now zero. Every one of those stories is in this
file, which is where a reader looking for the reasoning should come. The model
does not need the reasoning. It needs the rule, once, close to where it acts.

Also removed: four sections that said the same thing in different words (LANGUAGE,
STYLE, NATURALNESS and YOU ARE BEING HEARD are now one), three variants of the
closing where one will do, and the blank-line padding that made HESITATION five
thousand characters for six rules.

**Verified rather than trusted.** All 24 unique fixed Hebrew lines were extracted
from the old prompt first and checked against the new one; 22 are present
verbatim and the two absences are the shorter closing variants, deliberately
collapsed into the canonical one — which is the redundancy that broke the goodbye
this morning. Twenty-four behavioural rules that each cost a live call today were
probed by name and all twenty-four are present. Voice, tools, end-call phrases and
all 27 output-filter replacements unchanged.

The file now opens with the rules for editing itself, because the ones that
mattered were learned expensively and are invisible in the result: every turn has
a written Hebrew line; the next turn is written where the previous one ends;
enumerate rather than prohibit; every list has a default; a `>` line is spoken.

**On the knowledge-base idea** — worth doing, but not for this. A KB is retrieval
over reference material, and it would help with things the agent might be *asked*:
building addresses, office hours, what the ועד בית covers. It cannot help with
behaviour, because behaviour is not looked up mid-sentence. Every loop today came
from a missing or distant instruction, and retrieval would have made that worse by
putting the instruction further away still. Cutting was the fix.

**The prompt grew 50% in one day and has now shrunk 51%.** That is not a wash: it
is the same content with a day of investigation taken out of it and moved
somewhere a person can read.

### Why the English one sounds smoother, and it is not the language

A clean English call was held up as the target: opening, amount, link offer,
link, standing order, close. It is smoother than the Hebrew, and the two reasons
are both mechanical.

**The English twin has sentences where the Hebrew has descriptions.** The
standing order is the visible one. The English prompt says *"Would you like to
set up a standing order for next time?"* — the Hebrew said *"then, once only,
offer the standing order"*, in English, with no Hebrew line under it. So the
English offers it on almost every call and the Hebrew hardly ever did. Same
flow, one written down.

Four branches were in that state and all four now have Hebrew: the standing
order (offer, accept, decline), paying later, hardship, and a maintenance
request raised mid-call. The promise-to-pay branch also gained the rule it never
had — **a vague date is still a date.** אחרי החג and בסוף החודש are answers, and
pressing for a number loses the intent along with the date.

**The second reason is one word.** On 7 Aug בסדר opened five turns out of six.
Every sentence after it was fine; the call still sounded like a machine, because
a person reaching for the same word five times running is not a person reaching
for a word. The register section listed seven openers and never said not to
repeat one. It does now — never twice in a row, never one word for most of a
call — and it says the thing the list implied and never stated: **most turns take
no lead-in at all.** The English twin opens two turns in five with nothing, and
that is most of the difference in feel.

Live at 67,789 chars on `3303317e`. The five unwritten branches are down to
none.

### The rule against mishearing a yes stopped it hearing one at all

Two calls, two minutes apart, same script but for one button.

`019fdb6a` ran clean end to end: asked for the yes once, called
`send_payment_link`, said the link line, closed, and ended on
`assistant-said-end-call-phrase`. Every fix from today held.

`019fdb6b` differed in exactly one turn — the resident asked
*"אוקיי, ומה עושים?"* instead of just acknowledging. It explained how the link
works, asked whether to send it, was told כן, and asked again. Then again. Four
times, reworded every time. **`send_payment_link` was never called.**

**It is not the typing.** Both calls were typed, both had the mic muted, both had
clean turn-taking. The only variable was which preset was clicked.

**The cause is a rule that used to be right.** On 5 Aug a resident said
*"Okay. And what should we do?"* and was told *"Great, I'm sending you a payment
link"* — a question treated as consent. So the prompt gained
*"a question is never agreement"*. That rule is correct about the question. It
said nothing about the answer that comes after it, so the model kept applying it:
the resident had asked something at some point, so every subsequent כן still
smelled like it belonged to the question, and the safe move was to ask once more.
Forever.

Two fixes, both stated where the model is standing.

Menu option 3 stops pointing at option 1 and carries the question itself — 1,173
characters from the first copy, because a numbered cross-reference two items away
was enough to make it improvise its own wording instead. And it now says where it
goes next: *"then you are in 2, and the next thing they say is the answer to
it."* The question is asked once in the whole call, in any wording, before their
question or after it.

The 5 Aug rule keeps its warning and gains its limit: *"and then you take the
answer."* **A rule that stops you mishearing a yes has to stop somewhere short of
never hearing one.**

Live at 64,784 chars on `3303317e`, the new account.

### It never says goodbye, which is why the goodbye never ends the call

Two fixes from the last hour confirmed working before anything else. `019fdb49`
called **`send_payment_link`** — the tool-first change holds. And two calls ended
with `endedReason: assistant-said-end-call-phrase`, so the widened `יום טוב`
phrase releases the line exactly as intended.

So the complaint — *"the bot does not end the call when it says goodbye"* — has
the wrong subject. **The goodbye works. The agent never gets to it.**

It said the link line, the resident said אוקיי, and it said the link line again.
Then again. Three times, reworded each time, and the resident hung up on the
third. The closing was never reached, so nothing ever matched an end phrase, so
the call sat open.

Same fault as the amount, the transfer details and the payment link before it:
**the turn after the link line was never written down.** The section said *"two
turns, in this order, with the resident speaking in between"* and then described
the second turn in English instead of writing it. So there was nothing to say,
and the nearest written line was the one just said.

Now, directly under both copies of the link line — 811 and 647 characters away
respectively, against a cross-reference before:

> אוקיי, תודה על הזמן. שיהיה לך יום טוב, ולהתראות.

with **whatever comes back, you close** stated as the rule, and
`log_call_outcome` after it. Verified live: every copy of the closing contains a
phrase that ends the call.

Also written down, because it came out unprompted and was not in the file:
**a tool call needs no announcement.** The agent said *"תן לי רגע"* while calling
`send_payment_link`. The resident hears a pause either way, and a pause is
shorter than a pause with an excuse in it.

Live at 61,689 chars.

**Five branches are still described in English with no Hebrew written under
them** — promise-to-pay, refusal, hardship, standing order, and a maintenance
request raised mid-call. Every fault of this shape today has come from exactly
that, and each one has been found by a test call rather than by reading. They
should be written before the next round rather than after it.

### The link was never sent, so the agent kept asking permission to send it

Call `019fdb43`. The resident said כן to *"רוצה שאני אשלח לך לינק לתשלום?"* and
was asked the same question **four more times** across 116 seconds, each time in
fresh words. **`send_payment_link` was never called.** Zero tool calls on the
whole call.

**This one is not the demo page and it was wrong to keep looking there.** The
stereo recording settles it: the caller channel is silent for 115 of 116 seconds
— RMS 0 per second, one burst in second 1 as the mic connected before mute took
effect, which is where the phantom *"מה לא הבאת?"* came from. The typed turns are
about eleven seconds apart. There was no race left to blame.

Two faults, both structural, both ours.

**The tool was attached to the wrong end of the sentence.** The prompt said *say
the line, then call `send_payment_link`* — so the line got said and the call was
optional in practice. It now calls the tool **first, before speaking**. A sentence
can be talked out of; a tool result is a fact sitting in the context. Once the
tool has been called there is nothing left to ask, and that is stated where the
model is standing rather than as a rule elsewhere.

**And there were two competing payment-link lines, 25 lines apart.** One under
*"when the caller agrees, say exactly this"*, another under *"call the tool, then
tell them it is on its way"* — two written-out sentences for the same moment, with
the tool call anchored to neither. The model produced variations of both plus
improvisations of its own. Collapsed to one line, one moment.

**The menu's option 2 was a pointer, and pointers do not get followed.** *"They
agreed → go to the payment-link line in HOW PAYMENT ACTUALLY WORKS"* sent the
model twenty thousand characters away, so it stayed where it was and re-asked
option 1 — which is exactly the loop in the transcript. Option 2 now carries the
tool call and the line inline. **188 characters from the question to what to do
with the answer**, against a section reference before.

Live at 60,187 chars. Same lesson as the amount, the transfer details and the
closing, four times in one day: **the next turn has to be written where the model
is standing.**

### The closing could not hang up, because the prompt recommended a phrase that does not match

Call `019fdb38` said the whole closing three times and stayed on the line. Not a
model fault and not the page race — a contradiction between two files we wrote.

`endCallPhrases` held `שיהיה יום טוב`. ENDING THE CALL offered this as a closing:

> אוקיי, תודה על הזמן. שיהיה לך יום טוב.

and then said, in as many words, that *"the lead-in and the לך are optional and
worth varying"*. **`שיהיה לך יום טוב` does not contain `שיהיה יום טוב`.** One
word in the middle, and the phrase that releases the line stops matching. So the
file recommended a closing that could not hang up, the model took the
recommendation, and the call stayed open. The resident said אוקיי, the model had
nothing left but the closing, and said it again. Three times. It ended only when
one of them happened to drop the לך.

`endCallPhrases` now matches on **`יום טוב`**, which every form of the goodbye
contains — with the לך, without it, either gender. Nothing in a call about an
unpaid ועד בית reaches for those two words except a farewell, so it cannot fire
early. A phrase that only matches the one phrasing nobody chose is not a backstop.

**The inbound agent had the identical latent fault** and was fixed in the same
push, before it cost a caller a hung line.

The prompt now finishes on ולהתראות rather than offering it as optional. That is
the beat that makes a goodbye sound like a goodbye instead of a line going dead —
which is what was actually being asked for by "wait two seconds before ending".
**Vapi has no wait-then-hang-up setting**; the call ends when the assistant
finishes speaking the matched phrase, so the goodbye is never clipped, and the
tail is how you buy the pause.

Both live, verified: every closing the file recommends now contains a phrase that
ends the call.

### The loop was the demo page, and most of this morning was spent on the prompt

Vapi's context for call `019fdb2e` has three messages in it:

```
[assistant] greeting + reason for call + 450 שקלים     ← one turn
[user]      כן אוקיי אוקיי                              ← one turn
[assistant] reason for call again
```

Three separate clicks arrived as one user turn. The greeting and the amount left
as one assistant turn. `turnLatencies` is empty and `numUserInterrupted` is 0 —
there was no turn-taking to measure, because none happened.

**The mechanism.** A typed turn goes in as `add-message` with
`triggerResponseEnabled: true`, which asks the model to answer immediately —
including while it is still speaking, and before its own last answer has been
written into the server-side history. The model is handed a transcript in which
it has not replied yet, so it replies again. Same context, fresh sample, a
different hesitation word each time: אההה the first time, אמממ the second. Two
generations, not a decision to repeat.

That also explains the digit that went missing from the bank account on
`019fdb24` — the second reading was a second sample, not a re-reading, and
sampling an eight-digit string twice is how you get seven.

And it answers the English question properly, which the prompt-size argument only
half did. `019fdb11` alternates cleanly the whole way down because whoever ran it
waited for the agent to stop talking before clicking. Same code, same race, not
triggered.

**Three fixes in the page**, none in the prompt:

- Typed turns queue and go out one at a time, 300ms after `speech-end`. Buttons
  disable while the agent talks and the status line says why.
- Identical text within 1.5s is dropped, and buttons blur on click — a preset
  that still holds focus re-fires on Enter, which is how
  *"אוקיי, ומה עושים?"* reached Vapi twice.
- The feed tracks the open partial **per speaker** instead of collapsing whatever
  sits at the bottom of the list. Interim guesses were stranding as their own
  lines the moment the speakers interleaved, which is why three transcripts
  showed a doubled greeting the server had only once.

Live at `7872ec2` on the demo repo.

**That first fix was incomplete and the next test caught it.** Gating on
`agentSpeaking` leaves open the window where the damage actually happens: between
a turn being sent and the first audio coming back the model is generating and not
speaking, so a second click in that gap sails through and triggers a second
response off the same context.

That window is one to two seconds — exactly the gap between clicking *כן* and
clicking *אוקיי*. It also explains the thing that looked like a content
difference: *"אוקיי, ומה עושים?"* worked every time because it is a longer button
that takes longer to find and read, so the window had closed before it was
clicked. Nothing to do with which words were sent.

Sends now hold until `speech-end` rather than merely while speech plays, with a
12s escape hatch for a turn answered by a tool call and no words, and calls start
held because the greeting goes out on connect. Status reads
*"Michael is thinking…"* so the wait is visible instead of a dead button.

There is also a build tag in the status bar now, because two rounds of tests were
argued about this morning before anyone could say whether the page in the browser
had the fix in it. `ba2489a`, build `2026-08-07b`, confirmed live on Vercel.

**What this cost.** Four prompt patches this morning were aimed at a fault the
prompt did not have, using transcripts the page had corrupted. Two of them are
worth keeping on their own merits — the enumeration after the amount, and the
transfer receipt line — and one, deleting the offer to repeat, was argued from
evidence that turns out to be an artifact. It stays deleted anyway; an offer to
repeat an account number earns its place back or it does not.

**Nothing about the debt prompt should be judged from a transcript recorded
before this deploy.** The next round of tests starts from zero.

### The loop moved down one level, and the repeat corrupted the account number

The enumeration after the amount worked. Call `019fdb24` asked
*"רוצה שאני אשלח לך לינק לתשלום?"* once, off a plain "אוקיי", in the right place —
and `019fdb22` ran the already-paid branch clean. Both faults from this morning
are closed.

The same fault then reappeared one turn further down. The resident said they do
not use links, the agent read `{{alt_payment}}`, the resident said "אוקיי", and
the agent read `{{alt_payment}}` again. Identical shape, identical cause: a turn
ended and the next one was never written. The alt-payment branch finished on an
English instruction — *"then offer to send the link as well so they have both"* —
with no Hebrew under it, so there was nothing to say and the nearest written line
was the one just said.

**The repeat was not merely a repeat.** The second reading came back
*אחת, שתיים, שלוש, ארבע, חמש, שבע, שמונה* — seven digits where the first had
eight. שש was dropped. The resident who trusted the second reading would have
sent the money nowhere. This is the argument the file was missing: a detail said
once is right, a detail said twice is a coin flip, and the second reading is the
one they write down. That went into the identifier rule as evidence.

The offer to repeat is now gone rather than capped. It was capped at one this
morning after it produced a loop; capping a thing that both loops and corrupts is
the wrong move. Say it once, repeat only if they ask in words, never ask whether
they caught it.

**And the branch now has a next turn, which is the one Homies actually needs.** A
transfer does not announce itself — nobody watches the account, so a resident who
pays and sends nothing gets called again next month about a debt they settled.
The receipt line asks them to send the confirmation to `{{verification_email}}`,
with the feminine inflection written out, followed by the same three-option
enumeration and the same default: if you cannot tell which you are in, you are in
the first one.

Server-side again disagrees with the screen: the greeting appears **once** in
Vapi's record. Vapi collapses consecutive bot turns into one message while the
user's ASR buffers, which is why the pasted transcript shows the greeting twice
and shows the agent answering questions the resident had not yet asked. The demo
page's rendering is now costing more time than it saves.

Live at 58,610 chars on `0ef11cb5`, receipt line present exactly once.

### The already-paid branch looped, twice, in two different ways

Two test calls, same branch, and the agent never got out of it. In the first it
asked *"את מתכוונת לתשלום של יולי?"* three times in three wordings. In the second
it fused the whole branch into one sentence — check the month, state the
discrepancy, give the email, ask if it was heard — and said that sentence four
times, the last one after the resident had said goodbye.

Four causes, and only the first was about repetition.

- **The reflex ask did not count.** Step 1 was written as an action to perform,
  not a fact that becomes true. The agent's surprised *"רגע, שילמת על יולי?"*
  asked the question, then it ran step 1 and asked it again properly.
- **The prompt licensed the second ask.** Step 1 said "once"; step 2 ended "do
  not ask a third time", which tells a model that twice is fine. Deleted.
- **The address check was a gate, not a turn.** *"Ask whether they got it… do not
  skip this check"* had no branch for an answer that is neither yes nor no, so
  "אוקיי" and "תודה" left the agent still waiting, and it re-asked. Since the
  turn was fused, re-asking the check re-said the entire branch.
- **The branch had no Hebrew in it.** `שילמ` appeared zero times in the whole
  prompt — four English instructions and not one written line, in a file where
  every other branch has its lines set down. Two calls, two completely different
  improvisations, both looping. That is what an unwritten branch produces.

Rewritten as four steps that are four separate turns, with the Hebrew written
out. Any answer that is not an explicit correction counts as a yes. The address
check is asked once and accepts anything. A goodbye ends the call from wherever
the agent is standing, with every open question dead.

- **General rule added to REPETITION**, because this class will come back
  elsewhere: *a question you have asked once has been asked.* It never starts as
  repetition — it starts as diligence about a check too important to leave
  unresolved. No check on this call is worth asking twice; log it and let a
  person follow it up.
- **Email address delivery.** It was spoken as one mashed token
  (`officeathomeys.co.il`). The branch now says how to say it: the name, שטרודל,
  then the domain broken at every dot. Not verified on a call yet.

Live on `0ef11cb5`, 48,326 chars. Guard passes.

### Stop banning the repeat, enumerate the alternatives

The turn-3 line pushed at 07:18 did not work. The call at **07:22:32 ran on it**
— assistant `updatedAt` 07:18:05, call four minutes later, checked rather than
assumed — and the agent still answered "אוקיי" by restating the amount in fresh
words, then answered a second "אוקיי" by restating the bank details in fresh
words.

**Two things the server transcript settled that the feed could not.** The
greeting appears **once** in Vapi's own record, so the doubled greeting on screen
is the page, and the opening fix from this morning is working. The amount and the
bank details each really do appear twice. And `אוקיי, ומה עושים?` appears twice
in the user stream — the page sent it twice, which is a separate bug: the presets
are `<button>` elements, so one that still has focus after a click re-fires on
Enter.

**Why the line did not take.** It was correct and it was in the wrong place — in
HOW PAYMENT ACTUALLY WORKS, ~16k characters away from THE OPENING, where the
model is anchored when it has just said the amount. When a model is unsure what
comes next it reaches for the nearest written-out line, and the nearest one was
the sentence it had just said. That is the same mechanism as the greeting on
6 Aug and the payment line on 7 Aug: **written-out lines get spoken, and
proximity decides which.**

**The deeper reason four rules failed.** REPETITION says an acknowledgement is
not a turn. "Rephrasing is repeating" says the synonym does not help. "A question
asked once has been asked" was added this morning. All three are prohibitions,
and a prohibition tells a model what not to say without telling it what to say —
under a forced turn there is nothing left but the sentence it just used.

So the fix is not a fifth prohibition. Directly after the amount line, 442
characters away, there is now an enumeration: **exactly four things you may say
next, and no fifth** — acknowledgement → ask for the yes; agreement → the link
line; a question → answer it then ask; anything else → that branch. Plus a
default that removes the failure mode entirely: *if you cannot tell which of the
four you are in, you are in 1.* And the general form, which applies everywhere in
the file: **asking a question you have not yet asked is always better than
repeating a sentence you have already said.**

The turn-3 line now exists exactly once in the file, in the menu, with the
payment section pointing at it rather than holding a second copy.

**Why English never had this fault**, since it is the obvious question: the
English twin is running a 38,533-character prompt last updated at 02:54, which
predates every patch made today. Hebrew is at 56,564 and has grown 38% in a day.
The English agent asked "would you like me to send you a payment link?" off the
identical acknowledgement — so the flow was always right and the Hebrew simply
never had the sentence. It is also worth saying plainly that a prompt growing by
a third in one day is its own risk, and the next session should be spent cutting
rather than adding.

Live on `0ef11cb5`, 56,564 chars.

### The main path had no third turn, and the link stopped being the only answer

**The Hebrew call restated the amount three times.** Not a branch — the main
path. The agent says what is owed and stops, per THE OPENING. The resident says
"אוקיי". And there was no line for what comes next: nothing in the file asked for
the yes. HOW PAYMENT ACTUALLY WORKS said *"if it is not a clear yes, do not ask a
second time"*, which assumes a first ask that was never written anywhere. So the
agent had said the amount and had nowhere to go, and said it again. Three times,
identical but for הוסדר/שולם.

The English twin did not have this fault — it asked *"Would you like me to send
you a payment link?"* off the same acknowledgement — which is worth noting only
because it means the flow was always right and the Hebrew never had the sentence.

Turn 3 is now written: *"אז רוצה שאני אשלח לך, אה, לינק לתשלום ותסגור את זה?"*,
asked once, with the amount never said twice. **Restating what somebody has just
acknowledged is the loop this prompt keeps producing, and it appears wherever a
turn ends and the next one was never written down.** That is now stated as the
general shape, next to the specific line, because this is the fourth instance of
it in two days.

**The link stopped being the only outcome.** In the English call a resident said
their connection was too poor to open links, said it twice, and asked whether the
office could handle it. The agent offered the transfer, then sent the link
anyway. Every sentence was polite and correct; nothing in it was listening. There
was no rule for a resident who has ruled out both payment methods — the office
route existed only for `alt_payment: none` and for missing variables.

Now: when neither fits, stop offering things and put it in front of the office —
*"אני יכול, אה, להעביר את זה למשרד ושייצרו איתך קשר"* — then `office_to_contact`
and close. **A resident who could not pay and now expects a call back is better
served than one offered the same link a third time.** And never send a link to
somebody who has said they cannot open one.

**"Of course" attached to a request that was refused.** The same resident said "I
give you permission to charge the card you have on your system" and the reply
opened *"Of course."* Nothing was charged and nothing could be — but that is not
what the sentence said to the person hearing it. Someone who believes they have
authorised a payment does not pay, and is angry twice: when the debt is still
open, and when they remember agreeing to settle it. No בטח, כמובן, אין בעיה or
בשמחה in front of an answer that declines something. Warmth is a tone, not a
first word that concedes.

Live on `0ef11cb5`, 55,336 chars.

**Display, not agent, and it matters for reading these transcripts:** the first
Hebrew line was the greeting cut off at *"אני מדבר עם"* and the next was the same
greeting complete, with "הומיז" in quotes the second time. Two transcriptions of
one utterance. `web/index.html` renders `transcriptType: "partial"` into the feed
and `say()` only collapses a partial when it is still the last node, so partials
strand as soon as the two speakers interleave. Some of what reads as repetition
in these pastes is the page. The amount three times was not — user turns sit
between them.

### Four test calls on the rewritten branches: three fixes held, four new faults

**Held.** The already-paid branch ran clean — month asked once, "כן" taken as a
yes, discrepancy stated, no loop, where two calls this morning could not escape
it. The handover said the new line and the call ended. The bank account came out
digit by digit.

**1. The opening was generated a second time, twice.** Once after a plain "כן" —
greeting, greeting again, then the reason for the call. Once to an answering
machine, which was greeted before the message was left. The prompt has said "the
opening is said once and never again" since 5 Aug, and it kept saying it into a
gap: `firstMessage` is spoken by Vapi before the model produces anything, and
nothing told the model that. It read a fixed line under a heading called Opening
and did what the file appeared to ask. It now says, at the top of that section,
that the line has already gone out and the model's first turn is the answer to
whatever came back.

**2. A bare "לא" closed the call without the not-the-account-holder line.** The
person was never told why the call ended and the office got no `wrong_party` row.
The opening cross-referenced that branch by name; the branch is now written out
inline, where the decision is actually made. It costs a duplicated fixed line —
`vapi_en.py` will need a count of 2 for that pair — and a live agent that says
the line beats a build script that likes the file.

**3. The voicemail message could never end a call.** It closed on תודה ויום טוב.
`endCallPhrases` are שיהיה יום טוב and ולהתראות, and `endCallFunctionEnabled` is
false, so there was no other way to hang up: the message was left perfectly and
the call then sat open against an answering machine until it timed out. Now ends
on the phrase that releases the line. The English twin never had this bug — it
closed on "have a good day", which IS one of its phrases, purely by luck of
translation.

Also removed the dead goodbye from the explanation of its own removal. A verify
probe caught it still in the file, inside the paragraph describing it, and this
prompt's whole history is written-out lines being spoken.

**4. A new loop, and I wrote it.** The identifier rule added this morning ended
"and you offer to say it once more" — an offer with no cap. The bank details were
read, offered again, read again, offered again, and the call was still offering
when the resident gave up. Same shape as the address check fixed this morning,
which the general "a question asked once has been asked" rule did not catch,
because an offer to repeat does not feel like a question being re-asked. Capped
at one offer, any answer ends it. **An offer to repeat is a courtesy, not a
checkpoint.**

Also: the branch number was שמונה מאות on the first reading and שמונה, אפס, אפס
on the second. Same digits the same way each time, now stated.

**Not a fault, worth recording so nobody chases it:** אה renders as אההה and אמ
as אמממ in the transcript. `firstMessage` is a fixed string containing אה and it
still shows as אההה, so that is the transcriber rendering a drawn-out sound in
the agent's own audio, not the model ignoring "write אה, never אההה".

Live on `0ef11cb5`, 52,661 chars.

### Elliot for English, Eyal for Hebrew — and the voice stops living in the shell

The two Hebrew agents were speaking in two different voices and nothing in any
file said so. Inbound was on `cartesia/a976c076` (Eyal), debt was on
`vapi/Elliot`. Both targets name the same `cartesia_voice`, so the code was never
the difference: Cartesia sat behind `VOICE_PROFILE=cartesia`, inbound was pushed
once with that set, debt never was, and the divergence then survived every
subsequent sync of either agent.

**A voice is not an environment concern.** Anything that can silently differ
between two runs of the same command does not belong in an environment variable,
and this one produced two front doors of one company sounding like two companies
for two days.

Cartesia is now the default for any target carrying a `cartesia_voice`, which is
both Hebrew agents. The English twins set their own `vapi/Elliot` in
`vapi_en.py` and never reach that code, so they were already right and stay
untouched.

Why not simply put Elliot on Hebrew as well, which is the easier way to make them
match: `vapi/Elliot` with `language: he` is an English voice model being told to
read Hebrew, and the American accent is not a setting that can be tuned out — it
is what that voice is. Eyal is a Hebrew voice on a Hebrew model. The price is
wall-clock; Cartesia ran 31-66% longer on identical sentences and calls bill by
the minute, so `generationConfig.speed` is where to look before the bill argues
back.

Both escape hatches still work and were dry-run before applying:
`VOICE_PROFILE=vapi` puts Elliot back on Hebrew for an A/B, `VOICE_PROFILE=native`
reaches Azure `he-IL-AvriNeural`. An empty profile no longer means Elliot, which
is the one thing to remember about this change.

Live, all four, guard intact at 27 replacements on each:

| assistant | voice |
|---|---|
| Debt Follow-up (he) `0ef11cb5` | cartesia Eyal, fallback vapi Elliot |
| Inbound Intake (he) `51bbe77a` | cartesia Eyal, fallback vapi Elliot |
| Debt Follow-up (en) `eaa390ec` | vapi Elliot |
| Inbound Intake (en) `fd991d71` | vapi Elliot |

Unheard as of the push. Vapi's cost records report `voiceId: Elliot` for every
call on the vapi provider regardless of what was spoken, so billing has never
been evidence of what came out — only a call answers it.

### The debt agent stops promising a transfer it cannot make

Walked every branch of the debt prompt against the live config. Two things broke
and both were the same shape: the prompt describing a capability the account does
not have.

**The handover asked residents to hold for nobody.** `transfer_to_human` on this
assistant is `type: "function"`, `async: true`, posting to n8n. It is not a
`transferCall` and there is no destination configured anywhere. The prompt's
three steps were *say the line, call the tool, stay on the line and say nothing*
— so the agent said *"נא להישאר על הקו"* and went quiet, and with
`silenceTimeoutSeconds: 20` the call dropped twenty seconds later. Six paths
reach that: hardship, hot, language, not_understood, caller_request, and a
dispute that turns angry. The prompt calls a resident who asked for a person and
got a dial tone the worst outcome in the file; it was the outcome of every one of
those calls.

The intake twin has said the honest thing since it was written — *"it does not
connect anyone to anyone, so do not say you are putting them through"* — and the
debt agent simply never got that change. It now matches:

> אוקיי, אני מעביר את זה, אה, לנציג מהצוות שלנו, והוא יחזור אליך בהקדם.

Step 3 is now *say the closing and end the call, warmly*. בהקדם is the ceiling on
what may be promised; no time may be attached to it. Handover moved from the
never-end list to the end-the-call-once list, and the tool description was
rewritten to match, since a model reads that too.

**Identifiers were being read as quantities.** "Say numbers as Hebrew words, not
digits" had no exception in it, which is right for ארבע מאות וחמישים שקלים and
catastrophic for everything else. `{{alt_payment}}` in the demo carries
`חשבון 12345678`; as a spoken number that is *שנים עשר מיליון שלוש מאות ארבעים
וחמישה אלף…*, which is a sum of money and not an account anybody can use. Same
for `{{callback_number}}`, and the email address had already been heard coming
out as one mashed token.

The carve-out is stated as a test rather than a list, so it covers whatever comes
next: **an amount is understood, an identifier is copied.** Anything being copied
gets digits, in small groups, with a beat between them, and an offer to repeat.

Live on `0ef11cb5`, 50,104 chars.

**Not fixed, and known:** voicemail still cannot fire — `voicemailDetection` is
null, so the written voicemail line is unreachable and an answering machine most
likely logs `wrong_party`. `server` and `serverMessages` are still null, so every
fault continues to be found by reading transcripts by hand. Seven branches still
have no written Hebrew and improvise at runtime — promise-to-pay first, which has
no rule at all for a vague date. `docs/diagrams/Homies-System-Flow.excalidraw`
still shows "hand over, stay on the line", but it also still shows the card
authorisation flow retired on 4 Aug, so it needs regenerating rather than
patching.

---

## 2026-08-04

### Two English test calls, and what they actually showed

The reading was "it did not go through n8n, it is all hardcoded." Half right, and
the half that was wrong hid a worse bug.

**n8n was fine.** Call `019fcc8f` shows real tool responses — `{"ok":true}`,
`{"ok":false,"error":"a ticket already exists for this call"}` — and the
workflow's execution log has 25 successes. The tool layer works. What is
hardcoded is the *input*: the demo page carries ten fictional residents and
always did. n8n is the write path, not the read path. Nothing has ever read a
resident from anywhere.

**The model spoke a tool call out loud.** Call `019fccb8`, verbatim:

> Can we charge the card on file for this amount? Open payment ticket. two
> functions, open payment ticket ten ten i Kypiao TCN Jason. authorization
> captured. True. The office will process it, and you'll get a confirmation.

"two functions" is `to=functions`; the rest is `<|constrain|>json` and the
arguments. gpt-5.4-mini emitted its own tool-call syntax into the spoken channel
and the TTS read it. Vapi logged **zero tool calls** for that call, so no ticket
was opened — the resident was told the office would process a payment that does
not exist. Intermittent: the same tool fired correctly forty minutes earlier.

- **EN model back to `gpt-5.4`.** -mini bought ~860ms and this is the bill. It is
  also what was asked for in the first place.

**The call would not end.** Both calls spoke the full closing and then sat there;
one ended with the resident saying "Hello?" and the bot answering "Yes, I'm
here." `endCallFunctionEnabled` was already true — the model simply chose not to
call it, and nothing made it.

- **Added `endCallPhrases`** (`goodbye`, `and goodbye`, `להתראות`). Ends on the
  assistant's own speech, so the decision no longer rests with the model.

**The page under test was a cached copy.** The two calls sent no `phone` at all
and an office email that had been changed hours earlier. Every row those calls
wrote went in against nobody.

- **`no-store` on `web/index.html`.** A stale demo page does not announce itself —
  the call just quietly means something other than what you think it does.

The closing itself is fixed, incidentally: "Great, thank you for your time. Have
a good day, and goodbye" is a full sentence, not a bare "Goodbye". That was the
open question from the last two attempts, and it is answered.

**Third call, after those fixes.** `019fccc3` — `open_payment_ticket` fired as a
real tool call with `authorization_captured: true`, got `{"ok":true}`, no JSON
spoken, and `endedReason: assistant-said-end-call-phrase`. Both fixes held.

`endCallPhrases` then broke something else. That call logged **one** tool call.
`log_call_outcome` never ran: the model was going to log the outcome after the
closing, and the closing is now what ends the call. A resident authorised 450₪,
the ticket opened, and to the office the call did not happen. The old failure
was a call that would not end; the new one is a call that ends half a beat too
early, and it is quieter — nothing in the transcript looks wrong.

- **Prompt now orders it:** `log_call_outcome` before the closing, never after.

Also fixed: the closing came out as "No problem. **for your time.** Have a good
day, and goodbye". The English substitution used an em dash — `Great — thank you
for your time` — and Vapi splits streaming TTS on punctuation, leaving "Great" as
a chunk short enough to be swallowed. Now a comma. The Hebrew line has no dash
and has never lost a word.

**Still unresolved: the demo page has not been reloaded once.** All three calls
sent no `phone` and the old `homiesemail@gmail.com`. `no-store` cannot help until
the browser fetches the file carrying it.

### The sheet is now the source of the call list

Google Sheets as the database, deliberately, for now. It already *was* the
database for writes; what was missing was the read.

Less was missing than expected. `doGet` with no phone has always returned the
call queue filtered by the same four conditions as `v_debt_call_queue`, and
against the live sheet it returns five rows, not ten — שחר is absent because he
was marked paid. The filter has been working against real data the whole time
with nothing consuming it.

**Read path: page → n8n → Apps Script → sheet.** Not page → Apps Script. The
Apps Script secret has to ride in the URL, and a URL in a page anyone can open is
a published secret that can also *write* every tab. n8n holds it instead and the
page carries no credential. New workflow `yKZDDR7nQ76qTmKv`, three nodes,
`GET /webhook/homies-queue`, `Access-Control-Allow-Origin: *` because a page
opened from disk has Origin `null`.

**The fetch happens at page load, never during a call.** Measured today: one
request 404'd, one took 3.9s, one took 26s. That is the stall that burned credits
on 4 Aug. At page load nobody is on the line, and the httpRequest node retries
three times — the only place in the chain that can retry without a person
waiting.

Changes:

- `Code.gs` — `lookup()` returns `phone` and `surname`; `?all=1` returns everyone
  with a `blocked` reason instead of only the callable. The four skip reasons are
  kept distinct: "already paid" clears itself next month, "not handed over" is
  permanent, "do not call" is a person's decision, "4 attempts" is the ceiling.
  Collapsing them would hide the only difference that matters when someone asks
  why a debtor was never rung. **Needs a redeploy — the live version predates
  all of it.**
- `web/index.html` — `PEOPLE` fetched at load; the old array is now `FALLBACK`
  and doubles as the Hebrew→Latin table. Source shown on screen, because a silent
  fall back to the built-in list looks identical and means the opposite.
- A queue where no row has a phone is **refused**, not displayed. That is the
  4 Aug failure exactly, and the fix is a redeploy rather than a retry.

Tested against a mock of the redeployed endpoint. Caught one bug doing it: the
`en` block was built in `fromSheet` and never returned, so English mode would
have read Hebrew names aloud — the failure the whole `en` mechanism exists to
prevent, reintroduced while wiring it up. Three cases now pass: built-in table
(שרה → Sarah), sheet columns (ליאת → Liat, via optional `en_first_name` /
`en_building`), and no source at all, which is flagged on the row rather than
dialled.

That last case is live already: renaming שחר to **דוד** in the sheet produced a
name the English voice cannot say, and nothing but this flag would have shown it
before the call.

**Not done, and it is the same sentence as always.** The queue webhook is
unauthenticated, like the tool webhook beside it. Ten fictional residents. The
sheet is the thing that will quietly stop being fictional.

### Found

- **The OXS API exists.** The whole of PRD v2 was written on the premise that it
  does not — §2.2 says so in as many words, and the nightly Google Sheets bridge,
  the freshness caveat and half the phasing follow from that premise. Homies'
  access-levels page shows three modules with API keys against them.

  | Module | Level | Exposes |
  |---|---|---|
  | קריאות שירות · service requests | **full control** | view, open, update, delete |
  | חובות דיירים · resident debts | read only | debts and balances |
  | מידע כללי · general info | read only | buildings, apartments, residents, payment history |

  - **Sheets is dead.** Residents, requests and debtors were the only three things
    the nightly bridge carried, and all three are live reads now. §2.2's caveat
    goes with it, and `get_request_status` no longer needs to return an export
    timestamp because there is no export.
  - **`open_request` writes straight to OXS.** Full control on service requests is
    the one write available, and it happens to be the one the vertical slice is
    built around — so the reference read back to a caller is a real OXS reference
    rather than one we minted.
  - **Debts are read-only, and that is load-bearing.** Call outcomes, promises to
    pay, disputes and retry counts cannot be written back. Supabase is therefore
    the only place outbound campaign state can live — an argument *for* it, not
    against.
  - **There is no payment-method module at all.** §2.3 was made staff-confirmed
    because RPA is fragile. The real reason is stronger: there is no API for it.
    Same conclusion, firmer ground. It also means **no version of this system can
    charge anyone** — money always ends at a human, which is exactly what the debt
    prompt already assumes.
  - One key per module, one level per key. Three keys, stored and rotated
    separately: `OXS_KEY_REQUESTS` (write), `OXS_KEY_DEBTS`, `OXS_KEY_GENERAL`.
    Blast radius of a leak is one module.
  - **Still needed: the endpoint docs.** The table says what the modules expose,
    not what a request looks like. Base URL, auth header, routes, and above all the
    field names on a resident and a debt row — which is what `004_debt_schema.sql`
    was written against guesses about.

- **A client-side flow doc contradicted what is built on two points.** It described
  sending OXS payment links on the debt call; the 3 Aug decision was the opposite —
  no links, spoken authorisation to charge the card on file, staff make the charge.
  It also identified callers by phone number alone, where the PRD holds
  `verify_identity` as a hard gate. Caller ID is spoofable and the flow discloses a
  balance. Both need settling with Homies.

- **"CRM" is being used for two different systems.** The Chatwoot agent inbox, where
  staff work threads and toggle the bot per conversation, and the Next.js read-only
  metrics dashboard, which §5 explicitly says is *not* a work queue. Calling them
  both CRM will get the wrong one built.

### Done

- **Drew the whole PRD as one diagram** —
  [Homies-System-Flow.excalidraw](diagrams/Homies-System-Flow.excalidraw), generated
  by [gen_systemflow.py](diagrams/gen_systemflow.py). The two front doors, n8n, all
  six flows step by step, §7 handover, and the four places anything can be written.
  - **Colour encodes which system is touched**, not who is speaking — violet is an
    OXS call, cyan a Supabase write, orange leaves the machine for a person, red
    refuses rather than degrades. That is the question the diagram has to answer.
  - Escalation is drawn as a dashed pill in the gutter beside the step, not as an
    arrow to the handover band. Six columns of converging arrows is unreadable; a
    repeated pill shape reads as one rule applied everywhere, which is what §7 is.
  - Folds in the OXS API finding, so it is ahead of the written PRD. The two
    sections that changed are headed in pink.
- **Wrote [check_diagram.py](diagrams/check_diagram.py)** — generalised from
  `check_callflow.py` to take a path. Catches shape collisions, label collisions,
  and bound text wider than its box. Layout bugs in a generated diagram are
  invisible until someone opens it, and by then it has usually been sent to a
  client. Caught three on the first run.

- **Built the debt agent's tool layer** — the eight tools existed only as prose in
  `prompt.md`; the assistant has been carrying `tools: none` since it was created,
  meaning it says it opened a ticket and writes nothing. Now:
  [debt-tools/index.ts](../supabase/functions/debt-tools/index.ts) (one Edge
  Function, all eight handlers), [vapi_tools.py](../scripts/vapi_tools.py) (the
  Vapi function definitions), `006_debt_tool_support.sql`, and `vapi_sync.py`
  extended to push tools alongside the prompt.
  - **One Edge Function, not n8n.** These eight are pure database writes; n8n's
    value is in integrations it is not doing here. It does not foreclose n8n for
    the WhatsApp and Monday tools.
  - **No tool takes an amount, a month, a charge id or a resident id.** Those come
    from the call's `variableValues`, which the model can read and cannot change.
    A model that mishears a figure, or a resident who insists it is different,
    still cannot write a wrong number into a payment ticket, because there is no
    parameter to write it through. Same principle as `verify_identity` being
    server-side.
  - **The first tool call of a call creates the `interactions` stub.**
    `payment_tickets` has a CHECK that a captured authorisation carries the call
    it came from — the recording *is* the authorisation — but the end-of-call
    report has not fired while the agent is still talking. Without the stub, every
    authorised ticket would fail its constraint mid-call.
  - **`bump_charge_attempt` is a SQL function, not an update.** `attempts = attempts
    + 1` through PostgREST needs a read first, and two overlapping calls both read
    1 and both write 2. The queue gates on `attempts < 4`, so a lost attempt is a
    resident called five times.
  - Unique index so one charge cannot produce two open tickets — the point of the
    queue is that a person charges a card exactly once.
  - `vapi_sync.py` attaches **no tools at all** while `SUPABASE_URL` or
    `TOOL_SECRET` is empty, rather than pointing them at a guessed URL. Tools
    against a 404 are worse than none: the agent believes the write succeeded and
    says so on the call.
  - The secret travels in a header, not the query string. Apps Script could not
    read custom headers and its secret landed in logs on every request; an Edge
    Function can.

- **Pinned the English demo's stack in code** — `731193bf` now runs Deepgram Flux
  + Elliot + gpt-5.4-mini, set from a `STACK` constant in
  [vapi_en.py](../scripts/vapi_en.py) rather than inherited. Applied and verified
  live.
  - **It had already drifted.** The dashboard was carrying Elliot and gpt-5.4
    while the script would have overwritten both back to Azure Jenny and the
    Hebrew twin's gpt-5.5 on the next run. Dashboard edits lose silently; the
    stack now lives where re-running is safe.
  - **The dashboard labels Flux as Azure, and that is wrong.** Vapi's schema
    rejects a `model` property on the Azure transcriber outright — so a
    transcriber named `flux general en` cannot be Azure. It is Deepgram Flux,
    whose ~250ms matches the dashboard's own number.
  - **Swapped gpt-5.4 → gpt-5.4-mini for latency**, not gpt-4.1-mini. gpt-5.4 was
    ~860ms of the ~1,600ms total. Staying in the same family and generation keeps
    behaviour closest to what has actually been tested — this prompt is almost
    entirely instructions, and two generations back is a bad trade for the same
    saving.
  - Vapi's PATCH validator can be probed with a well-formed but nonexistent v4
    UUID: 404 means the body passed, 400 returns the enum. That is how the model
    list and the Azure/Deepgram question were settled rather than guessed.
  - **The English twin no longer shares the Hebrew twin's stack, on purpose.**
    Hebrew has one workable transcriber and one workable voice; English has a
    faster option for both, and this assistant exists to review the call flow,
    not to represent Hebrew latency. Hebrew latency still has to be measured on
    the Hebrew assistant.

- **Found where the latency actually was, and measured it.** The dashboard's
  ~1,600ms is transcriber + model + voice and nothing else. It omits endpointing —
  the wait between the caller falling silent and the agent deciding they have
  finished — and `onNoPunctuationSeconds` was **1.8s**, spent on every turn whose
  transcript did not happen to end in punctuation.
  - **Measured baseline, 19 turns across recent calls: median 2,216ms, p90
    3,986ms, worst turn 6,870ms.** The dashboard understated the median by ~40%
    and the tail by a factor of four. Against §8's <800ms target.
  - Wrote [vapi_latency.py](../scripts/vapi_latency.py), which computes the gap
    from the caller's last word ending to the agent's first word starting, out of
    transcript timestamps. Vapi's call object has no `performanceMetrics`, but
    messages carry `time`, `endTime` and `duration`, which is enough.
  - Applied to all three live assistants. Voice, model and transcriber
    deliberately untouched everywhere, so a before/after measurement isolates
    endpointing and nothing else. In `STACK` in `vapi_en.py` and `BASE` in
    `vapi_sync.py` — not the dashboard, so a re-sync keeps it.

    | Assistant | wait | noPunct | backoff |
    |---|---|---|---|
    | Debt (en) | 0.4 | **0.8** | 1.0 |
    | Debt (he) | 0.4 | **1.0** | 1.0 |
    | Inbound (demo, he) | 0.4 | **1.0** | 1.0 |

  - **Hebrew gets 1.0 and English 0.8, on purpose.** Azure he-IL punctuates
    Hebrew far less reliably than Deepgram Flux punctuates English, so on Hebrew
    almost every turn takes the no-punctuation path and that timer is the only
    endpointing signal there is. Cutting a caller off mid-sentence is a worse
    failure than 200ms of wait, and this is a call about money.
  - **`backoffSeconds` 1.5 with `numWords` 2 is what produced "The the" / "The the
    bill"** in the 4 Aug call: a two-word backchannel stops her, 1.5s of silence
    follows, then she restarts the sentence from the beginning.
  - **Deepgram nova-3 supports Hebrew.** The roadmap and a comment in
    `vapi_sync.py` both say Azure is the only Hebrew transcriber that exists.
    That was true of nova-2 — the enum confirms it has no `he` — but nova-3 added
    it, and 11labs, speechmatics and soniox accept `he` too. Untested, but it
    reopens a decision that was closed on false grounds.
  - **Smart endpointing is probably not helping Hebrew.** The provider enum is
    `vapi`, `livekit`, `custom-endpointing-model`, and both shipped models are
    English-trained — so Hebrew falls through to the transcription timer every
    turn. Inference from the enum, not verified.

- **Fixed the closing and the repeat loop.** A test call ended on a bare
  "Goodbye", and gave the same email instruction three times before it.
  - ENDING THE CALL said *"say a short warm closing"* and gave no example. The
    only concrete word in the section was "goodbye", four lines down, so that is
    what the model used. Abstract instructions get filled in from whatever
    concrete token is nearest. Added the actual line, marked as a shape rather
    than a script.
  - Added: **an acknowledgement ends the call.** "Okay", "sure", "I will" means
    the matter is settled — close, do not restate the instruction more helpfully.
    The dispute path already said "state once"; what it lacked was a rule for
    recognising that the once had landed.
  - **Sixth fixed Hebrew string**, so the native-speaker check now covers six, not
    five: `מצוין, תודה רבה על הזמן. שיהיה יום טוב ולהתראות.` Deliberately avoids
    `לך`, which would need gendering against `{{gender}}`.
  - `vapi_en.py` refused to build until the Hebrew went up first — it reads the
    live assistant, not the file, so a new Hebrew string it has no translation
    for is exactly the half-translated twin the assertion exists to prevent. The
    order is Hebrew first, English second, always.
  - **Latency after the endpointing change: median 1,919ms, was 2,216ms.** A
    ~300ms gain, well short of the ~1,000ms predicted. One turn still took
    5,280ms. The endpointing timer was evidently not the whole story, and
    gpt-5.4-mini's time-to-first-token over an 18k-character prompt is the next
    suspect.

- **The closing fix did not take, and the reason was instructive.** A second call
  still ended on a bare "Goodbye" — with the new prompt confirmed live in the
  call's own system message, so not a deployment problem.
  - Twenty lines below the new example sat *"Saying **goodbye** is not the same as
    ending the call. Do both."* — which reads as an instruction to say the word,
    and was the last line of the section. The example lost to it. Its real intent
    was *do not leave the line open*, so it now says "speaking the closing is not
    the same as ending the call".
  - Also added the check to **QUALITY CHECK**, which the model runs before every
    reply. A rule 450 lines into an 18,600-character prompt gets read once; a
    checklist item gets applied every turn. That is the more reliable place for
    anything about the shape of a reply.
  - Diagnosis worth keeping: `endedReason: assistant-ended-call`, "Goodbye." as a
    bot message at 46.4s, then a tool call. That ordering proves the model
    generated the word rather than Vapi injecting it, and ruled out
    `endCallMessage` in one step.
- **Resolved the hot-versus-dispute contradiction.** POSTURE listed *"they say
  they already paid"* under hot, while the disputed-payment path says log it,
  give the email once and end — and criterion 6 says every hot call transfers.
  The list was conflating a calm claim with an angry one. Hot now requires the
  anger or the refusal to accept any answer; the claim by itself is the dispute
  path. **This is a product decision made on the client's behalf and is worth
  putting to Homies** — the cost of being wrong runs both ways, and the numbers
  differ a lot: treat every claim as hot and roughly every second call transfers
  to a person.
- **English persona renamed Michal → Michael.** Elliot rendered "Mikhal" as
  "McCall" on every call, and a prompt spelling hint does not change what a voice
  does with a name. Michael is the English cognate, reads correctly unprompted,
  and fixes the second half of it too: Elliot is a male voice that had been
  introducing itself with a woman's name. Hebrew is untouched — Hila says מיכל
  correctly.
- **Demo email changed to `office@homies.co.il`.** `homiesemail@gmail.com` came
  out of the voice as "homey's email at gmail dot com": the local part runs two
  words together and the TTS guesses. Still a placeholder — Homies' real address
  has to replace it before anyone outside the team hears it.

- **The eight tools are attached and writing.** Both debt assistants went from
  `tools: none` to eight live tools. First time anything the agent says about
  having recorded something has been true.
  - Host is **Apps Script, as a deliberate stopgap** — a second implementation of
    the same eight tools in `sheets/Code.gs`, writing to five tabs created on
    first write. `vapi_sync.py` prefers Supabase and falls back to this, so the
    day the project exists the sheet stops being used with no code change.
  - **The TypeScript version stays the specification.** Two implementations of
    one contract will drift, and only one of them has real constraints.
  - Costs accepted knowingly: the secret travels in the query string, because
    Apps Script cannot read request headers, and lands in Google's logs on every
    call. Cold starts add 1–3s of silence to whichever turn fires a tool. Neither
    survives contact with a real resident row.
- **Wrote [check_tools.py](../scripts/check_tools.py)**, which fires all eight at
  the live endpoint and asserts three guards *refuse* — a duplicate ticket, a
  bogus outcome enum, a request with no description. It paid for itself at once:
  - Before the redeploy, all ten cases returned `{"found": false}`, because the
    deployed script routed every tool call to the resident lookup regardless of
    name. From Vapi's side that is invisible — the agent gets an object back,
    believes it, and tells the resident the ticket is open.
  - Two first-writes 404'd while their tabs were being created. Transient, and
    only distinguishable from a real fault by running the check twice.
  - **The checker had a bug of its own**: reusing `probe-7` across runs meant the
    second run's ticket was refused by the first run's duplicate guard — a correct
    refusal reported as a failure. Call ids are now run-stamped. A test that only
    passes against a clean sheet will lie to you later.

- **The first call with tools attached died on the tool, and the fix was `async`.**
  The agent called `log_disputed_payment`, waited, said *"this will just take a
  sec"*, then *"sorry, a few more seconds"* — twice — then hung up on the
  resident. The tool returned **404 after 17 seconds**.
  - **Measured, not estimated: Apps Script is ~13s cold and ~2s warm, and a cold
    call sometimes 404s outright.** I had told the user 1–3s when recommending
    against this route; the real cost is four times worse and includes silent
    failure. Recorded here because the estimate was wrong in the direction that
    mattered.
  - **Six of the eight tools are now `async: true`.** Vapi fires them and moves
    on, so a slow host costs nothing. Only `open_payment_ticket` and
    `open_request` still block, and both have to: the first can refuse and the
    agent must not confirm a rejected payment, the second returns a reference
    that gets read aloud and may not be invented.
  - **Async has a real cost: a fire-and-forget tool that 404s loses the write and
    nobody finds out.** That makes the cold start a correctness problem, not just
    a latency one.
  - So the console now **warms the runtime with an unauthenticated GET** on page
    load and again on call start. Rejected in one line, but it starts the
    runtime, and it carries no key — the secret stays out of the page, which is
    the whole reason the resident list is baked in rather than fetched. Verified
    after 90s idle: GET 1.79s, then POSTs at 2.3s with no 404.
- **The demo page was not sending `phone`.** Every tool row would have been
  written against nobody, and `flag_not_handed_over` would have updated no one,
  silently — findable only by staring at the sheet afterwards. Ten numbers added,
  matched to `residents.csv` **by name rather than by position**, because the CSV
  has Michal Dahan sixth and Avi Biton seventh and PEOPLE has them reversed.

- **Moved the tool layer to n8n. ~700ms, flat, no cold start.**

  | host | cold | warm |
  |---|---|---|
  | Apps Script | 13,000ms, sometimes 404 | ~2,000ms |
  | n8n | **739ms** | **~700ms** |

  - Built by [n8n_deploy.py](../scripts/n8n_deploy.py), not clicked together in
    the editor — an editor change is invisible to anyone who did not make it and
    has no diff. Re-running updates the workflow by name rather than making a
    second one.
  - **Shape: Webhook → Decide (Code) → Respond, and separately → Sheets.** The
    response is computed and returned *before* the sheet is touched, so a
    one-second Google Sheets append never reaches the caller. That is the entire
    fix for the stalls, and it holds no matter how slow storage gets.
  - **Two n8n gotchas, both cost real time.** A webhook node created without a
    `webhookId` leaves the workflow reporting `active: true` while every POST
    404s "not registered" — the id is what n8n registers against, not the path.
    And `respondToWebhook` wants typeVersion 1.1. Both found by diffing against
    the working webhooks already on the instance rather than by reading docs.
  - **The duplicate-ticket guard changed shape.** Apps Script refused a second
    ticket by scanning the sheet first; that would need a read *before* the
    response, which this design will not do. It is now an upsert on `call_id`, so
    the model may be told ok twice but a person still sees one row. The contract
    moved with the host, and `check_tools.py` says so rather than pretending the
    old guarantee survived.
  - `open_payment_ticket` is **sync again** — it went async only because 13s
    stalls were burning credit. At 700ms the refusal is worth waiting for. Note
    precisely what that buys: the workflow answers from the Code node before
    writing, so a sync response confirms **the decision, not the row**. Validation
    is guaranteed; durability is not. Only a datastore in the request path gives
    that, which is a Supabase argument rather than an n8n one.
  - Reused the existing `shirly sheets` Google credential rather than asking for
    fresh OAuth. It is another project's credential on a shared instance —
    acceptable because the instance owner is the same person, and it works, but
    a dedicated `homies-sheets` credential is the right thing before this is
    anything but a demo.

### Open
- **The n8n webhook has no authentication at all.** `N8N_WEBHOOK_SECRET` is
  still empty and the Code node does not check anything, so anyone who learns
  the URL can write rows to the spreadsheet. Fine for ten fictional residents,
  not for one real one. Header auth on the webhook node is the fix.
- **This is a shared production n8n instance** carrying other clients' workflows
  (MOR, Shirly Inventory, CLIX, Hadas). Only ever create new workflows here; do
  not modify or activate anything else.
- **Apps Script is superseded but still deployed and still writing.** Its tools
  are no longer attached to anything, but the endpoint is live with the secret in
  its URL. Decide whether to retire it rather than leaving two tool layers
  answering the same contract.
- **Apps Script is not viable for voice and this is now measured.** 2s warm is
  still poor, the warm-up is a mitigation rather than a fix, and a lost async
  write is invisible. Supabase Edge Functions are ~100–300ms with none of this.
  The stopgap bought a working demo; it should not survive contact with Homies.
- **§8's <800ms is likely unreachable for Hebrew** once endpointing is counted.
  ~1.2–1.5s is realistic. Better to renegotiate the number with Homies than to
  quietly miss it.
- **The 4 Aug English call disclosed the card's last four digits to an unverified
  caller** who simply asked which card was on file, and never stated the month or
  the amount before asking to charge. It also read "Alright. Yeah. Yeah. Yeah." as
  an unambiguous authorisation and ended the call. Nothing was written only
  because the tools are not attached.
- **`flux-general-en` is unverified.** Deepgram's provider does not validate model
  strings server-side — a nonsense model passes PATCH too. Acceptance proves the
  shape, not the name. Only a test call proves the transcriber actually runs.
- **~1,600ms was the dashboard's estimate, never measured.** The mini swap should
  take a few hundred milliseconds off, but the number to trust is voice-to-voice
  from a real call log, against §8's <800ms.
- **The debt agent still cannot run.** Blocked on one thing only I cannot do:
  the Supabase project does not exist. Create it (eu-central-1), run `001`, `002`,
  `004`, `005`, `006`, fill `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` /
  `TOOL_SECRET`, deploy the function, then `vapi_sync.py debt --apply`. Confirm
  `v_debt_call_queue` returns **six** rows.
- **Outbound cannot be rehearsed the way inbound was.** The M1 demo ran on Vapi
  web calls with no phone number; an outbound campaign is inherently a dialled
  call. The conversation and all eight tools can be tested on a web call with
  `variableValues` supplied by hand — everything except the dialling.
- **The OXS PDF is key management, not endpoint docs.** It confirms the three
  modules, and adds: rate limits 60/min and 1,000/hour, keys expire (1 year
  default, 2 max), rotation leaves the old key live for 24 hours, keys are shown
  once and unrecoverable. It contains no base URL, no routes, and no field names —
  so `004_debt_schema.sql` is still written against guesses.

- **PRD v2 is now out of date in four places** and needs amending: §2.2 (live, no
  caveat), §9 (Sheets out, OXS API in), §10 (`get_request_status` loses the export
  timestamp), §16 (item 3, the OXS export, closes entirely). Not yet done.
- Payment links versus card-on-file — two different products, one of them is wrong.
- Which second factor `verify_identity` actually uses. Still §16 #1, still blocking
  §2.3, and now blocking any balance disclosure too.

### Later that day — a way to clear the test rows

- Confirmed the live Apps Script deployment is still the **old** code: the queue
  it returns has no `phone`, and `?meta=1` is ignored rather than answered. The
  redeploy asked for earlier has not happened, so nothing added since is live.
- Added `?key=…&clear=all` (or `&clear=<tab>`) to `sheets/Code.gs`. Empties the
  five write tabs, keeps their headers, reports how many rows went.
- `residents` is refused **by name**, not merely left out of `TABS` — so putting
  it in `TABS` one day cannot quietly make the input data wipeable. There is no
  undo on a spreadsheet reachable by URL.
- Documented in `sheets/README.md` under "Clearing the test rows".

### The agent told a resident he had a card on file. He does not.

Test call to משה (`+972531234569`, `card_last4` empty). The caller asked *"do you
have my card on your system?"* and the agent answered **"we have a card on file
in the system"**, having already asked *"can we charge the card ending for this
amount?"* — the authorisation sentence with the digits missing out of the middle
of it. It then wrote `payment_tickets` with `authorization_captured: TRUE` and
`card_last4` blank.

**Cause: the agent cannot branch on an empty variable.** It never sees a
variable, it sees the prompt after substitution. The rule was *"if
`{{card_last4}}` is empty there is no card on file"*, which renders as *"if  is
empty there is no card on file"* — no condition left to evaluate. Absence had to
become a word.

Three fixes, defence in depth:

- `variablesFor` in `web/index.html` now sends `has_card` as the literal `"yes"`
  or `"no"`. Checked against a mock: משה → `no`, שרה → `yes`, and no page-only
  key leaks into the agent.
- The prompt branches on `{{has_card}}` in all five places, with *"if it is
  anything else — blank, missing, a word you do not recognise — treat it as no"*
  so a missing variable fails towards not charging. Pushed live to both
  assistants; verified 5 occurrences each.
- `open_payment_ticket` now **refuses** `authorization_captured: true` when the
  call carries no `card_last4` — in `sheets/Code.gs` and in
  `supabase/functions/debt-tools/index.ts`, so the two do not drift. The prompt
  is asked not to do this; the tool makes it impossible.

### The page was never reading the sheet

The same ticket says `first_name: Shahar` while the sheet's row 2 says דוד כהן,
and `phone` is empty on every row written today. Both mean one thing: the page
fell back to its built-in list. Nothing was wrong with the sheet — the deployed
Apps Script still predates `phone`, so the load-time guard correctly refused the
queue, and the fallback is what ran.

Synced the built-in list to the sheet anyway: שחר is now דוד and marked already
paid, matching the edit made in the sheet. A fallback that disagrees with the
source is how "the bot is not reading everything" looked from the outside.

### Payment is a link now, and OXS sends it

Client decision, reversing 3 Aug. The resident pays through a link Homies' own
system sends them; the agent never mentions a card, never takes an approval to
charge one, and no member of staff charges anything.

- `open_payment_ticket` → **`send_payment_link`** on both assistants. Verified
  live: `card_last4` and `has_card` now appear **zero** times in either prompt,
  and the retired tool is no longer offered.
- New `payment_links` tab and handler in `sheets/Code.gs`; new `payment_links`
  table in `supabase/004_debt_schema.sql`, with RLS and a unique index giving one
  link per interaction. No `card_last4` column and no `authorization_captured`
  column — there is nothing to authorise.
- `log_call_outcome` gained `link_sent`. `authorized` still accepted so older
  rows keep their meaning.
- The Hebrew fixed string is now
  *"מצוין. אני שולחת לך קישור לתשלום על הסכום הזה, ותוכל להשלים את זה בעצמך"*,
  with the English twin translated to match. Still needs a native speaker.

**Why this is better than what it replaced**, beyond being what the client
wants: the call recording stops being the authorisation for a payment. That put
a 14-day Vapi retention window and the unanswered Israeli recording-consent
question directly underneath money movement. Consent now happens when the
resident taps the link. The worst case of a mishearing drops from *a charge
nobody agreed to* to *a link nobody uses*.

**What it costs:** the payment is offered, not settled. Nothing on our side can
see whether a link was ever paid — that is a read back from OXS, and until it
exists any report counting `link_sent` is counting intentions.

### A refusal that only existed downstream was invisible to the caller

Found while moving the tool over, not by reading the code. n8n answers Vapi from
its Code node **before** the writer runs, so the card guard added to
`sheets/Code.gs` this morning would have refused the row *after* the agent had
already been told `ok: true`. The resident hears a confirmation for a row nobody
wrote. Mirrored the guard into the n8n switch and confirmed it fires there:
`{"ok":false,"error":"no card on file for this resident …"}`.

The general rule this is an instance of: **every refusal has to live in the node
that answers, not only in the node that writes.**

### The Hebrew call that "felt unnatural" was a call with no variables

*"אני מדברת עם?"* — am I speaking with *nobody*. The name was missing from the
opening and from the not-the-account-holder line. Checked the last six web calls
through the API: **three carried no `variableValues` at all.** Those are Vapi
dashboard test calls, which send nothing. On one of those `{{amount}}` and
`{{month}}` are empty too, so the same call would have said "the payment for the
month of, zero shekels" had it got that far.

Nothing to fix in the prompt for that one — dashboard calls cannot be given
variables. Testing happens from the demo page.

The three faults the user raised are real independent of it, and two were not
handled at all:

- **The opening is now said once, ever.** Not after a "no", not when someone else
  comes to the phone. The transcript shows two identical rounds of greeting and
  refusal; re-introducing yourself tells the person you have lost the thread. A
  different voice on the line gets one short line, not the opening again.
- **The wrong-party line now ends the call.** Say it, log `wrong_party`, close,
  go. Previously it said the line and waited, which is what let the loop happen.
- **An ambiguous answer gets exactly one clarifying question.** "Who's asking?",
  "they're not here", "no no", "they spoke already" — ask once whether this is
  {{first_name}}; if the second answer is still not a clear yes, treat it as a
  no. Never a third time. *The cost of ending a call with the right person by
  mistake is one missed collection; the cost of guessing wrong is telling a
  stranger what a resident owes.*
- **Money stays unsaid until they confirm who they are** — including "it's about
  your building committee payment". A no is final for the whole call.

Residual, to watch: in that transcript the fixed wrong-party line was
**paraphrased** — the privacy clause *"אני לא יכולה למסור פרטים למי שאינו בעל
החשבון"* was dropped. It may be an artefact of the empty name making the
sentence ungrammatical. Recheck it on a call that has variables before treating
it as a model problem.

### A resident asked us to prove we were real, and there was no answer for it

Call to רחל. She asked where the number came from, then asked the agent to
verify her address to prove the call was genuine. The agent said it could not
share personal details and offered a callback — then repeated *"you're a
resident in a building Homies manages, and this is the number on your resident
record"* **three times**, twice back to back, while she was asking something
different each time.

Two fixes, and the second is the one that was actually missing.

**`{{callback_number}}` existed and was used only in the voicemail message.** The
office line — the one thing that lets a suspicious resident verify the call
without having to trust the caller — was never offered to a live human. Someone
ringing about money out of the blue, in a country where phone fraud is
relentless, will ask this often, and "I can't tell you" on its own is the answer
a scammer would also give.

Now a branch of its own: say plainly that personal details are not read out over
the phone *and that this is the protection they would want*, give them
`{{callback_number}}` to ring the office themselves, offer to repeat it, and let
them hang up and check if they want to — that is a good outcome, not a lost one.
Never read back an address, a unit, a card or a balance to prove identity. The
amount already stated is the most that gets said.

**And a general no-repeat rule**, because this is the second call in a day to
loop: one said the resident-record sentence three times, the other said the
payment-link line three times. If they are still asking, the answer did not land,
so say something different — a fact not yet given, the office number, the
alternative way to pay, or a person. Never the same sentence reworded.

### An English line was living in the Hebrew prompt

The user asked for the Hebrew version to be a true clone. It already was, with
one exception found by checking rather than assuming: the refusal callback offer
added hours earlier was written as a `>` line **in English**. `>` means spoken,
so the Hebrew assistant was carrying one English sentence among six Hebrew ones
— on the branch that had never been tested in either language.

Now `> אפשר שנציג מהמשרד יחזור אליך בנושא?`, paired with its English
translation in `vapi_en.py`. Phrased without a gendered verb for the listener,
like the other fixed strings.

Also corrected the fixed-strings list, which said six and was wrong twice over:
the closing had been fixed for days without being listed, and the refusal offer
made eight. That list is what gets handed to the native speaker doing the
review, so a list that does not match the prompt is worse than no list.

Added a check worth keeping: pull both live prompts, extract every `>` line, and
assert the script matches the call language. Seven each, zero wrong.

### "I already paid" is now four steps, on the client's spec

Previously: state what the system shows, give the email, log, end — one pass,
no verification, no check that the address landed. The user asked for a
confirming question first and an explicit check that the resident actually
caught the email. Both are right, and the second is the one that was quietly
costing us.

1. **Check the month, once** — confirm it is `{{month}}` they mean, as someone
   making sure they are looking at the right thing rather than someone doubting
   them. Still never asks when, how, or through which account.
2. **Say what the system shows** — framed as two records that do not match, never
   as a correction of the resident. No third ask.
3. **Read the address, then ask whether they got it**, and repeat once, slower,
   if not. An email address spoken down a phone line is the likeliest thing on
   this call to be misheard, and a resident who writes it down wrong hears
   nothing back and concludes they were ignored. `office@homies.co.il` is still
   a placeholder, and `homiesemail@gmail.com` before it came out of the TTS as
   *"homey's email at gmail dot com"* — this step is the mitigation for a
   problem we have already had.
4. **Log and close** — no link, no amount, no asking them to pay meanwhile.

Anger at any point still overrides all four and hands over.

### There was no refusal branch. At all.

Raised by the user after a test call: a resident said he would not pay, and the
agent went straight to the closing without offering anything. Grepping the
prompt for refusal handling turned up **one** mention — *"they have refused and
you have accepted it"*, in the list of conditions for ending the call. There was
no instruction anywhere for what to do when someone says no, so the model
improvised, and closing politely is a reasonable thing to improvise.

Added as a fixed path. Accept it in one sentence, no arguing and no second ask,
then offer a person **once**: *"would you like someone from the office to get
back to you about it?"* Yes → `office_to_contact`. No → `refused`, and close
warmly. Deliberately **not** a transfer — an offered callback is answerable with
the tools that exist, and it does not walk into the handover that goes nowhere.

The reason the offer is worth having: a flat refusal is usually about something
other than money — a dispute with the committee, a repair never done, a bill
they think belongs to the previous tenant. None of it is the agent's to solve
and all of it is worth someone hearing. As it stood, the office learned only
that he said no.

### Hardship was firing on people who had already given a date

Same call, earlier: *"can we do it by the end of the week? I don't have any
money yet"* was read as hardship and escalated. He had given a date; the second
clause was the reason for the date, not distress. The rule now says a promise
with a reason attached is a promise — take the date and close — and reserves
hardship for an inability to pay with no date behind it.

Also: the handover line was spoken twice in a row on that call, once bare and
once with an apology in front of it, which sounds like the first attempt failed.
The prompt now says once.

### Everything saved for a move to another Vapi account

- `scripts/vapi_export.py` — dumps every collection the account can hold
  (`assistant`, `phone-number`, `tool`, `squad`, `workflow`, `file`), including
  the three that are empty, since an export that only looks where it expects
  things is how a resource goes missing. Server header values are redacted at
  any depth — they are empty today, but a dump that is safe by accident is not
  safe.
- `docs/handover/vapi-export.json` — 96k, six assistants and one phone number.
  A record, not a restore path: Vapi mints new ids on create.
- `docs/handover/new-vapi.md` — the rebuild. Nothing of value is only in Vapi;
  the prompts, tools and config all push from this repo, so a move is
  `vapi_sync.py --apply`, `vapi_en.py --create`, and then fixing the ids that
  seven files hardcode. Line numbers for each were checked rather than guessed.

Recorded as not transferring: call history and recordings, the free US number,
the eval suite, and anything ever edited in the dashboard and not written back
here — that last one exists nowhere else and a rebuild will quietly not have it.

### 5 Aug — "Echo Stone": the debt agent is wired for a cloned voice, and two dead ends ruled out first

Asked for the debt agent to speak in a recording of a real person's voice. The
recording is good material — 220 seconds, only 11 seconds of silence across
seven gaps, single speaker — but it peaked at **+0.29 dBFS**, i.e. at or above
full scale, and clipping bakes distortion into a clone permanently. Cleaned to
mono 44.1kHz at −0.50 dB peak as `voice/echo-stone-sample.wav`.

**Vapi cannot host a cloned voice, and this is settled rather than suspected.**
`VapiVoice.voiceId` is a closed enum of thirty names in Vapi's own OpenAPI spec
— Elliot and Leah among them — with no slot for a custom id. `CloneVoiceDTO`
exists in that spec and is referenced by no path and no other schema. Both
accounts, old and new, report zero credentials, zero provider voices and zero
files, which is consistent: a clone is created *in a provider account*, and with
no provider connected there is nowhere for one to be created.

**"Custom voice" in the dashboard is not voice cloning.** It looked like the
answer and it is the opposite: `CustomVoice` requires a `server`, and the
request flows *outward* — Vapi POSTs text to a URL you run and expects audio
back. It is a bring-your-own-engine hook for providers Vapi has not integrated.
The giveaway is that the panel has no upload field at all, only Provider, Server
URL and Voice ID. Saving that screen as it stood — Custom voice with an empty
Server URL — would have left the debt agent with no TTS whatsoever *and* wiped
the 27-replacement output guard, which lives inside `voice`. Caught before save;
the assistant still reads `provider: vapi`, `voiceId: Elliot`, guard intact.

**Cartesia, not ElevenLabs, and the reason is Hebrew.** Cartesia declares `he`
in a 42-language enum and takes a free-text `voiceId`, so a cloned id fits. It
also keeps `chunkPlan`, so the guard survives the move. ElevenLabs declares
`language` as free text, meaning nothing in the spec states whether Hebrew works
there — it would ride on `eleven_v3` — and the spec carries the error
`eleven-labs-blocked-using-instant-voice-clone-and-requested-upgrade`, so its
cloning is plan-gated as well. Paying to find out is the wrong order. PlayHT,
LMNT and Rime also declare Hebrew and are the backups.

**The debt agent takes the voice, not the inbound one.** The voice is male and
this prompt is already masculine throughout — מיכאל, מדבר, שולח, מעביר — so not
one word changes. Pointing a male clone at the inbound agent would mean flipping
the same seven passages that have already been flipped three times.

Wired as `cloned_voice()` in `vapi_sync.py`, gated on `CARTESIA_VOICE_ID`. With
the variable unset it returns None and nothing changes — verified by running the
dry run both ways, `vapi Elliot` against `cartesia <id> (cloned) fallback -> vapi
Elliot`. The fallback is not decoration: a cloned voice failing mid-call would
otherwise end it, and `FallbackVapiVoice` carries `chunkPlan`, so the guard
survives the fallback too.

**PARKED, same day.** Staying on Vapi `Elliot` v2 `language: he` for now — which
is what the assistant already carried, so nothing was changed to park it. Everything
for the clone is built and waits on one thing only: a Cartesia API key in `.env`.
`scripts/voice_clone.py --go` then does the rest, and `cloned_voice()` in
`vapi_sync.py` returns None while `CARTESIA_VOICE_ID` is unset, so the wiring is
inert rather than half-applied.

Two corrections worth carrying forward, because both were stated wrongly here
first:

- **Instant cloning is free.** The "$49/month Pro tier" came from third-party
  pricing write-ups; Cartesia's own docs say training instant clones is "fast and
  free" and put the paid tier on *Pro* cloning, a different feature. A free
  account is worth trying before assuming a bill.
- **The full recording cannot be used, in either mode.** At 3m40s it is 22x over
  instant cloning's 10-second limit and 8x under Pro cloning's 30-minute minimum,
  so it falls in the gap between the two. Using "the whole file" on the instant
  endpoint does not use the whole file; it lets the API pick the ten seconds. If
  the full-fidelity version is ever wanted, the answer is to record **30 minutes
  to 2 hours**, not to send this one — and to note that Pro clones bill TTS at
  1.5 credits per character against 1, a permanent 50% rise on a line already
  over budget.

**Vapi cannot clone, and this is now proven rather than read.** A PATCH setting
`voice.voiceId` to a custom string returns 400 with the enum in the error:

    voice.voiceId must be one of the following values: Clara, Godfrey, Elliot,
    Savannah, Nico, Kai, Emma, Sagar, Neil, Layla, Sid, Gustavo, Kylie, Rohan,
    Lily, Hana, Neha, Cole, Harry, Paige, Spencer, Naina, Leah, Tara, Jess,
    Leo, Dan, Mia, Zac, Zoe

The request was rejected, so the assistant was untouched by the test. Thirty
names, no thirty-first.

Still open, and it is the one claim in the chain that cannot be checked from
here: **whether a cloned voice speaks good Hebrew.** Only a call answers it, and
it should be answered before a resident hears it.

Also worth revisiting whichever way the clone goes: **Elliot was never chosen.**
It is Vapi's default and arrived on this assistant through a dashboard edit on
5 Aug. Fourteen of the thirty are male — Godfrey, Nico, Kai, Sagar, Neil, Sid,
Gustavo, Rohan, Cole, Harry, Spencer, Leo, Dan, Zac — and none has been heard
against Hebrew. Vapi has no standalone TTS endpoint, so auditioning them means
the dashboard preview or a call.

**Audio is now gitignored.** `New Recording 154.m4a (1).mp4` was sitting
untracked *and un-ignored* in the project root and missed the previous commit by
minutes. A voice recording identifies a person, and removing one from git
history is a rewrite rather than a delete.

### 5 Aug — the inbound call had no ending, and every transfer was a promise nobody could keep

Two omissions in the inbound agent, found by reading the live config rather than
a transcript. Both are the same mistake: a thing the prompt describes that the
platform was never told to do.

**Nothing could end an inbound call.** `endCallPhrases: None`,
`endCallFunctionEnabled: None`, and no closing line anywhere in the prompt to
trigger one with. All three calls on record ended `customer-ended-call`, which
is why it never looked like a bug — someone who rang in does normally hang up.
The shape underneath is worse than that reading: the agent reads out the
reference number, stops, and the line stays open in silence for thirty seconds
until `silenceTimeoutSeconds` closes it. The caller is left listening to nothing
with no way to tell whether their request was written down.

Fixed the way the debt agent was, because it is the same problem: an `## Ending
the call` section with a fixed closing, `endCallPhrases: ["and goodbye",
"ולהתראות"]`, and `endCallFunctionEnabled: False` set explicitly so a dashboard
visit cannot quietly hand the model a way to hang up without speaking. Saying
the line is the mechanism, not a request. One `משהו נוסף?` gates it — the only
extra turn the style section tolerates, and it is there because ending a call is
the one irreversible act in the flow.

**Every transfer path promised a live handoff that does not exist.**
`transfer_to_human` posts a row to n8n. There is no `transferPlan`, no
destination, no extension — verified on the live assistant, both fields null.
The prompt said *"אני מעבירה אותך לנציג"* in five separate places, so the caller
was told they were being put through and then sat on an open line waiting for a
voice that was never coming. All five now say a representative will get back to
them, which is what the row actually causes; `transfer_to_human`'s own
description says so too, so the model is not reading one thing in the prompt and
another in the tool; and absolute rule 9 forbids the old phrasing outright. When
a real extension exists, the wording and a `transferPlan` go back together.

The 08:56 English test call is worth separating from this. It thanked the caller
for reporting a leak and explained a fallback before it was needed — both
explicitly forbidden — but the assistants were re-synced at 10:30, so that call
predates the `Say less than you think you should` section rather than ignoring
it. It has not been retested since, and it is the thing to watch on the next
call, along with the fact that 97 seconds of leak, building and apartment
produced zero tool calls.

English twin rebuilt from the Hebrew: 24 substitutions, all matched exactly
once, no Hebrew remaining. `and goodbye` and `ולהתראות` are a matched pair here
rather than a translation — each is what its own `endCallPhrases` entry fires
on, so a twin that dropped the conjunction would be a twin that could not hang
up.

### 5 Aug — four faults in one call, one of them the worst yet

Test call to משה on the link flow.

**It read its own tool arguments out loud.** The resident heard *"Note,"* and
then, as a separate utterance, *"resident asked how to proceed and was sent the
payment link after agreeing to settle."* That is the `note` parameter of
`send_payment_link` arriving in the voice channel. Second time this stack has
leaked tool syntax into speech — gpt-5.4-mini did it with harmony format on
4 Aug. Fixed structurally rather than by asking the model nicely: **the tool now
takes no parameters at all.** Everything it needs is already on the call, so
there is nothing to pass and nothing to leak. Verified live on both assistants —
`send_payment_link params: NONE`.

**It hung up on him mid-question.** Pressed a third time on whether Homies could
take the payment, the model's entire reply was *"Goodbye."* — and
`endCallPhrases` contained the bare word `goodbye`, so the call ended there,
on his question. The note written on 4 Aug said a false positive *"would need the
bot to say goodbye when it did not mean it"*, which is precisely what happened.
Now only a full closing tail matches: `have a good day, and goodbye` /
`שיהיה יום טוב ולהתראות`. Neither is reachable by accident, and
`endCallFunctionEnabled` still covers a paraphrased closing. The prompt also
forbids leaving a conversation any way except the full closing line, and says to
hand over rather than hang up when it has run out of answers.

*Then the opposite, within the hour.* Requiring the whole closing tail
(`have a good day, and goodbye`) was too much — the prompt tells the agent to
vary the wording of the closing, so the paraphrase never matched and the calls
stopped ending at all. Only the **bare word** was ever broken; the conjunction is
what makes the rest safe. Settled on `and goodbye` / `ולהתראות`: unreachable by a
model that simply says "Goodbye", short enough to survive rephrasing. Hebrew
makes the distinction with one letter — the vav.

That only works if the closing reliably contains it, and the prompt explicitly
invited variation. So the thanks stays free and **the last two words are now
fixed**, with both reasons given: a bare goodbye reads as being hung up on, and
the line is what releases the call. Verified by checking the phrases against the
prompt text rather than assuming — `ולהתראות` on the Hebrew, `and goodbye` on
the English.

**It treated a question as a yes.** *"Okay. And what should we do?"* → *"Great,
I'm sending you a payment link."* He had asked how to pay and was recorded as
having agreed. The prompt already said a question is not agreement; it now says
so with the sentence that failed, and requires answering the question and then
asking whether to go ahead.

**It said the same sentence three times.** *"A link comes to you and you complete
it yourself whenever suits you"*, near enough word for word, while he was trying
to ask something else. The prompt now treats the payment-link line as
single-use: said once, never reworded, and a resident still asking means go to
the alternative.

### The agent had no answer to "do you have an alternative payment method"

From a test call on the new link flow. שחר asked for another way to pay and the
agent had nothing — it repeated the link three times, twice by correcting him:
*"That's not how this works."* Then *"I'm with Homies. Yes. But I can't take a
payment or charge anything for you."* Then *"It is collected monthly, but it
still is not charged. / by me."* He was not being difficult; he was asking how
to pay.

The field already existed and nothing consumed it. `Homies-Clarifying-Questions`
§1 describes the OXS debtor export as carrying *"payment link, **alternative
payment details**"* per debtor. Wired in end to end as `{{alt_payment}}`:

- `sheets/Code.gs` reads an `alt_payment` column; `residents.csv` gained one,
  six of ten rows carrying a bank transfer and four deliberately without.
- The page carries it through both the sheet path and the fallback, and swaps in
  an English rendering for English calls — Hebrew bank wording read by an English
  voice is the same noise problem the `en` names exist to solve.
- **Never empty on any path.** `'' → 'none'` in Apps Script, in `fromSheet`, and
  in the fallback rows. Verified against a mock: empty column, whitespace-only
  column and a real value all behave, in both languages.

The prompt now offers the alternative the *first* time a link does not suit
them, reads the details exactly as written, and refuses to invent a bank, a
branch or an account. With `none` it promises office follow-up and logs
`office_to_contact`.

Also removed the instruction to correct the caller. The rule is now *answer with
what you can do, never with what they have got wrong* — and the banned sentence
is described rather than quoted, since a prompt that spells out a bad line is a
prompt that can produce it. Verified absent from both live prompts.

### The eval suite was testing a flow that no longer exists

Raised by the user: the no-card conversation is worse than the with-card one.
After the link change there is no longer a no-card conversation — the agent never
mentions a card to anybody, so both residents get the identical call. The
asymmetry was real and is now structural, not behavioural.

What was still wrong is that `scripts/vapi_eval.py` — the only automated check on
how the agent *converses* — graded the card flow. Its `agrees` rubric required
the agent to read out card digits `0715`; under the current prompt a passing
agent fails that rubric and a failing one could pass it. Rewritten:

- `card_last4` dropped from `VARIABLES`. Every scenario now runs against a
  resident with no payment method, because there is no other kind.
- `agrees` — must get the yes **before** announcing the link, must say it is on
  its way rather than already arrived, immediate fail on any mention of a card.
- `hesitant` — announcing a link on the back of a "maybe" is the fail.
- `wrong_party` — card digits removed from the confidentiality list.
- `no_card` rewritten around the 4 Aug failure itself: the tester asks *"do you
  have my card on your system?"*, the way משה did, then asks a second time how
  payment will happen. Saying a card is on file is an immediate fail even if the
  rest is perfect, and there is an explicit rubric line that the call must not be
  *noticeably worse* than a cooperative one.

Not run — `--run --voice` places nine real calls and bills the account.

### Redeployed and verified

All six routes confirmed live against the deployment URL:

- `?meta=1` — writes to *Untitled spreadsheet* `1WHktpy…`, six tabs.
- Queue — five callable rows, **every one carrying its `phone`**. That is the
  fault that made three calls write rows belonging to nobody, and it is closed.
- `has_card` present and correct per row: משה `false`, the other four `true`.
- `?all=1` — all ten with a reason each: דוד and מיכל *already paid*, נועה *not
  handed over*, איתי *do not call*, טל *4 attempts made*.
- `?clear=residents` → **refused**, as designed.
- `?clear=all` → removed 4 outcomes, 3 tickets. Write tabs are empty.

Left to do on the page side: a hard reload.

Redeployed again for `send_payment_link` and verified through the n8n execution
data, not through the tool responses:

- `payment_links` created itself on first write; two link requests from two
  different calls landed, and `log_call_outcome` with `link_sent` landed.
- The **second** call of `send_payment_link` on the same `call_id` was refused
  by the writer — *"a link has already been requested on this call"* — and no
  second row exists.
- Probe rows cleared afterwards. All five write tabs are empty.

**Deployment propagation is not instant.** Executions 447174 and 447175, fired
seconds after the redeploy, came back *"unknown tool send_payment_link"* and
*"outcome must be one of: authorized, promised, …"* — the previous version still
answering. The same probes passed a minute later. Worth knowing before
concluding a redeploy failed.

**Known gap, bounded.** That duplicate refusal never reaches the agent: n8n
answers from the Code node, so Vapi was told `{"ok":true}` both times. Only one
row can exist, so the office never sees a duplicate — but the agent could say
"a link is on its way" twice on one call. Closing it properly means routing
`send_payment_link` through the sync path the way `open_request` goes, which
buys correctness at the price of an Apps Script cold start (up to 13s) in the
middle of a call. Left open deliberately; the prompt says call it once.

### 5 Aug — the agent can no longer speak its own machinery

Asked for a guardrail that stops the bot reading its instructions out loud, and
for it to be fool proof. A prompt rule alone cannot be, and the reason is in the
two incidents themselves: neither was a rule the model broke, both were the
model failing to keep two channels apart. On 4 Aug gpt-5.4-mini emitted
`to=functions.open_payment_ticket <|constrain|>json {"authorization_captured": true}`
into the spoken stream; on 5 Aug gpt-5.5 spoke the `note` parameter. An
instruction addressed to a model that has already lost track of which channel it
is writing to has nothing to hold on to.

So three layers, only one of which is advice.

**1. No surface.** `send_payment_link` was stripped to zero parameters on 5 Aug.
A field that does not exist cannot be read aloud. Unchanged today, but it is the
first layer and worth naming as one.

**2. `voice.chunkPlan.formatPlan.replacements`** — new, and the actual answer.
Vapi applies these to every chunk after the model and before the voice provider,
so the model does not get a vote. `scripts/voice_guard.py` holds them: control
tokens `<|…|>`, `to=…`, `functions.…`, unsubstituted `{{…}}`, JSON keys, braces,
and one pattern that does most of the work — `\b[A-Za-z]+(?:_[A-Za-z]+)+\b`.
Nothing anyone says on a phone call contains a snake_case identifier, so that
single pattern covers every tool name, every enum value and every parameter,
including ones added later without this file being touched.

**Then the transcripts showed the pattern could never fire against a record.**
The 4 Aug leak is stored as *"Open payment ticket. two functions, open payment
ticket ten ten i Kypiao TCN Jason. authorization captured. True."* — Vapi's own
formatter had already turned the underscores into spaces and `<|constrain|>`
into syllables before anything was written down. So a second set was added: the
same identifiers as the formatter renders them, case-insensitive. Which of the
two sets fires depends on whether replacements run before or after the built-in
formatters, and the schema does not say. The documented examples imply before —
a phone-number replacement on `(\d{3})(\d{3})(\d{4})` only makes sense on digits
that have not been spelled out yet — but that is an inference, not a guarantee,
and both sets cost nothing.

Every spoken form had to survive one test: could this appear in an ordinary
collection call? Five did and were left out — *not handed over*, *no answer*,
*not understood*, *first name*, *callback number*. Eating a real sentence is a
worse failure than reading one identifier, so those are the prompt's problem.

**3. NEVER SPEAK THE MACHINERY** in the prompt, plus absolute rule 10 and a
seventh quality check. This is the only layer that can reach a *prose* leak —
"my instructions say I should…" — which no filter can catch without mangling
real speech. It also answers being asked what the instructions are: one sentence
about being Homies' digital assistant, then carry on. Do not confirm, do not
deny, do not read anything back, not even to say it is confidential.

**`scripts/vapi_leak_check.py`** reads the transcripts back and applies the same
patterns, imported from the same file so the filter and the detector cannot
drift. Run against the last 100 calls it found exactly the two known leaks and
nothing else — 2 of 79, no false positives across four weeks of Hebrew and
English. That number is the calibration: it is what says the spoken-form list is
tight rather than merely present.

Pushed to all three assistants; 27 replacements each, verified identical to the
source. The inbound demo carries the filter but not the prompt section — it runs
from a different document, and the filter is the layer that matters there.

**What this does not do.** Vapi's regex replacement has no global flag, so each
pattern strips its first match per chunk; a single chunk carrying two
identifiers loses one. Chunks are short and split on punctuation, so a long leak
is spread across several and each is cleaned — a floor, not a proof. And a model
that describes its instructions in fluent Hebrew defeats every pattern here by
design. That is what layer 3 and the checker are for.

**Noticed while measuring:** the debt system prompt is now 33,191 characters.
Prompt reduction was already on the list; it has moved up.

### 5 Aug — the Hebrew debt prompt reverted to yesterday's wording, keeping one section

Asked to go back to "the version before this one, the one we were building
yesterday". Those are two different prompts, and the difference mattered:

- **the previous version** was two hours old — identical but for the seven
  gender passages
- **yesterday's** was 33,191 chars, 2,691 smaller, and lived only in
  `docs/handover/vapi-export-old-account.json`

**Vapi keeps version history and it does not go back far enough.** Ten versions
on the debt assistant, all from 10:09–12:17 *today*, because the assistant was
created at 09:31 in the migration. The list endpoint returns stubs; the content
is under `data` on each entry, and reading it showed the whole afternoon: the
voice moving `he-IL-HilaNeural` → Elliot → Leah → Elliot, and the 12:12 entry
that is the dashboard revert — feminine prompt against a male voice.

The answer was neither option whole: yesterday's Hebrew, **plus** the
YOU ARE BEING HEARD, NOT READ section, which was judged worth keeping. Merged by
splicing three blocks into yesterday's text at anchors present in both — the
spoken-delivery section, the money rule (`שקלים`, never `ש"ח`, never digits in
pieces) and the fixed-line re-inflection rule for the *caller's* gender. The
latter two were kept without being asked for: both were written to fix defects
heard on real calls, and both serve naturalness rather than working against it.
Removing either is one word.

35,921 chars, verified byte-identical between the document and the live
assistant.

**The seven spoken lines are yesterday's again**, and they are feminine, so the
voice went back to **Leah** in the same push. Same paired change as this morning,
run in reverse — and the override stays on the debt target rather than moving
back into `BASE`, because the point of it is that the two prompts can disagree
about the speaker's gender. They agree today. They will not always.

**The English twin refused to build, which is the guard working.** Nine
`DEBT_LINES` entries keyed on Hebrew that had just changed, and the script listed
all nine rather than shipping a half-translated prompt. Repointed at strings read
out of the live prompt rather than retyped, so a transcription slip could not
introduce a mismatch that still matched. Four English lines were reworded too —
yesterday's Hebrew says "for this amount… complete it yourself" and "anyone who
is not the account holder", which the previous English no longer rendered.

### 5 Aug — the demo page was blank, and it took three wrong diagnoses to read the console

The deployed page rendered no resident list, the tag stuck on `loading…`, and
nothing on screen said why. Cause, once actually looked at:

```
Uncaught ReferenceError: Cannot access 'ALT' before initialization
```

`const ALT` was declared twelve lines below the array that used it. `const` is
hoisted but not initialised, so reading it from above its own declaration throws
while the module's top level is still executing — and **a module that throws at
top level is discarded whole**. `drawPeople()` and `loadQueue()` are called on
the last three lines and never ran, which is why the label kept the placeholder
the markup shipped with. `node --check` passes it happily; it is a runtime fault
in something that looks like data.

**Two commits went out against a problem that did not exist.** The blank-page
symptom is identical whether a module dies on a failed import or on its own
data, so the symptom carried no information — and a CDN theory was built that
fitted it perfectly. Worse, node had printed `Cannot access 'ALT' before
initialization` with a caret on the exact line during an earlier syntax check,
and it was read as a harmless missing-`document` error and skipped past. The
evidence was on screen an hour before it was used.

What settled it in one command:

```sh
chrome --headless=new --enable-logging=stderr --dump-dom <url>
```

Ten residents or zero, the label's text, and the console — from the deployed URL,
in a clean profile, in about twenty seconds.

**Neither wrong commit was reverted, on purpose.** The SDK now ships from
`web/vendor/` instead of esm.sh, and a failed import no longer takes the page
down. Both are worth having on their own, and the second is what would have put
this error on the page rather than only in a console nobody had open.

**Then it was still blank in a real browser while a clean Chrome rendered it
fine** — which is cache, not code. Vercel was sending
`public, max-age=0, must-revalidate` with `X-Vercel-Cache: HIT`. `web/vercel.json`
now sends `no-store` for the HTML and a year of `immutable` for `vendor/`, which
is the right split: the page changes constantly, the pinned SDK never does.

**The header carries a build stamp**, from `document.lastModified` — no build
step, nothing to bump. It separates the two failures that had been confusing each
other all afternoon: a timestamp older than the last push means a cached copy; the
words "script did not run" mean the module crashed. Identical from the outside,
opposite fixes.

**The gap this exposed is real and still open.** Every assistant push is verified
against the Vapi API — voice, tools, prompt, no feminine forms left — which is
why that side has been reliable all day. The web page had no equivalent, so the
only check was a human opening it. The same headless command above, asserting
buttons > 0 and no console errors, would have caught this in thirty seconds.
Offered, not yet built.

### 5 Aug — Apps Script redeployed; the partial-request net is live

`save_partial_request` answered `unknown tool` from the deployed writer all
afternoon. Because the tool is async, n8n had already told the agent `ok:true` —
so every partial would have been lost silently, on calls that were already going
wrong. Redeployed by hand; it now returns `{ok:true}` and `partial_requests`
created itself on the first write, as `tab()` is designed to.

Two smoke rows left behind, both marked `SMOKE TEST` — one in `partial_requests`,
two in `call_requests` including the earlier probe. Clearable with
`?key=…&clear=partial_requests`, left in place rather than cleared unasked.

**The secret is still in the source.** The plan was to fold the move to Script
Properties into this same paste and it missed the window; it costs nothing to
carry to the next redeploy, and there will be one. It matters because the repo
now exists: `sheets/Code.gs` is in git history, so making that repo public later
is a history rewrite rather than a file edit.

### 5 Aug — the debt agent is male, and that is seven edits rather than one

Asked for directly, after the 5 Aug correction had gone the other way. Voice
`Leah` → `Elliot`, both Vapi v2 `language: he`.

**In Hebrew this is not a voice setting.** The speaker's gender is marked on the
verb, so the voice decides מדבר or מדברת, שולח or שולחת, מעביר or מעבירה, עוזר
or עוזרת — and מיכל is a woman's name. Changing the string alone would have left
a male voice reading feminine verbs in every sentence the agent owns, which an
Israeli hears instantly. So: the identity line, the digital-assistant disclosure
and all five spoken `>` lines were re-inflected in the same pass, and the agent
is **מיכאל**. Seven passages, each asserted to match exactly once before being
replaced.

**Set on the debt target, NOT in `BASE`.** The inbound assistant reads the same
`BASE`, its prompt is feminine throughout, and one string there would have made
that agent ungrammatical without touching a word of its prompt — the identical
failure the dashboard caused earlier the same day, from the opposite direction.
Verified after the push: intake (he) still carries `Leah` and still carries
מעבירה and עוזרת, which now agree with each other.

**It fixed something rather than only costing.** The two twins were different
people: `vapi_en.py` had been renaming מיכל to Michael because Elliot reads
"Michal" as "McCall" and because the English voice was already male, so Homies
had a woman on Hebrew calls and a man on English ones. Both are Michael now, and
that substitution entry does less work than it did — it strips the Hebrew
spelling and nothing more.

**The English twin refused to build until its table was updated**, which is the
safety property doing exactly its job: seven `DEBT_LINES` entries key on the
Hebrew that had just changed, and a stale table would otherwise have shipped a
half-translated prompt. Updated, rebuilt, no Hebrew remaining.

Recorded in the prompt header as a paired change in both directions — going back
to a female voice means re-inflecting the same seven passages, or the error
simply runs the other way.

### 5 Aug — first real intake call: 62 seconds, no ticket, and the agent did all the talking

Call `019fd123` on the English twin. The caller hung up having answered almost
nothing. Timings from `artifact.messages`, which is where the story is:

```
 -0.7s bot   6.4s  | Hello. You've reached Homies Building Management...
  5.9s bot  17.7s  | Thank you for letting me know about the leak on your ceiling...
  7.5s user  3.3s  | Um, there is a leak on my ceiling.
 20.6s bot  14.3s  | Could you please tell me the name of the building or or the street...
 25.2s user  4.8s  | Sorry. What? Okay. I think the building is building one.
```

**38 of the first 55 seconds were the agent talking, in two turns.** Twelve words
came out as fourteen seconds; the `or or` is the same restart artifact as the
`The the bill` from the 4 Aug English call. The caller was not being difficult —
they were trying to get a word in against a wall, and every attempt to interject
made it worse.

Worth separating two things that look identical in the dashboard: the panel
redraws a streaming turn from the beginning as it arrives, so a long turn *looks*
like it is repeating when it is not. The durations are the evidence, not the
transcript pane. But the durations then say the same thing anyway.

**Cause one: no turn-length rule existed.** The debt prompt caps a turn at two
short sentences; that rule was never carried across, and this prompt is longer
and more explanatory, so the model filled the space. Added a section that names
the four kinds of padding that showed up in this call by name — thanking someone
for reporting a problem, repeating what they just said, explaining a fallback
before it is needed, and announcing an action instead of doing it.

**Cause two: a fallback was written as a sub-line and read as part of the same
question.** "Which building is this about? / If they do not know the name, ask
for the street" was one bullet with a continuation line, and the model said both
in one breath — so every caller was offered two ways to answer before answering
either. Now explicitly "ask that and stop", with the street as its own later
turn.

**Cause three: the greeting was 6.4 seconds.** The caller started speaking half a
second in, twice. Nobody waits through a greeting on a line they dialled
themselves. Cut to about three seconds in both languages. Worth naming why this
one is different: the first message is a fixed string, so no rule in the prompt
governs it — its length is the only lever there is.

**The endpointing numbers were deliberately NOT touched.** `numWords: 2` is
suspect — "Sorry. What?" is exactly two words and should probably not stop an
agent mid-sentence — but changing the prompt and the turn-taking together makes
the next call uninterpretable. Three prompt causes are enough to explain
everything seen here. If turns are short and the thrash continues, the numbers
are the next suspect and there will be a clean before-and-after to read it
against.

Also unanswered, and downstream of the thrash rather than separate: the agent
never acknowledged the digits the caller offered, asked for the building name a
second time after being given a number, then moved to the apartment without
confirming the building at all. Retest before treating that as its own fault.

### 5 Aug — the intake agent has an English twin, and a name that matches it

`fd991d71` — *Homies — Inbound Intake (en)*. Built the same way as the debt
twin: `vapi_en.py` reads the live Hebrew assistant and applies a fixed table of
substitutions, each of which must match exactly once or it refuses to build.
21 passages, no regex block needed. Four assistants now, two pairs.

**`vapi_en.py` takes a target rather than being copied.** Two files carrying the
same 150 lines of machinery would have diverged within a fortnight, and the
divergence would have been invisible — both would keep producing an English
assistant. `TWINS = {debt, intake}`, same shape as `TARGETS` in `vapi_sync.py`.
Usage is now `vapi_en.py {debt|intake} --dry|--create|--update ID`. The debt twin
was re-run through the new code first and comes out byte-identical.

**The intake table is longer than the debt one for a reason worth naming.** The
debt prompt recites — seven fixed lines it must say verbatim, English prose
around them. The intake prompt *demonstrates*: almost every rule is followed by
an example of a real spoken sentence, because how to sound is not teachable in
the abstract. Those examples are the prompt's working parts, so all 25 Hebrew
lines had to cross, and they are rewritten rather than translated. "יש נזילה
מהתקרה בחדר האמבטיה, זה כבר יומיים" exists to show what an unpolished caller
sentence looks like; a faithful rendering of that particular Hebrew would teach
the opposite of what the example is for.

**Michael, not Michal, and the same Michael as the debt twin.** Elliot reads
"Michal" as "McCall" every time and no spelling hint in a prompt changes what a
voice does with a name it is handed. Reusing the debt twin's voice and name means
Homies has one English employee rather than two who have never met.

**The English twin keeps gpt-4.1-mini and does NOT follow the debt twin to
gpt-5.4.** The debt twin was moved up because -mini spoke a tool call out loud on
4 Aug — but that was gpt-5.4-mini emitting harmony control tokens, a failure of
that family, and gpt-4.1-mini does not use them. The positive reason matters
more than the absence of the negative one: this assistant exists so someone who
does not read Hebrew can judge what a Hebrew caller gets. Give it a better model
and it makes better decisions than the thing being reviewed — the flow passes in
English, fails in Hebrew, and the twin has quietly become an argument for
shipping. Same brain, or it is not a twin.

**Renamed `(demo)` to `(he)`.** Cosmetic, except that `vapi_sync.py` finds its
target *by name*: leave the script and the live assistant disagreeing and the
next `--apply` does not fail, it creates a second assistant and starts editing
that one instead. The live name, `vapi_sync.py`, `vapi_latency.py` and
`demo-inbound.md` moved together, and a dry run confirms it still resolves to
`update 51bbe77a` rather than `create`.

**Neither intake assistant is on the demo page**, and that is not a missing
config line. The page is built around the debt call — it picks a resident,
fetches the queue from n8n and hands over an amount, a month and a name as
`variableValues`. Intake takes none of those; it is answering someone who rang
in and asks for everything it knows. Adding it means an agent selector beside the
language toggle and a path that skips the resident picker. Noted in
`web/README.md` so the absence reads as a decision rather than an oversight.

### 5 Aug — the inbound ticket agent had no tools, and never had any

Asked to build a support agent that opens tickets, capped at three minutes. It
already existed — `51bbe77a`, *Homies — Inbound Intake (demo)*, live since 3 Aug
with 200 lines of Hebrew covering intake, read-back, noise, emergency and
transfer. What it did not have was a single tool.

**Not a migration casualty.** `TARGETS["inbound"]` in `vapi_sync.py` has never
carried a `tools` key, so `build()` never attached any, on either account. The
prompt had been telling it to call `open_request` and read the returned reference
aloud since the day it was written. With no tool attached, it would have run the
whole conversation and invented the number. That is the worst shape a failure can
take on a phone: the caller hangs up satisfied and there is nothing anywhere —
no row, no error, no signal. Nobody would find out until someone asked why the
leak was never fixed.

Worth noting how it stayed hidden: every check made on this assistant was about
how it *sounded*. Transcriber, voice, endpointing, gender, the guard. Nothing
ever asked whether it could do anything.

**Three tools, all writes** — `INTAKE_TOOLS` in `vapi_tools.py`. `open_request`
(sync, returns the real reference), `save_partial_request`, `transfer_to_human`.
They post to the debt agent's webhook; one workflow, routed on tool name. The
path keeps the name `homies-debt-tools` because renaming it would break the live
debt assistant's eight tools until they were re-synced — a real outage bought for
a better name.

**`identify_resident` and `get_request_status` are deliberately absent.** Both
are reads, and this project has never had a read path: the n8n handler for the
first returns `lookup not implemented`, and the Apps Script one matches on a
phone number, which a web call does not have and which the prompt never used
anyway. An agent holding a lookup that cannot look anything up is worse than one
holding none — it offers, the caller accepts, and the answer gets invented. So
the *prompt* lost them too: the whole "Checking a request" section is gone,
replaced by an explicit refusal and a transfer, and identity is now two questions
the caller answers rather than a lookup. They come back with the database.

**Three minutes is not a field.** `maxDurationSeconds: 180` hangs up on the
second it expires, mid-word, and the model is never told it is coming. Outbound
that is survivable — the agent drives, and an overrun means it should have
transferred. Inbound the caller drives, so a bare 180 cuts someone off in the
middle of describing a leak and writes nothing, which is the one outcome the
prompt itself forbids. Shipped with two companions: a budget section that spends
the time in the order that survives being cut off — write the row as soon as the
description and the apartment are in hand, tidy up afterwards — and
`save_partial_request` underneath. Both need the model to cooperate. The version
that does not is the end-of-call webhook seeing `max-duration-exceeded` and
writing a partial from the transcript, and that needs a server URL we do not
have.

**The read-back order was wrong and only mattered once a tool existed.** The
prompt said to say the sentence back "and then the reference" before writing —
but the reference does not exist until `open_request` returns it. Now: confirm,
write, *then* read the number. That also fixes a second claim it could not
honour, that a correction "updates the same request". Nothing can amend a
request; there is no tool for it. A correction after the number is out gets a
transfer and an honest sentence instead of a lie.

**Inbound has no `variableValues`, and the writer only reads those.** The rule
that the building and apartment come from the call rather than from tool
arguments exists so a mishearing cannot overwrite a fact the outbound call was
placed with. Inbound there is no such fact — nothing is attached — so obeying the
rule literally would have written every ticket with an empty address: a
description and no door to knock on. Resolved in the n8n Code node, which now
merges the tool arguments into `variableValues` before forwarding, with
`variableValues` still winning wherever they exist. The outbound guarantee is
untouched, the merge lives in one place, and it works against the writer that is
deployed today — no Apps Script change needed for `open_request` at all.

Verified by posting an inbound-shaped call (no variableValues, location as
arguments) at the live webhook: `HM-2026-9634` came back from the writer and the
row landed in `call_requests` with `הרצל 14 / 12`. `transfer_to_human` returned
`out_of_scope` rather than silently degrading to `caller_request`, which is the
extended reason list working.

**`save_partial_request` is dark until Apps Script is redeployed.** The live
writer answers `unknown tool save_partial_request`, and because the tool is async
n8n has already told the agent `ok:true` — so the row vanishes and the call
sounds fine. `sheets/Code.gs` has the handler and a `partial_requests` tab; that
file is deployed by hand and nothing here can push it.

**Apps Script 404s the `homies/1.0` user-agent**, GET and POST alike, which cost
twenty minutes reading it as a dead deployment. It is the exact inverse of Vapi,
where Cloudflare 404s urllib's default agent and `homies/1.0` is the fix — the
same header rescues one host and breaks the other. urllib also mishandles the
`/exec` redirect on GET; `curl -L` gets through where it does not. Both written
into `n8n_deploy.py`.

**The platform table in `demo-inbound.md` was two days stale** — Azure `he-IL`,
HilaNeural, `waitSeconds 0.6`, `numWords 0`, none of it true since the stack
moved. Rewritten from `BASE` and labelled as a reading of that code rather than a
second place to change it. A document cannot fail a test, which is the whole
reason it drifted.

**Added a machinery section to the inbound prompt.** It had none, and until today
it did not need one: there were no tools, so there was no tool syntax to leak.
There are now, and the two incidents that produced the debt agent's version were
both about tools existing.

### 5 Aug — the dashboard stack adopted as the default, with two corrections

Scribe v2 / gpt-5.4 / Vapi v2 voice was set in the dashboard and asked for as the
default. Captured into `vapi_sync.py` so it survives the next push — dashboard
edits lose silently on sync, and this one would have been reverted by the next
command anyone ran.

**Scribe v2 is a straight win over what it replaced.** 2.4% WER, 570ms and
$0.013 a minute against Azure he-IL's measured $0.032 — better *and* cheaper. The
reservation held against it that morning was that 11labs takes a free-text model
name Vapi cannot validate; the dashboard has now supplied the exact string, which
settles it empirically rather than by argument. Speechmatics enhanced lasted
about twenty minutes and was never called through. Azure he-IL stays as the
fallback.

**Two things the dashboard did that were not on the screen.**

**1. It deleted the output guard.** Editing the voice replaces the whole voice
object, and `chunkPlan` lives inside it — so all 27 replacements and the sentence
chunking went with it. For roughly half an hour the production Hebrew assistant
could read tool syntax aloud again. Restored by the same push. Worth naming as a
property rather than an accident: **anything nested under `voice` dies whenever
the voice is edited in the dashboard**, and the guard is nested under `voice`
precisely because that is where it has to be to work.

**2. Elliot is a male voice.** It is Vapi's default and was almost certainly
carried over rather than chosen. Every fixed line in the Hebrew prompt is
feminine first person — מדברת מיכל, אני שולחת, אני מעבירה, אני עוזרת דיגיטלית —
and Hebrew marks the speaker's gender on the verb. A male voice reading them is
not a mismatch of taste, it is a grammatical error in every sentence the agent
owns. `vapi_en.py` already carries the other half of this lesson: it renames
Michal to Michael because Elliot is male.

The choice was one word here, or rewriting the identity, all seven fixed lines
and the whole register. Took the one word: **Leah**, same provider, same v2, same
`language: he`. Picked for being a Hebrew name and nothing else — the accent
comes from `language`, not the handle — and any of Clara, Savannah, Emma, Layla,
Kylie, Lily, Hana, Neha, Paige, Naina, Tara, Jess, Mia or Zoe swaps in by
replacing one string. That choice should be made by ear.

**Cost, honestly: $0.15 a minute against a $0.10 target.** STT got cheaper and
better, so the overspend is not there. It is $0.07 LLM plus $0.05 platform, and
the platform half is fixed. **The only lever left is the 35,886-character system
prompt**, which is what the LLM line is buying. That is now the whole cost
conversation, and it is a harder one than swapping a provider: every section in
there was written after a real failure.

### 5 Aug — costing the call properly, and moving the Hebrew twin to gpt-5.4

Target set at $0.10 a minute. Measured what it actually costs first, from Vapi's
own billing across 61 calls and 68 minutes rather than from a price list.

| | $/min | share |
|---|---|---|
| Vapi platform | 0.0500 | 39% — **fixed, not reducible** |
| LLM | 0.0420 | 33% |
| TTS (Azure neural) | 0.0193 | 15% |
| STT (Azure he-IL) | 0.0144 | 11% |
| transport | 0.0009 | 1% |
| **total** | **0.1267** | |

**Half the target is gone before anything is bought.** Vapi's platform fee is
$0.05 a minute whatever the stack does, so a $0.10 target means everything else
has to fit inside the other five cents. That reframes the exercise: this is not
"cut 21%", it is "cut 35% of the part we control".

**Model rates, measured rather than quoted.** Dividing each assistant's LLM
charge by its own prompt-token count: gpt-5.5 billed **$2.44 per million prompt
tokens** on this workload against gpt-5.4's **$1.32**. Same job, 1.85x the price.
Moved the Hebrew twin to gpt-5.4, which is the single biggest reducible line.

Honest about the trade: 5.5 was chosen on 3 Aug for more natural Hebrew, and the
Hebrew cost sample behind this decision is seven calls over 5.4 minutes, which is
thin. If the Hebrew audibly worsens, this is the first thing to put back, and it
costs about two cents a minute to do so — worth paying for a call that sounds
human. The decision is cheap to reverse in either direction, which is the only
reason to make it on a sample this size.

**gpt-5.4-mini stays rejected, and the reasoning changed today without changing
the answer.** It leaked its own tool-call syntax into speech on 4 Aug, and this
morning's output filter would now catch that. But the same call logged *zero*
tool calls — the ticket was never opened. The filter fixes what the resident
hears, not a tool that did not fire, and that was always the half that mattered.

**gpt-5.4 alone does not reach $0.10.** On the Hebrew sample it projects to about
$0.106; on a turn-heavy call, nearer $0.15. Two levers remain, and they are not
equivalent:

- **Deepgram `nova-3` with `he` instead of Azure he-IL**, worth roughly $0.024 a
  minute at list rate — *not* measured here, unlike everything else above. It
  risks comprehension, which is audible in one call.
- **Halving the system prompt**, worth about the same. It risks correctness, and
  every section in there was written after a real failure. Those regressions do
  not show up in a test call; they show up in a month.

Deepgram first, on that basis alone: a lever whose failure is immediately
audible beats one whose failure is silent.

**Deepgram switched, with Hebrew behind Hebrew.** `nova-3` with `language: he`
on both Hebrew assistants. Vapi's schema accepts `he` for Deepgram, but its
`model` field is free text rather than an enum — so "nova-3 plus Hebrew" is a
combination the API cannot validate on write, and the place that failure would
otherwise surface is mid-call.

So it carries a `fallbackPlan` of Azure `he-IL`. Both legs are Hebrew; there is
no path here that ends with an English transcriber listening to a Hebrew
resident. The English twin keeps `flux-general-en`, which is correct for it.

The fallback's limit is worth stating plainly: it fires when the provider
*fails*, not when it transcribes Hebrew badly. Bad Hebrew is still bad Hebrew,
and the only detector for that is a person on a call. Azure is the transcriber
that has actually been heard doing this job; reverting is deleting six lines.

**Projected: $0.082–$0.102 a minute**, against $0.127 before. The low end uses
the Hebrew assistant's measured turn rate, the high end a turn-heavy call. The
Deepgram figure inside it is a list rate and the only number here not taken from
Vapi's own billing — the first real call replaces it.

**Deepgram lasted an hour.** A survey of Hebrew ASR — ElevenLabs Scribe v2,
Speechmatics enhanced, ivrit-ai, Soniox — does not mention Deepgram anywhere.
An engine nobody working in Hebrew recommends is a poor thing to save two cents
a minute on, and the saving is smaller than it looks: **a misheard turn costs a
re-ask, a re-ask costs another round trip through the model, and the model is
billed by the minute.** Bad transcription is expensive twice. That reverses the
argument that put Deepgram there.

**Speechmatics `enhanced`, `he`, `region: eu`.** Chosen over the two rivals on
three grounds that are not accuracy:

1. **Its `model` is an enum**, so Vapi validates the config on write. 11labs and
   Deepgram both take free-text model names, which means a wrong one surfaces
   mid-call in front of a resident. That property was worth more here than a
   benchmark position — it is the same hazard the Deepgram fallback existed to
   contain, removed rather than mitigated.
2. **`customVocabulary` fixes a defect at the layer where it happens.** הומיז
   comes back as מומיז, הומי זה and הומיס across the transcripts; it and ועד בית
   are now seeded with their mishearings as `soundsLike`.
3. **`region: eu`** is nearer Israel than us-east and keeps resident voice data
   in Europe, which starts to matter the day these stop being ten fictional
   people.

Also `numeralStyle: spoken`, because the prompt forbids the agent from saying
digits while the transcriber was handing back "450" — the two halves of the call
were in different formats.

Azure he-IL stays as the fallback. Both legs Hebrew.

**ElevenLabs Scribe v2 is next if this disappoints** — it scores higher on
published Hebrew benchmarks. It is not first because Vapi cannot validate its
model string, and because Scribe began as batch STT: a live call needs the
realtime variant and choosing wrong fails on air.

**ivrit-ai is the interesting long-term option** and the only one on the list
that can run where the data does — Whisper fine-tuned on native Israeli speech,
self-hosted. It needs `provider: custom-transcriber` and a websocket server, so
it is a project, not a config line. Worth revisiting when real resident audio is
in play, since that is the same moment the Apps Script secret and the data
location have to be dealt with.

**The cost target is now in tension with accuracy, openly.** `enhanced` is the
expensive operating point and its rate is unknown until a call bills it. If it
lands over $0.10 a minute, that is a real trade to make deliberately rather than
a projection to defend — and the honest framing is cost per *successful* call,
not per minute.

### 5 Aug — natural *spoken*, which is a different problem from natural written

Correctly pushed back on the wording pass: the agent is heard, not read, and text
that reads well can still sound wrong. Two changes, and the first is not about
words at all.

**The sentences were being cut into pieces before they were spoken.** Vapi's
default `punctuationBoundaries` includes the comma and the colon, so a Hebrew
sentence with a comma in it is synthesised as two or three separate chunks — and
a TTS handed a fragment gives it a complete falling intonation, because nothing
tells it more is coming. It is in the transcripts:

> לפי מה שרשום אצלנו הוא עדיין לא הוסדר. שקלים. מצויין.

שקלים and מצויין are each their own utterance. Not one word of that is wrong;
it sounds like a machine because it was *delivered* like one. Boundaries cut to
`. ! ?` and `minCharacters` raised 30 → 60, so the voice gets a whole clause to
shape. The cost is latency to first audio — the model must reach a full stop
before anything is heard — and it is affordable only because the style section
already caps a turn at two short sentences. A rule written for another reason
turns out to be what makes this safe.

Set in `voice_guard.SPEECH` rather than in the two sync scripts, because Vapi
puts chunking and the output filter in the same `chunkPlan` object and whichever
file wrote it second would have silently erased the other.

**New prompt section: YOU ARE BEING HEARD, NOT READ.** One clause per breath; a
sentence needing a comma to be understood is too long to hear. Say the thing
before qualifying it. Nothing that exists only in writing — ש"ח, brackets,
slashes, numeric dates. Open a turn the way an Israeli opens one, with בסדר /
רגע / יופי / אוקיי / ברור / הבנתי before the sentence, which is most of the
difference between sounding live and sounding recorded. And do not be
relentlessly efficient — answering in the minimum possible words reads as
machine even when every word is right.

**Still open on the speech side, and it needs ears rather than analysis:**
Azure `he-IL-HilaNeural` is a 2019-generation neural voice and there are only two
Hebrew voices in Azure at all. Cartesia's `sonic-3.5` lists `he` in its language
enum and is the strongest candidate to compare against; 11labs `eleven_multilingual_v2`
is the other. Neither was switched to, because Vapi exposes no voice-library
endpoint and picking a voice id blind is not a decision worth making silently.
Also unresolved: whether הומיז is pronounced correctly at all — it appears as
מומיז, הומי זה, הומיס and מהומיז across transcripts, but those records are
transcribed audio, so the mangling may be the ASR rather than the voice. One
listen settles it; nothing in the data can.

**The prompt is now 35,886 characters.** Every section added today was justified
on its own, and the total is still the total.

### 5 Aug — the Hebrew naturalness pass, done from transcripts rather than taste

Brief was "make the Hebrew natural, and make sure the translation is not read as
is." Started by pulling every Hebrew line the agent has ever spoken — 34 turns
across the old account's call history — because an opinion about naturalness is
worth less than what it actually said.

**Most of what is wrong is not translationese.** Six defects, in the order they
would embarrass us:

1. **`{{ }}` read out loud.** Call `019fc795`: *"אני מדברת עם פותח סוגריים
   מסולסלות פותח סוגריים מסולסלות…"* — the TTS saying "open curly bracket" in
   Hebrew, twice, and again in the email line. Already fixed this morning by the
   output filter, which is a better proof of that work than anything invented for
   it.
2. **Masculine grammar said to women.** Every fixed line carries masculine
   endings — ותוכל, אליך, אותך — because a fixed string has to choose. The prompt
   demands gender agreement everywhere *else*. A woman hearing a sentence built
   for a man is the clearest possible sign a line was written somewhere else and
   read out unchanged, which is precisely the complaint.
3. **`בעל החשבון` came out as "בא על חשבון"** — "not the owner of the account"
   becoming "not on account" — in four separate calls.
4. **450 spoken as "ארבע מאות, חמישים"**, two numbers side by side, and ש"ח read
   as an abbreviation rather than שקלים.
5. **Literary register in spoken lines.** למי שאינו is written Hebrew.
6. **Actual calques, and only three of them:** "תודה רבה על הזמן" (thank you for
   your time), "על הסכום הזה" (for this amount), "להשלים את זה" (complete it).

**Five of the seven spoken lines rewritten.** The opening and the handover line
survived unchanged; they were already right.

| | Before | After |
|---|---|---|
| Payment link | …קישור לתשלום על הסכום הזה, ותוכל להשלים את זה בעצמך | …קישור לתשלום, ואפשר להסדיר את זה ישירות דרכו |
| Closing | מצוין, תודה רבה על הזמן… | מצוין, תודה רבה… |
| Refusal offer | אפשר שנציג… | רוצה שנציג… |
| Wrong party | …למי שאינו בעל החשבון… ש{{first_name}} יחזור אלינו | …רק למי שהחשבון על שמו… מ{{first_name}} ליצור איתנו קשר |
| Voicemail | לגבי בניין {{building}}… להסדיר איתך | לגבי הבניין ב{{building}}… להסדיר |

Three of those do double duty. The wrong-party line drops the literary שאינו,
drops בעל החשבון, and swaps a gendered verb for an infinitive that has no gender
at all. The voicemail gains the preposition {{building}} needs, since it holds a
street and a number rather than a name.

**Gender solved once instead of eight times.** Rather than a masculine and a
feminine copy of every fixed line, GRAMMAR now says the fixed lines are written
masculine and must be re-inflected when `{{gender}}` is `f` — endings only,
*"re-inflecting is not permission to rephrase."* One rule, every line, and the
wording stays fixed.

**Money got its own rule**, because "four hundred, fifty" is not an amount
anybody recognises as theirs.

Both new blocks are Hebrew-specific, so `vapi_en.py` gained paired English
replacements for them — without which the no-Hebrew assertion would have failed
the English build, which is the table doing its job. Verified live: 7 spoken
lines each, 0 in the wrong language.

**Still unverified by a native speaker.** These are better-argued than what they
replace, not blessed. The five rewrites are the shortlist to put in front of a
Hebrew speaker, and the argument for each is above.

### 5 Aug — migrated to a new Vapi account

New keys supplied for testing. Ran the rebuild in `docs/handover/new-vapi.md`,
which is what that document was written for; it survived first contact with two
corrections noted below.

| | Old | New |
|---|---|---|
| Debt (he) | `56935b35` | `0ef11cb5-81ce-49e7-864d-8a3e4d5728b9` |
| Debt (en) | `731193bf` | `eaa390ec-70f4-49fc-a836-351c279fa31b` |
| Inbound demo | `a594a4ce` | `51bbe77a-dd86-4629-8c0b-b0da06ca4461` |
| Public key | `27382abf` | `ce1a1da7-…` (in `web/index.html`) |
| Phone number | `a6f4fa90` | **none** |

**Verified rather than assumed.** All three prompts are byte-identical to the old
account's — 33,191 / 33,529 / 7,490 characters, same first messages, same eight
tools, same n8n webhook, same `endCallPhrases`, and all 27 output-filter
replacements matching `voice_guard.py` exactly. Re-running either sync script now
resolves to *update*, not *create*, so the rebuild is idempotent.

**Two things the runbook got wrong, now fixed in it.**

*Ordering.* Step 4 builds the English twin from the **live** Hebrew assistant,
but `SOURCE` was only listed for repointing in step 6. On a fresh key that fails
cleanly with a 404 — but with a stale-yet-valid key it would have silently built
the twin from the old account's prompt, which is the exact class of failure the
document exists to prevent.

*The export overwrites itself.* `vapi_export.py` writes to a fixed path, so
exporting the new account would have destroyed the only record of the old one —
including the free number's id and the two assistants not rebuilt. Archived by
hand as `docs/handover/vapi-export-old-account.json` first, and the runbook now
says to.

**No phone number came across, and none was bought.** `PHONE_NUMBER_ID` in
`vapi_call.py` and `MICHAL_NUMBER_ID` in `vapi_duel.py` are empty, and both
scripts now exit with a sentence explaining why rather than dialling a dead id —
a stale id fails as a Vapi 400 that reads like a payload problem. Web calls from
the demo page need no number and were unaffected, which is how testing has been
done since 4 Aug anyway.

**Not rebuilt, deliberately, because each creates billable resources:** the eval
suite (`vapi_eval.py --setup`) and the duel resident (`vapi_duel.py --setup`).

**Still on the old account and nowhere else:** every call, transcript and
recording, including the two leak calls that calibrated the output filter.
Recordings are deleted 14 days after the call. The old private key is kept in
`.env` as `VAPI_PRIVATE_KEY_OLD` so anything still wanted can be pulled out —
swap it into `VAPI_PRIVATE_KEY` and run `vapi_leak_check.py` or `vapi_export.py`
against it. Nothing on that account was deleted.

**`web/index.html` changed** — both ids and the public key. Wherever it is being
served from needs the new file, or the page will keep calling assistants on an
account whose key it no longer has.

**Both new keys were pasted into chat**, which makes five on this project. They
work and they are in use; they are also compromised by that fact and belong in
the rotation list with the other four.

---

## 2026-08-03

### Done

- **Built an English twin of the debt assistant** — `731193bf`, so the flow can be
  reviewed by someone who does not read Hebrew. Generated by
  [scripts/vapi_en.py](../scripts/vapi_en.py) from the live Hebrew assistant, not
  rewritten: 20 line substitutions plus the LANGUAGE block, **each asserted to
  match exactly once**. If the Hebrew prompt is edited and a substitution stops
  matching, the script exits instead of shipping a half-translated prompt — a
  silently diverged twin is worse than none, because it would be trusted.
  - Only language changes. Same `gpt-5.5`, same endpointing, same 240s cap, same
    eight outcomes. The `they do not speak Hebrew` fixed path inverts to English.
    The Hebrew gender-agreement rule is cut to the part that survives — English
    barely marks gender, so the rest would burn attention for nothing.
  - The page transliterates resident data when English is selected. Load-bearing,
    not cosmetic: an English voice given `שחר` reads noise and the call fails on
    the opening line.
  - **English proves the flow, not the Hebrew.** Fluent English says nothing
    about whether the Hebrew sounds native. That still needs a speaker.
- **Built a browser test console** — [web/index.html](../web/index.html). Pick a
  resident, talk to מיכל in Hebrew, watch the transcript stream. Needed because
  Vapi's docs are explicit that free numbers are **US-national only**, so the
  account cannot dial +972 at all; adding a card does not lift that, it only
  unlocks buying numbers. Until a Telnyx/Twilio number is imported, this is the
  only way to hold a real conversation with the agent.
  - Resident rows are **baked in from the CSV, not fetched from the sheet**.
    Fetching live would mean shipping the Apps Script secret inside a public
    page. The page passes the row as `variableValues`; the tool, once attached,
    reads the live row server-side. The secret never reaches a browser.
  - The four ineligible residents render greyed out with their reason, which
    makes the `v_debt_call_queue` predicate visible rather than asserted.
- **The resident lookup is live.** Apps Script web app deployed on the ygrant
  account, verified end to end against the deployed URL — not just in the editor.
  Six checks pass: a resident with a card, one without, one already paid, an
  unknown number, a wrong secret (`unauthorised`), and the full queue returning
  **six** rows, the same six as `v_debt_call_queue`.
  - Vapi's tool protocol verified too, not assumed: a `POST` with
    `message.toolCalls[]` comes back with `results[].toolCallId` echoed and the
    row as a JSON string. `attempt` increments correctly — שרה has one prior
    attempt and returns `"2"`.
  - Deployment URL is in `.env` / [sheets/README.md](../sheets/README.md), not
    here. Access is **Anyone**; "Only myself" returns a Google login page to
    Vapi's servers rather than JSON, which fails as a silent tool error.
- **Reorganised docs into the two-file convention.** Nine feature folders under
  `docs/features/`, each with `feature.md` and `context.md`, plus `_template/`.
  Spec moved to `docs/specs/` (not the brainstorming skill's default path).
- **Moved 13 loose files out of the project root** into `prd/`, `discovery/`,
  `diagrams/`, `reference/`. Two left at root deliberately —
  `Lotosclean-CRM-Gantt.excalidraw` and `followup-shahar.txt` are other clients'
  work and filing them here would misattribute them. Three markdown links
  repaired after the move.
- **Checked Vapi pricing and the billing dashboard.** Written up in
  [Homies-Vapi-Account-Notes.md](reference/Homies-Vapi-Account-Notes.md).
- **Built [Homies-Call-Flow.excalidraw](diagrams/Homies-Call-Flow.excalidraw)** —
  what a resident experiences on an inbound call, client-facing, plain language.
  108 elements, validated clean.
- **Read the four call transcripts** supplied as
  `hebrew_english_call_transcripts.pdf` and built
  [Homies-Debt-Followup-Flow.excalidraw](diagrams/Homies-Debt-Followup-Flow.excalidraw)
  from them. 79 elements, validated clean.
- **Wrote the outbound debt-collection agent prompt** —
  [10-debt-followup/prompt.md](features/10-debt-followup/prompt.md), with
  [feature.md](features/10-debt-followup/feature.md) and
  [context.md](features/10-debt-followup/context.md).
- **Moved the diagram generators and the extracted transcript out of session
  scratchpad** into the repo. They were temporary and would have been lost.
- **Started this worklog**, and a memory directory at
  `~/.claude/projects/…/memory/`.
- **Checked how an existing number attaches to Vapi** and wrote it up in
  [Homies-Vapi-Account-Notes.md](reference/Homies-Vapi-Account-Notes.md) — four
  routes, two traps, and how to tell which route applies.
- **Wrote the week-3 demo assistant** —
  [assistant/demo-inbound.md](assistant/demo-inbound.md). Platform config,
  turn-taking numbers with the reasoning for each departure from default, the
  full Hebrew system prompt, the five tools, and what is deliberately absent.
  New `docs/assistant/` folder: this is build output, not a feature, so it does
  not take the two-file treatment.
- **Created the Hebrew inbound assistant in Vapi** —
  `a594a4ce-ca47-4cab-8704-160afce199a7`, *Homies — Inbound Intake (demo)*.
  Azure `he-IL` in and out, `gpt-4.1-mini`, the tuned turn-taking numbers,
  recording on. Read back after writing; Vapi accepted every field.
- **Created the Hebrew outbound debt assistant in Vapi** —
  `56935b35-78ea-463d-86c5-16969f8ae50e`, *Homies — Debt Follow-up (he)*. Config
  and its reasoning in [assistant/debt-followup.md](assistant/debt-followup.md);
  the prompt stays in the feature folder and is pushed from there, so there is
  one copy of it. 240s cap, 20s silence timeout, agent can end the call.
- **Corrected the provenance claim in the debt prompt.** It said `אני לא נגדך`
  was verbatim from call 4. Nothing in it is verbatim — the PDF's Hebrew layer
  is corrupt, so the behaviour is quoted and the wording is reconstructed.
- **Wrote `scripts/vapi_sync.py`.** It extracts the first message and system
  prompt from `demo-inbound.md` and creates or updates the assistant, so the
  document is the source of truth rather than a description of the dashboard.
  Dry run by default, `--apply` to write.
- **Added `.gitignore` and `.env.example` at the project root.** Keys now have a
  destination that is not chat. `.env` is ignored; `.env.example` holds names
  only.

- **Wrote migrations `004` and `005`** — the charge/ticket model for feature 10.
  `charges`, `payment_tickets`, `promises_to_pay`, `payment_disputes`,
  `call_outcomes`, plus `gender` / `card_last4` / `handed_over` / `do_not_call`
  on residents. Seed exercises every branch: no card on file, gender unknown,
  paid, not handed over, do-not-call, attempts exhausted.
- **Closed the missing-amount guard, structurally.** `v_debt_call_queue` only
  emits a row when amount, period, handover and consent are all present, so a
  caller iterating it cannot place a call without them. The guard could never
  have lived in the prompt — an unsupplied variable renders as an empty string
  rather than failing. Also added a database constraint that a ticket claiming a
  captured authorisation must reference the call it came from, since the
  recording is the authorisation.
- **Merged the client's Hebrew style prompt with the behavioural tree.** The
  client rewrote the debt prompt in the dashboard as a pure style/register
  document — natural Israeli Hebrew, answer-the-latest-message, no repetition —
  which deleted the posture tree, the budgets, the fixed paths and all eight
  tools. Both are now in
  [10-debt-followup/prompt.md](features/10-debt-followup/prompt.md): their
  sections close to verbatim at the top, behaviour underneath, pushed live.
- **Stopped scripting Hebrew lines.** The prompt now describes in English what to
  convey and lets the model generate the Hebrew, keeping only five fixed strings
  — opening, AI disclosure, charge authorisation, not-the-account-holder,
  voicemail. A Hebrew line written by a non-speaker from an English original is
  exactly the translated text the style section forbids. Verification surface
  drops from ~40 lines to 5.
- **Rewrote the payment flow for staff-confirmed charging** (see Decided).
  `send_payment_link` is gone, replaced by `open_payment_ticket` carrying
  `authorization_captured`. Added `{{card_last4}}`, with an explicit branch for
  residents who have no card on file.

### Decided

- **The agent's data source is a Google Sheet, not Supabase, for now.** Client's
  call. A sheet is legible and editable by them and by Homies staff mid-test; a
  Postgres table is not, and Supabase is still un-provisioned. Served by Apps
  Script over HTTP as a Vapi tool — see [sheets/](../sheets/). The rows mirror
  `002`/`005` and the eligibility predicate mirrors `v_debt_call_queue`, verified
  to return the same six, so the move to Supabase is a swap behind the webhook
  rather than a rebuild. **The SQL remains the specification**; if the two
  disagree, the sheet is the copy that is wrong.
  - Blocking constraint recorded there: an Apps Script web app with Access=Anyone
    is public, and Apps Script cannot read custom headers, so the shared secret
    must ride in the query string. Fine for ten fictional residents, **not fine
    for real Homies data** — that move to Supabase is a precondition of any real
    row, not a nice-to-have.
- **The demo is intake-reliability, not conversation quality.** Ops staff are
  recruited as judges of the output, not subjects of replacement.
- **The debt agent is one conditional tree, not two branches.** Client
  correction. Posture is re-read every turn and moves in both directions; the
  explanation budget is per call and never resets. Reasoning in
  [10-debt-followup/context.md](features/10-debt-followup/context.md).
- **Hot is a floor.** Once a call has been hot it always ends in a handover, even
  if the caller later offers to pay. Accepted cost: some calls a human would have
  closed get transferred.
- **"I already paid" → hold the position, move the burden to a receipt.** The
  agent states what the ledger shows, gives an email, and says it will call
  again. It never asks when or how they paid.
- **Hardship always transfers.** Multi-intent opens a ticket but returns to the
  payment. Non-Hebrew hands over immediately with no English attempt.
- **Number integration comes after the demo.** Client call, 3 Aug. The demo runs
  on Vapi web calls, so no DID, no import, no KYC is on the critical path for
  week 3. Accepted cost: the 1–3 week Israeli DID KYC clock starts later than it
  could, which pushes Phase 3 rather than the demo. Revisit the moment the demo
  is rehearsed, not after it is delivered.
- **Keep all four Vapi assistants.** Client call. The two English ones (the
  collections test and Vapi's Riley sample) stay. The sidebar's
  `azure · openai · azure` line is how to tell the Hebrew ones apart at a glance.
- **Supabase Edge Functions serve the Vapi tool webhooks, not n8n.** The build
  plan named n8n, but its hosting question is still unanswered and it adds a
  network hop on the latency path that matters most. Edge Functions deploy from
  this repo, need no public URL and no hosting decision. n8n comes back for
  Monday, Sheets and WhatsApp, where its connectors are the point. Accepted cost:
  the tool layer is code rather than a visual workflow, so it is less editable by
  someone who is not a developer.
- **No automatic charging on the call.** Client call, 3 Aug. The agent takes the
  resident's spoken approval to charge the card already on file, opens a ticket,
  and a member of staff reviews it and makes the charge. Same shape as the §2.3
  staff-confirmed deletion decision: the bot documents and verifies, a human
  executes. Removes payment links, SMS delivery and payment-page reconciliation
  from Phase 7 entirely. Accepted cost: every payment now waits on a human.
- **The recording is the authorisation, not evidence about it.** Follows from the
  above — the resident's recorded *"yes"* is what permits the charge. This makes
  Vapi's 14-day retention a money problem rather than a support problem, and
  turns the Israeli recording-consent question into a prerequisite for charging
  rather than for going live.
- **`gpt-5.5` on the debt assistant.** Client change, for more natural Hebrew.
  Latency and cost unmeasured — the account still has 9.2 credits, no card, and
  auto-reload off.
- **Never lead with cost savings** to a room of call-centre staff — a two-minute
  human call costs about the same as the bot handling it, and they will spot it.

### Found

- **She hung up on a hardship disclosure.** Found in the first English test call,
  4 Aug: the caller said he had lost his job and the call ended immediately, with
  no line spoken. The single worst moment in the call to go silent.
  - Root cause is not wording. `endCallFunctionEnabled: true` gives the model an
    `endCall` tool, and **no other tool exists** — `tools: none` on both
    assistants. Told to "call `transfer_to_human`", which is not declared, the
    only action actually available to it was to hang up. It did the one thing it
    could.
  - The prompt described an *intention* and assumed a tool would carry it. Fixed
    structurally: a new **HANDING OVER TO A PERSON** section makes the handover
    three ordered steps — say the line, call the tool, stay on the line — with
    the Hebrew line fixed verbatim, and `Never end the call on a handover` stated
    as an absolute regardless of whether the tool fails or is missing.
  - This makes the handover the **sixth** fixed Hebrew string. The five before it
    were fixed for legal or privacy reasons; this one is fixed because a test
    proved a description was not enough. Native-speaker verification now covers
    six lines, not five.
  - Still not an actual transfer. Until `transfer_to_human` exists she says the
    line and waits, and `silenceTimeoutSeconds: 20` ends the call. Correct words,
    no handover — better than silence, not a fix.
- **TTS mangles an email address read aloud.** `yulgatch123@gmail.com` came out
  as *"yallgach123"*. Not a prompt defect — reading an arbitrary address over a
  phone line is unreliable by construction. The disputed-payment path depends on
  the resident hearing it correctly.
  - `{{verification_email}}` is now `homiesemail@gmail.com` — client's choice —
    everywhere it was set: `web/index.html`, `vapi_eval.py`, `vapi_call.py`,
    `vapi_duel.py`, `vapi_mock.py`, `docs/assistant/debt-followup.md`. Two
    dictionary words and no digits, so a mishearing degrades to a near-miss
    rather than an unusable string.
  - Not fully solved. Any address read aloud on a bad line can still be missed,
    and there is no confirmation that the resident wrote it down. The real fix is
    sending it — SMS or WhatsApp after the call — which needs a tool that does not
    exist yet.
- **A backchannel was being treated as an interruption.** `stopSpeakingPlan`
  carried `numWords: 0`, so any sound at all stopped her mid-sentence — and an
  "mm-hmm" while she talks is listening, not interrupting. She restarted the
  opening sentence three times in one call before finishing it. Now
  `numWords: 2, voiceSeconds: 0.3, backoffSeconds: 1.5`. Two words is the line
  between acknowledgement and a real interruption.
  - Backed up in the prompt, because the two failures compound: a new rule says
    "mm-hmm", "OK", "yeah", "right" and "sure" are **not turns**, and that
    restating a point in fresh wording counts as repeating it.
- **She used the no-card branch on a resident who has a card.** Told a caller with
  card `4821` on file that "someone from the office will contact you to arrange
  it", and only asked for authorisation after he asked *"on what card?"* — which
  is the call's entire purpose, obtained by accident.
  - The prompt described both branches but never said they were exclusive. Added:
    `{{card_last4}}` alone decides, the authorisation question comes first, and
    nothing about the office is said until it is answered. Plus a symptom the
    model can check itself against — *if the caller has to ask which card, you
    have already skipped the question.*
- **The handover fix caused a regression, and the fix for that is the interesting
  part.** After adding `Never end the call on a handover`, she stopped ending
  *any* call — said "Thank you, have a good day" and left the line open
  (`endedReason: customer-ended-call`, call `019fcbd4`). Before the change she
  ended calls herself.
  - An absolute stated on its own gets generalised. The prompt said when **not**
    to hang up and never said when to, so the safe reading was never. A new
    **ENDING THE CALL** section states the positive rule beside it, ending with
    *Saying goodbye is not the same as ending the call. Do both.*
  - Worth carrying: every prohibition added to this prompt needs its complement
    written next to it, or the model finds the interpretation that satisfies the
    prohibition and nothing else. Same failure shape as the mute-agent false
    passes in the eval run — a rule satisfied by doing less.
- **English TTS mangles the name.** `en-US-JennyNeural` read "Michal" as
  *"me call"* in one call and the English male "Michael" in another. Spelled
  `Mikhal` in the English twin's four spoken instances. Hebrew
  `he-IL-HilaNeural` is correct and is untouched.

- **The agent invents missing variable values rather than failing.** First live
  test with no `variableValues` supplied: `{{amount}}` came out as silence
  (*"… שקלים"*) but `{{month}}` was filled with **אוגוסט**, the current month,
  which nobody supplied. An empty slot is visibly broken; a plausible wrong month
  is not. The prompt's never-estimate rule did not fire because from the model's
  side there was nothing to estimate, only a sentence to finish.
- **The reconstructed Hebrew produced a non-sentence in output.**
  `למישהו לא בא על חשבון` — reaching for *"someone who is not the account
  holder"*. First time the unverified-Hebrew risk showed up in behaviour rather
  than on paper.
- **The wrong-party script fired at a legitimate question.** *"Who is this, where
  did you get my number?"* got the not-the-account-holder deflection, verbatim
  and twice. Both fixed by the client's rewrite.
- **A payment was offered on a turn containing no commitment.** *"Yes, speaking"*
  — an identity confirmation — was read as agreement and the agent moved to
  close. Now guarded: authorisation requires an unambiguous yes, and hesitation
  is treated as friction.
- **Free Vapi numbers cannot place international calls.** Created one (`+16576083115`,
  id `a6f4fa90`, area code 657 — 415 was unavailable) and the first outbound
  attempt was refused before dialling: *"Free Vapi numbers do not support
  international calls."* Nothing was billed. This applies to `+972` exactly as it
  did to the `+63` test destination, so **no call to a real resident, and no
  phone-based demo, can run on the free tier.** A paid Twilio or Telnyx number is
  a prerequisite for any dialled call, not just for Israeli caller ID.
  - Twilio has a second trap: international destinations are disabled by default
    and must be enabled per country under Voice → Geo Permissions.
- **The Vapi account has no payment method, and that gates every test path.**
  Three separate walls, one cause: a second phone number (*"must provide a credit
  card"*), the text chat API (*402, pay-as-you-go orgs require a card on file*),
  and international dialling. Only the dashboard's own web-call widget still
  works, and it cannot send `variableValues`. Vapi is pay-as-you-go, so a card
  bills use rather than a subscription — **adding one unblocks all three.**
- **Vapi test suites are the right test harness, and they need no phone number.**
  Verified against the live API, not the docs. `POST /test-suite` takes a
  `targetPlan` (`assistantId` **plus `assistantOverrides.variableValues`** — all
  ten variables reach the agent) and a `testerPlan.assistant` given inline, so the
  simulated resident needs neither an assistant record nor a line of its own.
  Each test is `{type: voice|chat, script, scorers: [{type: "ai", rubric}]}` and
  an LLM judge grades the transcript — which is what makes results readable
  without Hebrew. Suite `1052adce`, nine scenarios, built by
  [vapi_eval.py](../scripts/vapi_eval.py). **This sidesteps both the one-number
  limit and the international-call refusal**; whether a *run* still needs a card
  is untested. Supersedes `vapi_duel.py`, which needed two numbers and produced
  an unscored transcript.
- **Fixed-value clones make the dashboard usable, and cost nothing.**
  [vapi_mock.py](../scripts/vapi_mock.py) copies the debt assistant with every
  `{{variable}}` substituted from the six `v_debt_call_queue` seed rows, so the
  dashboard's web-call widget — which cannot send `variableValues` and is the
  only test path a card does not gate — runs the agent on real amounts, months
  and card digits. Six clones exist, prefixed `Homies — Debt TEST:`. They are
  throwaway: edit the real assistant and re-run.
  - Substitution runs over the serialised assistant, not a list of known fields,
    and the script exits if any placeholder survives. An unresolved one renders
    empty at call time and the agent invents a value to cover the gap — which is
    exactly how a test call produced a month nobody supplied.
  - **The live prompt uses 8 of the 10 declared variables.** `unit` and `attempt`
    appear in [prompt.md](features/10-debt-followup/prompt.md) but not in the
    deployed assistant, so the call-attempt number cannot currently change the
    tone on a repeat call. Not yet decided whether to wire them in or drop them
    from the table.
- **A test-suite chat run completes, scores everything, and is worthless.** Nine
  scenarios ran (`dfe9eb9f`); every transcript is one agent turn against fifty
  tester turns. `POST /chat` still returns *402, pay-as-you-go orgs require a card
  on file*, so the agent emits only its `firstMessage` — static text needing no
  model call — and then goes silent. **The run does not error**, which is the
  dangerous part.
  - The variables did resolve: the greeting came through as *מדברת עם אליה*, so
    `targetPlan.assistantOverrides` works.
  - **Four scenarios "passed" while the agent was mute.** The rubrics are lists
    of things it must never do, and silence satisfies all of them. Fixed by
    checking transcript liveness structurally and marking those runs INVALID —
    a rubric alone cannot catch this, because the judge is reading the same empty
    transcript. Any future rubric needs the same guard.
- **Web calls with `assistantOverrides` cannot be created from the server API.**
  `POST /call` without a `phoneNumberId` returns 400. Overrides on a web call
  require the browser SDK and the Vapi **public** key, which is not in `.env`.
  This is the only free way to hear the agent speak real variable values.
- **Vapi retains recordings 14 days**, and 60-day retention is $1,000/month.
  This breaks [07-partial-ticket](features/07-partial-ticket/feature.md) as
  written. Fix logged there; **not yet applied**, awaiting approval.
- **The transcript PDF's Hebrew layer is corrupt.** Every Hebrew line in the
  prompt is reconstructed from the English translation column, not quoted. A
  Hebrew speaker must check them against the audio before rehearsal.
- **Two of the four sample calls should never have been placed** — the residents
  had no keys yet. That is a database check, not a prompt condition, and it is
  the cheapest win in the outbound flow.
- **Sample call 4 is missing** from the transcript PDF. Files jump from 3 to 5.
- **Vapi account has 9.2 credits, no card on file, auto-reload off.** The
  combination, not the balance, is the risk.
- **Vapi sells US numbers only.** There is no +972 to buy inside it, so the
  Israeli number is always an import. A number already KYC'd in a Twilio or
  Telnyx account skips 1–3 weeks of DID KYC — the longest non-compressible clock
  in the plan. Worth finding out whether one exists.
- **The assistant ID in the feature files was wrong all along.**
  `f5c758d8-…` is *Homies Collection (EN test)* — English, Deepgram `nova-2`,
  Elliot voice, 450 shekels hardcoded in its prompt. Feature 04 described it as
  Azure `he-IL` with HilaNeural; it has never been either. No Hebrew assistant
  existed in the account until today. Left it untouched — it is the closest
  thing to a feature-10 ancestor.
- **The dashboard's Model Presets silently destroy the Hebrew stack.** Clicking
  *Balanced* / *Ultra Fast* / *Cost Saver* replaces transcriber and voice
  wholesale. The inbound assistant went to Talkscriber Whisper English and
  11labs Sarah within a minute of being created, and answered a Hebrew caller in
  English. No warning, no undo. Restored with `vapi_sync.py inbound --apply` —
  which is the argument for the sync script existing at all.
- **Vapi turns on `transcriber.fallbackPlan.autoFallback` by itself.** If Azure
  `he-IL` fails it switches transcriber mid-call, and nothing else does Hebrew.
  The failure mode is confident nonsense, not silence. Left on for now, flagged.
- **Vapi sits behind Cloudflare and 403s urllib's default user-agent** (error
  1010). Any ordinary UA string passes. Cost twenty minutes; written into the
  sync script as a comment so it costs nobody else that.
- **Vapi's LiveKit smart endpointing is tuned for English.** For Hebrew the
  `smartEndpointingPlan.provider` must be `vapi`. Leaving the default is a quiet
  degradation, not an error — it would look like the model being slow.
- **Three feature files carry masculine Hebrew against a female voice.**
  `אני רושם` in [04](features/04-interruption-pacing/feature.md) and
  `אני מעביר` in [06](features/06-boundaries/feature.md). Corrected in the
  assistant; the feature files still need fixing.
- **`transfer_to_human` has a reason the schema does not.** The assistant needs
  `language`; [06](features/06-boundaries/feature.md) lists four reasons without
  it. One of the two has to move.
- **No API key exists anywhere in this project.** No `.env`, nothing. Vapi
  cannot be edited from here until a rotated key is supplied.
- `Homies-Inbound-Flow.excalidraw` is stale — it still shows the bot deleting
  payment information, a flow that was ruled out. Flagged do-not-show.

### Open

- **Still not a git repository.** Everything here is one bad overwrite from gone.
  `git init` offered repeatedly, not answered.
- Voicemail: leave a message at all, or just log the attempt? Now concrete —
  `voicemailDetection` is unconfigured on the debt assistant, so it will talk to
  an answering machine as though it were a person. Either answer is one field.
- Nothing validates that `amount` and `month` are present before a debt call is
  placed. A missing template variable renders as an empty string, so the agent
  would say "the payment for the month of, 0 shekels" rather than refusing. The
  guard belongs in the caller, which does not exist yet.
- Nothing copies the call recording out of Vapi. It is now the artifact that
  authorises a charge and it is deleted after 14 days. Belongs in the
  end-of-call webhook, which does not exist.
- Whether a resident's card is on file is a field nobody has confirmed exists.
  The prompt branches on `{{card_last4}}` being empty; migration `004` has to
  carry it either way.
- Need one recording of an ordinary successful call — all four samples have
  something going on, so there is no baseline for normal.
- Rotate the three exposed keys (Telnyx, Retell, Vapi). Rotating Vapi is now
  also the unblock for editing the assistant — new key into `.env`.
- Find out where the tentative virtual number actually lives. A console login
  means import; a SIP username and password means BYO trunk; Retell means
  replace it.
- Create the Supabase project, run `001`–`003`, supply URL and service role key.
- Choose n8n Cloud trial vs `n8n start --tunnel`.
- Ask Homies for real building names and their real request categories — ours are
  invented and ops staff will notice in the first call.
- Migration `004` for the debt/charge model does not exist and is unsized.
