# Dialer test on the dashboard: context

**Asked 28 Oct by the owner:** *"we need to connect the tokomni on the dashboard we have and create a section for testing there where we just insert the number there or like call ido button on that to make the dialer work without the need of creating and uploading an excel file everytime"*.

**Why a page and not the script.**
- `scripts/tokomni_lead.py` (27 Oct) sends the same lead, but only from this PC.
- The tests are run by the owner and Ido, over AnyDesk, during the Israeli day.

**Why only the test building's own people get a button.**
- `residents.source = 'agent'` marks the people we added to בר כוכבא 23 (debt_demo_person.py and the like).
- The building's OXS rows are real numbers. Yariv, the client, is flat 3 there and on the debt call list with ₪2,000. A button for him would be one mis-click from a debt call to the client.
- So the OXS rows get no button, and any of them can still be typed.

**Why a typed number for a tenant elsewhere is refused.**
- Feature 18 gives the debt agent to anyone on the debt call list, in any building.
- So a typed tenant's number could start a real debt conversation from a test page.
- A real tenant's call is the Debts page's deliberate step (feature 15), not this page's.
- Numbers that are no tenant's (a tester's own phone) are allowed, and get the intake agent.

**Why calling hours are enforced here.**
- Omni's dialer rings at any hour (25 Oct), and CONTEXT says our side sends only in calling hours.
- The page uses the same hours as `tokomni_lead.py`, and shows the time in Israel. The owner is 6 hours ahead in the Philippines.

**Why the external_id carries the press time.**
- Omni's insert adds a lead "if not already present".
- A bare resident id could make the second press for Ido a lead Tokomni already has, and then nothing rings.
- The resident id stays first, so a later reading of Omni's external_id header finds it in the first 36 characters.
- If Tokomni dedupes by number instead, this does not help. The page then says what to check (see below).

**Why no PIN.**
- The Debts page's PIN guards a call about money to a real tenant. This page only rings testers and numbers that are no tenant's, behind the login.
- The owner asked for one press.

**Why the Ring button is the page's only client JavaScript.**
- A second click is a second lead and a second ring.
- `useFormStatus` greys the button while its press is on its way.
- `react-dom` has no types installed here, so `types/react-dom.d.ts` declares that one hook instead of adding a dependency.

## Constraints

- **Omni's API:** one insert call, with no status, no remove and no outcome callback. 200 means "added if not already present", and 404 means a missing field or a bad token. Seen from this PC on 28 Oct: a GET on the insert path answers Tokomni's own JSON 404 ("Route Not Found"), so Cloudflare lets a plain Node request through. The host's root is a Cloudflare block page.
- **List 2's rules** (Omni, 27 Oct): Play once, never Stop, never upload a sheet into it.
- **Vercel's function limit** is about 10 seconds, so the page waits 8 for Tokomni.

## Known failure modes

- **Tokomni answers 200 and nothing rings.** Either List 2 is stopped (Play), or the number is still in List 2 from an earlier send and Tokomni dedupes by number. The notice says both. The second would need Omni to say how a number is rung again.
- **No answer from Tokomni.** The lead may have landed. The notice says to check List 2 before pressing again.
- **The tester answers and gets Michael instead of the debt agent.** After 4 debt calls the person leaves the debt call list. The row shows "call N of 4" beforehand. `bk_reset_attempts.py --apply` puts the test building back.
- **Cloudflare blocks Vercel's servers.** The notice shows the block page's title ("Attention Required! | Cloudflare").

## Open questions

- **Does Tokomni dedupe by number or by external_id?** The second press for the same number settles it.
- **Does the external_id reach Vapi as a header?** This is Omni's own test. `scripts/tokomni_lead.py --check` reads the last two hours of calls and finds the id by its resident-id prefix.

## Related

- `docs/features/18-dialer-routing/` (who answers), `docs/features/15-call-button/` (the Debts page's button)
- `local/omnitelecom/2026-10-27-token-list2.txt` (Omni's email, minus the token)
