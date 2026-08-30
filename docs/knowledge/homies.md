# What we know about Homies

**The master copy of the thirteen facts.** Two channels state them — the
WhatsApp bot and the inbound voice agent — and before this file existed only one
of them knew any of it. Edit here, then edit the two prompts, then run
`python scripts/facts_check.py`, which fails when they drift apart.

The facts themselves came from the client on 16 Aug and are recorded in
`docs/features/11-whatsapp-bot/prompt.md` under `### מידע על הומיז`. That
section is unchanged and stays the WhatsApp bot's live copy; this file was
created from it, not instead of it.

**Anything not written here does not exist.** No website, no staff names, no
prices, no contract clauses beyond what is below. A fact we do not hold is not
an escalation — say so and give the office number. Never invent half of one: a
number that sounds right, an approximate hour, a website that might exist are
all worse than "I don't have that", because a resident will rely on them.

---

## Why one fact has two forms

A phone number written `077-6687949` is correct on WhatsApp, where a resident
copies it, and broken on the phone, where Vapi's formatter splits it into
digits before the voice ever sees it — the 30 Aug defect. A number written in
Hebrew words is correct spoken and wrong in a chat window.

So seven of the thirteen carry two renderings and six carry one. The rule for
which is which: **anything with a digit, a colon or a Latin character in it
differs; anything that is already ordinary Hebrew does not.**

`::` separates the columns below because it cannot occur in either language.
`-` in the spoken column means the fact is never said aloud.

```facts
office_phone       :: 077-6687949 :: אפס שבע שבע, שש שש שמונה, שבע תשע ארבע תשע
office_email       :: Office@homies-management.co.il :: -
office_address     :: בצלאל 1, רמת גן :: בצלאל אחת, רמת גן
office_hours       :: ראשון עד חמישי, 09:00-17:00 :: ראשון עד חמישי, תשע בבוקר עד חמש אחר הצהריים
payment_due        :: עד ה־10 בכל חודש :: עד העשירי בכל חודש
sla_emergency      :: עד 4 שעות :: עד ארבע שעות
sla_standard       :: עד 3 ימי עסקים :: עד שלושה ימי עסקים
fee_includes       :: ביטוח, חשבון חשמל, חשבון מעלית, בודק מעליות, ניקיון, גינון, ביקורת גילוי אש, ביקורת מערכת לשחרור עשן, טיפול במערכת המשאבות, חיטוי מאגר מים, קופה קטנה לתקלות קטנות, קווי בזק למעלית ולמערכת האש, עמלות בנק, וניהול, אחזקה וגביית כספים של חברת הניהול :: =
fee_excludes       :: תיקונים ותקלות שאינם מן השוטף, תקלות עקב בלאי או שבר, פרויקטים מיוחדים, וכל דבר שאינו נכלל בתקציב השוטף :: =
payment_methods    :: העברה בנקאית, הוראת קבע, כרטיס אשראי או שיקים :: =
house_committee    :: מי שלא מכיר את ועד הבית של הבניין שלו, שיפנה אלינו ואנחנו נקשר ביניהם :: =
responsibility     :: כל מה שהוגדר בחוק כרכוש משותף הוא באחריות משותפת של ועד הבית וחברת הניהול. כל מה שהוגדר בחוק כרכוש פרטי הוא באחריות הדייר :: =
emergency_line     :: אין קו חירום נפרד :: =
```

`=` means the spoken form is the written form, unchanged.

---

## The email cannot be spoken, and that is not a formatting problem

`Office@homies-management.co.il` is the one fact the voice agent holds and
cannot deliver. The prompt's own rule says foreign words are written in Hebrew
letters, because a Hebrew voice mangles Latin ones — and unlike a phone number,
nobody can reconstruct a mangled email from context. Reading it aloud produces
something a resident will write down wrong and then blame us for.

**So the voice agent gives the phone number and does not offer the email.** If a
caller asks for it specifically, the honest answer is that the office can send
it. This is a limitation being recorded rather than solved; it goes away with an
SMS-after-call tool, which does not exist.

---

## Four rules that travel with the facts

These are not facts and cannot be looked up — they govern how the facts are
used, and they belong in both prompts in full.

**Contacts are quoted, not phrased.** Character for character, no shortening,
no translating, no reformatting. A resident copies these. A wrong number is
worse than a missing one.

**Response times are policy, never a promise about one ticket.** *"תקלות חירום
עד ארבע שעות, השאר עד שלושה ימי עסקים"* is a statement about the standard and
may be said. *"יטפלו בזה עד מחר"* is a commitment somebody else has to keep and
stays forbidden — a question about a specific request is answered from
`get_request_status` and from nothing else.

**Answer what was asked; do not recite the list.** Somebody asking whether
cleaning is included gets *"כן, ניקיון כלול"*, not the whole list. The full
list goes out only when it is asked for.

**Doubt about responsibility is not resolved.** Common versus private property
is sometimes obvious from the law and sometimes not. Where it is not perfectly
clear, say it will be checked and hand it to a person. Getting this wrong costs
a resident money, which is why the responsibility fact itself ends *in case of
doubt, contact us*.

---

## When this file should stop existing

When there is a corpus rather than a list — contracts, house rules, per-building
documents — these move into a real knowledge base and both channels query it.
Vapi hosts one (`POST /file` → `POST /v2/knowledge-base`, which generates the
retrieval tool by itself); the reason it is not used for fourteen facts is
written up in the 30 Aug WORKLOG entry, and the short version is that retrieval
costs a round trip on a turn already measured at 5,283ms, has never been tested
on Hebrew, and would not serve the WhatsApp bot at all.
