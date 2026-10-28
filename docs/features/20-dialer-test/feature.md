# Dialer test on the dashboard

**Estimate:** 0.5d
**Depends on:** 18-dialer-routing (who answers), Omni's dialer API token (27 Oct)
**Status:** page LIVE on `homies-dashboard.vercel.app/dialer` since 28 Oct (main `c97eca3`); `TOKOMNI_TOKEN` and `TOKOMNI_CAMPAIGN_ID` set in Vercel 28 Oct, 11:44 UTC; production redeployed with them 12:33 UTC (`dpl_hnfcMnUHm4VasRVmyhARgD9FZRGh`); the first press for Ido is owed

## Purpose

A test call through Omni's dialer used to mean building an Excel sheet and
uploading it as a new list in Tokomni, every time. This page puts one number
on the dialer with one press: type a number, or press the Ring button beside a
test person. The owner asked for it on 28 Oct: *"a section for testing there
where we just insert the number there or like call ido button"*.

## Behaviour

1. **The page** (`/dialer`, "בדיקת חייגן", under System in the sidebar and in
   the phone's top bar) has two panels:
   - **Ring a number:** one field and a Ring button. It takes an Israeli number
     in any form: dashes, spaces, `972`, `+972`, `00972`, and `+972 054…`.
   - **Test people in בר כוכבא 23:** one row per person we put in the test
     building ourselves (`residents.source = 'agent'`) with an Israeli number.
     Each row shows who will pick up and has its own button ("חייג לעידו").
     Today that is Ido's mobile. The building's OXS rows (Yariv's own number
     among them) get no button; they can still be typed.
2. **Who picks up** is read from `v_debt_call_queue_person`, the list feature
   18's router reads: exactly one row with something owed gets the debt agent
   ("₪2,000, call 2 of 4"); anything else gets Michael, the intake agent, with
   the reason.
3. **A press** (`lib/dialer.ts`, `dial()`), refused before anything is sent when:
   - `TOKOMNI_TOKEN` or `TOKOMNI_CAMPAIGN_ID` is not set (the buttons are off);
   - the number is not Israeli;
   - it is outside calling hours: Sunday to Thursday 09:00-20:00, Friday until
     13:00, never Saturday, Israel time (the buttons are off, and the page says
     the time in Israel);
   - the number is on file for a tenant outside the test building.
4. **Otherwise one lead goes to Omni:**

   ```
   POST https://api.tokomni.cc/api/campaign/insert/?token=<TOKOMNI_TOKEN>
   {"external_id": "<resident id or test>-<YYYYMMDDTHHMMSS UTC>",
    "campaign_id": "<TOKOMNI_CAMPAIGN_ID>", "number": "05XXXXXXXX"}
   ```

   It waits 8 seconds for an answer. List 2 is always on, so the dialer rings
   the number at once. The answered call reaches 208 and Vapi, and feature 18
   picks the agent.
5. **The outcome** comes back in the URL. On success it shows Tokomni's answer,
   who will pick up, the lead id, and what to check if nothing rings. On a
   refusal it shows the reason. With no answer at all, it says the lead may
   have landed and to check List 2 before pressing again.
6. **The Ring button greys out** while its press is on its way
   (`components/pending-button.tsx`), so a double click does not ring twice.

## Interface

Server action `ring(formData)` on the page → `dial(number)` →
`redirect('/dialer?r=…')`. Codes: `ok`, `http` (Tokomni refused), `net` (no
answer), `db` (the residents check failed), `tenant`, `number`, `hours`, `off`.

## Files

- `dashboard/app/(app)/dialer/page.tsx` and `loading.tsx`
- `dashboard/lib/dialer.ts`: server-only; the env, the checks, the call to Tokomni.
- `dashboard/lib/dialer-rules.ts`: pure; number form, calling hours, who answers, external_id, Tokomni's answer.
- `dashboard/components/pending-button.tsx`, `dashboard/types/react-dom.d.ts`
- `scripts/check_dialer.test.ts`: `node --test scripts/check_dialer.test.ts` (7 tests; "who answers" is run beside feature 18's `routeOf` on the same rows).

## Going live

1. **Done 28 Oct:** the page is on `main` (`c97eca3`) and deployed.
2. **Done 28 Oct, 11:44 UTC (owner's "set them"):** two values in Vercel (project `homies-dashboard`), copied from the repo root `.env`:
   - `TOKOMNI_TOKEN`, as Sensitive, for Production and Preview;
   - `TOKOMNI_CAMPAIGN_ID`, for all three environments.
3. **Done 28 Oct, 12:33 UTC (owner's "try again"):** production redeployed, so the running deployment has them (`dpl_hnfcMnUHm4VasRVmyhARgD9FZRGh`, the same `c97eca3`). The first try had been refused by the session's permission check as a production deploy. Any later change to either value needs another redeploy.
4. **List 2 must be playing** in Tokomni (Play pressed once).
5. **The first test:** Ido ready to pick up, in calling hours, then Ring Ido. He should get the debt agent with ₪2,000.

## Not in this feature

- **The Debts page's Call button** still goes to Vapi's phone number (feature 15), which does not exist. Moving it to the dialer is a separate decision.
- **A calling-hours check for the live dialer** in general. This page has its own.
- **Removing a lead from List 2.** Omni's API has no remove call.
- **Reading call results from Tokomni.** The outcome of the call is on the Calls page, from Vapi.
