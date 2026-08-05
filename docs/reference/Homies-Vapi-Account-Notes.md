# Vapi account — what we know, and what it costs us

Checked 3 August 2026 against the pricing page and the billing dashboard. Prices
change; re-check before quoting anything to Homies.

## What Vapi actually is

**A switchboard, not a model.** It holds the call, does turn-taking, barge-in and
endpointing, and brokers out to three separate services:

| Role | Provider | Note |
|---|---|---|
| Transcriber | Azure `he-IL` | Deepgram has no Hebrew at all. There is no faster alternative to switch to. |
| LLM | OpenAI (mini-class) | A frontier model roughly doubles the LLM line and buys very little for slot-filling |
| Voice | Azure `he-IL-HilaNeural` | Female. Every Hebrew line we write is in feminine first person because of this. |

Vapi bills all three through its own pay-as-you-go at pass-through cost, so no
Azure or OpenAI account is needed for the demo. **When Hebrew transcription is
wrong, Vapi is not the thing to tune — Azure is.**

The one thing that would force a bring-your-own Azure key is tuning on the Azure
side — phrase lists or custom vocabulary, feeding the recogniser the actual
building names. Whether Vapi exposes that through its transcriber config is
unverified. Worth knowing before it becomes urgent.

## Cost

| | |
|---|---|
| Vapi platform | $0.050 / min |
| Azure `he-IL` STT | ~$0.017 / min |
| LLM (mini-class) | ~$0.020 / min |
| Azure Neural TTS | ~$0.005 / min |
| **Planning figure** | **~$0.12 / min** |

Concurrency 10 is included. Extra lines are $10/month each. Nothing to buy — one
call at a time in the demo, and 10 matches the Phase 8 load-test target exactly.

**Average call length is the cost lever, not the rate.** At 50 calls/day: 2 min
average is ~$260/month, 3 min ~$400, 5 min ~$660. Same traffic, 2.5× the bill.
The work that makes the agent better — fewer re-asks, cleaner numeral capture,
faster turn-taking — is the same work that makes it cheaper. Those are not
competing priorities here, which is unusual.

At Homies' full 200 interactions/day it is roughly $1,000/month. **Cost is not a
constraint on this project and should not get design attention.**

### Do not lead with cost savings

A loaded call-centre minute in Israel is roughly $0.20, so a two-minute human
call costs about the same as the bot handling it. The money argument is weak and
ops staff will spot that immediately. What holds up: nobody waits on hold, calls
get taken at 11pm, and staff stop doing intake and start doing the work that
needs judgment.

## Account state as of 3 August 2026

- **9.2 credits remaining**, roughly 45–75 minutes at Hebrew rates
- **No card on file**
- **Auto-reload off**
- Plan: Build (PAYG)
- Account owner: a personal Gmail address

**The combination is the risk, not the balance.** Empty card plus auto-reload off
means that when credits hit zero the call simply stops, with nothing to fall back
on. If that lands mid-sentence during the open mic while the ops manager is
holding the microphone, the room is not recoverable. A card plus auto-reload at a
$10 threshold makes it impossible rather than merely unlikely.

The 9.2 credits are fine for a 30-minute demo and will not survive the day of
adversarial rehearsal before it, which is a hundred-plus short calls.

## Getting an Israeli number onto Vapi

**Vapi does not sell +972 numbers.** Its own numbers are US area codes only (five
free per account). Every route to a real Israeli number is therefore an import
route, and which one depends entirely on where the DID already lives.

| Number lives in | What Vapi needs | Effort |
|---|---|---|
| Twilio | Account SID, auth token, the number | Dashboard, ~5 min. Most reliable path. |
| Telnyx | Telnyx API key, the number, **plus** adding Vapi's connection to an Outbound Voice Profile in the Telnyx portal | Dashboard, ~10 min |
| Any SIP provider (012, Cellcom, Zadarma, an ITSP) | A `byo-sip-trunk` credential — gateway, username/password — then the provider forwards inbound to `{number}@<credential_id>.sip.vapi.ai` | API only, ~1 hour |
| Retell | — | **Not possible.** Retell is a platform, not a carrier. Numbers provisioned there do not come out. Replace, do not move. |

Two traps worth writing down. On Telnyx, **the outbound voice profile step is not
optional** — omit it and inbound works while outbound fails silently, which is the
worst way for it to fail. On BYO SIP, the credential's region and the API region
must match, or inbound returns 401 because the IP never gets whitelisted.
Numbers must be E.164 throughout, and Vapi's own docs warn that FQDNs like
`sip.telnyx.com` return 400 — use gateway IPs.

**None of this is needed for the week-3 demo**, which runs on Vapi web calls: a
browser microphone, no number, no KYC. It becomes real at Phase 3. The reason to
chase the number down early is not the import — that is an afternoon — it is that
**Israeli DID KYC runs 1–3 weeks elapsed**. A number already sitting in someone's
Twilio or Telnyx account has served that time. Finding one skips the longest
non-compressible clock in the plan.

**How to tell where a number lives**, when nobody remembers: it arrived either as
a console login or as a SIP username and password in an email. A console means
import; a SIP credential means BYO trunk. There is no third shape.

Sources: [import from Telnyx](https://docs.vapi.ai/telnyx),
[import from Twilio](https://docs.vapi.ai/phone-numbers/import-twilio),
[BYO SIP trunking](https://docs.vapi.ai/advanced/sip/sip-trunk),
[phone quickstart](https://docs.vapi.ai/quickstart/phone). Checked 3 Aug 2026.

## Retention — this one changes the build

**Call and chat history is retained 14 days on the Build plan.** Extending to 60
days is a $1,000/month add-on, so buying out of it is not an option.

This breaks [07-partial-ticket](../features/07-partial-ticket/feature.md) as
written. The whole argument for a partial ticket is *"we saved what we heard plus
the recording, someone will call you back"* — if `interactions.audio_url` points
at Vapi's storage, those links die after two weeks, and the tickets that most
need a human to listen are exactly the ones that sit longest.

**Required change, not yet applied:** n8n copies the recording into Supabase
Storage on the same branch that writes the row, and `audio_url` points at our
copy. Roughly an hour of work. It changes the `save_partial_request` contract —
the tool fetches and re-hosts rather than storing whatever Vapi handed it. The
same applies to any outbound call recording under
[10-debt-followup](../features/10-debt-followup/feature.md).

## Add-ons — all irrelevant

| Add-on | Price | Verdict |
|---|---|---|
| HIPAA compliance | $2,000/mo | US healthcare law. No jurisdiction in Israel, no medical data. Off. |
| Zero data retention | $1,000/mo | Off. |
| 60-day retention | $1,000/mo | See above — solve it in n8n instead. |
| Reserved concurrency | $10/mo per line | Not until real traffic proves 10 is short. |

The real regulatory question is a different one: **Israeli call-recording
consent** under the Protection of Privacy Law. Recordings are central to the
design. What is usually needed is a spoken notice at the start of the call, which
costs one line in the greeting — but it changes the first thing every caller
hears, including everyone in the demo room. Get Homies' answer before rehearsal.

## Open

**Account ownership.** Vapi is registered to a personal Gmail address. Moving it
later means re-pointing every webhook and reissuing keys, and if Homies ever take
the system over, a personal billing account is an awkward conversation. Decide
before there is anything in production.

**Key rotation.** The Vapi private key pasted in chat during design is
compromised and must be rotated, along with the Telnyx and Retell keys. Assistant
`f5c758d8-9246-4f70-89a7-2eea5f1ec9df` itself is unaffected.
