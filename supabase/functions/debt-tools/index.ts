// Homies — the eight tools of the outbound debt agent (feature 10).
//
// One function, eight tools, because they share one hard rule and it is easier
// to keep true in one file than in eight: the model does not get to say which
// debt it is collecting.
//
// Deploy:
//   supabase functions deploy debt-tools --no-verify-jwt
// Then set the secrets it reads:
//   supabase secrets set TOOL_SECRET=...           # 32+ random chars
//
// --no-verify-jwt is deliberate. Vapi is not a Supabase user and cannot present
// a Supabase JWT. The shared secret in the X-Homies-Secret header is what
// stands in front of this instead. Unlike the Apps Script endpoint, an Edge
// Function can read request headers — so the secret does not have to travel in
// the query string where it lands in logs.
//
// THE RULE THIS FILE EXISTS TO ENFORCE
// The agent never supplies charge_id, resident_id, amount or period. Those come
// from the variableValues the campaign runner attached to the call, which the
// model can read but cannot change. A model that hallucinates an amount, or is
// talked into collecting a different debt, still writes the right row — because
// the row is not built from anything it said. This is the same principle as
// verify_identity being server-side: never the agent's own claim.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const db = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

const SECRET = Deno.env.get("TOOL_SECRET") ?? "";

/** What the campaign runner attached to the call. Set once, never from the model. */
type CallContext = {
  callId: string;
  chargeId: string | null;
  residentId: string | null;
  amount: number | null;
  period: string | null; // first of the month, e.g. 2026-07-01
  cardLast4: string | null;
  building: string | null;
  unit: string | null;
};

/**
 * Vapi nests the call one or two levels deep depending on the event, and
 * variableValues can sit on the assistant or on the override. Read all the
 * places it is known to appear rather than picking one and being wrong on a
 * version bump.
 */
function context(message: any): CallContext {
  const call = message?.call ?? {};
  const v =
    call?.assistantOverrides?.variableValues ??
    message?.assistant?.variableValues ??
    call?.assistant?.variableValues ??
    {};

  const num = (x: unknown) => {
    const n = Number(x);
    return Number.isFinite(n) && n > 0 ? n : null;
  };

  return {
    callId: call?.id ?? message?.callId ?? "",
    chargeId: v.charge_id ?? null,
    residentId: v.resident_id ?? null,
    amount: num(v.amount),
    period: v.period ?? null,
    cardLast4: v.card_last4 ? String(v.card_last4) : null,
    building: v.building ?? null,
    unit: v.unit ?? null,
  };
}

/**
 * payment_tickets has a CHECK that a captured authorisation must carry the call
 * it came from, because the recording IS the authorisation and a ticket nobody
 * can listen to must never be charged. But interactions is normally written by
 * the end-of-call report, which has not fired yet while the agent is still
 * talking. So the first tool call of any call creates the stub row, and the
 * end-of-call report fills in the transcript and audio later.
 */
async function interactionId(ctx: CallContext): Promise<string | null> {
  if (!ctx.callId) return null;

  // Read before write, rather than upsert. An upsert updates on conflict, which
  // would push started_at forward on every tool call until it recorded the last
  // one instead of the first — and started_at is what call duration is measured
  // from. A row that already exists is left exactly as it is.
  const found = await db
    .from("interactions")
    .select("id")
    .eq("external_call_id", ctx.callId)
    .maybeSingle();
  if (found.data?.id) return found.data.id;

  // Both of these were hardcoded — "voice" and "outbound" — from when Vapi was
  // the only caller, and both were already wrong: every WhatsApp interaction
  // written on 8 Aug is filed as an outbound voice call. The dashboard would
  // have reported those as calls that were placed, which is not a display bug
  // but a false statement about what happened.
  //
  // A chat is inbound by definition here: the resident writes first, always.
  const wa = channel(ctx) === "whatsapp";
  const { data } = await db
    .from("interactions")
    .insert({
      external_call_id: ctx.callId,
      channel: wa ? "whatsapp" : "voice",
      direction: wa ? "inbound" : "outbound",
      // The phone is on the call id as `wa:<number>` and nowhere else for chat,
      // so without this the row cannot be tied back to a person at all.
      caller_phone: wa ? ctx.callId.slice(3) : null,
      resident_id: ctx.residentId,
      started_at: new Date().toISOString(),
    })
    .select("id")
    .single();

  // Two tools firing at once both miss the select and one insert loses the
  // unique constraint. Re-read rather than fail: the row exists either way.
  if (data?.id) return data.id;
  const retry = await db
    .from("interactions")
    .select("id")
    .eq("external_call_id", ctx.callId)
    .maybeSingle();
  return retry.data?.id ?? null;
}

