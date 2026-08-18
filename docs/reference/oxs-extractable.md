# Everything the OXS keys can give us

**Probed live on 12 Aug 2026**, GET only, against
`https://api.oxs.co.il/api/external/v1`. This is not a reading of the PDF — it is
what the three keys in `.env` actually returned. Field names are recorded;
no value from any record is reproduced here.

Twelve top-level endpoints were tried against all three keys. **Four families
answer. Eight do not exist.**

## What answers

| Endpoint | Key | Returns |
|---|---|---|
| `/buildings` | `OXS_KEY_GENERAL` | 193 buildings |
| `/buildings/:id/tenants` | `OXS_KEY_GENERAL` | residents of that building |
| `/buildings/:id/apartments` | `OXS_KEY_GENERAL` | apartment list |
| `/buildings/:id/payments` | `OXS_KEY_GENERAL` | payment records, deeply nested |
| `/debts` | `OXS_KEY_DEBTS` | **one record, company-wide** |
| `/service-calls` | `OXS_KEY_REQUESTS` | 33 open maintenance calls |

## What does not

`/apartments`, `/tenants`, `/requests`, `/suppliers`, `/payments`, `/expenses`,
`/employees`, `/committees`, `/documents` — all unroutable on every key. So are
the per-building forms of `service-calls`, `expenses`, `documents`, `committee`
and `suppliers`. Buildings are the only collection with sub-resources.

Keys are strictly scoped: `/debts` returns 403 to the general key, and
`/service-calls` 403s to both general and debts.

---

## 1. Buildings — `/buildings`

193 records, of which 173 are active (`disable: false`).

    _id            str      the id every sub-resource is keyed on
    street         str
    number         str
    city           str
    enterance      str      entrance letter, for split buildings
    type           str
    disable        bool     20 are disabled
    vaadSettings   list[9]  committee configuration
    strings        str

**Imported twice, for two different jobs.** `residents.building` is
`street number, city`, composed at resident-import time — a label on a person.
Since 13 Aug the list itself is also a table, `buildings` (migration 016), so
an address can be *checked* rather than only recorded.

Measured across all 173 active: **street + number is unique portfolio-wide** —
no duplicate addresses, and no street+number appearing in two cities. So the
city is never worth asking a caller for. Three street names span two cities
(גולומב, החשמונאים, סוקולוב) but never at the same house number, and only two
buildings carry an `enterance` letter, neither of them at a duplicated address.
`oxs_buildings_sync.py` re-checks all of this on every run and refuses to write
if it stops holding.

## 2. Residents — `/buildings/:id/tenants`

    _id          str    → residents.oxs_ref
    name         str    → residents.full_name
    number       str    apartment number → residents.unit
    phone        str    mobile, sometimes null → residents.phone
    email        str    sometimes null      NOT IMPORTED
    isActive     bool   inactive rows are skipped
    payerType    int    who pays — owner or tenant   NOT IMPORTED
    orderIndex   int
    job          null   always empty in every building sampled

**Mostly imported.** 7,391 residents came from here. **`email` and `payerType`
are available and unused** — email is a second channel for payment proof, which
is an open question with the client; `payerType` decides who a debt call should
actually reach, owner or renter.

## 3. Apartments — `/buildings/:id/apartments`

    _id          str
    number       str
    orderIndex   int

**Imported 13 Aug** into `apartments` (migration 016), by
`scripts/oxs_buildings_sync.py`: **4,092 flats** across the 173 active
buildings — median 23 per building, smallest 2, largest 72.

**`number` is usually a sequential integer and sometimes a label**, which the
four-building sample above did not show and the full sweep did. 138 of the
4,092 are חנות, מסחר 1–4, מחסן, חניה 43, דירת ועד, חברי וועד, a company name,
or `1.5`; two are blank. **It is also not unique within a building** —
זבולון 17 has two units both called חנות. Do not parse it as a number, and do
not read the last row of a building as the highest flat: sorted by
`order_index`, the last row is frequently a shop.

This is the only way to know an apartment exists when nobody lives in it or
nobody has a phone, which is what it is now used for: `verify_address` refuses
a flat number that is not in the building. The 18 apartments in arrears with no
contact details are invisible in `residents` and are visible here.

## 4. Payments — `/buildings/:id/payments`

A list of lists — the leaf record is two levels down, which is why a naive
walker returns nothing.

    apartmentId    str
    buildingId     str
    monthsPaid     list   [{year, month, amount, isKeva}]  ← arrears are computed from this
    paidFor        str
    paidBy         object the full owner record, see below
    paidByLabel    str
    paymentByUser  object {_id, firstName, lastName} — the staff member who took it
    notes          str
    comission      int
    kevaComission  int
    comissionPayer str
    cancelReason   str

`paidBy` is not an id — it is the whole owner record:

    _id, firstName, isActive, apartmentId, buildingId, companyId,
    contactDetails       object   phones and email
    approvedTerms
    automatedCreditFailedMessage  str   ← a failed standing-order charge
    cars                 list
    communicationTypes   list     how this owner has agreed to be contacted
    legalActions         list     ← collection history
    roleId

