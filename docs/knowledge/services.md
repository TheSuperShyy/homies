# What Homies sells, from their own website

**Scraped 16 Sep 2026 from `homies-management.co.il`** — 41 pages, WordPress +
Elementor, all server-rendered (`scripts/scrape_site.py`). The client asked for
their site turned into a knowledge base.

**This file is reference, not a script.** `docs/knowledge/homies.md` holds the
thirteen facts both prompts must state verbatim and `facts_check.py` guards
them; this one is the service catalogue behind *"do you do gardening?"* and
*"how often is the generator checked?"* — questions the bots currently cannot
answer at all. **Nothing here is in either prompt yet.** Wiring it in is a
separate decision, because the inbound agent is open by owner decision (6 Sep)
and pasting a catalogue into its fence would be adding rules to it.

**Marketing copy is not fact.** The site is written to sell. Numbers in it
contradict each other (see the last section), and phrases like *"מענה 24/7"*
are a sales promise, not an SLA the bot may repeat. Where the site and the
client's own 16 Aug facts disagree, **the client's facts win** until he says
otherwise.

---

## The company, in its own words

**הומי'ז** — note the spelling: the site writes the name with a geresh
(`הומי'ז`, and `הומי’ז` with a curly apostrophe in body text), never the bare
`הומיז` our prompts use. That is the company's own orthography and it bears
directly on the 12 Aug pronunciation complaint: `הומי-ז` is one of the five
forms rendered in `voice/samples/name-*.mp3`, and the site says the client
already thinks of the name as two parts.

Founded to bundle every service a residential building and its residents need
into one package. Positions itself on reliability, availability and
transparency. The site claims **over 10 years** managing buildings in one place
and **"over 5 years"** in another (see contradictions). Google reviews embedded
on the site: **38 reviews, rated "מעולה"**, the visible ones from 2022–2023,
several naming **יריב** as the person running it.

Self-described coverage: **מרכז הארץ**, with dedicated pages for **רמת גן,
תל אביב, הרצליה, רמת השרון, גבעתיים** and a generic *נוא* page.

---

## The services

### ניהול ועד בית / שירותי ניהול
- An **annual budget** built per building, sized to its systems, deliberately
  conservative to avoid a mid-year deficit.
- **Collection of dues from residents.** Payment methods the site names:
  צ'קים, העברה בנקאית, הוראת קבע, כרטיס אשראי. **Digital receipts** to
  everyone who pays; everything recorded in the building's כרטסת גבייה.
- **Weekly** bank reconciliation, expense recording and balance-sheet update.
- **An app** for committee members with 24/7 access to reports and the
  building's financial position. *(The bots do not know this app exists and
  residents may well ask about it — see contradictions.)*
- Handles all dealings with outside suppliers and their payments.

### אחזקת הבניין — the אב בית
Every managed building gets an **אב בית** assigned: a technically qualified
person who visits at an agreed frequency.
- Checks lighting throughout the building and the installed systems.
- Sets the electricity timers (שעוני חשמל), and adjusts indoor and outdoor
  lighting when the clocks change.
- Handles resident faults and complaints; **both the committee and individual
  residents can open a service call**.
- **Supervises the cleaners** against the agreed specification.
- Small repairs named explicitly: replacing blown bulbs and light fittings,
  adjusting and repairing doors, replacing handles and cylinders, clearing
  gutter channels.
- **Protects the lift before a resident moves in or out** (מיגון מעלית).
- Every call is logged in a maintenance journal visible 24/7 in the app.

### ביקורות שוטפות
Weekly, monthly, quarterly and annual inspections, by system. Includes
**controlled operation** so equipment does not seize: running the generator,
switching on the car-park smoke fans, running the submersible pumps through the
summer when they are otherwise idle, and opening the drainage pits before the
rainy season.

### תחזוקת מערכות
Covers fire detection and suppression, smoke-release fans, water pumps of all
kinds, and generators. Monthly checks by the אב בית; **annual inspections by a
certified specialist** per system.

| system | routine | annual |
|---|---|---|
| **גנרטור** | run ~10 minutes, at least monthly; check oil, diesel, water | full service by a certified technician, per manufacturer's instructions |
| **רכזת גילוי אש** | monthly check of detectors and alarms | inspection by a certified professional; frequency set by רשות הכבאות וההצלה per building and fire risk. Certificates go to the fire authority and the insurers, and into the building file |
| **מפוחים לשחרור עשן** | monthly check by the אב בית | annual inspection by a qualified engineer, who issues a certificate sent to the committee and kept in the building file. Standard named: **ת"י 1001** |
| **משאבות מים** | checked by the אב בית: pressure pumps (buildings over 4 floors), fire-system pumps for sprinklers and hydrants, submersible pumps for rainwater | **חיטוי מאגר מי שתייה once a year**, by a certified professional, as the Health Ministry regulations require; certificate to the committee and the building file |

Smoke fans trigger from the fire panel or from CO sensors in the car park, and
can also be run on a timer for controlled ventilation.

### שירותי ניקיון
- **A regular, named cleaner** assigned to the building, with a stand-in
  briefed and sent the same day if they cannot come.
- Specification agreed in advance. Generally covers: **חדר אשפה** including
  washing the bins, **חדר מדרגות**, **מעלית**, **ארונות חשמל**, doors in
  common areas, passageways, **תיבות דואר**, vitrines.
