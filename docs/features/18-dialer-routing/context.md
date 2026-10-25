# Who answers on the 208 line: context

**One extension for both directions was Homies' choice with Omni (Yariv, 12 Oct).**
The menu's bot option and the dialer's answered calls both ring 208. So our side tells them apart per call, which is what this feature does.

**Why the caller name and not Omni's external_id.**
- Omni's external_id is "still under review" (25 Oct).
- The one dialer call we have (21 Oct, `01a15d92`) carried none. Its INVITE has `dialer-<number>` as the caller, `X-OMNIUF-XT: 208`, Omni's account code and call ids.
- The name already tells a dialer call apart, and its number finds the tenant.
- When an id arrives (Vapi keeps every INVITE header under `phoneCallProviderDetails.sip.headers`), it can replace the number match. Nothing else here changes.

**Why only the call list.**
- Omni's dialer rings whatever is uploaded, at any hour, and Tokomni uploads are by hand (Ido, for now).
- Reading only `v_debt_call_queue_person` means a debt conversation needs our side's own decision: the handed-over flag that the Call button's press sets.
- A real tenant uploaded by mistake meets the receptionist, not a demand for money.
- Two rows on one number get the receptionist, because the agent never guesses whose debt it is.

**Why the incoming agent on every doubt.**
- An `assistant-request` that fails hangs the caller up (Vapi's spec; there is no `fallbackDestination` on the address).
- So `assistantFor()` always answers, and any error answers what the line answered before.
- **The one new dependency:** if the function itself is down, the line cannot answer at all. Before, the agent answered and only its tools failed.

**Why the Call button's composer is copied, not shared.**
- The dashboard (Next.js) and the function (Deno) build separately.
- So `route.ts` copies the texts, and the test runs the dashboard's own `debtVariableValues` beside ours on the same rows.
- A change to either side fails the test until the other follows.

**Ruled out:**
- **A second SIP address for the dialer.** It still needs a server to find the tenant, and it means another change on Omni's side.
- **The debt agent looking the caller up by a tool call.** Its first sentence is a template filled at the start of the call, before any tool can run.