/**
 * Which front door this row came in through.
 *
 * Hardcoded "voice" at all three insert sites while Vapi was the only caller.
 * WhatsApp writes through this same function now, so every one of them was
 * about to start lying — and a channel column that lies is worse than one that
 * is absent, because every report broken down by channel would have been
 * quietly wrong rather than obviously empty.
 *
 * The `wa:` prefix is minted by the WhatsApp bot's tool nodes, which build a
 * call id of `wa:<phone>` precisely because this function was written for Vapi
 * and expects a call to exist.
 */
function channel(ctx: { callId?: string | null }): string {
  return String(ctx?.callId ?? "").startsWith("wa:") ? "whatsapp" : "voice";
}

/**
 * An apartment number, or nothing.
 *
 * A lobby leak has no apartment, and the prompt says so — but on 8 Aug the
 * model complied with the idea and not the field: it filled `unit` with
 * "שטחים משותפים" ("common areas"). Nothing errors. The row reads correctly to
 * a person and is wrong to every query: `unit IS NULL` no longer finds
 * common-area faults, grouping by unit invents a flat called Common Areas, and
 * the duplicate guard below stops matching, because two lobby leaks phrased
 * differently get two different "units".
 *
 * A model asked to leave a field empty will often name the emptiness instead.
 * So the writer decides, not the prompt: a unit is a short thing with a digit
 * in it, and a label is not a unit.
 */
function unitOf(value: unknown): string | null {
  const v = String(value ?? "").trim();
  if (!v) return null;
  // Long enough to be a phrase, or carrying no digit at all — "קומה ב" and
  // "ground floor" are as wrong as "common areas", and none of them identify a
  // flat. Kept deliberately crude: the cost of dropping an odd real unit is one
  // ticket a human still reads, and the cost of keeping a label is silent.
  if (v.length > 12 || !/\d/.test(v)) return null;
  return v;
}

/**
 * requests.urgency has been constrained to these four since migration 001.
 *
 * The value used to be passed straight through, so an out-of-enum word was
 * caught by Postgres and came back as an English constraint message in the
 * middle of a Hebrew call — which the agent can neither read out nor act on.
 * `urgent` reached here that way on 8 Aug from the WhatsApp bot's own tool
 * schema. The synonyms below are the near-misses a model actually produces;
 * anything else lands on normal, because urgency is inferred rather than asked
 * for and a wrong-but-valid value costs less than a failed write.
 *
 * Deliberately not clamped to `low`: the failure that matters is an emergency
 * filed as routine, so unknown words go to the middle and not to the floor.
 */
function urgency(value: unknown): string {
  const v = String(value ?? "").trim().toLowerCase();
  const allowed = ["low", "normal", "high", "emergency"];
  if (allowed.includes(v)) return v;
  const synonyms: Record<string, string> = {
    urgent: "high",
    critical: "emergency",
    immediate: "emergency",
    routine: "normal",
    medium: "normal",
    "": "normal",
  };
  return synonyms[v] ?? "normal";
}

// ---------------------------------------------------------------------------
// The tools
// ---------------------------------------------------------------------------
// Each returns a short object the agent can read back. Keep the strings plain:
// they land in the model's context and anything florid there gets spoken.

