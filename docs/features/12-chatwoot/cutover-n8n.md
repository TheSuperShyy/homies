# 12 — The n8n changes the cutover needs

**Applied 21 Aug. Chatwoot is in the message path and the bot answers through
it.** Written first as a plan, then applied through n8n's REST API -- the MCP is
not required for a workflow update, which the plan wrongly assumed.

## The thing this document got wrong, and it matters most

**Creating a WhatsApp Cloud inbox in Chatwoot repoints the number, immediately,
with no separate registration step.** Chatwoot sets a **per-phone-number
webhook override** on Meta, and that beats the app-level subscription:

```
webhook_configuration:
  phone_number: https://chat.../webhooks/whatsapp/+15551781261   <- wins
  application:  https://n8n-zqvb.../webhook/homies-whatsapp
```

Checking `GET /{app-id}/subscriptions` still showed n8n, so the cutover looked
un-done for two hours while it had in fact already happened. During that window
the bot was dead: every message reached Chatwoot, was forwarded to n8n, and was
rejected as `unsigned` by a signature check still looking for Meta's HMAC.

**So the safe order is not "changes, then repoint". It is "changes, THEN create
the inbox".** Creating the inbox IS the repoint. Check
`GET /{phone-number-id}?fields=webhook_configuration`, never the app
subscription, to find out where a number actually points.

## The changes

Read [feature.md](feature.md) for why Chatwoot owns the number at all.

## What is already built on the Chatwoot side

| thing | value |
|---|---|
| account | 2, named `CLIX` |
| inbox | 1, `Channel::Whatsapp`, `whatsapp_cloud`, `+15551781261` |
| agent bot | 1, "Homies bot", linked to inbox 1, status `active` |
| callback | `CHATWOOT_WA_CALLBACK` in `.env`, handshake verified 200/401 |
| bot credential | `CHATWOOT_BOT_TOKEN` in `.env` |

All inert: Meta still delivers to n8n.

**The number is a placeholder and is meant to be replaced.** `+15551781261` is
Meta's test number; a real Israeli DID takes its place before pilot. What
survives that swap and what does not:

| survives | changes |
|---|---|
| account, the four teams | the inbox's `phone_number` |
| agent bot 1 and `CHATWOOT_BOT_TOKEN` | `provider_config` -- phone number id, WABA id, token |
| `CHATWOOT_API_TOKEN`, admin login | `CHATWOOT_WA_CALLBACK`, because Chatwoot's callback path **contains the number** |
| every one of the four n8n changes below | the Meta subscription, which must be re-registered at the new callback |

So a number swap is a Chatwoot edit plus one Meta call, and touches n8n not at
all. That is worth stating because it is currently untrue: today's `Send` and
`Send menu` nodes have the phone number id **baked into their URLs**
(`graph.facebook.com/v21.0/1207299225801644/messages`). Change 3 removes it.
After the cutover n8n never names the number anywhere, which is exactly the
property you want in the thing that is about to be swapped.

Editing inbox 1 in place is preferred over creating a second one: the agent bot
link, the teams and any conversation history hang off the inbox id.

## Change 1 — the door. Signature check out, shared secret in

`WhatsApp` (webhook) → `Sign the raw body` (crypto) → `Sort`.

Meta signs every POST with `X-Hub-Signature-256`, an HMAC of the raw body keyed
on the app secret. Chatwoot does not send that header, so the check cannot be
kept -- and it must not simply be deleted either: without it the webhook is a
public URL that files service tickets for anyone who finds it, and the phone
number in the envelope decides whose ticket gets opened.

**Chatwoot does sign, and an earlier draft of this file said it did not.**
`lib/webhooks/trigger.rb` sends `X-Chatwoot-Signature`, an HMAC-SHA256 over
`${timestamp}.${body}`. Verifying it in n8n is currently not possible:
`require('crypto')` throws `Module 'crypto' is disallowed` in the task-runner
sandbox, and the Crypto node cannot prepend a timestamp to the RAW bytes --
re-serialising the parsed body does not reproduce them. So the shared secret
below is what shipped, and verifying the signature properly is the obvious
hardening once the Code node can hash.

The replacement is a secret in the query string, because Chatwoot's agent bot
sends a fixed URL and no custom headers — there is nowhere else to put one.

1. Set the agent bot's `outgoing_url` to carry it:
   `https://n8n-zqvb.srv1879140.hstgr.cloud/webhook/homies-whatsapp?s=<N8N_WEBHOOK_SECRET>`
2. **Delete the `Sign the raw body` node** and wire `WhatsApp` straight to
   `Sort`. It exists only to compute Meta's HMAC.
3. `rawBody` on the webhook node is now pointless but harmless. Leave it; a
   second reader may want the bytes.

The secret is compared in `Sort` (Change 2), fails closed, and answers 200
either way — a caller who is not Chatwoot learns nothing from the response.

## Change 2 — the parser. Chatwoot's envelope is not Meta's

Replace the whole of `Sort`'s code with the following.

Four things about it that are not obvious:

**It filters on three fields, not one.** Chatwoot posts every event to the same
URL: `message_created`, `message_updated`, `conversation_status_changed`, and
the bot's own outgoing messages. Answering any of those is a loop.

**`conversation.status` is the AI toggle**, and it is the whole reason for
moving to Chatwoot. `pending` means the bot owns the thread. The moment a human
replies, Chatwoot flips it to `open` — and the bot must go quiet on that
conversation while continuing to work on every other one. That is one line here
and it is the point of the exercise.

**The tapped id is gone.** Chatwoot keeps only the button title
(`incoming_message_service_helpers.rb` has a `TODO` admitting it), so routing
matches on the Hebrew label. **The titles below are load-bearing** — reword one
in the menu and the flow it starts silently stops starting.

**The menu is three buttons now, not four rows.** Decided 21 Aug. Chatwoot
builds the WhatsApp payload from its own fields and drops row descriptions and
the footer, and its list wrapper renders `Choose an item` in English (or
`בחר פריט`, masculine, in Hebrew) — both of which we control by staying at
three items, where WhatsApp shows the titles directly and there is no wrapper.
`יתרה ותשלומים` is the option that goes; the agent still answers balance
questions typed as words, and reading a balance out is gated on the identity
question anyway.

```js
// Chatwoot posts here, not Meta. One item, one event.
const item = $input.first().json;
const q    = item.query   || {};
const body = item.body    || {};

const SHARED = "REPLACE_WITH_N8N_WEBHOOK_SECRET";

// --- Is this actually from Chatwoot? --------------------------------------
// Chatwoot sends no signature of any kind, so the only thing separating this
// URL from a public ticket-filing endpoint is the secret in the query string.
// Fails CLOSED, and answers 200 regardless: a caller who is not Chatwoot must
// learn nothing from the response.
if (String(q.s || '') !== SHARED) {
  return [{ json: { _reply: '', _work: false, _rejected: 'bad secret' } }];
}

// --- Which events are ours ------------------------------------------------
// Everything Chatwoot does on this inbox arrives here. Three filters:
//   event         - only a new message; ignore edits and status changes
//   message_type  - only inbound; 'outgoing' is the bot's own words, and
//                   answering them is an infinite loop
//   private       - a private note is staff talking to staff
if (body.event !== 'message_created') {
  return [{ json: { _reply: '', _work: false } }];
}
if (body.message_type !== 'incoming' || body.private === true) {
  return [{ json: { _reply: '', _work: false } }];
}

const conv = body.conversation || {};
const convId = conv.id;

// --- The AI toggle, and the reason Chatwoot exists ------------------------
// 'pending' means the bot owns this thread. The moment a human replies in the
// inbox, Chatwoot flips it to 'open' and the bot must fall silent on THIS
// conversation while carrying on with every other one. There was nowhere for
// this fact to live when a webhook owned the number.
if (String(conv.status || '') !== 'pending') {
  return [{ json: { _reply: '', _work: false, _handedOver: true } }];
}

const sender = body.sender || {};
// E.164 with a leading +. Meta's `from` had no plus, so anything downstream
// that matches a phone must be checked against this shape once.
const from = String(sender.phone_number || '');
const id   = String(body.id || '');
const text = String(body.content || '');

// --- Duplicate suppression ------------------------------------------------
// On Chatwoot's message id now, not Meta's wamid. Same reasoning: stable
// across retries, and never on content, because a resident who sends the same
// word twice means it twice.
const store = $getWorkflowStaticData('global');
store.seen = store.seen || {};
const now = Date.now();
for (const k of Object.keys(store.seen)) {
  if (now - store.seen[k] > 86400000) delete store.seen[k];
}
if (store.seen[id]) {
  return [{ json: { _reply: '', _work: false } }];
}
store.seen[id] = now;

const lang = 'he';
const inText = text.trim() ? text : null;

// --- Has this handset already been spoken to? -----------------------------
// Unchanged in purpose: the menu and the canned lines never reach the model,
// so without this the agent introduces itself twice.
store.greeted = store.greeted || {};
const greeted = store.greeted[from] === true;
store.greeted[from] = true;

// Media, location and stickers arrive as an attachment with empty content.
if (!text.trim()) {
  return [{ json: {
    _reply: '', _work: false, _canned: true, _menu: false,
    to: from, conv_id: convId, lang,
    text: "אני קורא כאן רק טקסט. אפשר לכתוב לי מה קרה?",
    in_text: inText, msg_type: 'attachment', message_id: id,
  } }];
}

// --- A tapped button ------------------------------------------------------
// Chatwoot discards the button id and sends the TITLE as the message content,
// so these strings are the routing table. Keep them identical to the menu
// below, or a tap stops starting its flow and quietly falls through to the
// model instead.
const TAPPED = {
  "פתיחת קריאת שירות": "בסדר. מה התקלה?",
  "מצב קריאה קיימת":   "מה מספר הקריאה? אפשר גם רק את הספרות האחרונות — ואם אין מספר, בניין ודירה.",
};
const canned = TAPPED[text.trim()];
if (canned) {
  return [{ json: {
    _reply: '', _work: false, _canned: true, _menu: false,
    to: from, conv_id: convId, lang, text: canned,
    in_text: inText, msg_type: 'interactive', message_id: id,
  } }];
}

// "לדבר עם נציג" is deliberately absent above: it falls through to the agent,
// which calls transfer_to_human and says the right thing on the way out.

// --- A greeting, and nothing else -----------------------------------------
// Someone who opens with "שלום" has told us nothing, so offering choices is
// useful. Someone who opens with "there's a leak in the lobby" has told us
// everything, and a menu there would undo the rule the prompt is built on: do
// not ask what happened when you have already been told.
const bare = text.trim()
  .replace(/[\p{Extended_Pictographic}️]/gu, '')
  .replace(/[\s!?.,־-]+$/u, '')
  .trim().toLowerCase();
const GREETING = new RegExp(
  '^(שלום|שלום רב|היי|הי|אהלן|אהלן וסהלן|יו|מה נשמע|מה קורה|בוקר טוב|צהריים טובים|' +
  'ערב טוב|לילה טוב|hi|hii|hey|hello|yo|good morning|good afternoon|good evening|' +
  'shalom|ahlan)$', 'u');

// Three items, so Chatwoot sends reply buttons and not a list. `items` and
// `content` are Chatwoot's field names, not WhatsApp's -- Chatwoot builds the
// WhatsApp payload itself from these.
const MENU = {
  content: "היי, כאן שירות הלקוחות של הומיז. במה אפשר לעזור?",
  items: [
    { title: "פתיחת קריאת שירות", value: "open" },
    { title: "מצב קריאה קיימת",   value: "status" },
    { title: "לדבר עם נציג",      value: "human" },
  ],
};

if (GREETING.test(bare)) {
  return [{ json: {
    _reply: '', _work: false, _canned: false, _menu: true,
    to: from, conv_id: convId, text, lang, message_id: id,
    in_text: inText, msg_type: 'text', menu: MENU,
  } }];
}

return [{ json: {
  _reply: '', _work: true, _canned: false, _menu: false,
  to: from, conv_id: convId, text, lang, greeted, message_id: id,
  in_text: inText, msg_type: 'text', followup: {
    content: "עוד משהו?",
    items: MENU.items,
  },
} }];
```

