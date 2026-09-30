# Debt agent, 30 Sep: one person, by the name's gender (Claude replay)

Offline. Claude played the model (gpt-5.6-sol on Vapi) and the resident. The input
was the new fence rendered with Bar Kochba 23, apartment 4, and the tool
definitions. No OpenRouter was spent and no call was placed. This checks the
rules, not the production model's exact wording. `{{gender_forms}}` was the
`dashboard/lib/call.ts` text for f, m and unknown. The owner's decision and the
design are in `docs/features/10-debt-followup/prompt.md`, "30 Sep — one person,
by their name".

## A: מיכל (the name gives f)

- **Michael:** צהריים טובים, מיכל? מדבר מיכאל מהצוות של הומיז, מה נשמע?
- **מיכל:** כן, מדברת.
- **Michael:** היי מיכל, טוב שתפסתי אותך. איך את, איך עובר היום?
- **מיכל:** בסדר, תודה.
- **Michael:** טוב לשמוע. אני מתקשר לגבי התשלום של ועד הבית, יש לך דקה?
- **מיכל:** אה, נכון, שכחתי לגמרי.
- **Michael:** קורה לכולם, זה על דירה ארבע, על יולי, אוגוסט וספטמבר, ובסך הכול שבע מאות וחמישים שקלים. תרצי שאשלח לך לינק לתשלום?
- **מיכל:** כן, תשלח לי.
- `[send_payment_link → sent true]`
- **Michael:** שלחתי לך את הלינק לוואטסאפ, למספר שרשום אצלנו. תוכלי להיכנס ולסיים את התשלום משם?
- **מיכל:** תודה רבה.
- `[log_call_outcome authorized]`
- **Michael:** בשמחה, מיכל, ותודה לך. יום טוב, ולהתראות.

## B: דוד (the name gives m)

- **Michael:** צהריים טובים, דוד? מדבר מיכאל מהצוות של הומיז, מה נשמע?
- **דוד:** כן, זה אני.
- **Michael:** היי דוד, איך אתה, הכול בסדר?
- **דוד:** הכול טוב.
- **Michael:** יופי, שמח לשמוע. אני מתקשר לגבי התשלום של ועד הבית, יש לך רגע?
- **דוד:** אני אסדר את זה עד סוף השבוע.
- **Michael:** מעולה, תודה, ורק שיהיה לך מול העיניים: זה על דירה ארבע, על יולי, אוגוסט וספטמבר, ובסך הכול שבע מאות וחמישים שקלים. יש יום מסוים שנוח לך?
- **דוד:** ביום חמישי.
- `[log_promise_to_pay "ביום חמישי"]`
- **Michael:** מעולה, תודה רבה, דוד. יש עוד משהו שאוכל לעזור לך בו?
- **דוד:** תודה.
- `[log_call_outcome promised]`
- **Michael:** בשמחה, דוד. יום טוב, ולהתראות.

## C: טל (a name used for both, so unknown; a woman on the line)

- **Michael:** צהריים טובים, טל? מדבר מיכאל מהצוות של הומיז, מה נשמע?
- **טל:** כן.
- **Michael:** היי טל, איך אתה, הכול טוב?
- **טל:** בסדר.
- **Michael:** יופי. אני מתקשר לגבי התשלום של ועד הבית, יש לך דקה?
- **טל:** אני צריכה לבדוק את זה, אני לא בטוחה שזה נכון.
- **Michael:** בטח, תבדקי בנחת, וכדי שיהיה לך מה לבדוק: זה על דירה ארבע, על יולי, אוגוסט וספטמבר, ובסך הכול שבע מאות וחמישים שקלים. תרצי שמישהו מהצוות יחזור אלייך ויעבור על זה איתך?
- **טל:** טוב, תודה.
- **Michael:** מעולה, אז מישהו מהצוות יחזור אלייך.
- `[transfer_to_human dispute]`
- `[log_call_outcome transferred]`
- **Michael:** תודה רבה, טל. יום טוב, ולהתראות.

## Read

- **The gender held.** A: feminine every time (את, תרצי, תוכלי). B: masculine (אתה, לך, שנוח לך).
- **The switch rule fired.** C opened masculine, the default for a name used for both. It went feminine from `אני צריכה` onward (תבדקי, תרצי, אלייך).
- **No plural in any call.** The opener asked `מה נשמע`, and each call closed on `יום טוב, ולהתראות` after the outcome was logged.