const tools: Record<string, (args: any, ctx: CallContext) => Promise<unknown>> = {
  /**
   * They agreed to settle, so OXS sends them a link and they pay it themselves.
   *
   * This replaced open_payment_ticket on 4 Aug. Nothing here sends the link:
   * the row is the request and OXS is the sender, which is why the agent says a
   * link is on its way rather than that one has arrived. When the OXS API is
   * finally documented, the call to it goes here — the tool's contract with the
   * agent does not change.
   *
   * Deliberately does NOT touch charges.status. The old flow moved the charge to
   * `pending_charge` because a staff member was about to charge a card; a link
   * that has been sent is not a payment, and marking it as one would take the
   * resident out of the call queue for something they have not done yet.
   */
  async send_payment_link(args, ctx) {
    if (!ctx.chargeId) return { ok: false, error: "no charge on this call" };
    const iid = await interactionId(ctx);

    const { error } = await db.from("payment_links").insert({
      charge_id: ctx.chargeId,
      resident_id: ctx.residentId,
      interaction_id: iid,
      amount: ctx.amount,
      period: ctx.period,
      status: "requested",
      note: args?.note ?? null,
    });

    if (error) return { ok: false, error: error.message };
    return { ok: true };
  },

  /**
   * Retired 4 Aug — no longer offered to the agent, kept so a stale assistant
   * still gets an answer. authorization_captured was the difference between
   * "a person may charge the card on file" and "the office has to call them".
   */
  async open_payment_ticket(args, ctx) {
    if (!ctx.chargeId) return { ok: false, error: "no charge on this call" };
    const captured = args?.authorization_captured === true;
    const iid = await interactionId(ctx);

    // The constraint would reject this anyway; failing here says why.
    if (captured && !iid) {
      return { ok: false, error: "cannot capture authorisation without a call record" };
    }

    // No card, no authorisation — the claim cannot be true whatever the agent
    // believed. It believed it on 4 Aug: a resident with no card on file was
    // told there was one and a ticket was written claiming they had approved a
    // charge to it. The prompt is asked not to do this; here it cannot.
    if (captured && !ctx.cardLast4) {
      return {
        ok: false,
        error: "no card on file for this resident — authorisation cannot be captured",
      };
    }

    const { data, error } = await db
      .from("payment_tickets")
      .insert({
        charge_id: ctx.chargeId,
        resident_id: ctx.residentId,
        interaction_id: iid,
        authorization_captured: captured,
        amount: ctx.amount,
        period: ctx.period,
        card_last4: ctx.cardLast4,
        note: args?.note ?? null,
      })
      .select("id")
      .single();

    if (error) return { ok: false, error: error.message };

    // Stop the same debt being called about again while a person reviews it.
    await db.from("charges").update({ status: "pending_charge" }).eq("id", ctx.chargeId);

    return { ok: true, ticket_id: data.id, authorization_captured: captured };
  },

  /**
   * `said` is their own words and is required. Our parse of a spoken Hebrew date
   * is the thing most likely to be wrong later, so what they actually said is
   * kept beside it and outranks it when a promise is disputed.
   */
  async log_promise_to_pay(args, ctx) {
    if (!ctx.chargeId) return { ok: false, error: "no charge on this call" };
    if (!args?.said) return { ok: false, error: "said is required" };

    const { error } = await db.from("promises_to_pay").insert({
      charge_id: ctx.chargeId,
      interaction_id: await interactionId(ctx),
      promised_date: args?.promised_date ?? null,
      said: String(args.said),
    });

    return error ? { ok: false, error: error.message } : { ok: true };
  },

  /**
   * There is no standing_orders table and there should not be one — the agent
   * cannot set a standing order up, only record that they asked for one. It is a
   * flag on the outcome, which is where a person will look for it.
   */
  async request_standing_order(_args, ctx) {
    if (!ctx.chargeId) return { ok: false, error: "no charge on this call" };
    await db.from("call_outcomes").insert({
      charge_id: ctx.chargeId,
      resident_id: ctx.residentId,
      interaction_id: await interactionId(ctx),
      outcome: "office_to_contact",
      standing_order_requested: true,
    });
    return { ok: true };
  },

  /** They say they already paid. The agent never asks when or how. */
  async log_disputed_payment(_args, ctx) {
    if (!ctx.chargeId) return { ok: false, error: "no charge on this call" };

    const { error } = await db.from("payment_disputes").insert({
      charge_id: ctx.chargeId,
      interaction_id: await interactionId(ctx),
      receipt_requested: true,
    });
    if (error) return { ok: false, error: error.message };

    await db.from("charges").update({ status: "disputed" }).eq("id", ctx.chargeId);
    return { ok: true };
  },

  /**
   * A resident asks what happened to a ticket. Read-only, and the answer is
   * live: these rows are the system of record for tickets opened here, so no
   * freshness caveat is owed — PRD §2.2's caveat is about OXS-side status,
   * which this deliberately does not touch.
   *
   * Lookup order mirrors open_request's asymmetry: an explicit reference wins,
   * then the resident on the call, then building+unit — context first,
   * arguments second. The reference matches on its numeric tail, because a
   * caller says "אלף שלוש עשרה", not "HM-2026-1013".
   */
  async get_request_status(args, ctx) {
    const fields =
      "reference,type,description,status,urgency,building,unit,created_at,updated_at";
    let rows: any[] | null = null;

    const tail = String(args?.reference ?? "").replace(/\D/g, "").slice(-4);
    if (tail.length === 4) {
      const { data, error } = await db
        .from("requests")
        .select(fields)
        .like("reference", "%-" + tail)
        .order("created_at", { ascending: false })
        .limit(3);
      if (error) return { ok: false, error: error.message };
      rows = data;
    }

    if (!rows?.length && ctx.residentId) {
      const { data, error } = await db
        .from("requests")
        .select(fields)
        .eq("resident_id", ctx.residentId)
        .order("created_at", { ascending: false })
        .limit(3);
      if (error) return { ok: false, error: error.message };
      rows = data;
    }

    if (!rows?.length) {
      const building = ctx.building || args?.building || "";
      const unit = unitOf(ctx.unit || args?.unit);
      if (building && unit) {
        const { data, error } = await db
          .from("requests")
          .select(fields)
          .eq("building", building)
          .eq("unit", unit)
          .order("created_at", { ascending: false })
          .limit(3);
        if (error) return { ok: false, error: error.message };
        rows = data;
      }
    }

    return {
      ok: true,
      found: rows?.length ?? 0,
      as_of: "live", // our own system of record, not a nightly export
      requests: (rows ?? []).map((r) => ({
        reference: r.reference,
        status: r.status, // open | in_progress | resolved | cancelled
        type: r.type,
        urgency: r.urgency,
        opened: String(r.created_at).slice(0, 10),
        last_update: String(r.updated_at).slice(0, 10),
        description: r.description ? String(r.description).slice(0, 200) : null,
      })),
    };
  },

  /**
   * A maintenance issue raised during a debt call, and the whole job of the
   * inbound intake agent. Acceptance criterion 7 is zero silent drops, so this
   * writes a real requests row and hands back the real reference — the agent is
   * forbidden from inventing one.
   */
  async open_request(args, ctx) {
    if (!args?.description) return { ok: false, error: "description is required" };

    // Context first, arguments second — the same order n8n uses, and the
    // asymmetry documented in vapi_tools.py LOCATION. Outbound, the building is
    // a fact attached to the call and the model may not overwrite it. Inbound
    // there is no caller ID and no lookup, so the only source is what the caller
    // just said, and these arguments are it.
    //
    // This read `ctx.building ?? ""` until 8 Aug, which is correct outbound and
    // silently wrong inbound: every intake ticket would have carried an empty
    // building while the agent read a reference number back to the caller.
    const building = ctx.building || args?.building || "";
    const unit = unitOf(ctx.unit || args?.unit);
    const type = args?.type ?? "other";

    // --- The duplicate guard ------------------------------------------------
    //
    // Same place, same kind of fault, still open, opened in the last 30 minutes
    // → hand back the reference that already exists instead of minting a second
    // one. The resident is told about their ticket either way and cannot tell
    // the difference; the difference is that a technician is not dispatched
    // twice to one leak.
    //
    // Three ways this happens and none of them are the resident being careless:
    // Meta retries a webhook that was slow to answer, a caller repeats
    // themselves when the line is bad, and a resident who has heard nothing for
    // an hour reports the same thing again. Only the first is a true duplicate
    // in the technical sense; all three should produce one ticket.
    //
    // It is deliberately NOT keyed on the description. Two people describing
    // one lobby leak will not phrase it the same way, and a substring match on
    // free text is exactly the kind of clever that fails silently at 3am.
    // Place plus type is coarse, and coarse is the safe direction: the failure
    // mode is a second genuine fault of the same kind in the same lobby inside
    // half an hour getting attached to the first, which a human reading the
    // ticket will catch. The opposite failure — two tickets, two vans — costs
    // real money and looks incompetent to the resident.
    //
    // 30 minutes, not 24 hours, because "the leak is back" the next morning is
    // a new fact and deserves its own row.
    const since = new Date(Date.now() - 30 * 60 * 1000).toISOString();
    let dupeQuery = db
      .from("requests")
      .select("reference")
      .eq("building", building)
      .eq("type", type)
      .gte("created_at", since)
      .in("status", ["open", "in_progress", "needs_review"])
      .order("created_at", { ascending: false })
      .limit(1);
    // .eq() never matches NULL in Postgres, so a common-area fault — which has
    // no unit — has to be asked for with .is(), or the guard silently never
    // fires on exactly the tickets most likely to be reported twice.
    dupeQuery = unit === null ? dupeQuery.is("unit", null) : dupeQuery.eq("unit", unit);

    const { data: existing } = await dupeQuery;
    if (existing && existing.length) {
      return { ok: true, reference: existing[0].reference, duplicate: true };
    }

    const { data, error } = await db
      .from("requests")
      .insert({
        resident_id: ctx.residentId,
        interaction_id: await interactionId(ctx),
        type,
        description: String(args.description),
        building,
        unit,
        urgency: urgency(args?.urgency),
        opened_via: channel(ctx),
      })
      .select("reference")
      .single();

    return error ? { ok: false, error: error.message } : { ok: true, reference: data.reference };
  },

  /**
   * The net under the inbound agent: a call that is already failing still leaves
   * a row. Never refuses — a validation error here turns a salvaged call into a
   * lost one, and an empty description is a real answer, because it says the
   * audio was unusable, which is exactly what the row is for.
   *
   * `needs_review` is the status migration 003 added for this, and the reason
   * type/description/building are nullable on that status alone. Captured slots
   * are trustworthy; empty ones were never captured and are never guessed.
   *
   * Was missing from this file until 8 Aug while the live intake assistant
   * carried the tool, so pointing that assistant here would have answered
   * `unknown tool save_partial_request` at the exact moment it was salvaging a
   * call.
   */
  async save_partial_request(args, ctx) {
    const reasons = ["audio", "time_limit", "caller_left"];
    const reason = reasons.includes(args?.reason) ? args.reason : "audio";
    const description = args?.description ? String(args.description) : null;

    const { data, error } = await db
      .from("requests")
      .insert({
        resident_id: ctx.residentId,
        interaction_id: await interactionId(ctx),
        description,
        building: ctx.building || args?.building || null,
        unit: unitOf(ctx.unit || args?.unit),
        urgency: "normal",
        status: "needs_review",
        opened_via: channel(ctx),
        oxs_ref: `partial:${reason}`,
      })
      .select("reference")
      .single();

    // Still ok:true on a failure. The agent is seconds from losing the call and
    // there is nothing useful it can do with the error; the end-of-call report
    // writes its own partial from the transcript regardless.
    return error ? { ok: true } : { ok: true, reference: data.reference };
  },

  /**
   * Not handed over. This stops every future call for the apartment, which is
   * why the agent cannot undo it — the tool contract says irreversible and there
   * is deliberately no tool that sets handed_over back to true.
   */
  async flag_not_handed_over(_args, ctx) {
    if (!ctx.residentId) return { ok: false, error: "no resident on this call" };

    await db.from("residents").update({ handed_over: false }).eq("id", ctx.residentId);
    if (ctx.chargeId) {
      await db.from("charges").update({ status: "waived" }).eq("id", ctx.chargeId);
    }
    return { ok: true };
  },

  /**
   * The transfer itself is Vapi's, configured on the assistant. This records why,
   * so the reason survives even when no rep is free and the transfer fails.
   */
  async transfer_to_human(args, ctx) {
    const reasons = ["hardship", "dispute", "distress", "language", "not_understood", "caller_request"];
    const reason = reasons.includes(args?.reason) ? args.reason : "caller_request";

    await db.from("call_outcomes").insert({
      charge_id: ctx.chargeId,
      resident_id: ctx.residentId,
      interaction_id: await interactionId(ctx),
      outcome: "transferred",
      transfer_reason: reason,
      posture_reached: args?.posture_reached ?? null,
    });

    // Matches the scoreboard query in 08-instrumentation.
    await db
      .from("interactions")
      .update({ disposition: `transfer:${reason}` })
      .eq("external_call_id", ctx.callId);

    return { ok: true, reason };
  },

  /**
   * Every call, always — including voicemail, wrong party and no answer.
   * posture_reached is the number worth watching: hot is a floor, so the rate of
   * hot calls is the honest measure of whether the agent is damaging
   * relationships. Nothing else in the system records it.
   */
  async log_call_outcome(args, ctx) {
    const outcomes = [
      "authorized", "promised", "disputed", "refused", "transferred", "voicemail",
      "wrong_party", "not_handed_over", "no_answer", "office_to_contact",
    ];
    if (!outcomes.includes(args?.outcome)) {
      return { ok: false, error: `outcome must be one of: ${outcomes.join(", ")}` };
    }

    const { error } = await db.from("call_outcomes").insert({
      charge_id: ctx.chargeId,
      resident_id: ctx.residentId,
      interaction_id: await interactionId(ctx),
      outcome: args.outcome,
      posture_reached: args?.posture_reached ?? null,
      transfer_reason: args?.transfer_reason ?? null,
    });
    if (error) return { ok: false, error: error.message };

    // The attempt counter gates the queue at four. Properly this belongs to the
    // campaign runner, which knows a call was placed even when the agent never
    // reached this tool; doing it here too is the backstop, not the design.
    if (ctx.chargeId) {
      await db.rpc("bump_charge_attempt", { p_charge_id: ctx.chargeId }).then(
        () => {},
        () => {}, // the view still works without it; never fail a call over a counter
      );
    }

    return { ok: true };
  },
};