## Change 3 — the reply path. Two nodes stop talking to Meta

`Send` and `Send menu` both POST to
`https://graph.facebook.com/v21.0/1207299225801644/messages` today. **They must
not after the cutover**, and the reason is not that it would fail — it is that
it would *work*. The reply would reach the resident and never appear in the
conversation the staff are watching, which is a one-sided transcript and the
exact failure Chatwoot is being introduced to prevent.

Both become one Chatwoot call.

**`Send`** — plain text:

```
POST https://chat.srv1879140.hstgr.cloud/api/v1/accounts/2/conversations/{{ $('Sort').item.json.conv_id }}/messages
header  api_access_token: <CHATWOOT_BOT_TOKEN>
body    {{ JSON.stringify({ content: $json.output || $json.text, message_type: 'outgoing' }) }}
```

**`Send menu`** — the three buttons. Same URL, different body:

```
{{ JSON.stringify({
     content: $json.menu.content,
     message_type: 'outgoing',
     content_type: 'input_select',
     content_attributes: { items: $json.menu.items }
}) }}
```

Notes that will cost an afternoon otherwise:

- **Use `CHATWOOT_BOT_TOKEN`, not `CHATWOOT_API_TOKEN`.** The admin token
  works, but every reply is then attributed to a person rather than the bot,
  and the inbox cannot show who said what.
- **`conv_id` is `conversation.id` from the webhook**, which is the *display*
  id — the number in the agent's URL bar. It is not the same as the internal
  primary key, and the API path wants this one.
- **`content_type: 'input_select'` is what triggers buttons.** Anything ≤3
  items becomes reply buttons; 4+ silently becomes a list with an English
  wrapper label. Stay at three.
- Store the token as an n8n **Header Auth** credential, the way
  `N8N_TOOLSECRET_CRED_ID` already is. Not in the node.

## Change 4 — `scripts/check_whatsapp.py`

It posts a synthetic **Meta** envelope at the n8n webhook and then looks for the
row. The envelope has to become Chatwoot's shape and carry `?s=`, or the
end-to-end test goes red against a working system. Everything it asserts about
Supabase stays true.

## Order of operations

1. Changes 1–3 in n8n. Save, do not activate anything new.
2. Change 4, and run it. **It should pass before Meta knows anything.** This is
   the whole safety net: the new path is proved with a synthetic message while
   the old path still carries real ones.
3. Repoint Meta's callback at `CHATWOOT_WA_CALLBACK`.
4. Send a real WhatsApp message. Expect: a conversation in Chatwoot, a reply
   from "Homies bot", and a row in `messages`.
5. Reply as a human from the Chatwoot inbox and confirm the bot goes quiet on
   that thread and only that thread.

Step 5 is the acceptance test for the entire project, not a nicety. It is the
capability that could not be built on a webhook.
