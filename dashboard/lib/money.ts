/**
 * What a charge is, what it is worth, and when it fell due — shared by every
 * page that shows one.
 *
 * All three lived in `debts/page.tsx` and were copied, or nearly copied, into
 * `search/page.tsx`. Each copy is a way for two screens to disagree about one
 * resident's money: `shekels` if one rounds and the other stops, `month` if one
 * shows the due day, `OUTSTANDING` if one counts a status the other ignores.
 * The last of those actually happened and is why this file exists at all.
 */

/**
 * Whole shekels.
 *
 * Monthly rates from OXS carry agorot (683.4), and a total of ₪105,760.7 on a
 * card reads as a typo, not as precision anybody wanted.
 */
export const shekels = (n: number) => '₪' + Math.round(n).toLocaleString('en-US');

/**
 * `charges.period` is the first of the month — `2026-06-01`. Everything that
 * shows one to a reader shows `2026-06`, so the day never implies the charge
 * fell due on the 1st.
 */
export const month = (p: string) => p.slice(0, 7);

/**
 * The statuses that mean a charge is still outstanding.
 *
 * `/debts` and `/search` both answer "what does this person owe" from the same
 * table, and for one commit they answered it differently: search filtered to
 * `unpaid` while debts read all three. Nothing looked wrong, because no row
 * carries `disputed` or `pending_charge` today — it would have surfaced as two
 * pages quoting different money for one resident, months later, with no error
 * anywhere.
 *
 * `paid` and `waived` are absent on purpose: neither is owed.
 *
 * NOT the same as "add it to the total". `disputed` and `pending_charge` are
 * waiting on a person, so both pages LIST them under a review label and total
 * only `unpaid` — a disputed month inside a total is a number somebody acts on
 * before the dispute is settled. See REVIEW in the debts page.
 */
export const OUTSTANDING = ['unpaid', 'disputed', 'pending_charge'] as const;
