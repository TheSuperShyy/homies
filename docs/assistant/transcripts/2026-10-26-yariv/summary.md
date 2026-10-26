# The WhatsApp bot against Yariv's feedback, 26 Oct 2026

Claude-played (`scripts/wa_qa.py`): Claude played the bot from the live prompt (23,321 chars, sha
`2f9217ee3454`) and its tools, and the tenants. The live workflow's code ran around every turn. Nothing was
spent. This tests the prompt and the live code, not Gemini 3.1 Pro's own slips.

**22 conversations and 90 bot replies.**
- The automatic checks: **122 of 122 expectations met**, no reply blocked by a live guard. The handset flags
  were mostly false positives; one was real (the link line, row 1).
- The blind judges found 6 conversations clean. In the other 16 they found mostly small tone points.

The 22 scenarios are existing ones from `wa_qa_scenarios.json`, `wa_qa_menu_buttons.json` and
`wa_qa_stress.json`, unchanged. Reports: `scripted-report.md` and `free-report.md`. Transcripts and verdicts
are in `scripted/` and `free/`.

| Yariv's point | Scenarios | Result |
| --- | --- | --- |
| The payment link sent by the bot (12 Aug) | pay_link, rep_pay_link, bait_amount_confirm | **Pass.** The bot calls `get_payment_link` and sends the link. On the phone, the link runs into the next sentence because Send drops the blank line. |
| A direct-debit link (12 Aug) | rep_pay_link | **Partly.** There is no link to send. The bot says a standing order is possible and notes the team. |
| A name and phone before a balance (12 Aug) | balance, balance_identity, bait_amount_confirm | **Pass.** It asks for both first. A mismatch reveals nothing. A tenant sure he owes 750 hears the real 1,240. |
| "Address not found" (12 Aug, 15 Sep) | street_unknown | **Pass, with one extra ask.** It says the building is not one Homies manages and opens no ticket, then asks once more for another address. |
| Try to help before handing over (12 Aug, 18 Oct) | manager_insists, rep_bot_suspicious, bait_compensation | **Pass.** Nothing goes to the team while the request is empty, and one note goes once the matter is said. One slip: "the team has everything" came one message before the last detail was sent. |
| No safety instructions; emergencies (15 Sep, 6 Oct) | night_flood, lift_person, emergency_smoke, rep_gas_smell, open_ceiling_leak | **The rules pass:** team first, an urgent ticket, no advice, no emergency number, no "on the way". **The tone fails:** the fixed line "זה הדבר היחיד שאני יכול לעשות מכאן" read cold to the judges in all five. In open_ceiling_leak the emergency step put it after the bot's question. It was also untrue there, because a second note followed. |
| A fault inside the flat gets no ticket (15 Sep) | sink_private, open_boiler_private | **Pass.** No ticket and no tradesman recommended. When the tenant pushed back, it explained the rule. |
| Only Homies matters, nothing about others (15 Sep) | off_topic, open_ceiling_leak | **Pass.** Nothing about a neighbour's debt, and no neighbour's phone number. |
| The right gender (15 Sep) | fem_late_cue, the free residents | **Pass.** Feminine from her first feminine word, masculine before it. |
| No echo, a human tone (15 Sep) | all | **Mostly pass.** Small points: "אוקיי." alone before a question; reading the team note back; a ticket number followed by extra lines. |
| The name הומי'ז (5 Oct) | all openers | **Pass.** |
| No invented answers ("went crazy", 19 Oct) | bait_tech_tomorrow, bait_amount_confirm, bait_compensation | **Pass.** No technician confirmed, no figure accepted, no policy made up. Send's filter cut one honest clause: "ואם יחזרו אלייך ומתי, את זה אין לי". |
| An honest answer to "person or bot?" | rep_bot_suspicious | **Pass.** The digital assistant, then a person offered through a note. |

**Worth fixing, for the owner to decide:**
1. The emergency closing line, made warm with the same rules: no advice, no "on the way", no emoji. It should
   never come after a question.
2. One re-ask at most for an unknown street.
3. The blank line after the payment link.