// ---------------------------------------------------------------------------
// The end-of-call report
// ---------------------------------------------------------------------------
// Vapi POSTs this to the assistant's server URL once the call is over, carrying
// everything that only exists after the fact: the transcript, the recording, the
// reason it ended, the duration, the cost, and the per-stage latency.
//
// Nothing consumed it until 8 Aug, so `interactions` had zero rows while eleven
// test calls happened — every transcript, every latency number and every ended
// reason lived in the Vapi dashboard and nowhere the CRM, the scoreboard in
// 08-instrumentation or a native Hebrew reviewer could reach. The tools wrote
// stub interaction rows during the call and nothing ever filled them in.
//
// It also closes the hole `maxDurationSeconds` opens. Vapi hangs up on the
// second the cap expires, mid-word, and never tells the model it is coming — so
// the agent cannot be relied on to call save_partial_request first. A server
// that sees endedReason `max-duration-exceeded` writes the partial itself, from
// the transcript, with no cooperation from the model at all. That is the version
// that cannot be talked out of.

/** Vapi's endedReason -> what a human reading the CRM needs to know. */
function disposition(reason: string): string {
  if (!reason) return "unknown";
  if (reason.includes("assistant-said-end-call-phrase")) return "completed";
  if (reason.includes("customer-ended-call")) return "caller_hung_up";
  if (reason.includes("max-duration")) return "cut_off_time_limit";
  if (reason.includes("silence-timed-out")) return "silence";
  if (reason.includes("voicemail")) return "voicemail";
  if (reason.includes("error") || reason.includes("failed")) return `error:${reason}`;
  return reason;
}

