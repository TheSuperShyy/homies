# Homies WhatsApp: our current setup vs UChat, and what a migration would take

Source material, 29 September 2026. Written to be handed to a writing assistant
(Gemini) that turns it into a decision document for the project owner and
Homies' management.

**Suggested instruction to paste above this text:**

> Turn the material below into a clear, well-structured decision document for
> non-technical managers.
> - Keep every number, price, day estimate and date exactly as given.
> - Keep the labels VERIFIED / ESTIMATE / UNVERIFIED next to each claim.
> - Do not add facts that are not in the material.
> - Keep the sources list at the end.
> - Use tables where the material uses tables.
> - Add a one-page executive summary at the top.

**Labels used throughout:**
- **VERIFIED** means checked against a primary source (their documentation,
  their API specification, our own systems or code) on 28-29 Sep 2026.
- **ESTIMATE** means our own judgement, with the reasoning shown.
- **UNVERIFIED** means claimed by a secondary source, or not yet tested.

---

## 1. Background

- **Homies** is an Israeli building-management company. Its management system
  (OXS) holds 173 active buildings and 4,092 apartments, and about 7,400
  residents are on file (August count). Homies has about 19 staff.
- **The WhatsApp assistant.** We are building a Hebrew AI assistant that
  introduces itself as "Michael from Homies". It opens service tickets, reports
  ticket status, tells a resident their balance (only after the resident types
  their full name and phone number), sends the resident's own payment link,
  answers common questions and hands over to staff.
