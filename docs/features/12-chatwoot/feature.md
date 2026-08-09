# 12 — Chatwoot — the shared inbox

The thing PRD item 3 is actually asking for. See
[11-whatsapp-bot/prd.md](../11-whatsapp-bot/prd.md) for the requirement and the
gap map; this file is how it gets built.

## Why a product and not more n8n

Five of the six required capabilities are inbox features, not bot features:
seats, department routing, transfer between agents, open/closed status, and
turning the AI off for one conversation. None of them can be retrofitted onto a
webhook, and the reason is structural rather than effort: **a webhook answers
every message by definition.** There is no seat to assign a conversation to, no
second participant to hand it to, and nowhere for "the bot is off for this
thread" to live.

Meta's Cloud API delivers to exactly one callback URL. Whatever owns that URL
owns the inbox. So the choice is not *whether* something sits between Meta and
n8n — it is what.

## The shape

```
        now                             after
  Meta ─→ n8n ─→ reply           Meta ─→ Chatwoot ─→ n8n (agent bot) ─→ reply
                                            │
                                            ├─ agents, seats, teams
                                            ├─ conversation status
                                            └─ human takes over → bot goes
                                               quiet on THIS conversation
```

**n8n does not disappear and the bot does not change.** The agent, the prompt,
the two tools and the Supabase writer all stay exactly as they are. What changes
is who calls them: Chatwoot, as an *agent bot*, instead of Meta directly. That
is the whole reason this is affordable — a day's work at the seam, not a
rebuild.

**Chatwoot owns the number.** Decided 8 Aug. The alternative — n8n keeps the
number and Chatwoot mirrors conversations read-only — is less disruptive today
and leaves the AI toggle and real handover permanently impossible, which are two
of the six things being asked for.

## Hosting

Self-hosted on Hostinger, decided 8 Aug alongside the above. At 19 staff,
Chatwoot Cloud is $19/agent/month — about **$361/month**, against a VPS at
roughly $7–15. The trade is upgrades and backups becoming ours, which is the
same trade already made for n8n on the same provider.

Files live in [deploy/chatwoot/](../../../deploy/chatwoot/):
`docker-compose.yml` and `env.example`.

### The box it goes on

**srv1879140.hstgr.cloud — `186.240.147.235` — the same VPS that runs n8n.**
KVM 2, and on 8 Aug it was sitting at 11% memory and 4% disk, so there is
room. A second VPS buys isolation for another $7–15/month; the same box is the
cheaper call at this size, with one condition attached below.

**It is already running Traefik.** Port 80 answers a bare `301 Moved
Permanently` with no `Server` header, which is Traefik's signature and is what
Hostinger's n8n template ships. So Chatwoot brings **no proxy of its own** — a
second one would fight for 443, and the process that loses to bind might be the
one serving n8n. It attaches to the existing Traefik by labels instead.

**The condition: memory limits.** This box runs the bot. If Rails leaks under
load on 2 vCPU, the OOM killer picks its victim by size, and without a ceiling
that victim can be n8n — taking WhatsApp down to fix nothing. `rails` is capped
at 2g and `sidekiq` at 1g in the compose file for that reason and no other.

Behaviour confirmed from outside on 8 Aug, which is as far as it can be pinned
without a shell:

```
:80   any host        -> 301 to https://<same host>/
:443  n8n's hostname  -> 200
:443  unknown host    -> 404
```

A host-routing proxy with no `Server` header that 404s unmatched names. That is
Traefik's signature. **Confirm with `docker ps` before deploying** — the hPanel
tile says the n8n application is "1 container", so the proxy is either outside
that app or managed by Hostinger, and which one decides whether the labels in
the compose file do anything at all.

**The hostname needs no DNS work at all.** `*.srv1879140.hstgr.cloud` is a
wildcard — checked 8 Aug, every name under it already resolves to
`186.240.147.235`:

```
srv1879140.hstgr.cloud                      -> 186.240.147.235
n8n-zqvb.srv1879140.hstgr.cloud             -> 186.240.147.235
chat.srv1879140.hstgr.cloud                 -> 186.240.147.235
anything-random-xyz.srv1879140.hstgr.cloud  -> 186.240.147.235
```