async function endOfCall(message: any, ctx: CallContext) {
  const call = message?.call ?? {};
  const artifact = message?.artifact ?? {};
  const endedReason = String(message?.endedReason ?? call?.endedReason ?? "");

  const startedAt = message?.startedAt ?? call?.startedAt ?? null;
  const endedAt = message?.endedAt ?? call?.endedAt ?? new Date().toISOString();
  const duration =
    message?.durationSeconds != null
      ? Math.round(Number(message.durationSeconds))
      : startedAt
      ? Math.round((Date.parse(endedAt) - Date.parse(startedAt)) / 1000)
      : null;

  // Vapi has moved this between message.performanceMetrics and the artifact
  // across versions, and reports it under two names. Read every known place: a
  // null here is indistinguishable from a fast call, which is the one number
  // this whole report was wired up to stop guessing at.
  const perf =
    message?.performanceMetrics ??
    artifact?.performanceMetrics ??
    call?.performanceMetrics ??
    {};
  const latency =
    perf?.turnLatency?.average ??
    perf?.modelLatencyAverage ??
    perf?.averageTurnLatency ??
    null;

  // The transcript, then the structured turns as a fallback. A call that ends in
  // the first second has neither, and an empty string is a truer record than a
  // null that reads as "we did not ask".
  const transcript =
    artifact?.transcript ??
    message?.transcript ??
    (Array.isArray(artifact?.messages)
      ? artifact.messages
          .filter((m: any) => m?.role && m?.role !== "system" && m?.message)
          .map((m: any) => `${m.role}: ${m.message}`)
          .join("\n")
      : null);

  const toolCalls = Array.isArray(artifact?.messages)
    ? artifact.messages
        .flatMap((m: any) => m?.toolCalls ?? [])
        .map((t: any) => ({ name: t?.function?.name, arguments: t?.function?.arguments }))
        .filter((t: any) => t.name)
    : [];

  const row = {
    channel: "voice",
    // Web calls have no phone number at either end. `type` is `webCall`,
    // `outboundPhoneCall` or `inboundPhoneCall`, and it is the only reliable
    // signal — the demo runs entirely on web calls, so direction cannot be
    // inferred from a customer number that is never there.
    direction: String(call?.type ?? "").toLowerCase().includes("inbound") ? "inbound" : "outbound",
    resident_id: ctx.residentId,
    caller_phone: call?.customer?.number ?? null,
    transcript,
    summary: message?.summary ?? artifact?.summary ?? null,
    audio_url: message?.recordingUrl ?? artifact?.recordingUrl ?? artifact?.recording?.stereoUrl ?? null,
    duration_seconds: duration,
    latency_ms: latency != null ? Math.round(Number(latency)) : null,
    tool_calls: toolCalls,
    started_at: startedAt,
    ended_at: endedAt,
  };

  // The tools create a stub row during the call, so update-then-insert rather
  // than insert. `disposition` is only written here if a tool has not already
  // set a more specific one — transfer:hardship says more than caller_hung_up,
  // and the transfer is the fact worth keeping.
  const existing = await db
    .from("interactions")
    .select("id, disposition, resident_id")
    .eq("external_call_id", ctx.callId)
    .maybeSingle();

  if (existing.data?.id) {
    await db
      .from("interactions")
      .update({
        ...row,
        resident_id: ctx.residentId ?? existing.data.resident_id,
        disposition: existing.data.disposition ?? disposition(endedReason),
      })
      .eq("id", existing.data.id);
    return { id: existing.data.id, endedReason };
  }

  const { data } = await db
    .from("interactions")
    .insert({ ...row, external_call_id: ctx.callId, disposition: disposition(endedReason) })
    .select("id")
    .single();
  return { id: data?.id ?? null, endedReason };
}

