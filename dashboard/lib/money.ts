/**
 * Money and periods, shared by every page that shows a charge.
 *
 * Both of these lived in `debts/page.tsx` and were about to be copied into
 * `search/page.tsx`. A second copy of `shekels` is how one page starts rounding
 * and the other stops — the failure would be two different totals for the same
 * resident on two screens, which is worse than either rounding rule.
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
