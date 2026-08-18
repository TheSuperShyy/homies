# Connecting Homies' number to Meta — the AnyDesk session

A runbook for one screen-share with the client. Written 14 Aug, not yet run.

The order matters: business verification is slow and everything downstream waits
on it, and the phone number cannot be added while it is still live on the
WhatsApp Business app. Both are worth settling before the call rather than
discovering during it.

**The one decision to make first: whose Business Manager owns this.** If the app
and the WABA sit in our account, Homies does not own their own WhatsApp
presence, and moving a number between Business Managers later is considerably
harder than starting in the right one. The recommendation is Homies' account,
with us added as a partner — the same argument that moved the database.

## Before the call — the client brings

- A Facebook account that is an **admin** of Homies' Business Manager
- Company registration document
- Bank statement or utility bill showing the company address
- The phone number for the bot, **not currently active on WhatsApp**
- Somebody able to answer an SMS or voice call on that number
- A decision on the **display name** residents will see
- Company website, address and email for the business profile

## During the call — in this order

1. Create or confirm the Meta Business Account
2. Submit business verification
3. Create the WhatsApp Business app
4. Create the WhatsApp Business Account (WABA)
5. Add the phone number and verify it by code
6. Set the display name
7. Create a **system user** and grant it access to the WABA
8. Generate a **permanent** token with `whatsapp_business_messaging` and
   `whatsapp_business_management`
9. Switch the app from Development to **Live**
10. Add us as a partner or developer on the app

## The five values to capture

| Key | Where it comes from |
|---|---|
| `APP_ID` | app settings |
| `APP_SECRET` | app settings, basic |
| `WHATSAPP_WABA_ID` | WhatsApp account overview |
| `WHATSAPP_PHONE_NUMBER_ID` | API setup, next to the number |
| `WHATSAPP_ACCESS_TOKEN` | the system user token from step 8 |

`WHATSAPP_WEBHOOK_VERIFY_TOKEN` is ours and does not change.

**They go straight into `.env` and nowhere else.** Not into chat, not into a
document, not into a message to anybody. `APP_SECRET` is the app's password and
`WHATSAPP_ACCESS_TOKEN` can send messages as Homies to any resident.

## After the call — by script, no dashboard

1. `POST /{app-id}/subscriptions` — register the callback, object
   `whatsapp_business_account`, fields `['messages']`. Takes an app access
   token, so this needs no human.
2. `POST /{waba}/subscribed_apps` — let the account deliver to the app. Needs
   the **system user** token, not the app token. This is the one that was
   silently missing on 11 Aug and cost an afternoon.
3. `python scripts/n8n_whatsapp.py --apply` — redeploy against the new
   `WHATSAPP_PHONE_NUMBER_ID`
4. `python scripts/check_whatsapp.py` — callback active, token valid and
   non-expiring, WABA subscribed, and a forged message refused
5. One real message from a handset

## Three things that will bite

**The number cannot already be on WhatsApp.** If Homies runs the WhatsApp
Business app on it today, it has to be deleted from there first, and that erases
the chat history on that number. Ask before the call, not during it.

**Business verification takes days.** The number may not go live on the same
session. Everything up to step 6 can be done anyway, so the call is still worth
holding.

**The token on the API Setup page expires in 24 hours.** It works, which is what
makes it dangerous — the bot goes live, works all afternoon, and stops overnight.
Step 7 exists precisely to avoid it. `check_whatsapp.py` asserts the token has no
expiry for the same reason.

## What is not needed yet

Message templates. They are required only for messages **we** start outside the
24-hour window, and the bot only ever replies. This becomes blocking the day
debt follow-up moves to WhatsApp, not before.