/**
 * The call was cut off by the duration cap and no row was written. Salvage one.
 *
 * Only fires when the call produced nothing — a completed request or a partial
 * the agent saved itself both count, and this stays out of the way. The
 * transcript goes in verbatim under `needs_review` because the alternative is
 * summarising it here, and a guessed building on a maintenance ticket sends
 * somebody to the wrong address.
 */
async function salvage(interactionId: string | null, ctx: CallContext, transcriptFrom: any) {
  if (!interactionId) return false;

  const already = await db
    .from("requests")
    .select("id")
    .eq("interaction_id", interactionId)
    .limit(1);
  if (already.data?.length) return false;

  const text = transcriptFrom ?? null;
  const { error } = await db.from("requests").insert({
    resident_id: ctx.residentId,
    interaction_id: interactionId,
    description: text ? String(text).slice(0, 4000) : null,
    building: ctx.building || null,
    unit: unitOf(ctx.unit),
    urgency: "normal",
    status: "needs_review",
    opened_via: channel(ctx),
    oxs_ref: "partial:cut_off",
  });
  return !error;
}

// ---------------------------------------------------------------------------
// Vapi's tool protocol
// ---------------------------------------------------------------------------
// It POSTs { message: { toolCalls: [ { id, function: { name, arguments } } ] } }
// and expects { results: [ { toolCallId, result } ] } where result is a string.
// `arguments` arrives as an object on some versions and a JSON string on others.

