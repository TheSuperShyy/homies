# 16 — Setting up a representative's PC for handover alerts

One page per seat. Five minutes. Done once per PC and browser profile.

## What arrives, and how

When the bot hands a WhatsApp conversation to a department, it posts a private
note in Chatwoot that @mentions that department's team. Chatwoot turns the
mention into three things for every member of the team:

| Channel | Where it shows | Needs |
|---|---|---|
| Browser push | a Windows toast, bottom-right, even with the Chatwoot tab in the background | push enabled once (below), the browser running |
| Bell | the badge on the bell in Chatwoot's top bar and the count in the tab title | the tab open |
| Email | the seat's mailbox | live since 6 Sep (Brevo relay) |

The push is the alert. The bell is what you check. Email is the safety net
for a closed browser.

## Steps

1. Open `https://chat.srv1879140.hstgr.cloud` in **Chrome or Edge** and log in.
2. Click your avatar (bottom-left) → **Profile settings** → **Notifications**.
3. Under push notifications, switch on **"Enable push notifications for your
   browser"**. The browser asks for permission: choose **Allow**. If nothing
   asks, the site is already blocked: click the padlock in the address bar →
   Notifications → Allow, reload, try again.
4. Push column: tick **A conversation is assigned to you**, **You are
   mentioned in a conversation** (the handover alert) and **A new message is
   created in an assigned conversation** (the resident's replies once the
   thread is yours). Leave **A new conversation is created** unticked: with
   it on, every bot conversation pings you at its first bot reply. Leave
   **participating conversation** unticked: it fires for any thread you ever
   wrote a note in.
5. Email column: tick **assigned to you** and **mentioned** only, for the day
   SMTP is set.
5a. An administrator adds the seat to **both** inboxes — *WhatsApp — Homies*
   and *Homies — Voice* (Settings → Inboxes → Collaborators). A mention on
   an inbox you are not a member of is dropped in silence: no toast, no
   email, nothing in Mentions (measured 6 Sep on the first seat).
6. Audio: either off, or scoped to **conversations assigned to me**. Never
   "all" or "unassigned": in this inbox every bot thread is unassigned, so
   those scopes ring on every resident message everywhere. The two
   conditions (only when the window is not active; repeat every 30 s until
   read) are fine with the "assigned to me" scope.
7. Install Chatwoot as an app. This is the browser wrapping the website in
   its own window; nothing is installed on the server, and it works the same
   for a self-hosted Chatwoot on a VPS as for any other site. Chrome: the
   install icon at the right end of the address bar, or menu (⋮) → **Cast,
   save, and share** → **Install page as app**. Edge: menu (…) → **Apps** →
   **Install this site as an app**. Then in the app's own menu → App
   settings → **Start app when you sign in**. Now the browser engine is
   running from the start of the shift and toasts arrive with the window
   closed.
8. Windows: Settings → System → Notifications → make sure Chrome/Edge is
   allowed, and **Focus assist / Do not disturb is off** during office hours.

## The one-minute test

Ask an administrator to open any test conversation, write a private note
(the "Private note" tab in the reply box) containing `@` + your name, and send
it. Within a few seconds: a toast on your screen, and the bell badge goes up.
No toast → step 3 or 8. Toast but no badge → refresh the tab. First passed
on the owner's PC on 3 Sep.

## If no toast arrives

The toggle in Chatwoot can show ON while the browser never finished
registering; the server then has no subscription to push to (3 Sep: zero
subscriptions on the instance after the toggle looked on). Check, in order:

1. Address bar padlock → Notifications must say **Allow**. Chrome's quiet
   prompt (a crossed bell icon in the address bar) counts as not allowed.
2. Press F12 on the Chatwoot tab → Console, and paste:
   `Notification.permission` → must print `"granted"`.
3. Paste: `navigator.serviceWorker.ready.then(r => r.pushManager.getSubscription()).then(s => console.log('subscribed:', !!s))`
   → must print `subscribed: true`. If `false`, paste:
   `navigator.serviceWorker.ready.then(r => r.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: window.chatwootConfig.vapidPublicKey })).then(s => console.log('ok', s.endpoint)).catch(e => console.error(e))`
   and read the error. `AbortError: Registration failed - push service error`
   means the browser cannot reach its push service: in **Brave**, turn on
   Settings → Privacy → "Use Google services for push messaging"; behind a
   VPN or proxy, allow `fcm.googleapis.com` (Chrome) or
   `*.notify.windows.com` (Edge).
4. Then in Chatwoot switch the push toggle OFF and ON again. An
   administrator can confirm the registration reached the server
   (`NotificationSubscription.count` goes up by one).
5. Windows: Settings → System → Notifications → the browser is allowed, and
   Focus assist is off.

This is what happened on the owner's PC on 3 Sep: toggle ON, no subscription
on the server, every push job finishing in 100 ms with nothing to send.
Re-enabling push registered the subscription, and the next mention arrived
as a toast.

## Taking a handover

A paged conversation appears in two places in the left sidebar: **Mentions**
and **Participating**. Both fill the moment the note lands, before anyone is
assigned. That is where to look for work that is yours.

The note says which team was paged, why, the phone number and the last things
the resident wrote. Open the conversation and **reply to the resident**. Your
first reply claims the thread; the bot goes quiet on it from that moment. If
you handle it by phone instead, **resolve** the conversation or reply once,
or the escalation keeps running: after 10 minutes unanswered, the team is
paged again together with Management; after 15 more, every team. Clicking
"assign to me" does **not** stop the escalation -- only an actual reply to the
resident does, because a reply is what Chatwoot records as answering.

Out of office hours (Sun–Thu 09:00–17:00) nothing is paged; the conversation
waits with the `after-hours` label and the department is paged at 09:00.

**A voice note** (inbox *Homies — Voice*, since 14 Sep) is a phone call the
bot has already finished. Nothing you type there reaches the caller. The note
carries what they said, the number if the call had one, and the building and
apartment if they gave them: **phone the resident, then press Resolve**. An
emergency voice note escalates like a WhatsApp one until it is resolved or
replied to.

## Known limits

- A toast only arrives while Chrome/Edge (or the installed app) is running.
  Step 7 is what makes that the default.
- The Chatwoot mobile app is not part of this setup.
- SMTP went live 6 Sep (Brevo's free relay); invites and password resets
  work by email now. An administrator can still create a seat in
  `/super_admin` with a set password if email delivery to that address is in
  doubt.
