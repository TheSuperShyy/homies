# WhatsApp message templates — the fixed messages, and why they are fixed

Meta lets a business write freely to a person only inside 24 hours of that
person's last message. Anything sent after that window is refused unless it is
a **message template**: a fixed text, submitted to Meta in advance and
approved, with numbered variables. That is a Meta rule, not a design choice.

The owner's standing rule for this bot is *no fixed message except the menu*.
Every template on this page is an exception to it made on purpose, by the
owner, because the message has to reach someone who has not written to us
today and Meta permits nothing else. Each one says who decided and when.

`scripts/wa_templates.py` reads this file: `create <name>` submits the
section of that name to the WhatsApp Business Account in `.env`
(`WHATSAPP_WABA_ID`, token `WHATSAPP_ACCESS_TOKEN`), `list` shows what Meta
thinks of it. Templates belong to the WABA, so **at cutover to Homies' own
number every one of them has to be created again on Homies' WABA**, from this
same file.

Fields per template: `name` (Meta's rules: lowercase, digits, underscores),
`category` (UTILITY for service notices), `language` (`he`), `body` (the text
with `{{1}}`, `{{2}}`… — no newlines inside a variable, no variable at the
very start or end, Meta rejects both), `examples` (one sample value per
variable, which Meta's reviewers read).

---

## ticket_resolved_he

- **What:** the "done" message — sent once, when a service call opened from
  WhatsApp is set to resolved, to the number that opened it.
- **Decided:** owner, 22 Sep 2026 ("help me setup a templated message for
  the done when the ticket has been resolved"; wording chosen from three
  options: reference + what it was + write back).
- **Sender:** `send_ticket_notices` in the Edge Function, fed by the
  `ticket_notices` outbox (migration 036), driven by the n8n cron
  `Homies — ticket notices`.
- **category:** UTILITY
- **language:** he
- **body:**

```
שלום, כאן מיכאל מהומי'ז. הקריאה שלכם מספר {{1}} ({{2}}) טופלה ונסגרה. אם משהו עדיין לא בסדר, פשוט כתבו לנו כאן.
```

- **variables:**
  - `{{1}}` — the ticket reference, Homies' own format (`255-1294-26`)
  - `{{2}}` — the fault in a few words: `requests.description`, the resident's
    own words, cut at 80 characters
- **examples:** `255-1294-26` · `ריח רע בחניון`