Deno.serve(async (req) => {
  if (req.headers.get("x-homies-secret") !== SECRET || !SECRET) {
    return new Response(JSON.stringify({ error: "unauthorised" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  let body: any;
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "bad json" }), { status: 400 });
  }

  const message = body?.message ?? {};
  const ctx = context(message);
  const calls = message?.toolCalls ?? [];

  // Server messages arrive on the same URL as tool calls and are told apart by
  // `type`. Everything that is not a tool call gets 200 and is ignored by name:
  // Vapi retries a non-2xx, and a status-update retried forever is noise that
  // looks like an outage. Adding a serverMessage to the assistant is therefore
  // safe here — an unhandled one costs nothing.
  const type = String(message?.type ?? "");
  if (type && !calls.length) {
    if (type !== "end-of-call-report") {
      return new Response(JSON.stringify({ ok: true, ignored: type }), {
        headers: { "content-type": "application/json" },
      });
    }
    try {
      const { id, endedReason } = await endOfCall(message, ctx);
      let salvaged = false;
      if (endedReason.includes("max-duration") || endedReason.includes("silence-timed-out")) {
        const artifact = message?.artifact ?? {};
        salvaged = await salvage(id, ctx, artifact?.transcript ?? message?.transcript ?? null);
      }
      return new Response(JSON.stringify({ ok: true, interaction: id, salvaged }), {
        headers: { "content-type": "application/json" },
      });
    } catch (e) {
      // 200 on failure, on purpose. The call is already over, so a retry storm
      // buys nothing, and the report is the only copy — losing it to a 500 that
      // Vapi replays six times is worse than losing it once, visibly.
      return new Response(JSON.stringify({ ok: false, error: String(e) }), {
        headers: { "content-type": "application/json" },
      });
    }
  }

  const results = await Promise.all(
    calls.map(async (c: any) => {
      const name = c?.function?.name;
      let args = c?.function?.arguments ?? {};
      if (typeof args === "string") {
        try { args = JSON.parse(args); } catch { args = {}; }
      }

      const fn = tools[name];
      if (!fn) return { toolCallId: c.id, result: JSON.stringify({ ok: false, error: `unknown tool ${name}` }) };

      try {
        return { toolCallId: c.id, result: JSON.stringify(await fn(args, ctx)) };
      } catch (e) {
        // Never throw at Vapi. A 500 mid-call is dead air; a failed result at
        // least lets the agent say it will check and come back to them.
        return { toolCallId: c.id, result: JSON.stringify({ ok: false, error: String(e) }) };
      }
    }),
  );

  return new Response(JSON.stringify({ results }), {
    headers: { "content-type": "application/json" },
  });
});