- New buildings get **car-park washing with high-pressure water** as part of the
  agreement.
- Advanced, safe cleaning products chosen to leave a pleasant smell.
- Frequency is per building and budget, not a fixed number.
- **Post-renovation cleaning** is offered as a separate crew.

### ניקיון חניונים
Done with a dedicated washing machine, with a high-pressure washer as backup,
for epoxy or smoothed-concrete surfaces. Removes oil, diesel, mud, soot and
smoke stains. **Recommended once or twice a year**, timed with the committee to
avoid disrupting the building.

### שירותי הדברה
- **Seasonal treatment** across the whole building: lobby, car parks,
  residential floors, stairwells, cupboards, and sewage and drainage openings.
- **A certificate and a 12-month warranty** after treatment; the certificate is
  kept in the building file.
- **Residents and the committee are told at least a week in advance**, with
  instructions for before the exterminator arrives and safety points for after.
- Approved materials only.
- Also handles what cannot be prevented: a wasp nest, rats in the bin room.

### שירותי גינון
Gardening crews work alongside the cleaning crews in most managed buildings.
The design approach is agreed with the building; the promise is a maintained
garden receiving its necessary treatments on time.

### שיפוצים
Renovation of apartments and villas — **over 70 a year** per the site, in the
centre of the country. Trades listed: **ריצוף, צבע, אינסטלציה, חשמל, עבודות
איטום, עבודות גבס**. Emphasis on a clean, sterile working environment.

### ניהול נכסים (for landlords, not residents)
Tenant vetting, contract preparation, 24/7 fault handling, regular visual
reports on repairs and payments. Explicitly answers that they are available on
**Friday and Saturday** for a tenant's fault.

### ניהול דירות לתקופות קצרות
Airbnb / Booking / HomeAway listings, calendar management, guest turnover,
preparing the apartment between guests, ongoing fault maintenance, and full
guest communication before, during and after the stay.

### Other trades the About page claims
הנדימן, חשמלאות, שיפוצים, אינסטלציה, מיזוג, תחזוקה, גינון — offered by
bundling vetted external suppliers.

---

## Contact details on the site

| | |
|---|---|
| Phone | **077-6687949** — matches our facts |
| Email | **office@homies-management.co.il** — matches |
| Address | **בצלאל 1, רמת גן** — matches |
| Fault form | `/ptihat-takala/` asks for full name, phone, building address, apartment number, description |
| Social | Facebook and WhatsApp links in the footer |

---

## Contradictions, and what to do about them

**These are for the client to settle. Nothing here has been changed in any
prompt.** Each one is a place where a bot answering from the website would
tell a resident something different from what it says today.

1. **Opening hours — three different answers, and ours is one of them.**
   - Our prompts and `homies.md`: **ראשון עד חמישי, 09:00–17:00**, no Friday.
   - The site's contact block: **א–ה 09:00–17:00, ו 09:00–14:00**.
   - The site's own footer, on the same page: **א׳–ה׳ 08:00–18:00, ו׳ 08:00–14:00**.

   So the site disagrees with itself, and **both of its versions say Homies is
   open on Friday while our bots tell residents it is closed.** This is the
   single most likely thing to embarrass the client, because a resident who
   rings on a Friday morning was told by the bot that nobody is there. Ask
   which is right; the answer changes `homies.md`, both prompts, and
   `facts_check.py`.

2. **How long they have been in business.** "מעל 10 שנים" and "למעלה מעשור" on
   the management pages, "מעל 5 שנים" on the homepage and gardening page, "15
   שנה" for cleaning experience and "מעל 15 שנים" on the renovations page. The
   bot should not state any of these until one is confirmed.

3. **"מענה 24/7" is on almost every page.** Our bots say the office is open
   office hours and refuse to promise anyone will call back. The site promises
   round-the-clock availability. These are not reconcilable by a prompt edit —
   the client has to say which is true for residents as opposed to for
   landlords, because the 24/7 claim appears most often on the property-owner
   pages.

4. **The resident/committee app.** The site promises 24/7 access to reports and
   a maintenance journal through "אפליקציה חדשנית". Neither bot knows it
   exists, so a committee member asking about it gets "I don't have that". If
   it is real and current, it belongs in the facts; if it is the OXS portal
   under another name, the bot should say so.

5. **Payment methods.** The site adds **צ'קים** and names credit card, standing
   order and bank transfer; `homies.md` says עד ה־10 בכל חודש, בהעברה בנקאית,
   הוראת קבע, כרטיס אשראי או שיקים. These agree — worth noting as the one place
   they do.

6. **`homies.md` opens with "Anything not written here does not exist. No
   website…"** That sentence is now literally false: there is a website, it is
   public, and this file is its contents. The sentence should be narrowed to
   what it actually means — the bot does not invent facts — rather than left
   denying a site the client will expect it to know.

---

## What was not scraped

Images, the embedded Google reviews widget beyond the visible text, the two
privacy-policy pages (20k and 6k characters of legal boilerplate, saved in the
scrape but not summarised here), the recruitment pages, and the thank-you
pages. The raw text of all 41 pages is reproducible with
`python scripts/scrape_site.py <urls file>`.
