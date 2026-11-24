# Moving the WhatsApp bot to Homies' own number (077-668-7949)

Prepared 23 Nov 2026. The owner: *"so right now just prepare everything but dont disconnect everything"*. Only the
read-only checks below have run. ManyChat still answers on Homies' number, and our bot is still on the test number.

## Where things stand (read 23 Nov, about 10:50 UTC)

| | |
|---|---|
| Their WhatsApp account | "הומי'ז ניהול ואחזקת מבנים" (WABA …0527, business …2992), approved, business **not verified** (141010) |
| Their number | …8637, CONNECTED on the Cloud API, quality GREEN, display name approved. Already registered, so **no PIN** |
| Our access | system user "CLIX", app HOMIES, never expires; `.env` `HOMIES_WHATSAPP_TOKEN` and `HOMIES_WHATSAPP_WABA_ID` |
| Templates on their account | the four (`ticket_resolved_he`, `payment_link_he`, `homies_hello_he`, `homies_message_he`) **APPROVED** |
| Connected to their number | **ManyChat** only (its own app, no override). The webhook settings of their HOMIES app are empty |
| Our bot today | Chatwoot inbox 1 on "hadas 1" (+972…029) with our token |

## The switch: one sitting, after hours, about 10 minutes

0. **Preflight:** `python scripts/switch_to_homies.py`, read only. Every line as above, and `validates : True`.
1. **ManyChat stops answering on WhatsApp** (Homies, or the owner in ManyChat). Disconnecting WhatsApp in ManyChat takes
   its app off the number. Turning its automations off keeps it connected, and then step 2 needs `--manychat-is-off`.
   Otherwise both bots answer every message.
2. **`python scripts/switch_to_homies.py --apply --app-is-published`** (add `--manychat-is-off` if ManyChat stays
   connected). It does:
   - inbox 1 → their number, number id, account and token, with the verify token kept;
   - Chatwoot's `register_callback` with that token, which subscribes their HOMIES app and points their number at
     Chatwoot;
   - the template sync.
   If a step fails, inbox 1 is back on the test number in the same run.
   - Then the script sets their app's own webhook with `HOMIES_APP_SECRET`: the callback is the override just set,
     with inbox 1's verify token and the `messages` field. `--apply` refuses without the secret, unless
     `--app-webhook-by-hand`, and `--restore` removes it.
3. **The typing dots:**
   - `python scripts/n8n_whatsapp_tohomies.py --dump F`;
   - then `python scripts/check_whatsapp_rules.py --candidate F --replay`, which must be all green;
   - then `--apply`, which makes the n8n credential with their token once;
   - then the check on live.
4. **Proof, from a phone:**
   - "היי" to 077-668-7949 gets the bot's greeting and menu;
   - a template from Chatwoot (the "ticket closed" one) reaches the owner's phone;
   - Chatwoot shows delivered and read.
5. **Nothing else names the number:**
   - replies, ticket notices and payment links go through inbox 1, and so does the debt call's link
     (`WHATSAPP_VIA=chatwoot`);
   - the memory key is the tenant's number;
   - `.env`'s `WHATSAPP_*` stay ours;
   - the number watch keeps watching the test number.

## Rollback

1. `python scripts/n8n_whatsapp_tohomies.py --restore`.
2. `python scripts/switch_to_homies.py --restore`:
   - inbox 1 goes back to the test number, with our token (checked against the snapshot) and our `register_callback`;
   - with their token, their number's redirect is cleared and their HOMIES app comes off their account.
3. ManyChat's WhatsApp replies back on.

## Still needed from Homies before the switch

- **Their HOMIES app published.** Seen 23 Nov on its WhatsApp setup page: *"Apps will only be able to receive test
  webhooks sent from the app dashboard while the app is unpublished. No production data … will be delivered unless the
  app has been published."*
  - Unpublished, the switch would leave the number silent.
  - Publishing changes nothing for ManyChat, which runs through its own app, so it goes first.
  - Logged in to their Meta: App settings → Basic, then Publish in the left menu.
    - The category is not set, and the icon is the default (read with the app secret).
    - The privacy policy, a public Google Doc "Privacy Policy – HOMIES", is already set.
    - Add a data-deletion URL if the Publish page asks for one.
  - The callback URL and verify token on that page stay empty: step 2 sets them.
  - `--apply` needs `--app-is-published`, since the app's mode can't be read from here.
- ~~Their HOMIES app's secret~~ **in `.env` since 23 Nov 13:19 UTC** (`HOMIES_APP_ID`, `HOMIES_APP_SECRET`).
  - Checked: it opens their app, whose own webhook is still empty.
  - The app's webhook is needed: Meta's docs subscribe webhook fields at the app level, and the WABA subscription
    documents none of its own (read 23 Nov).
  - Step 2 sets it.
- ~~`HOMIES_WHATSAPP_WABA_ID` empty again~~ **back since 14:07 UTC**, found through the number's own
  `health_status`. Both dry runs are green (14:08 UTC), and nothing more is needed from Meta.
- Who turns ManyChat's WhatsApp off at the switch, and when (the switch time).
- At least one person per department signed in to Chatwoot. Today every mention reaches only the owner's login.
- ~~The OK for OXS tickets for every tenant.~~ Given 24 Nov, and every tenant's ticket goes into OXS since 09:22 UTC
  (`oxs_mirror_list.py --every-tenant`).
- Business verification, later. Until then, at most 250 people a day for messages we start. Replies are not limited.

## Notes

- Chatwoot 4.16's `register_callback` (read on the server, 23 Nov):
  - `POST /{waba}/subscribed_apps` with `subscribed_fields` messages and smb_message_echoes;
  - then the phone-level `override_callback_uri` to `<chatwoot>/webhooks/whatsapp/<number>`, with the inbox's verify
    token.
  - Registration with a PIN is only in `perform`, which this does not call.
  - If no message arrives after step 2, the first place to look is their HOMIES app's WhatsApp → Configuration page,
    whose webhook settings are empty.
- Contacts and conversations stay in inbox 1. A test contact who writes to the new number continues their thread.
- The gate ran on the would-be workflow on 23 Nov: all green, and 1,620 past replies unchanged.
