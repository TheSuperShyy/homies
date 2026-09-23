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

---

## payment_link_he

- **What:** the payment link a resident agreed to on a debt call. A debt call
  is outbound — we ring someone who has not written to us — so Meta's 24-hour
  window is shut by default and the free-text link is refused. This template
  is the only way that link reaches them during the call.
- **Decided:** owner, 23 Sep 2026, after the "done" message was proven end to
  end. The limit was recorded on 20 Sep in the Edge Function itself: *"Meta
  accepts free-form text only inside 24 hours… the template is the fix,
  later."* Wording chosen from three (*"i want the combination of a and b"*):
  the callback to the call, which is what stops it reading as spam, **and** the
  line saying the link is personal — it opens that apartment's own balance, and
  a forwarded link shows a neighbour the lot. The flow itself does not change:
  *"we need to maintain the current flow we have, the call then send the
  payment link in whatsapp after"* — no outreach, no messaging first.
- **Sender:** `send_payment_link` in the Edge Function, on `outside_window`
  only, into the conversation the free-text attempt already resolved. Inside
  the window nothing changes: the model-written line plus the link goes as
  ordinary text, which reads better than a fixed form.
- **Why the link is a body variable:** WhatsApp's tidier shape is a URL button
  with a dynamic suffix, and we cannot use it. OXS mints an opaque link and its
  contract says to use it verbatim (`docs/reference/oxs-payment-link.md`), so
  we do not know which part varies; and neither `wa_templates.py` (submits one
  BODY component) nor Chatwoot's message payload (`processed_params`, a flat
  body map) can carry button parameters.
- **category:** UTILITY
- **language:** he
- **body:**

```
שלום, כאן מיכאל מהומי'ז. כמו שסיכמנו בשיחה, זה הקישור לתשלום ועד הבית עבור {{1}} בסך {{2}} ₪: {{3}} הקישור אישי ומיועד לדירה שלכם בלבד. אם משהו לא ברור, פשוט כתבו לנו כאן.
```

- **variables:**
  - `{{1}}` — the months owed, in Hebrew (`monthsHe(periods)`, joined)
  - `{{2}}` — the amount, digits only; the ₪ is in the fixed text
  - `{{3}}` — the OXS payment link, verbatim. **Never written to a log, never
    read aloud, never printed whole anywhere.**
- **examples:** `יולי 2026` · `450` · `https://example.com/pay/sample`
