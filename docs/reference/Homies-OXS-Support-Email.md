# OXS Support email — API reference request

Drafted 2026-08-10, ready to send. Recipient: **support@oxs.co.il**
(phone alternative: +972 3-679-7269). Send from the company account OXS knows,
not a personal address — the guide says API activation is tracked per company.

Why this email: we hold three valid API keys (General Information, Tenant
Debts, Service Requests) but no endpoint documentation exists anywhere —
no base URL, no routes, no auth header name. The guide PDF covers key
management only, and oxs.co.il publishes nothing. Repo rule: never guess a
hostname and send a live key at it, so nothing can be called until OXS answers.

Do **not** include any API key in the email. Key names are fine; values never.

---

## English version

**Subject:** API documentation request — endpoint reference for issued keys

Hello,

We are using OXS for building management and have generated API keys for
three modules: General Information, Tenant Debts, and Service Requests
(all read-only). The API Keys guide covers key management, but we could not
find the technical reference for actually calling the API. Could you send us,
or point us to:

1. **Base URL** of the API.
2. **Authentication** — which header carries the key, and its exact format
   (e.g. `Authorization: Bearer <key>` or a custom header name).
3. **Endpoint routes** for the three modules above — in particular listing
   tenants, listing/reading tenant debts, and listing service requests.
4. **Field names** returned on a tenant record and on a debt record.
5. Specifically: does the General Information tenants endpoint return the
   tenant's **mobile phone number**? This is the field we need most.
6. Confirmation that **API service is activated** for our company account —
   the guide notes activation is done by Support.
7. Does the Tenant Debts module expose the **payment link** for an open debt —
   either returned on the debt record or via a dedicated endpoint? Our
   collection flow sends residents a payment link, and being able to read it
   through the API would let us deliver it directly.

If there is a developer portal, an OpenAPI/Swagger file, or a PDF reference,
that would be ideal.

Thank you,
[name]
[company / building name as registered with OXS]

---

## Hebrew version

**נושא:** בקשת תיעוד API — מפרט קריאות עבור מפתחות שהונפקו

שלום רב,

אנחנו משתמשים ב-OXS לניהול בניינים והנפקנו מפתחות API לשלושה מודולים:
מידע כללי, חובות דיירים, ובקשות שירות (כולם לקריאה בלבד). המדריך למפתחות
API עוסק בניהול המפתחות בלבד, ולא מצאנו את המפרט הטכני לביצוע קריאות.
נשמח לקבל, או הפניה אל:

1. **כתובת הבסיס (Base URL)** של ה-API.
2. **אימות** — באיזה header עובר המפתח ובאיזה פורמט מדויק.
3. **נתיבי הקריאות (Routes)** לשלושת המודולים — בפרט: רשימת דיירים,
   קריאת חובות דייר, ורשימת בקשות שירות.
4. **שמות השדות** המוחזרים ברשומת דייר וברשומת חוב.
5. באופן ספציפי: האם רשומת הדייר במודול המידע הכללי כוללת את
   **מספר הטלפון הנייד** של הדייר? זה השדה החשוב לנו ביותר.
6. אישור ש**שירות ה-API מופעל** עבור חשבון החברה שלנו — לפי המדריך
   ההפעלה מתבצעת על ידי התמיכה.
7. האם מודול חובות הדיירים חושף את **לינק התשלום** של חוב פתוח — בתוך
   רשומת החוב או בקריאה ייעודית? תהליך הגבייה שלנו שולח לדיירים לינק
   לתשלום, וקריאת הלינק דרך ה-API תאפשר לנו לשלוח אותו ישירות.

אם קיים פורטל מפתחים, קובץ OpenAPI/Swagger או מסמך PDF — זה יהיה מצוין.

תודה רבה,
[שם]
[שם החברה / הבניין כפי שרשום ב-OXS]

---

## When the answer arrives

- Record the base URL, auth header and routes in this folder, then build the
  probe script (read-only, General Information first).
- If tenants carry real mobiles: run `scripts/oxs_purge_synthetic.py --apply`
  **before** re-importing, then import with real phones (no `--test-phones`).
- If the answer is "no API docs / not available on your tier": fall back to
  the re-export path — ask for a collection report with the real טלפון column
  populated.