So `chat.srv1879140.hstgr.cloud` is usable immediately, with no A record and no
domain purchase. Let's Encrypt's HTTP-01 challenge only needs the name to point
at a box we control on port 80, not ownership of the zone, so the certificate
issues normally.

The bare hostname answers **404** on 443, meaning nothing is routed to it yet —
it is free, but a subdomain is the better habit: it leaves the bare name for
whatever comes next.

hPanel's **Claim your free domain** is therefore not a blocker and not required.
Worth doing later for a URL ~19 staff log into daily, and a rename after the
fact costs one `FRONTEND_URL` change, a Traefik label, and re-registering the
Meta callback. Cheap, but not free — so if Homies already owns a domain, use it
from the start.

### Two values that must be discovered, not guessed

Both go in `.env`. A wrong network name means Traefik cannot see the container
and the host 404s; a wrong resolver means no certificate, and Meta will not
deliver to a callback it cannot verify.

```bash
docker network ls
docker ps --format '{{.Names}}\t{{.Image}}'
docker inspect $(docker ps -qf name=traefik) | grep -o 'certificatesresolvers\.[a-z0-9]*' | sort -u
```

### Setup, in order

No SSH client needed — hPanel has **Web console** on the VPS overview, which is
a root shell in the browser.

```bash
# Docker is already installed — this box runs n8n on it.
mkdir -p /opt/chatwoot && cd /opt/chatwoot
# copy docker-compose.yml and env.example up, then:
cp env.example .env

openssl rand -hex 64     # -> SECRET_KEY_BASE
openssl rand -hex 32     # -> POSTGRES_PASSWORD
openssl rand -hex 32     # -> REDIS_PASSWORD, and into REDIS_URL

# Fill in TRAEFIK_NETWORK, TRAEFIK_CERTRESOLVER, CHATWOOT_HOST, FRONTEND_URL.
# CHATWOOT_HOST and FRONTEND_URL must name the same host.

# First-run database. NOT optional — `up -d` on an empty database gives a
# container that restarts forever.
docker compose run --rm rails bundle exec rails db:chatwoot_prepare

docker compose up -d
docker compose logs -f rails
```

**Check n8n is still up before doing anything else.** It shares this box, and
the whole point of the limits above is that it should not have noticed.

Then open the URL, create the first admin account, and **immediately confirm
`ENABLE_ACCOUNT_SIGNUP=false` took effect** by opening the signup page in a
private window. A public Chatwoot with open registration collects strangers.

## Moving the number — the part with a live channel in it

This is the only genuinely risky step, because for a few minutes Meta's callback
points somewhere that is not yet answering, and inbound messages in that window
are lost rather than queued.

1. In Chatwoot: **Inboxes → Add → WhatsApp → Cloud API**, with the phone number
   id, the WABA id and the System User token already in `.env` here.
2. Chatwoot produces its own callback URL and verify token.
3. Register them with Meta — the same `POST /{app-id}/subscriptions` call used
   on 8 Aug, pointed at Chatwoot instead of n8n.
4. Confirm delivery reaches Chatwoot before touching n8n at all.
5. Only then: **Settings → Integrations → Agent Bots**, create one, and point it
   at the n8n webhook. Chatwoot posts a different payload shape than Meta does,
   so `Sort` needs a second parser — this is the one code change.
6. `scripts/check_whatsapp.py` needs its envelope updating to match.

Do it outside working hours. The test number has no residents on it, so the
first pass costs nothing.

## What this unlocks, and what it does not

**Unlocks:** seats, department routing across Collections / Operations /
Management / Service, transfer between agents, open/closed status, the
per-conversation AI toggle, durable chat logs, and tagging. Seven of the twelve
open PRD lines, from one product.

**Does not:** FAQs still need a source of answers. Ticket status and balance
still need PRD §13 #1 — how a resident proves who they are — answered before
anything financial is read out to whoever is holding the handset. Chatwoot moves
neither of those.