**Partly imported.** `monthsPaid[].amount` is the monthly rate the whole arrears
calculation rests on. Everything else here is unused, and three fields are worth
a decision:

- **`paymentType` / `paymentTypeLabel`** on the payment record — how they pay:
  credit card standing order, bank transfer, credit card, bank standing order,
  cheque. Established 11 Aug.
- **`automatedCreditFailedMessage`** — a resident whose standing order bounced
  is a different call from one who never paid, and this names which.
- **`legalActions`** — anyone already in collections must not be cold-called by
  a bot.

**Never import `paymentDetails[]`** — card `digits`, `token`, `shvaParams`,
`dealNumber`, expiry, `transferBank`/`transferBranch`/`transferAccount`. It is
instrument data and this system has no use for it.

## 5. Debts — `/debts`

    _id, address, buildingId, currentMonth
    apartment                    {_id, number}
    owners                       [{_id, firstName, isActive, contactDetails}]
    renters                      []
    totalDebt                    int
    totalDebtWithCurrentMonth    int
    regularPaymentsDebt          [{year, debt}]
    regularPaymentsDebtTotal     int
    specialPayments              []
    specialPaymentsDebt          int
    currentYearRegularPayments   int
    currentYearRegularPaymentsWithCurrentMonth  int
    previousYearRegularPayments  int
    paymentNotes                 {description}

**One record for the entire company** — a 2022 balance on an inactive owner.
The shape is right and the data is not there, which is why arrears are computed
from payments instead. Re-check it after any OXS-side change; if it ever fills
in, it replaces a lot of inference.

## 6. Service calls — `/service-calls` — **NOT IMPORTED AT ALL**

33 records via `OXS_KEY_REQUESTS`, and the largest thing on this page.

    _id, taskNumber          str    their reference
    createdAt, lastUpdate    str
    buildingId               {_id, address}
    serviceCallData          {description, isPriority, reportedBy}
      reportedBy             {name, phone, email, apartmentNumber,
                              apartmentId, entity, entityId}
    facilityCategory         {_id, name, icon, mobileIcon}
    status                   {status, label}
    platform                 {platform, label}
    isServiceCall            bool
    isFuture                 bool
    totalCost                int
    images                   list   0-2 per call
    treatmentLog             list   0-2 entries
    handling, providers, responsible, tags   list, all empty in this sample
    closedBy                 {_id, firstName}
    lastUpdateNote           str
    destinationDate, doneDate, executionDate, facility,
    maintenanceDefinition    null across the sample
    reminder                 {reminder, label}

What the 33 records say:

| | |
|---|---|
| Date range | 10 Feb → 12 Aug 2026 |
| Buildings covered | 27 |
| Status | **פתוחה on all 33** |
| Reported via | resident app 29, web 4 |
| Priority | 6 of 33 |
| With photos | 12 of 33 |
| With a cost | 0 |
| Categories | אחר 10, תאורה 8, אחזקה 3, חשמל 2, and one each of אינסטלציה, מעלית, הדברה, מנעולן, ניקיון, גינון, כיבוי אש; 3 uncategorised |

**Residents are already reporting faults, through an app, and have been since
February.** Our intake agent writes tickets into Supabase that this system knows
nothing about, and this system holds tickets our agent cannot see — so a
resident who asks "what is happening with my request" gets the wrong answer
depending on which door they came through.

Two things to establish with the client before using it:

1. **Does `/service-calls` only return open ones, or does nothing ever close?**
   Every record is `פתוחה` and one is six months old. Those are very different
   facts and the API cannot tell them apart.
2. **`reportedBy.phone` matches our `residents.phone`**, which makes ticket
   history joinable to the debt queue without any new identifier.

`facilityCategory.name` is also the client's own fault vocabulary — twelve
categories they actually use. Ours was invented. Theirs should win.

---

## Ranked by what it would buy

| | What | Effort |
|---|---|---|
| 1 | **Import `/service-calls`** — their open tickets, so the agents stop being blind to them | a new sync, plus a merge decision |
| 2 | **Adopt `facilityCategory` as the ticket vocabulary** — replaces our invented list | mapping table |
| 3 | **`payerType`** on tenants — owner or renter, decides who a debt call reaches | one field on the existing import |
| 4 | **`legalActions`** — never cold-call someone already in collections | a filter on the queue |
| 5 | **`automatedCreditFailedMessage`** — a bounced standing order is a different conversation | one field |
| 6 | **`paymentType`** — how they pay, so the agent stops offering the wrong thing | one field |
| ~~7~~ | ~~**`/buildings/:id/apartments`**~~ — **done 13 Aug**, 4,092 flats in `apartments`; it is what lets the bot refuse an apartment that does not exist | was a small sync, and was |
| 8 | **`email`** on tenants — a second channel for payment proof | one field |

## Standing constraints

- **OXS is read-only, forever.** These are GET endpoints and there are no others
  as far as this system is concerned. A change a resident asks for becomes staff
  work, not an API call.
- **60 requests/minute and 1,000/hour, per key**, not shared. A full resident
  sweep is 193 building calls and takes about four minutes at a 1.05s pace.
- **No webhooks.** Everything here is polled, so freshness is whatever the last
  run was.
