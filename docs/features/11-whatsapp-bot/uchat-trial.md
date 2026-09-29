# UChat trial: WhatsApp numbers, and how the test copy is set up

Written 29 Sep 2026 for whoever sets up or continues the UChat trial. Why we
are trying UChat at all, what it costs and the recommendation are in
[context.md](context.md), "29 Sep".

## The short version

- **UChat does not provide WhatsApp numbers.** A number has to be registered
  with Meta (the WhatsApp Business Platform) under a Meta business account.
  UChat only connects to it.
- **Never connect our current test number or Homies' official number to
  UChat.** Connecting a number moves its messages to UChat on the spot, and the
  live bot goes silent.
- **The look-and-feel test needs no WhatsApp at all.** It runs on UChat's web
  chat widget.

## Two ways UChat connects a number

| Way | What you do | Use it? |
|---|---|---|
| **WhatsApp Cloud** (the left sidebar, or the Cloud option in the Provider list) | Log in with Facebook, pick or create the Meta business, and Meta's own sign-up verifies the number by SMS or a call. | **Yes.** This is the current way. |
| **"WABA (Deprecated)"** in the *Add WhatsApp Number* screen | Build an app on Meta's developer site yourself, then paste its access token, WhatsApp Business Account ID, phone number ID and API domain. | **No.** UChat marks it deprecated. |

Either way the number is registered with Meta. The only difference is whether
Meta's steps are guided or done by hand.

## What a number needs

- It must not be active on the ordinary WhatsApp or WhatsApp Business app.
  UChat's own docs say either delete that account first or use a different
  number.
- It must be able to receive Meta's verification SMS or call.
- It sits under a Meta business account.
  - Business verification is not needed to start.
  - An unverified business can answer people who write first.
  - It can only *start* a limited number of conversations a day.
- UChat adds no fee per message. Meta's own WhatsApp fees apply, the same as on
  any platform.

## Why the two numbers we have are off-limits

**How Meta routes messages.**
- Meta delivers each number's messages to exactly one place.
- When a platform connects a number, it writes an override on that number, and
  that override outranks every other setting, with no warning.

**How we learned it.** On 21 Aug, creating the WhatsApp inbox in Chatwoot moved
our test number that way. The bot was silent for two hours while every other
setting still pointed at it. See CONTEXT.md, "Creating a WhatsApp inbox in
Chatwoot IS the cutover".

**The same would happen with UChat.** Connecting the same number would do it
again to today's bot. So:

- **Our test number stays on Chatwoot.** Its access token and IDs exist on our
  side, and they must never be pasted into the screen above.
- **Homies' official number is not ours to connect.** It is still answered by
  the old ManyChat router, and moving it needs the client and whoever holds the
  "office homies" Meta account.

## If the copy is worth seeing on WhatsApp

Only after the web widget test looks worth it:
- Use a **spare number**, either a new SIM or a virtual number.
- It must never have been on WhatsApp, and must be able to take the SMS or call.
- Connect it through **WhatsApp Cloud**.

## The look-and-feel test, step by step

The owner chose **Gemini, no tools** on 29 Sep. Gemini is the same model as the
live bot. With no tools, the copy reaches no data at all.

1. **Gemini key.**
   - It's free from Google AI Studio (aistudio.google.com/app/apikey) and needs
     no card.
   - Paste it into UChat under **Integrations → Gemini**. Their API has no call
     for this step.
   - Google may train on free-tier chats, so type test messages only.
   - The OpenRouter key cannot be used:
     - UChat has no OpenRouter provider.
     - Its OpenAI connection has no field for a different address.
     - That key pays for the live bot.
   - Groq's free tier cannot run the bot either: its limit is 6,000 tokens a
     minute and the prompt alone is 7,359.
2. **AI agent.**
   - **Instructions:** the contents of `local/uchat/agent-prompt.txt`. Don't use
     their "Generate Agent Prompt" button, because it replaces the text.
   - **Model:** `gemini-2.5-flash`, temperature 0.6.
   - **Leave out** functions, tasks, knowledge base and MCP.
3. **Start flow.**
   - The message is `שלום 👋 במה אפשר לעזור?`, with three buttons: פתיחת
     קריאת שירות, מצב קריאה קיימת and לדבר עם נציג.
   - Each button goes to the agent, and so does the default reply.
   - The live bot opens with a greeting that follows the hour. The copy always
     says שלום, which is the live bot's own form after midnight.
4. **Web chat widget.** Turn it on and chat through its preview.
5. **Then, from our side:**
   - Set the model and reply length through the API
     (`POST /flow/update-ai-agent-provider`, max_tokens 4096, because thinking
     shares that budget).
   - Read the setting back.
   - Run six test messages on the bot's known hard cases:
     - a second greeting;
     - a hello in the middle of a conversation;
     - a fault report;
     - "who are you";
     - a balance question;
     - "hello good afternoon".

### The prompt file

`local/uchat/agent-prompt.txt` is gitignored, so a fresh clone does not have it.
To rebuild it:
- Take the `## System prompt` section of [prompt.md](prompt.md) exactly. On 29
  Sep it was 19,663 characters, fingerprint `8afa16824480`, the same as the live
  bot.
- Append this demo note unchanged:

```
## גרסת הדגמה
זו גרסת הדגמה בלי כלים. אינך יכול לבצע שום פעולה, ואינך רואה שום מידע על דיירים, קריאות או תשלומים. כשהשיחה מגיעה לפעולה כזו, אמור בפשטות שבגרסת ההדגמה הזו זה לא זמין, והמשך את השיחה כרגיל. אל תמציא מספרים, סכומים, תאריכים או קישורים. כל שאר ההנחיות למעלה חלות כרגיל.
```

The note exists because a bot with no tools invents actions. That is the exact
27 Sep bug, when the bot claimed it had replaced bulbs. The note names no
action to avoid, because a model that is shown a phrase tends to write it.

## Where things are

- **Workspace:** "clix".
- **API key:** `.env`, `Uchat_api_key`, with the Manage Flow ability only, so it
  cannot add or remove team members.
- **API spec:** `https://www.uchat.com.au/default-api-docs/api-docs.json`, 240
  paths.
  - It cannot create an AI agent or a flow. Both are made in the dashboard.
  - Everything after that is reachable through it: model and limits, MCP tools,
    agent groups, sending, and pausing the bot for any number of minutes.

## Sources

- UChat, WhatsApp Cloud API: https://docs.uchat.com.au/guide/cloudapi.html
- UChat, connecting channels: https://docs.uchat.com.au/guide/setup-create.html
- UChat, API authorization: https://docs.uchat.com.au/for-developers/API/
- Gemini API pricing and free tier: https://ai.google.dev/gemini-api/docs/pricing
