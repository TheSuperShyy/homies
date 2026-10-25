# Who answers on the 208 line

**Estimate:** 1d
**Depends on:** 15-call-button (the debt agent's variables), 17-name-before-ticket (`callNumberOf`)
**Status:** built 25 Oct, tested offline; not live

## Purpose

Omni's extension 208 takes two kinds of call: a caller who pressed 9 in the
main number's menu, and a tenant Omni's dialer rang and who picked up. Until
this, the line answered every call with the incoming agent, so a dialer call
reached a receptionist who did not know whom it had called or what they owe.
This picks the agent per call, so a dialer call to a tenant on the debt call
list gets the debt agent with that tenant's figures.

## Behaviour

1. The 208 address names no agent. It names a server: debt-tools, with the
   `x-homies-secret` and `x-region: ap-northeast-1` headers the agents use, and
   10 seconds to answer. Vapi sends it `assistant-request` as each call starts.
2. A dialer call is one whose caller name starts `dialer-` (Omni's dialer names
   its calls `dialer-<the number it rang>`). Its number is `callNumberOf()`,
   the same reading as feature 17, from the SIP URI.
3. The number is looked up in `v_debt_call_queue_person`: people a person put on
   the list (unpaid, handed over, not on do-not-call, under four attempts).
4. Exactly one row, with something owed: the debt agent, with that row's
   variables composed exactly as the Call button composes them
   (`debtVariables`, byte-identical texts to `dashboard/lib/call.ts`).
5. Anything else gets the incoming agent, as before. That covers a press-9 call, staff on an
   extension, no number, nobody on the list, two rows on one number, nothing
   owed, a failed read, or any error.

## Interface

`assistant-request` in, Vapi's `ServerMessageResponseAssistantRequest` out:

```json
{ "assistantId": "<debt agent>", "assistantOverrides": { "variableValues": { "first_name": "…", "amount": "2000", "…": "…" } } }
```

or `{ "assistantId": "<incoming agent>" }`.

## Files

- `supabase/functions/debt-tools/route.ts`: the pure rules (`isDialerCall`, `routeOf`, `debtVariables`).
- `supabase/functions/debt-tools/index.ts`: `assistantFor()`, answered before any other server message.
- `scripts/vapi_sip.py --route on|off [--apply]`: points the 208 address at the server, or back at the incoming agent.
- `scripts/check_route.test.ts`: `node --test scripts/check_route.test.ts`.

## Going live (the owner's go, both steps)

1. `python scripts/supabase_functions.py --apply --oxs-mirror`. This is inert until step 2.
   Without `--oxs-mirror`, a plain deploy deletes the OXS mirror.
2. `python scripts/vapi_sip.py --route on --apply`, which reads the address back.
3. Test with Ido Clix (בר כוכבא 23 flat 1, ₪2,000):
   - pressing 9 gets the incoming agent;
   - his own number uploaded in Tokomni gets the debt agent.

**Undo:** `python scripts/vapi_sip.py --route off --apply`.

## Not in this feature

- **The feminine pronunciation dictionary for women on dialer calls.** The Call button copies the debt agent's voice with a Vapi key, and the function holds none.
- **The Call button sending numbers to Omni's dialer.** It needs Omni's API token.
- **A calling-hours check.**
- **Counting unanswered calls.** They never reach Vapi, so they come from Tokomni's report.
