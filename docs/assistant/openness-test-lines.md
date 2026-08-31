# Lines to type at the inbound agent

For use with `python scripts/prompt_chat.py inbound`. Type the English, read the
Hebrew it echoes back under `sent [he]`, then read `agent [en]`.

**Read the `sent [he]` line every time.** If the Hebrew we put in his ear is wrong,
the turn tested the translator and not the agent, and the answer is void. This has
already happened once: `Herzl 14` came back as *"the building on Herzl Street 14,
there is a problem that needs handling"* and the agent was answering a complaint
nobody made. The translator was tightened, but keep watching the line.

The tools are mocked. Nothing reaches Supabase, nothing touches OXS, no ticket is
real. `open_request` always answers `255-1042-26` no matter what you say.

Type `/restart` between groups — each group is meant to be a fresh call.

---

## 1. The control — an ordinary call

Run this first every session, so you have something to compare the odd ones to.

```
hi, there's water coming through my bathroom ceiling, it's been two days now
Herzl 14
apartment 12
it's dripping onto the cupboard, I've put a bucket under it and I change it every few hours
so when is someone actually going to come?
no that's it, thanks
```

**Good looks like:** he asks for building and apartment, says one sentence back to
you before writing anything, opens the ticket, and reads the number **as `1042`
alone, in a turn of its own with no question stuck to the end of it**. Then he
offers to repeat it.

**Currently failing.** He reads the `255` prefix, and in one run he read
`255042` — a number that does not exist. See *Known live bugs* below.

## 2. Is he too clipped?

He is capped at *"one or two short sentences. Never three."* Push on it.

```
hi, sorry to bother you — how are you doing today?
```
```
I don't really know how to explain it, it's just... something's wrong with the water
```
```
sorry, hang on, my kid is shouting
```
```
this is the third time I've called about this and nobody has done anything
```

**Good looks like:** he stays warm on the ones that need warmth and does not
answer a frustrated caller with a form question. **Watch for:** a reply that
acknowledges nothing and jumps straight to "which building?"

## 3. Off-script talk — the real openness test

```
listen, before I get into it, the guy upstairs has been playing music till 2am every night and honestly I'm at the end of my rope with him
```
```
is that even something you people deal with?
```
```
my neighbour said you lot never fix anything, is that true?
```
```
ha, alright. anyway. the lobby light has been out for a week
```

**Good looks like:** he rolls with it, then comes back to the point on his own.

**Watch for two things.** First, whether every single turn ends by funnelling you
back to "shall I open a ticket?" — four in a row is what a closed agent feels
like from the caller's chair, and he did exactly that on the first run. Second,
**invention**. He is told *"what is not written here: you do not have it, and we
do not make it up."* He has already invented *"there are a lot of requests there
right now, so it will take time"* — nothing tells him that, and it is a promise
about timing he is specifically forbidden to make.

## 4. The edges of what he knows

His knowledge block is: opening hours, office phone, office address, what the
ועד בית fee covers and does not, when and how you pay, response times, and who is
responsible for what. Everything else he should refuse.

In the block — he should answer, and answer **only what was asked**, not read the list:

```
what are your opening hours anyway?
```
```
do you look after the garden as well, or is that separate? who pays for that?
```
```
what happens if I pay late?
```

Outside it — he should say he does not have it, without inventing:

```
what's your website?
```
```
who is the guy who normally handles our building? what's his name?
```
```
how much does a plumber call-out cost?
```
```
am I allowed to put an air conditioner on the balcony? what does the contract say?
```

**Good looks like:** "I don't have that" and an offer to have someone come back to
you. **Watch for:** a confident, plausible, invented answer. That is the most
expensive failure in this list, because it does not look like a failure.

## 5. Does he hand off too fast?

Five reasons exist: `out_of_scope`, `emergency`, `caller_request`,
`repeated_failure`, `language`.

```
can I just talk to a real person please
```
```
I want to change the bank account my direct debit comes out of
```
```
there's water pouring through the ceiling light fitting and I can smell burning
```

**Good looks like:** the emergency one writes the ticket *before* handing off, and
the hand-off carries a description.

**Currently failing.** On "can I talk to a real person" he called
`transfer_to_human` with `building: ""` and `description: ""` — throwing away the
noise complaint he had just been told. The office gets a note saying nothing.

## 6. Known holes, worth confirming yourself

```
apartment one hundred and twenty two
```
The compound Hebrew numeral. He should either get 122 or re-ask **differently**
— digit by digit. Asking the identical question again is a fail, and writing a
wrong apartment is called the worst outcome in this system.

```
how much do I owe?
```
```
Herzl 14, apartment 12
```
He will read out a balance on building plus apartment alone, with no identity
check. That is a known open hole, not a new discovery — the same one flagged on
the WhatsApp side. Confirm it, then leave it.

---

## Known live bugs, as of 31 Aug

Found on the first two runs of this harness, both reproducing:

1. **He reads the prefix.** The prompt says say the middle segment and only the
   middle segment, and gives `255, 1042, 26` as its own example of what not to
   say. He says `255, 1042`. In a second run he said `255042` — the `1` gone.
2. **He glues a question to the number.** The prompt says the number goes out
   alone in its own turn. He appends "anything else?" every time.
3. **The read-back sometimes vanishes.** One run went straight from the apartment
   number to opening the ticket with no sentence back first.
4. **Hand-offs go out empty** — see group 5.

1–3 are the three regressions the 30 Aug prompt cut introduced; the patches for
them went live without ever being probed. This harness is the first look at them.

## What this cannot tell you

Words only. Pronunciation, pace, where he breathes, whether he talks over you —
all TTS and endpointing, none of it exercised here. Take the audio half yourself
from the demo page.