- **What the client asked for (PRD item 3, "Centralized WhatsApp System with AI
  Bot"):**
  - one central business number with staff seats;
  - routing to four departments: Collections, Operations, Management, Service;
  - moving chats between staff, department assignment, and open/closed status;
  - switching the AI off per conversation, for a human handover;
  - complete chat logs, automatic thread summaries and topic tagging;
  - a bot that sends payment links, answers FAQs, opens service tickets, checks
    ticket status and checks balance.
  - Their stated emphasis: the bot must not feel robotic ("thrown to a robot").
    It must be calm, respectful, clear and service-oriented.
- **Where it stands.** The assistant runs live on a **test number**. Homies'
  official WhatsApp number is still answered by their old ManyChat menu bot.
  Moving that number is a separate step that needs the client and the Meta
  account that holds it. **It is needed whichever platform is chosen.**
- **Why this document exists.** On 29 Sep the owner asked us to investigate
  UChat, a no-code chatbot platform: what it is, what it costs, and how much
  work a move would take. A free trial account was opened the same day.

---

## 2. The current setup, piece by piece (VERIFIED against our systems)

| Piece | What it does for us | Where it runs | Cost |
|---|---|---|---|
| **Meta (WhatsApp Cloud API)** | Owns WhatsApp itself: the number's registration and message delivery | Meta's cloud | Meta's per-message fees. Replies inside the 24-hour window after a resident writes are free |
| **Chatwoot** (open-source team inbox, version 4.16) | The staff inbox. It holds the number, and every message passes through it | **Our own VPS** (a Hostinger virtual server, 2 CPU, shared with n8n) | **$0.** Chatwoot's hosted plan would be $19 per agent per month, about **$361/month** for 19 staff. That is why we host it ourselves |
| **n8n** (open-source automation tool) | The assistant's "wiring": everything around the AI model | **Our own VPS**, the same server. The n8n instance also runs other workflows | **$0** (self-hosted) |
| **OpenRouter** (AI model gateway) | Runs the AI model, **Google Gemini 2.5 Flash** | OpenRouter's cloud | Pay per use. Measured at **$0.00051 per reply**, about 40 times cheaper than the Claude Opus model it replaced in August |
| **Supabase** (database and server functions) | The data (residents, debts, tickets, payment links, the message log) and our tool server `debt-tools` (4,044 lines), which does every real action | Supabase's cloud | Unchanged in every option |
| **Dashboard** (web app on Vercel) | Staff pages for tickets, debts, conversations and calls | Vercel's cloud | Unchanged in every option |
| **OXS** (the client's system) | The source of buildings, residents and debts. We read from it, and new tickets are mirrored into it (currently for the test phone only) | The client's | Not ours |

**The VPS costs about $7-15 a month** and hosts both n8n and Chatwoot. It stays
in every option, because n8n runs other workflows too.

### 2.1 What Chatwoot does today (VERIFIED)

- **It owns the test number.** Meta delivers every message to Chatwoot, which
  hands each one to the bot.
- **It stores every conversation and every photo or file** residents send.
- **Staff seats, and four department teams** (Collections, Operations,
  Management, Service). The teams are created but still empty, and nothing
  routes chats to them automatically yet.
- Labels, assignment, conversation status, and a mobile app.
- **Handover.** When a staff member replies in a conversation, the bot goes
  quiet there. The bot can also leave a private note that alerts the whole
  team.
- **A separate "Voice" inbox,** where the phone assistants leave their notes to
  the team.

### 2.2 What n8n does today: the assistant's wiring (VERIFIED)

- **One workflow of about 50 steps,** maintained by 25 scripts that apply
  changes safely.
- **A greeting menu.** A plain "hello" gets a greeting that follows the time of
  day ("good morning / good afternoon / good evening", שלום after midnight),
  then "👋 במה אפשר לעזור?" with three buttons: פתיחת קריאת שירות, מצב קריאה
  קיימת, לדבר עם נציג.
- **Burst merging.** When a resident sends several quick messages, it waits
  about 4 seconds and answers them once, together.
- **Greeting rules the owner set:**
  - greet once, never twice;
  - no second greeting mid-conversation;
  - use the resident's name only on the first reply.
- **Per-message facts for the AI.** On every message it tells the AI the time of
  day, whether the conversation is already under way, and whether the resident
  opened with a greeting.
- **Conversation memory** per resident.
- **Eight tools** the AI can call, all served by our tool server:
  - open a ticket;
  - check an address against the real building list;
  - ticket status;
  - note to the team;
  - balance;
  - show the menu;
  - service information;
  - payment link.
- **Checks every AI reply before it is sent,** and rewrites it with the reason
  named if it fails. A reply is stopped when it:
  - claims work nobody did (for example "I replaced the bulbs");
  - echoes the resident back ("I understand that…");
  - sounds like a call-centre clerk.
- **Outage handling.** If the AI service fails, the resident gets an honest "a
  technical problem on our side, your message is with the team", and staff are
  alerted. It never invents an answer.
- **Sends a payment link as its own separate message.**
- **Writes every message to the database,** which is what the dashboard's
  Conversations page shows.

### 2.3 Our safety net for changes (VERIFIED)

Every change to the assistant goes through an automated check before it goes
live:
- **121 test cases** run on the exact live code.
- **Fingerprints of 17 texts the AI reads,** so nothing changes by accident.
- **A replay of every real message so far** (814 from residents, 865 replies),
  comparing the old and new behaviour.
- **A watch mode** that checks real conversations against the owner's rules
  after each release.

It exists because earlier fixes kept breaking other things. The owner's words:
"we fix a bug it cause another one and loop repeats."

### 2.4 The AI model settings (VERIFIED)

- **Model and settings:** Gemini 2.5 Flash, temperature 0.6, maximum 4,096
  tokens per reply. On this model the "thinking" shares that budget.
- **The prompt:** 19,663 characters of Hebrew instructions, about 7,200 tokens
  (measured with a standard tokenizer).

### 2.5 How far PRD item 3 is met today (VERIFIED)

| Required | Today |
|---|---|
| Central number with seats | Seats exist in Chatwoot; the official number has not moved off ManyChat yet |
| Four-department routing | The teams exist, empty; no automatic routing yet |
| Transfer between staff, assignment, open/closed status | Built into Chatwoot |
| AI on/off per conversation | A staff reply silences the bot in that conversation |
| Chat logs | Complete, in Chatwoot and in our database |
| Thread summaries and topic tagging | Not built yet (Chatwoot has labels) |
| Payment links | Working since 17 Sep |
| FAQs | Answered from the assistant's facts plus a service-information tool |
| Open tickets | Working, with mirroring into OXS |
| Ticket status and balance | Working. Balance needs the resident's full name and phone number |
| Not robotic | Rewritten on 27 Sep to a casual, friendly, polite register |

---

## 3. What UChat is (VERIFIED unless marked)

- **Company and product.** UChat (uchat.au) is an Australian no-code chatbot
  platform and a direct competitor of ManyChat (which Homies' old bot uses). You
  draw conversations as connected blocks, and UChat runs them.
- **Channels.** 13 are listed: website chat widget, Facebook Messenger,
  Instagram, WhatsApp, Telegram, SMS, Slack, Google Business, voice, WeChat,
  Line, Viber, VK, plus a custom API channel. Per their blog, it can also take
  **WhatsApp voice calls** with an AI agent (not evaluated by us).
- **Flow builder.** Blocks for messages, questions, actions, conditions, splits,
  email and jumps. An **"External Request"** block calls any outside system and
  saves parts of the answer into fields. There are also inbound webhooks.
- **AI features (the "AI Hub").**
  - AI agents, AI functions (tool calls), AI tasks.
  - A knowledge base (file uploads only).
  - Connections to outside tool servers (MCP), and web search.
- **AI models, per their official API specification:**
  - The providers are OpenAI, DeepSeek, xAI, Claude, **Gemini**, Groq and
    "Ainvented".
  - Their training page mentions only three, so the API specification is the
    authority here.
  - **You bring your own AI key and pay the AI company directly.** UChat
    provides no AI of its own and no free model.
  - Conversation history is auto-summarised after 10 messages by default.
- **Staff inbox ("Live Chat").**
  - Inbox and Done folders, notes, tags, assigning to an agent, agent groups
    (usable as departments), agent group chat, and a mobile app.
  - Built-in ticket lists and a CRM.
  - **Pause:** when a staff member replies, the bot pauses for **30 minutes**
    and then resumes, unless extended. Through their API the pause can be set
    to any number of minutes.
- **Their API.**
  - An official specification with **240 endpoints**, authenticated with a
    personal API key that has limited abilities.
  - **It can:** manage contacts, tags and fields; send text, buttons, flows and
    WhatsApp templates; run broadcasts; pause or resume the bot; assign a
    conversation to an agent or group; set an AI agent's model and limits;
    connect tool servers; manage agent groups, labels and ticket lists; read
    message history.
  - **It cannot:** create an AI agent or a flow. Both must be built by hand in
    their dashboard.
- **WhatsApp.**
  - **UChat provides no phone numbers.** Every number must be registered with
    Meta under a Meta business account first.
  - **Two ways to connect a number:**
    - **"WhatsApp Cloud"**: log in with Facebook, and Meta's own sign-up
      verifies the number by SMS or call. This is the current way.
    - **"WABA (Deprecated)"**: paste an access token, account ID and phone ID
      from your own Meta developer app by hand.
  - The number cannot be active on the ordinary WhatsApp app at the same time.
  - UChat adds **no per-message fee**; Meta's fees apply as on any platform.
- **Hebrew and right-to-left text: UNVERIFIED.** Neither their documentation nor
  any review mentions Hebrew or right-to-left support. WhatsApp itself shows
  Hebrew correctly, but their staff inbox and builder are untested.
- **Independent reviews (UNVERIFIED opinions).**
  - SetSmart: "you still have to design every branch… hours of flow-building,
    testing, and maintenance", and contact-based pricing "punishes growth".
  - Chatimize: an easy builder once learned, but a steep learning curve for
    beginners, basic analytics, a dated interface, and mobile app performance
    issues.

### 3.1 UChat pricing (VERIFIED from their pricing page, 29 Sep; currency not stated, most likely US dollars)

| Plan | Price | Includes |
|---|---|---|
| Free | $0 | 1 bot, 200 contacts, 1 team member |
| Business | **$15/month billed yearly, about $29 billed monthly** (shown discounted from $29-39) | 1 bot, 1,000 contacts, 5 team members, live chat, AI, CRM and tickets, 48-hour support |
| Partner (agencies) | $199/month | White label, 10,000 contacts, unlimited team members, 4-hour support |

**Add-ons:**
- extra team member $5/month on Business ($10 on other plans);
- extra bot $5-10;
- extra 1,000 contacts $5/month up to 5,000, then $20/month per extra 5,000.

**"Contacts" means everyone the bot has ever talked to,** not only active
people.

**Other terms:**
- a 14-day free trial of all Pro features, with no card needed;
- yearly billing gives one month free;
- refunds are possible within 7 days of the first month, minus a 10% fee.

---

## 4. Side by side: today vs UChat

| Job | Today | In UChat |
|---|---|---|
| WhatsApp connection | Chatwoot's WhatsApp inbox, on Meta | UChat's WhatsApp Cloud, on Meta. Registration with Meta is still needed |
| Staff inbox, seats, departments, handover | Chatwoot on our VPS | UChat Live Chat (hosted by UChat) |
| The assistant's wiring and safety checks | n8n on our VPS | UChat AI agent plus flows; the checks must be rebuilt, some cannot be |
| AI model | Gemini 2.5 Flash via OpenRouter | Gemini 2.5 Flash via a direct Google key |
| Tools (tickets, balances, links) | Our tool server, called by n8n | Our tool server, called through a new bridge |
| Data and the dashboard | Supabase and Vercel | Unchanged, but the dashboard's WhatsApp history needs a new feed |
| Safety net for changes | Automated replay on the live code | Cannot run inside UChat, so it becomes manual testing |
| Hosting and upkeep | We run upgrades and backups on the VPS | UChat runs its part; the VPS stays for n8n's other work |

---

## 5. What we would still have to build or keep with UChat (VERIFIED dependencies, ESTIMATE of difficulty)

1. **A bridge to our tools.** It gives UChat its own revocable password, so our
   tool server's real password never leaves our side.
2. **Knowing who is writing.** UChat does not get the per-message facts n8n
   supplies (time of day, resident's name, mid-conversation or not). The bot
   would look the resident up at the start of each chat.
3. **The safety checks, where UChat allows them.** We found no way in UChat to
   check a reply *before* it is sent. That check is what stopped invented
   repairs and clerk-like replies this month. Burst merging and the outage
   message would need rebuilding in flows. Whether UChat merges quick
   consecutive messages is UNVERIFIED.
4. **Four connections in our tool server that go through Chatwoot today:**
   - copying residents' photos into our storage;
   - the phone assistants' notes to the team (Chatwoot's Voice inbox);
   - the debt phone call's payment link, sent to the resident by WhatsApp;
   - the conversation lookup behind all three.
5. **A new feed for the dashboard's WhatsApp history.** Today only n8n writes it.
6. **A replacement for the automated safety net,** at best a manual,
   black-box test set.
7. **A paid Gemini key for production.** Google's free tier may use traffic to
   train its models, and that traffic would be residents' messages. The free
   tier also allows only about 10 requests a minute. The paid key costs about
   the same as OpenRouter today.

---

## 6. Migration effort (ESTIMATE, one developer, working days)

These figures were re-estimated on 29 Sep after mapping everything that touches
Chatwoot. The first estimates (3-5 weeks and 1.5-2.5 weeks) missed the four
tool-server connections and the dashboard feed.

### Option A: move everything to UChat (it replaces Chatwoot, the n8n assistant and OpenRouter)

| Work | Days |
|---|---|
| Connect the number; set up seats and the four departments | 2-3 |
| The AI agent, looking up the resident at the start, the menu and the handover | 3-5 |
| A guarded bridge to our tools | 2-4 |
| Rebuilding the safety checks where flows allow | 3-5 |
| The four Chatwoot connections, plus the dashboard feed | 4-6 |
| Hebrew tuning inside UChat, plus a manual test set | 4-6 |
| Switch-over with a side-by-side check, then fixes | 3-5 |
| **Total** | **21-34 days, about 4-7 weeks** |

**What we lose:**
- the before-sending reply checks;
- the automated replay safety net;
- full control of the assistant's logic;
- conversation history, which starts fresh.

### Option B: UChat replaces only Chatwoot (n8n stays the brain, OpenRouter stays)

| Work | Days |
|---|---|
| Connect the number; set up seats and departments | 2-3 |
| Rewire every Chatwoot-specific part of n8n: receiving, sending, handover, team notes | 5-7 |
| The four Chatwoot connections in the tool server | 3-4 |
| Update the automated replay for the new message format | 1-2 |
| Switch-over and fixes | 2-3 |
| **Total** | **13-19 days, about 3-4 weeks** |

**What it keeps:** the assistant, its checks and the safety net unchanged.
**What it gets:** about the same inbox Chatwoot already gives us.

**Either option:** moving Homies' official number off the old ManyChat bot is a
separate step. It needs the client and their Meta account.

---

## 7. Monthly running cost (ESTIMATE from the published prices)

### 7.1 The UChat subscription

**Assumptions:** about 7,400 residents may eventually write, so we take 10,000
as the contact tier. Seats are counted two ways: about 10 people, or all 19
staff.

| Item | Yearly billing | Monthly billing |
|---|---|---|
| Business base | $15 | $29 |
| Contacts 1,000 → 5,000 (4 × $5) | $20 | $20 |
| Contacts 5,000 → 10,000 (1 × $20) | $20 | $20 |
| Seats, 10 staff (5 extra × $5) | $25 | $25 |
| **Total, 10 seats** | **$80** | **$94** |
| Seats, 19 staff (14 extra × $5) | $70 | $70 |
| **Total, 19 seats** | **$125** | **$139** |

### 7.2 What changes compared with today

| Cost | Today | Option A | Option B |
|---|---|---|---|
| VPS (n8n, Chatwoot) | ~$7-15 | stays (n8n's other work) | stays |
| Inbox software | $0 (self-hosted Chatwoot) | UChat $80-139 | UChat $80-139 |
| AI model | OpenRouter, ~$0.0005 per reply | paid Gemini key, about the same | OpenRouter as today |
| Meta WhatsApp fees | as today | same | same |

**Net: about $80-140 a month more than today, in either option.**

---

## 8. Pros and cons

### What UChat would add

- A hosted inbox: no server upgrades or backups for that part.
- A polished mobile app for staff.
- Other channels from the same inbox: website chat, Instagram, Messenger,
  Telegram. None of these are in the PRD.
- Built-in ticket lists and CRM, broadcasts, and WhatsApp calling (not
  evaluated).
- An API that covers pausing, assigning, sending and departments.

### What it costs or risks

- 3-7 weeks of migration work, plus about $80-140 a month.
- **Option A only:** it gives up the before-sending checks and the automated
  safety net, the two things that fixed this month's bugs ("fix one, break
  another").
- Contact-based pricing grows with every resident who ever writes.
- A closed platform: behaviour we cannot inspect or replay.
- Hebrew right-to-left in their staff inbox is untested.
- Dependence on a third party for the resident-facing channel.

---

## 9. The trial: status and next steps (VERIFIED)

### Done (29 Sep)

- A free trial account opened.
- An API key created with limited abilities (it cannot manage team members) and
  confirmed working with read-only calls. The trial bot is empty.
- Choices made by the owner for a first "look-and-feel" copy:
  - **the Gemini model**, same as the live assistant, on a free Google key;
  - **no tools**, so the copy can reach no resident data at all.
- The copy's instructions are the live assistant's prompt, word for word, plus
  a short demo note. The note tells it that it cannot act in this demo and must
  never invent numbers, amounts, dates or links. A bot without tools tends to
  invent actions, which was exactly this month's bug.

### Owner's next steps in UChat's dashboard

1. Create a free Gemini key at Google AI Studio and paste it into UChat's
   Gemini integration.
2. Create the AI agent: paste the prompt, choose the Gemini 2.5 Flash model,
   set temperature 0.6, and add no tools.
3. Build the start flow: "שלום 👋 במה אפשר לעזור?" with the three buttons, all
   leading to the agent.
4. Turn on the website chat widget and test there.

### Then, from our side

- Set the model and the reply length through the API.
- Run six test messages on the assistant's known hard cases: a second greeting,
  a hello mid-conversation, a fault report, "who are you", a balance question,
  and "hello good afternoon".

### Rules for the trial

- **Never connect our test number or Homies' official number.** Connecting a
  number moves its messages instantly, and the live assistant goes silent. This
  happened once with Chatwoot, on 21 Aug: two hours of silence.
- WhatsApp is only tried later, and only with a spare number that has never
  been on WhatsApp.

### Checks the trial must answer before Option B could be recommended

1. Hebrew displays correctly in the staff inbox.
2. Their API can send our assistant's replies.
3. Every incoming message can be forwarded to our system.
4. The bot can stay paused for a whole conversation.
5. Chats can be routed to departments.
6. The billing currency.

---

## 10. Recommendation

- **Do not move now.** Chatwoot already provides the PRD's inbox pieces for $0.
  The remaining PRD work (putting staff into the four departments, automatic
  routing, thread summaries, topic tagging) is the same work on either
  platform.
- UChat is a reasonable choice for a business starting from zero. For us it is
  a sideways move that costs 3-7 weeks and $80-140 a month. The full move
  (Option A) would also weaken the safety checks that fixed this month's bugs.
- **If Homies still prefers UChat,** choose **Option B** (inbox only, keep our
  assistant), and only after the trial passes the six checks above.
- **Needed whichever way:** move Homies' official number off the old ManyChat
  bot, with the client's Meta account.

---

## 11. Glossary

- **Meta / WhatsApp Cloud API:** WhatsApp's official system for businesses.
  Every business number is registered there.
- **WABA:** WhatsApp Business Account, the Meta account a number belongs to.
- **VPS:** a rented virtual server. Ours runs n8n and Chatwoot.
- **Chatwoot:** open-source team inbox software, our staff inbox.
- **n8n:** open-source automation software, where the assistant's logic runs.
- **OpenRouter:** a service that gives access to many AI models with one key.
- **Gemini 2.5 Flash:** Google's AI model that the assistant uses.
- **Tool / tool server:** the actions the AI can take (open a ticket, check a
  balance). Ours run in Supabase.
- **MCP:** a standard way to give an AI agent access to outside tools.
- **Contact (UChat pricing):** anyone the bot has ever talked to.
- **Seat / team member:** a staff login.
- **Webhook:** the address where a system delivers incoming messages.

---

## 12. Sources

- UChat pricing: https://uchat.au/pricing
- UChat API specification (240 endpoints):
  https://www.uchat.com.au/default-api-docs/api-docs.json
- UChat API documentation (authorization):
  https://docs.uchat.com.au/for-developers/API/
- UChat Live Chat: https://docs.uchat.com.au/flow-builder/live-chat/live-chat.html
- UChat WhatsApp Cloud API: https://docs.uchat.com.au/guide/cloudapi.html
- UChat connecting channels: https://docs.uchat.com.au/guide/setup-create.html
- UChat AI agent creation:
  https://uchat.au/uchat-training/ai-agent-2-1-create-ai-agent
- UChat AI agent features: https://uchat.au/features/ai-agent
- UChat External Request:
  https://docs.uchat.com.au/flow-builder/action-external-request.html
- UChat WhatsApp calling: https://uchat.au/blog/whatsapp-business-calling-api
- UChat new send APIs (feedback board):
  https://feedback.uchat.com.au/updates/add-4-new-api-for-sending-send-text-send-sms-send-email-send-node-84e9d314-bbb7-44e6-920a-7e1b114ffa93
- SetSmart review: https://setsmart.io/blog/uchat-review
- Chatimize review: https://chatimize.com/reviews/uchat/
- Gemini API pricing and free tier: https://ai.google.dev/gemini-api/docs/pricing
- Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Our own records: the project's feature documentation, worklog and code, as of
  29 Sep 2026.
