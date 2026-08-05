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

  const { data } = await db
    .from("interactions")
    .insert({
      external_call_id: ctx.callId,
      channel: "voice",
      direction: "outbound",
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
   * A maintenance issue raised during a debt call. Acceptance criterion 7 is
   * zero silent drops, so this writes a real requests row and hands back the
   * real reference — the agent is forbidden from inventing one.
   */
  async open_request(args, ctx) {
    if (!args?.description) return { ok: false, error: "description is required" };

    const { data, error } = await db
      .from("requests")
      .insert({
        resident_id: ctx.residentId,
        interaction_id: await interactionId(ctx),
        type: args?.type ?? "other",
        description: String(args.description),
        building: ctx.building ?? "",
        unit: ctx.unit,
        urgency: args?.urgency ?? "normal",
        opened_via: "voice",
      })
      .select("reference")
      .single();

    return error ? { ok: false, error: error.message } : { ok: true, reference: data.reference };
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
