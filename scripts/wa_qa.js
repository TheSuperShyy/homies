'use strict';
// The code half of the WhatsApp QA harness (scripts/wa_qa.py). A Claude
// player writes the model's turns offline; this runs the live workflow's OWN
// code around each of them, so what is graded is what a handset would get:
//
//   the inject       the bracket facts the model was handed, rendered by the
//                    live expression with the scenario's clock;
//   Worth a word?    the note the payment-ack model reads, and A word first?,
//                    which decides whether its ack went out;
//   Reply usable?    every guard, by id, and the note Try again would write;
//   Send             the greeting/name filter and the buttons;
//   Two parts?       the payment split, and Send the rest.
//
// Nothing here is a copy of n8n's code: every expression is the live node's
// own, extracted by wa_qa.py the way check_whatsapp_rules.py does it. No
// network, no model, nothing written to disk. Fed on stdin:
//   { code, clock: { time: 'HH:mm', weekday: 1-7, iso: '...' }, turns: [...] }
// and prints one JSON result per turn.
const fs = require('fs');

const P = JSON.parse(fs.readFileSync(0, 'utf8'));
const NL = String.fromCharCode(10);

function compile(args, body, what) {
  try {
    return new Function(...args, body);
  } catch (e) {
    return () => { throw new Error(what + ' does not compile: ' + e.message); };
  }
}

function build(X) {
  const map = (o, args) => Object.fromEntries(Object.entries(o || {})
    .map(([k, v]) => [k, compile(args, 'return (' + v + ');', k)]));
  return {
    isGreeting: compile(['text'], X.sort_greeting + NL + 'return isGreeting;', 'Sort greeting test'),
    send: compile(['$json', '$'], 'return (' + X.send_body + ');', 'Send'),
    sendRest: compile(['$json', '$'], 'return (' + X.send_rest + ');', 'Send the rest'),
    two: compile(['$json', '$'], 'return (' + X.two_parts + ');', 'Two parts?'),
    reply: map(X.reply_usable, ['$json', '$runIndex', '$']),
    // Date is an argument so the ack note's hour word follows the scenario's
    // clock and not this machine's.
    worth: compile(['$json', 'Date'], 'return (' + X.worth_text + ');', 'Worth a word?'),
    word: compile(['$json'], 'return (' + X.word_gate + ');', 'A word first?'),
    inject: compile(['$json', '$now'], 'return (' + X.inject + ');', 'the inject'),
    tryAgain: compile(['$json', '$'], 'return (' + X.try_again + ');', 'Try again'),
    sayNow: compile(['$json'], 'return (' + X.say_now + ');', 'Say it now'),
  };
}

// The agent's intermediateSteps, the way n8n records an HTTP tool's run.
function stepsOf(calls) {
  return (calls || []).map((c) => ({
    action: { tool: c.name, toolInput: c.arguments || {} },
    observation: JSON.stringify([{ results: [{ toolCallId: 'wa', result: JSON.stringify(c.result == null ? {} : c.result) }] }]),
  }));
}

function fakeDate(iso) {
  const Real = Date;
  class Fixed extends Real {
    constructor(...a) { if (a.length) { super(...a); } else { super(iso); } }
    static now() { return new Real(iso).getTime(); }
  }
  return Fixed;
}

// One turn, the way n8n hands each node its world.
function run(E, clock, o) {
  const S = {
    greeting: false, greeted: !!o.greeted, last_bot: o.last_bot || '', text: o.text || '',
    tap_now: !!o.tap_now, tap: o.tap || '', photo: !!o.photo, attachment: !!o.attachment,
    to: '599000000', conv_id: 0, burst_size: 1,
  };
  const ack = String(o.ack || '').trim();
  const acked = ack.toUpperCase() === 'NONE' ? '' : ack;          // Carry on
  const ackSent = acked !== '' && E.word({ output: acked }) === true; // A word first?
  const steps = stepsOf(o.tool_calls);
  const $now = { setZone: () => ({ toFormat: () => clock.time, weekday: clock.weekday }) };
  const nodes = {
    'Sort': { first: () => ({ json: S }) },
    'Still the last word?': { first: () => ({ json: Object.assign({}, S) }) },
    'Carry on': { first: () => ({ json: Object.assign({}, S, { acked }) }) },
    'Answer the resident': { first: () => ({ json: { output: o.output || '', intermediateSteps: steps } }) },
    'Type for a moment': { first: () => ({ json: { output: o.output || '' } }) },
    'Anything newer?': { all: () => [] },
    'Say it now': { all: () => { if (!ackSent) throw new Error('unexecuted'); return [{ json: {} }]; } },
    'Worth a word?': { first: () => ({ json: { output: ack || 'NONE' } }) },
  };
  const $ = (name) => { if (!nodes[name]) throw new Error('no node ' + name); return nodes[name]; };

  const out = { text: o.text || '' };
  // What the two models read.
  out.worth_input = String(E.worth({ greeted: S.greeted, text: S.text }, fakeDate(clock.iso)));
  out.inject = String(E.inject({
    greeted: S.greeted, text: S.text, tap_now: S.tap_now, photo: S.photo, attachment: S.attachment,
    last_bot: S.last_bot, retry_note: o.retry_note || '', acked,
  }, $now));
  out.ack_sent = ackSent;
  out.ack_text = ackSent ? JSON.parse(E.sayNow({ output: acked })).content : '';

  // The guards, by id, on the first pass.
  const j = { output: o.output || '', intermediateSteps: steps };
  out.guards = {};
  for (const [id, f] of Object.entries(E.reply)) {
    try { out.guards[id] = f(j, 0, $) === true; } catch (e) { out.guards[id] = 'THREW ' + e.message; }
  }
  out.failed = Object.entries(out.guards).filter(([, v]) => v !== true).map(([k]) => k);
  out.retry_note = out.failed.length ? JSON.parse(E.tryAgain({ output: o.output || '' }, $)).retry_note : '';

  // Send, and the payment split.
  let sent;
  try { sent = JSON.parse(E.send({ output: o.output || '' }, $)); } catch (e) { sent = { content: 'THREW ' + e.message }; }
  let two = false;
  try { two = E.two({}, $) === true; } catch (e) { two = false; }
  const handset = [];
  if (ackSent) handset.push(out.ack_text);
  handset.push(sent.content);
  if (two) {
    try { handset.push(JSON.parse(E.sendRest({}, $)).content); } catch (e) { handset.push('THREW ' + e.message); }
  }
  out.two = two;
  out.buttons = sent.content_type === 'input_select';
  out.handset = handset;
  return out;
}

const E = build(P.code);
if (P.mode === 'sort') {
  console.log(JSON.stringify((P.texts || []).map((t) => E.isGreeting(t) === true)));
} else {
  const res = (P.turns || []).map((t) => {
    try { return run(E, P.clock, t); } catch (e) { return { error: e.message, text: t.text }; }
  });
  console.log(JSON.stringify(res));
}
