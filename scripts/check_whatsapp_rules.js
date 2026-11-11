'use strict';
// The WhatsApp bot's rules and its past bugs, run against the EXACT code n8n
// runs -- Sort's greeting test, Send's body, the guards, the notes a model is
// handed. Fed on stdin by scripts/check_whatsapp_rules.py, whose docstring
// says why this exists. No network, no model, nothing written to disk.
//
// A BUG FIXED IS A CASE ADDED HERE. The cases below are the owner's greeting
// table and every bug that could be written down as "this in, that out".
const fs = require('fs');

const P = JSON.parse(fs.readFileSync(0, 'utf8'));
const NL = String.fromCharCode(10);
// 8 Oct (n8n_whatsapp_menuline.py): the menu says it is Homies. The old sentence
// stays as a case: a chat whose last menu went out before the change.
const MENU_TEXT = 'צהריים טובים 👋 כאן הומי' + "'" + 'ז. במה אפשר לעזור?';
const MENU_TEXT_BEFORE = 'צהריים טובים 👋 במה אפשר לעזור?';

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
    // `$now` since 9 Nov (n8n_whatsapp_feedback9.py): danger v6 reads the office hours; none reads as open.
    send: compile(['$json', '$', '$now'], 'return (' + X.send_body + ');', 'Send'),
    reply: map(X.reply_usable, ['$json', '$runIndex', '$']),
    second: map(X.second_try, ['$json', '$runIndex', '$']),
    // 5 Oct: the last resort without a model (scripts/n8n_whatsapp_safetynet.py).
    claimed: map(X.claimed, ['$json', '$runIndex', '$']),
    mend: X.mend ? compile(['$json', '$'], 'return (' + X.mend + ');', 'Mend the reply') : null,
    outage: map(X.outage_gate, ['$json', '$runIndex', '$']),
    worth: compile(['$json'], 'return (' + X.worth_text + ');', 'Worth a word?'),
    word: compile(['$json', '$'], 'return (' + X.word_gate + ');', 'A word first?'),
    carry: compile(['$json', '$'], 'return (' + X.carry_on + ');', 'Carry on'),
    // `$` since 29 Oct: section 6's inject reads the sender's line from `Add who`.
    inject: compile(['$json', '$now', '$'], 'return (' + X.inject + ');', 'the inject'),
    tryAgain: compile(['$json', '$'], 'return (' + X.try_again + ');', 'Try again'),
    teamNote: compile(['$json', '$'], 'return (' + X.team_note + ');', 'Team note this turn?'),
    // 6 Nov (scripts/n8n_whatsapp_retest3.py): a Code node's body, run as n8n runs it.
    lastWord: X.last_word ? compile(['$input', '$'], X.last_word, 'Still the last word?') : null,
  };
}

// One mocked turn, the way n8n hands Send its world. `ackSent` false means
// `Say it now` did not run, and n8n throws on an unexecuted node.
function turn(o) {
  const S = Object.assign({ greeting: !!o.canned, greeted: true, last_bot: '', text: o.said || '', tap_now: false }, o.S || {});
  const nodes = {
    'Sort': { first: () => ({ json: S }) },
    'Still the last word?': { first: () => ({ json: S }) },
    'Carry on': { first: () => ({ json: { acked: o.acked || '', text: o.said || '' } }) },
    'Answer the resident': { first: () => ({ json: { intermediateSteps: o.steps || [] } }) },
    'Anything newer?': { all: () => (o.rows || []).map((r) => ({ json: r })) },
    'Say it now': { all: () => { if (!o.ackSent) throw new Error('unexecuted'); return [{ json: {} }]; } },
  };
  const $ = (name) => { if (!nodes[name]) throw new Error('no node ' + name); return nodes[name]; };
  return { $json: o.canned ? { text: o.reply } : { output: o.reply }, $, $now: o.now };
}
const sent = (E, o) => { const m = turn(o); return JSON.parse(E.send(m.$json, m.$, m.$now)); };
const content = (E, o) => sent(E, o).content;
// 10 Nov: Send's promise version as a number, so a block for vN keeps running on every later version
// (the v5 block was keyed to 'promise v5' exactly and stopped running when epoch 100 made it v6).
const promiseV = (body) => { const m = String(body || '').match(/const pv = 'promise v(\d+)'/); return m ? +m[1] : 0; };
// 11 Nov: Send's manners version, the same way (n8n_whatsapp_hiintro.py made it v5).
const mannersV = (body) => { const m = String(body || '').match(/const mv = 'manners v(\d+)'/); return m ? +m[1] : 0; };
// 11 Nov: Send's danger version, the same way (n8n_whatsapp_hotline.py made it v7: our emergency line at any hour).
// The v5 and v4 blocks below were keyed to 'danger v[56]' and 'danger v[456]' and would have stopped at v7.
const dangerV = (body) => { const m = String(body || '').match(/const dv = 'danger v(\d+)'/); return m ? +m[1] : 0; };
// 11 Nov (n8n_whatsapp_hotline.py, danger v7): the one sentence Send adds when an emergency turn's reply has no line.
const HOTS = 'למקרי חירום יש לנו מוקד טלפוני ייעודי, ואפשר להתקשר אליו עכשיו: 077-6687949.';
// 11 Nov, evening (n8n_whatsapp_line.py): Send's line step, the same way. 0 where there is none.
const lineV = (body) => { const m = String(body || '').match(/const lv = 'line v(\d+)'/); return m ? +m[1] : 0; };
// 11 Nov, night (n8n_whatsapp_confirm.py): the copy guard's version, read from Reply usable?'s `repeat`. 1 before the label.
const repeatV = (code) => { const m = String(code || '').match(/const rpv = 'repeat v(\d+)'/); return m ? +m[1] : (code ? 1 : 0); };

function mask(s) {
  return String(s).replace(/https?:\/\/\S+/g, '<link>').replace(/\+?\d{9,15}/g, '<phone>')
    .replace(/\s+/g, ' ').slice(0, 110);
}

// ---------------------------------------------------------------------------
// The cases.
// ---------------------------------------------------------------------------
function cases(E) {
  let fails = 0;
  let n = 0;
  function expect(name, fn, want) {
    n++;
    let got;
    try { got = fn(); } catch (e) { got = 'THREW: ' + e.message; }
    const ok = got === want;
    if (!ok) fails++;
    console.log((ok ? 'PASS ' : 'FAIL ') + name + (ok ? '' : NL + '      got : ' + JSON.stringify(got) + NL + '      want: ' + JSON.stringify(want)));
  }
  const say = (o) => () => content(E, o);

  console.log('--- Sort: a bare hello gets the menu, and only a bare hello ---');
  for (const t of ['hi', 'היי', 'שלום', 'מה נשמע', 'wassup',
    // 27 Sep, executions 65683/65694: a RUN of hellos is still a hello.
    'hello good afternoon', 'hello, good afternoon', 'Hello Good Afternoon 👋', 'hey good morning',
    'היי, צהריים טובים!', 'hi there good evening', 'שלום שלום']) {
    expect('menu: ' + JSON.stringify(t), () => E.isGreeting(t), true);
  }
  for (const t of ['hello good afternoon, the lights are out', 'בוקר טוב, מה נשמע?', 'hey whatsup',
    'לילה טוב, שלום', 'שלום, יש נזילה', 'היי מיכאל', 'hi is this homies support?', 'היתרה שלי?', '']) {
    expect('model, not the menu: ' + JSON.stringify(t), () => E.isGreeting(t), false);
  }

  console.log(NL + "--- Send: the owner's greeting table (27 Sep, \"greet back once, never twice\") ---");
  const TODAY = "צהריים טובים, מיכאל מהומי'ז. אני מבין שיש תקלה בתאורה. באיזה בניין ובאיזו דירה?";
  const MENU_ROW = { direction: 'outbound', body: MENU_TEXT };
  const HI_ROW = { direction: 'inbound', body: 'hi' };
  const PAY_REPLY = "צהריים טובים! מיכאל מהומי'ז כאן. איך אפשר לעזור בתשלום?";
  expect('first reply in a conversation: greeting + name kept',
    say({ reply: TODAY, S: { greeted: false }, said: 'hey good morning, lights flicker' }), TODAY);
  expect('resident greets mid-conversation: one greeting back, no name',
    say({ reply: TODAY, said: 'hi, so i want to let you know' }),
    'צהריים טובים, אני מבין שיש תקלה בתאורה. באיזה בניין ובאיזו דירה?');
  expect('resident does not greet mid-conversation: no greeting, no name',
    say({ reply: TODAY, said: 'the elevator is stuck too' }), 'אני מבין שיש תקלה בתאורה. באיזה בניין ובאיזו דירה?');
  expect('right after the system menu (last_bot): no greeting, name kept',
    say({ reply: PAY_REPLY, said: 'I want to pay', S: { last_bot: MENU_TEXT } }), "מיכאל מהומי'ז כאן. איך אפשר לעזור בתשלום?");
  expect('after the menu, race: last_bot empty but Anything newer? shows the menu',
    say({ reply: PAY_REPLY, said: 'I want to pay', rows: [{ direction: 'inbound', body: 'I want to pay' }, MENU_ROW, HI_ROW] }),
    "מיכאל מהומי'ז כאן. איך אפשר לעזור בתשלום?");
  expect('after the menu, race: a menu sent before 8 Oct (the old tail) still counts',
    say({ reply: PAY_REPLY, said: 'I want to pay', rows: [{ direction: 'inbound', body: 'I want to pay' },
      { direction: 'outbound', body: MENU_TEXT_BEFORE }, HI_ROW] }),
    "מיכאל מהומי'ז כאן. איך אפשר לעזור בתשלום?");
  expect('a reply that copies the 8 Oct menu sentence gets the buttons',
    () => sent(E, { reply: MENU_TEXT, said: 'hi there', S: { greeted: false } }).content_type, 'input_select');
  expect('a reply that copies the old menu sentence still gets them',
    () => sent(E, { reply: MENU_TEXT_BEFORE, said: 'hi there', S: { greeted: false } }).content_type, 'input_select');
  expect('an ack that greeted and named went out: the answer loses both',
    say({ reply: "שלום רב, מיכאל מהומי'ז. הנה הקישור לתשלום שלכם.", said: 'hi, link please', S: { greeted: false },
      acked: "בוקר טוב, כאן מיכאל מהומי'ז, רגע אני בודק", ackSent: true }), 'הנה הקישור לתשלום שלכם.');
  expect('an ack computed but NOT sent: the greeting back is kept',
    say({ reply: 'היי! הנה הקישור לתשלום שלכם.', said: 'hi, link please', acked: 'רגע, אני בודק', ackSent: false }),
    'היי! הנה הקישור לתשלום שלכם.');
  expect('an ack sent without a greeting, resident greeted: the greeting back is kept',
    say({ reply: 'היי! הנה הקישור לתשלום שלכם.', said: 'hi, link please', acked: 'רגע, אני בודק', ackSent: true }),
    'היי! הנה הקישור לתשלום שלכם.');
  expect('two greetings in one message: one kept',
    say({ reply: 'היי! צהריים טובים, איזה לא נעים. באיזה בניין?', said: 'hi there, lights' }), 'היי! איזה לא נעים. באיזה בניין?');
  expect('the canned menu passes untouched', say({ canned: true, reply: MENU_TEXT }), MENU_TEXT);

  console.log(NL + '--- Send: 27 Sep afternoon, the name step (executions 65683, 65694) ---');
  const R = 'צהריים טובים!' + NL + "אני מיכאל מהומי'ז, ובשמחה אעזור לכם." + NL + 'במה אוכל לעזור?';
  const ACK = 'צהריים טובים, אני מבין שאתם צריכים קישור לתשלום. אני בודק את זה כרגע.';
  expect('65683 exactly: an ack that greeted, then this: only the question is left',
    say({ reply: R, said: 'hello good afternoon', acked: ACK, ackSent: true }), 'במה אוכל לעזור?');
  expect('the same answer, no ack, resident greeted: one greeting back, no introduction',
    say({ reply: R, said: 'hello good afternoon, quick question' }), 'צהריים טובים!' + NL + 'במה אוכל לעזור?');
  expect('the same answer, no ack, resident did not greet: the question only',
    say({ reply: R, said: 'the elevator is stuck' }), 'במה אוכל לעזור?');
  expect('the same answer as a first reply: untouched', say({ reply: R, S: { greeted: false }, said: 'hi' }), R);
  expect('the same answer right after the menu: greeting cut, name kept',
    say({ reply: R, said: 'question', S: { last_bot: MENU_TEXT } }), "אני מיכאל מהומי'ז, ובשמחה אעזור לכם." + NL + 'במה אוכל לעזור?');
  expect('"ואני חלק מהצוות" goes with the name',
    say({ reply: "אני מיכאל מהומי'ז, ואני חלק מהצוות של הומיז. במה אפשר לעזור?", said: 'question' }), 'במה אפשר לעזור?');
  expect('"ואשמח לעזור!" goes with the name',
    say({ reply: "אני מיכאל מהומי'ז, ואשמח לעזור! במה אפשר לעזור?", said: 'question' }), 'במה אפשר לעזור?');
  expect('a link after the name keeps every character, loses only the ו',
    say({ reply: "היי! אני מיכאל מהומי'ז, והנה הקישור לתשלום: https://pay.example.co.il/abc123 אפשר לשלם עד מחר.", said: 'hi, the link?' }),
    'היי! הנה הקישור לתשלום: https://pay.example.co.il/abc123 אפשר לשלם עד מחר.');
  expect('an amount after the name keeps its decimal point',
    say({ reply: `אני מיכאל מהומי'ז, והיתרה שלכם היא 1,234.50 ש"ח. רוצים קישור לתשלום?`, said: 'how much' }),
    `היתרה שלכם היא 1,234.50 ש"ח. רוצים קישור לתשלום?`);
  // 1 Oct: the sample's middle sentence is a promise, and the promise filter
  // (below) removes it; the name step's own point, the number, still holds.
  expect('a ticket number after the name survives',
    say({ reply: "אני מיכאל מהומי'ז, ופתחתי לכם קריאה מספר 123-4567-89. הטכנאי יחזור אליכם בהקדם. יש עוד משהו?", said: 'leak' }),
    'פתחתי לכם קריאה מספר 123-4567-89. יש עוד משהו?');
  expect('no sentence end after the name: only the ו goes',
    say({ reply: "אני מיכאל מהומי'ז ואשמח לעזור לכם היום עם כל מה שצריך", said: 'question' }), 'אשמח לעזור לכם היום עם כל מה שצריך');
  const APPO = "צהריים טובים! אני מיכאל, נציג השירות של הומי'ז, ואשמח לעזור. במה אפשר לעזור?";
  expect('an apposition keeps the name (resident greeted: untouched)', say({ reply: APPO, said: 'hi, question' }), APPO);
  expect('an apposition keeps the name (no hello: the greeting still goes)',
    say({ reply: APPO, said: 'question' }), "אני מיכאל, נציג השירות של הומי'ז, ואשמח לעזור. במה אפשר לעזור?");
  const DASH = "אני מיכאל מהומי'ז - ובשמחה אעזור. במה אפשר לעזור?";
  expect('a dash after the name: untouched, never a "- ובשמחה" fragment', say({ reply: DASH, said: 'question' }), DASH);
  const VAAD = "אני מיכאל מהומי'ז." + NL + 'ועד הבית ביקש שנעדכן: המים ינותקו מחר. יש שאלות?';
  expect('a NEW sentence starting with ו ("ועד הבית") is never cut', say({ reply: VAAD, said: 'question' }), VAAD);

  // 2 Sep, found by the 27 Sep replay: "who are you" was answered with the name,
  // and v1 cut the answer down to "נציג השירות של הומיז.".
  expect('"who are you": the name is the answer and stays',
    say({ reply: "אני מיכאל מהומי'ז. אני כאן כדי לעזור בכל מה שקשור לבניין. במה אפשר לעזור?", said: 'who are you' }),
    "אני מיכאל מהומי'ז. אני כאן כדי לעזור בכל מה שקשור לבניין. במה אפשר לעזור?");
  expect('"מי זה?": the greeting goes, the name stays',
    say({ reply: "היי! אני מיכאל מהומי'ז, ובשמחה אעזור לכם. במה אוכל לעזור?", said: 'מי זה?' }),
    "אני מיכאל מהומי'ז, ובשמחה אעזור לכם. במה אוכל לעזור?");
  expect('"are you a bot?": the name stays',
    say({ reply: "אני מיכאל, נציג השירות של הומי'ז. במה אפשר לעזור?", said: 'are you a bot?' }),
    "אני מיכאל, נציג השירות של הומי'ז. במה אפשר לעזור?");
  // 18 Oct, late (execution 112618, manners v4): "are you the manager?" got "מצוות השירות
  // של הומי'ז. אני כאן...": the model answered with the name, as the prompt says, and
  // the name step cut "אני מיכאל" and left the rest. Now the question keeps the name,
  // and a cut takes "מצוות השירות של הומי'ז" with it, never a fragment.
  const R112618 = "אני מיכאל מצוות השירות של הומי'ז. אני כאן כדי לעזור לך ולטפל בפנייה שלך. אם תספר לי במה מדובר, אוכל לרשום את זה לצוות המתאים, כולל למנהל במידת הצורך.";
  expect('112618 exactly: "are you the manager?" is asking who he is, the name stays',
    say({ reply: R112618, said: 'why would i tell you are you the manager?' }), R112618);
  expect('"אתה המנהל?": the name stays', say({ reply: R112618, said: 'אתה המנהל?' }), R112618);
  expect('not asked who: the whole introduction goes, the team with the name',
    say({ reply: R112618, said: 'no i just need a manager' }),
    'אני כאן כדי לעזור לך ולטפל בפנייה שלך. אם תספר לי במה מדובר, אוכל לרשום את זה לצוות המתאים, כולל למנהל במידת הצורך.');
  const R_TEAM = "אני מיכאל מצוות הלקוחות של הומי'ז. אני כאן בשבילך. על מה מדובר?";
  expect('a "from the team" tail the name step does not know keeps the name, never a fragment',
    say({ reply: R_TEAM, said: 'no i just need a manager' }), R_TEAM);
  // 1 Oct: "הטכנאי יגיע מחר בבוקר" is an invented promise (the bot does not know
  // when anyone comes), and the promise filter removes it; the name still goes.
  expect('a question about a person on the team is not about us: the name still goes',
    say({ reply: "אני מיכאל מהומי'ז. הטכנאי יגיע מחר בבוקר. עוד משהו?", said: 'when is the technician coming' }),
    'עוד משהו?');

  console.log(NL + '--- Send: edges ---');
  expect('burst: the merged text starts with a hello, the greeting back is kept',
    say({ reply: 'היי! איזה מעצבן. באיזה בניין?', said: 'היי מיכאל' + NL + 'יש נזילה בלובי' }), 'היי! איזה מעצבן. באיזה בניין?');
  expect('"היתרה" is not "הי"', say({ reply: 'היתרה שלכם היא 450 שקל.', said: 'what do i owe' }), 'היתרה שלכם היא 450 שקל.');
  expect('"היום" is not "הי"', say({ reply: 'היום אין קריאות פתוחות אצלכם.', said: 'status?' }), 'היום אין קריאות פתוחות אצלכם.');
  expect('"שלום לכם," stripped cleanly', say({ reply: 'שלום לכם, איזה לא נעים. באיזה בניין?', said: 'lights' }), 'איזה לא נעים. באיזה בניין?');
  expect('"ערב טוב גם לכם" kept whole', say({ reply: 'ערב טוב גם לכם! תודה שפניתם.', said: 'thanks, good evening' }), 'ערב טוב גם לכם! תודה שפניתם.');
  expect('"בוקר טוב ותודה" kept whole', say({ reply: 'בוקר טוב ותודה שפניתם אלינו.', said: 'thanks' }), 'בוקר טוב ותודה שפניתם אלינו.');
  expect('a greeting-only reply is never emptied', say({ reply: 'ערב טוב!', said: 'bye' }), 'ערב טוב!');
  expect('the wave emoji goes with the greeting', say({ reply: 'היי 👋 איזה לא נעים. באיזה בניין?', said: 'lights' }), 'איזה לא נעים. באיזה בניין?');
  expect('the Hebrew geresh variant of the name', say({ reply: 'כאן מיכאל מהומי׳ז. באיזה בניין ובאיזו דירה?', said: 'lights' }), 'באיזה בניין ובאיזו דירה?');
  const CLEAN = 'איזה לא נעים לעלות במדרגות בחושך. באיזה בניין ובאיזו דירה אתם גרים?';
  expect('nothing to remove: byte-identical', say({ reply: CLEAN, said: 'lights flicker' }), CLEAN);
  expect('the menu buttons still attach to the menu', () => sent(E, { canned: true, reply: MENU_TEXT }).content_type, 'input_select');

  // 1 Oct: the promise filter (scripts/n8n_whatsapp_nopromise.py). The model
  // writes promises the prompt forbids ("הצוות שלנו יטפל בזה בהקדם": 2 of the 3
  // real replies after the 27 Sep deploy). Send removes them, and only them:
  // the clause when a clean sentence is left, else the sentence; never a
  // ticket number, never a link, never the whole message.
  console.log(NL + '--- Send: no promises reach a resident (1 Oct) ---');
  // 5 Oct, promise v3: "אל דאגה" and "the team will handle it", with no time,
  // are the owner's reassurance and stay; "I'm on it" and the time still go.
  expect('27 Sep 15:05 (v3): "אני מטפל בזה" and "בהקדם" go; "אל דאגה" and "יטפל בזה" stay',
    say({ reply: 'מבאס, אבל אל דאגה, אני מטפל בזה. פתחתי לכם קריאת שירות מספר 255-1339-26. הצוות שלנו יטפל בזה בהקדם. במה אוכל לעזור עוד?', said: 'Bar Kochba 23, apartment 4' }),
    // 6 Nov: with slang v1 the opening "מבאס" is "לא נעים"; what this case tests (the promise clauses) is unchanged.
    (String(P.code.send_body || '').indexOf("const sv = 'slang v") !== -1 ? 'לא נעים' : 'מבאס')
      + ', אבל אל דאגה. פתחתי לכם קריאת שירות מספר 255-1339-26. הצוות שלנו יטפל בזה. במה אוכל לעזור עוד?');
  const DONT_WORRY = "היי! כאן מיכאל מהומי'ז. אני מבין, זה ממש לא נעים ללכת במדרגות ככה. אל דאגה, אני אפתח קריאת שירות כדי שיטפלו בתאורה. באיזה בניין אתם גרים ובאיזו דירה?";
  expect('27 Sep 14:52, first contact (v3): "אל דאגה," is reassurance and stays',
    say({ reply: DONT_WORRY, S: { greeted: false }, said: 'hi, lights' }),
    // 8 Nov: with voice v1 "כדי שיטפלו בתאורה" (someone else handling it) goes; "אל דאגה" stays all the same.
    (String(P.code.send_body || '').indexOf("const vv = 'voice v") !== -1) ? DONT_WORRY.replace(' כדי שיטפלו בתאורה', '') : DONT_WORRY);
  expect('the only sentence: the promise clause goes, the sentence stays',
    say({ reply: 'אני מעביר את זה לצוות, נחזור בהקדם.', said: 'question' }), 'אני מעביר את זה לצוות.');
  expect('a comma clause goes',
    say({ reply: 'העברתי את הפנייה שלכם לצוות שלנו, שיחזור אליכם בהקדם.', said: 'question' }), 'העברתי את הפנייה שלכם לצוות שלנו.');
  // v3: the mechanics cases below use a promise v3 still cuts ("יחזור אליכם").
  expect('a ticket number in the sentence: cut from the ו, the number stays',
    say({ reply: 'פתחתי קריאה מספר 255-1-26 והצוות יחזור אליכם בהקדם.', said: 'question' }), 'פתחתי קריאה מספר 255-1-26.');
  expect('a ticket number is never cut away: no clean cut, so the sentence stays whole',
    say({ reply: 'פתחתי לכם קריאה 255-1339-26 שהצוות יחזור אליכם בהקדם.', said: 'question' }), 'פתחתי לכם קריאה 255-1339-26 שהצוות יחזור אליכם בהקדם.');
  expect('an emergency pass-on stays true: its call promise and "עזרה בדרך" go (v3: "שיטפל בזה" stays)',
    say({ reply: 'בבקשה אל תנסו לפתוח את הדלת בכוח! זה מסוכן מאוד ויכול לגרום לפציעה. אני מעביר את הפנייה הזו מיד לצוות שלנו שיטפל בזה, והם יצרו איתכם קשר בהקדם. בינתיים, נסו להישאר רגועים. עזרה בדרך.', said: 'help' }),
    'בבקשה אל תנסו לפתוח את הדלת בכוח! זה מסוכן מאוד ויכול לגרום לפציעה. אני מעביר את הפנייה הזו מיד לצוות שלנו שיטפל בזה. בינתיים, נסו להישאר רגועים.');
  expect('an offer keeps its question',
    say({ reply: 'אני מצטער לשמוע שאתם לא מרוצים מהשירות. אני רוצה לוודא שאני מבין אתכם נכון, האם תרצו שאעביר את הפנייה שלכם לנציג מהצוות שלנו שיחזור אליכם?', said: 'question' }),
    'אני מצטער לשמוע שאתם לא מרוצים מהשירות. אני רוצה לוודא שאני מבין אתכם נכון, האם תרצו שאעביר את הפנייה שלכם לנציג מהצוות שלנו?');
  const ASKED = 'העברתי את פנייתכם לצוות הרלוונטי וביקשתי שיחזרו אליכם בהקדם. במה עוד אפשר לעזור?';
  expect('v3: what was asked of the team is a report, not a promise ("וביקשתי שיחזרו אליכם בהקדם" stays)',
    say({ reply: ASKED, said: 'question' }), ASKED);
  expect('no clean cut: the sentence goes whole, never "ברגע שאפתח קריאה."',
    say({ reply: 'אני מבין שאתם רוצים שהתקלה תתוקן מיד. פתיחת קריאת שירות היא הדרך שלנו לטפל בתקלות כאלה ולהבטיח שהן יטופלו. ברגע שאפתח קריאה, הצוות שלנו יחזור אליכם בהקדם. באיזה בניין מדובר?', said: 'question' }),
    'אני מבין שאתם רוצים שהתקלה תתוקן מיד. פתיחת קריאת שירות היא הדרך שלנו לטפל בתקלות כאלה ולהבטיח שהן יטופלו. באיזה בניין מדובר?');
  expect('never "כדי." at the end of a cut',
    say({ reply: 'אני לא יכול לראות אם בוצעה הדברה ספציפית בבניין. אם יש לכם מזיקים בדירה, אני יכול לפתוח קריאת שירות כדי שיחזרו אליכם. תרצו שאפתח קריאה?', said: 'question' }),
    'אני לא יכול לראות אם בוצעה הדברה ספציפית בבניין. תרצו שאפתח קריאה?');
  expect('a comma inside a number is not a boundary (v3: the time alone goes after "יטופלו")',
    say({ reply: 'היתרה שלכם 1,240 שקלים יטופלו בקרוב.', said: 'question' }), 'היתרה שלכם 1,240 שקלים יטופלו.');
  const PAY2 = 'אני מבין שאתם צריכים שוב את קישור התשלום שלכם. בטח, אני מטפל בזה. §§§ הנה קישור התשלום: https://pay.example.co.il/abc123 הקישור אישי.';
  const PAY_STEPS = [{ action: { tool: 'get_payment_link' } }];
  expect('the two-part payment reply: its first beat is untouched',
    say({ reply: PAY2, said: 'the link again', steps: PAY_STEPS }), 'אני מבין שאתם צריכים שוב את קישור התשלום שלכם. בטח, אני מטפל בזה.');
  expect('the two-part payment reply: no buttons on the first beat',
    () => sent(E, { reply: PAY2, said: 'the link again', steps: PAY_STEPS }).content_type, undefined);
  expect('the canned menu is untouched, buttons attached',
    () => { const b = sent(E, { canned: true, reply: MENU_TEXT }); return b.content + '|' + b.content_type; }, MENU_TEXT + '|input_select');
  expect('a status the tool returned is not a promise',
    say({ reply: 'בדקתי במערכת: הקריאה 255-1152-26 בטיפול. במה עוד אפשר לעזור?', said: 'status?' }), 'בדקתי במערכת: הקריאה 255-1152-26 בטיפול. במה עוד אפשר לעזור?');
  expect('the facts answer is not a promise',
    say({ reply: 'תקלות שאינן חירום מטופלות עד 3 ימי עסקים, זה הסטנדרט הכללי. יש עוד משהו?', said: 'how long?' }),
    'תקלות שאינן חירום מטופלות עד 3 ימי עסקים, זה הסטנדרט הכללי. יש עוד משהו?');
  expect('"זה יצור קשר עם מוקד החירום" is not a promise',
    say({ reply: 'נסו ללחוץ על כפתור החירום במעלית. ברוב המעליות זה יצור קשר עם מוקד החירום של חברת המעליות.', said: 'stuck' }),
    'נסו ללחוץ על כפתור החירום במעלית. ברוב המעליות זה יצור קשר עם מוקד החירום של חברת המעליות.');
  expect('"אפשר לשלם עד מחר" is not a promise',
    say({ reply: 'היתרה שלכם היא 620 שקלים. אפשר לשלם עד מחר דרך הקישור. יש עוד משהו?', said: 'how much' }),
    'היתרה שלכם היא 620 שקלים. אפשר לשלם עד מחר דרך הקישור. יש עוד משהו?');
  expect('a message that is all promise is never emptied',
    say({ reply: 'נחזור אליכם בהקדם.', said: 'question' }), 'נחזור אליכם בהקדם.');
  expect('v3: "אל דאגה," stays when the promise after its comma goes',
    say({ reply: 'אל דאגה, נחזור אליכם בהקדם.', said: 'question' }), 'אל דאגה.');
  expect('a newline is a sentence boundary',
    say({ reply: 'פתחתי לכם קריאה מספר 255-1339-26' + NL + 'הצוות יחזור אליכם בהקדם' + NL + 'יש עוד משהו?', said: 'question' }),
    'פתחתי לכם קריאה מספר 255-1339-26' + NL + 'יש עוד משהו?');
  expect('an emoji stays with its sentence',
    say({ reply: 'פתחתי קריאה 255-1339-26. 🙂 הצוות יחזור אליכם בהקדם. במה עוד?', said: 'question' }), 'פתחתי קריאה 255-1339-26. 🙂 במה עוד?');
  expect('a promise glued to an emoji goes with it',
    say({ reply: 'פתחתי קריאה 255-1339-26. הצוות יחזור אליכם בהקדם🙂 במה עוד?', said: 'question' }), 'פתחתי קריאה 255-1339-26. במה עוד?');
  expect('a link loses only the promise clause after it',
    say({ reply: 'הנה הקישור: https://pay.example.co.il/abc123, ואם יש בעיה אני אטפל בזה. הקישור אישי.', said: 'question' }),
    'הנה הקישור: https://pay.example.co.il/abc123. הקישור אישי.');
  const MENU_LIKE = 'אפשר לפתוח קריאת שירות, לבדוק מצב קריאה קיימת או לברר יתרה, ונציג יחזור אליכם בהקדם.';
  expect('menu-like text: the promise goes',
    say({ reply: MENU_LIKE, said: 'what can you do' }), 'אפשר לפתוח קריאת שירות, לבדוק מצב קריאה קיימת או לברר יתרה.');
  expect('menu-like text: the buttons still attach (the rule reads the text before the filter)',
    () => sent(E, { reply: MENU_LIKE, said: 'what can you do' }).content_type, 'input_select');
  // Found by the 1 Oct replay (a real 17 Sep reply): when the promise IS the
  // main clause of an "if" sentence, a comma cut would leave a dangling "if…".
  // v3: that reply's "נטפל בזה כמובן" is reassurance with no time, and stays;
  // the dangling "אם…" rule is kept by the same sentence with a visit promise.
  const COMMON = 'חשוב לי לציין שאם התקלה בתוך הדירה, הטיפול הוא באחריותכם. אם מדובר בתקלה ברכוש המשותף, כמו בחשמל הכללי של הבניין, נטפל בזה כמובן. במה עוד אוכל לעזור?';
  expect('17 Sep (v3): "נטפל בזה כמובן" is reassurance and stays', say({ reply: COMMON, said: 'question' }), COMMON);
  expect('a conditional whose main clause is the promise goes whole, never a dangling "אם…"',
    say({ reply: 'חשוב לי לציין שאם התקלה בתוך הדירה, הטיפול הוא באחריותכם. אם מדובר בתקלה ברכוש המשותף, כמו בחשמל הכללי של הבניין, הטכנאי יגיע מחר. במה עוד אוכל לעזור?', said: 'question' }),
    'חשוב לי לציין שאם התקלה בתוך הדירה, הטיפול הוא באחריותכם. במה עוד אוכל לעזור?');
  expect('a step back past "ולדאוג": the main clause stays',
    say({ reply: 'ברגע שאקבל את הפרטים, אוכל לפתוח קריאת שירות דחופה ולדאוג שיגיעו אליכם מהר ככל האפשר. באיזה בניין מדובר?', said: 'question' }),
    'ברגע שאקבל את הפרטים, אוכל לפתוח קריאת שירות דחופה. באיזה בניין מדובר?');
  expect('a technician time is an invented promise and goes',
    say({ reply: 'פתחתי לכם קריאה 255-1339-26. הטכנאי יגיע מחר בבוקר. יש עוד משהו?', said: 'question' }),
    'פתחתי לכם קריאה 255-1339-26. יש עוד משהו?');

  // 5 Oct, promise v3 (scripts/n8n_whatsapp_nopromise.py, fix 2 of 5): on the
  // live run as Assaf the filter cut 37 of 72 replies, about half of them
  // honest: "I can't say when", what Michael asked the team, wishes, and the
  // owner's "it will be handled". Once only "anything else?" was left.
  console.log(NL + '--- Send: promises only, not reports, wishes or "I can\'t say when" (5 Oct) ---');
  const same = (name, reply) => expect(name, say({ reply, said: 'question' }), reply);
  same('v3: "I can\'t say exactly when" is not a promise',
    'אני לא יכול להגיד לך מתי בדיוק יחזרו אליך. הצוות קיבל את הפנייה שלך ויטפל בה. במה אוכל לעזור לך עוד?');
  same('v3: "מתי או אם יחזרו אליך" is a question, not a promise',
    'אני לא יכול להבטיח מתי או אם יחזרו אליך, אבל העברתי את זה הלאה. במה אוכל לעזור לך עוד?');
  expect('v3: a note to the team, reported, stays ("רשמתי לצוות שלנו שיחזרו אליך")',
    say({ reply: 'בטח, רשמתי לצוות שלנו שיחזרו אליך דחוף. יש עוד משהו?', said: 'question' }),
    // 8 Nov: with voice v1 the note is in the system, not "for our team"; the promise filter's answer is the same.
    (String(P.code.send_body || '').indexOf("const vv = 'voice v") !== -1) ? 'בטח, רשמתי במערכת שיחזרו אליך דחוף. יש עוד משהו?' : 'בטח, רשמתי לצוות שלנו שיחזרו אליך דחוף. יש עוד משהו?');
  same('v3: the tenant\'s own want stays ("שאתה מחכה שיחזרו אליך")',
    'עדכנתי את הצוות שאתה מחכה שיחזרו אליך. יש עוד משהו?');
  same('v3: a wish stays ("אני מקווה שיחזרו אליך בהקדם")', 'אני מקווה שיחזרו אליך בהקדם. יש עוד משהו?');
  same('v3: "I can\'t promise that…" is honest and stays',
    'אני לא יכול להבטיח שיחזרו אליך היום, אבל העברתי את זה לצוות. יש עוד משהו?');
  same('v3: a negated visit is not a promise', 'לצערי הטכנאי לא יגיע היום. אפשר לעזור בעוד משהו?');
  expect('v3: after "will be handled", the time alone goes',
    say({ reply: 'הם קיבלו את הקריאה ויטפלו בה בהקדם. יש עוד משהו?', said: 'when?' }),
    'הם קיבלו את הקריאה ויטפלו בה. יש עוד משהו?');
  expect('v3: "בהקדם האפשרי" goes whole',
    say({ reply: 'הקריאה תטופל בהקדם האפשרי. יש עוד משהו?', said: 'when?' }), 'הקריאה תטופל. יש עוד משהו?');
  expect('v3: "במהירות האפשרית" is a time too',
    say({ reply: 'פתחתי לך קריאה 255-1347-26. הצוות שלנו יטפל בזה במהירות האפשרית. יש עוד משהו?', said: 'lift' }),
    'פתחתי לך קריאה 255-1347-26. הצוות שלנו יטפל בזה. יש עוד משהו?');
  expect('v3: "העברתי את זה לצוות שיחזור אליך" is the team that will call: still cut',
    say({ reply: 'העברתי את זה לצוות שיחזור אליך היום. יש עוד משהו?', said: 'question' }),
    'העברתי את זה לצוות. יש עוד משהו?');
  expect('v3: a ש clause after a comma is a relative clause: still a promise',
    say({ reply: 'עדכנתי את הצוות שלנו, שיחזור אליך בהקדם. יש עוד משהו?', said: 'question' }),
    'עדכנתי את הצוות שלנו. יש עוד משהו?');
  expect('v3: "מבטיח ש…" keeps it a promise, never "אני מבטיח." left',
    say({ reply: 'פתחתי לך קריאה 255-1347-26. אני מבטיח שיחזרו אליך היום. יש עוד משהו?', said: 'question' }),
    'פתחתי לך קריאה 255-1347-26. יש עוד משהו?');
  expect('v3: "the team will update you" after a comma is still cut, never a dangling "וברגע ש…"',
    say({ reply: 'הצוות קיבל את הבקשה שלך, וברגע שיהיו חדשות, הם יעדכנו אותך. יש עוד משהו?', said: 'question' }),
    'הצוות קיבל את הבקשה שלך. יש עוד משהו?');
  // 19 Oct, promise v4 (the stress test, docs/assistant/transcripts/
  // 2026-10-19-whatsapp-stress-test.md): "whether", under "I don't know", is
  // honesty. v3 cut it, so "will someone get back to me?" went unanswered (one
  // resident asked twice) and once left the text opening with "אבל".
  same('v4: "whether and when they\'ll get back to you, I don\'t know" stays',
    'אם יחזרו אליך ומתי, את זה אני לא יודע, ואני לא רוצה להבטיח לך משהו שאין לי. מה שבטוח, שתי השאלות כבר אצל הצוות. יש עוד משהו?');
  same('v4: "no way to know from here whether they\'ll update you" stays',
    'את זה אני לא יכול להבטיח לך, ואין לי דרך לדעת מכאן אם יעדכנו אותך. אם תכתבי לי מחר בבוקר, אבדוק שוב. מתאים לך?');
  same('v4: one subject word between "אם" and the phrase still stays',
    'אם מישהו יחזור אליך, את זה אני באמת לא יודע. להתקשר לא צריך, השאלות כבר אצלם. זה מסתדר לך ככה?');
  same('v4: the honest sentence stays, so the "אבל" after it never dangles',
    'אם יעדכנו אותך כשזה יתוקן, את זה אני לא יודע. אבל לבדוק לבד את לא צריכה: תכתבי לי מתי שתרצי ואבדוק. בסדר?');
  expect('v4: a conditional offer is still a promise ("אם תרצה, יחזרו אליך")',
    say({ reply: 'אם תרצה, יחזרו אליך מחר. יש עוד משהו שאוכל לעזור בו?', said: 'question' }),
    'יש עוד משהו שאוכל לעזור בו?');
  expect('v4: "but if needed they\'ll get back to you" is still a promise',
    say({ reply: 'אני לא יודע מתי, אבל אם צריך הם יחזרו אליך. יש עוד משהו?', said: 'question' }),
    'אני לא יודע מתי. יש עוד משהו?');
  // v4, the check of the new paragraph: Hebrew fronts what it cannot promise.
  same('v4: "להבטיח שיחזרו אליך אני לא יכול" is honest and stays',
    'להבטיח שיחזרו אליך אני לא יכול. מה שעשיתי זה לרשום לצוות שאתה מחכה לתשובה. יש עוד משהו בתקלה שכדאי שאוסיף?');
  same('v4: "אבל להבטיח שיגיעו היום אני לא יכול, כי…" stays',
    'זה שזה דחוף לך כבר רשום אצל הצוות, אבל להבטיח שיגיעו היום אני לא יכול, כי את ההחלטה הזאת מקבלים שם ולא אני. משהו השתנה עם השער מאז אתמול?');
  expect('v4: "אני מבטיח שיחזרו אליך היום" is still a promise',
    say({ reply: 'אני מבטיח שיחזרו אליך היום. יש עוד משהו?', said: 'question' }), 'יש עוד משהו?');
  expect('v4: "I know they\'ll get back to you tomorrow" goes whole, never a bare "אני יודע."',
    say({ reply: 'אני יודע שיחזרו אליך מחר, אבל אני לא יכול להגיד מתי בדיוק. יש עוד משהו?', said: 'question' }), 'יש עוד משהו?');
  // v4, later (run 3 of the lowkey check, 20 Oct): the honest answer said with a
  // verb of saying, after "whether someone already", or with its object fronted,
  // was cut; unnegated, a verb of saying is still a promise, and a cut never
  // leaves "להגיד לך." behind.
  same('v4, later: I cannot tell you they come today, stays',
    'אני לא יכול להגיד לך שיגיעו היום. יש עוד משהו בתקלה שכדאי שאוסיף?');
  same('v4, later: I will not be able to tell you they call tomorrow, stays',
    'לא אוכל להגיד לך שיחזרו אליך מחר, כי זה לא כתוב אצלי. זה בסדר מבחינתך?');
  same('v4, later: I cannot commit they come tomorrow, stays',
    'אני לא יכול להתחייב שיגיעו מחר. רוצה שאבדוק את הקריאה שוב?');
  same('v4, later: whether someone already calls back, I do not know, stays',
    'אם מישהו כבר יחזור אליך היום, את זה אני לא יודע. רוצה שאוסיף לצוות שאתה מחכה?');
  same('v4, later: to tell you they call tomorrow, that I cannot, stays',
    'להגיד לך שיחזרו אליך מחר, את זה אני לא יכול. מה עוד חשוב שהצוות ידע?');
  same('v4, later: that they call today I cannot promise, stays',
    'את זה שיחזרו אליך היום אני לא יכול להבטיח. רוצה שאבדוק שוב בעוד שעה?');
  same('v4, later: telling you they come today would not be fair, stays (run 3, cut to a fragment before)',
    'בדקתי את הקריאה שוב עכשיו: היא עדיין פתוחה, והעדכון האחרון בה מאתמול. אני יודע כמה זה דחוף לך, אבל להגיד לך שיגיעו היום בלי שזה כתוב אצלי יהיה לא הוגן כלפיך. הצוות יודע שאתה תקוע בלי האוטו. יש שעה מסוימת שבה אתה חייב לצאת היום?');
  expect('v4, later: I can tell you they come today, is a promise',
    say({ reply: 'אני יכול להגיד לך שיגיעו היום. יש עוד משהו?', said: 'question' }), 'יש עוד משהו?');
  expect('v4, later: the cut of a promise never leaves a verb of saying hanging',
    say({ reply: 'זה דחוף, אבל אני רוצה להגיד לך שיגיעו היום. יש עוד משהו?', said: 'question' }), 'זה דחוף. יש עוד משהו?');
  expect('v4, later: I promise today and not tomorrow, is still a promise',
    say({ reply: 'אני מבטיח שיחזרו אליך היום ולא מחר. יש עוד משהו?', said: 'question' }), 'יש עוד משהו?');
  // Not "never only anything else?": the filter can only remove, so that would
  // mean sending the promise, and an all-promise reply can be an invented one.
  expect('v3: a reply that is all promise still loses it, even down to "anything else?"',
    say({ reply: 'הם יחזרו אליך בהקדם. במה אוכל לעזור לך עוד?', said: 'when?' }), 'במה אוכל לעזור לך עוד?');
  // The 37 live replies (scripts/wa_promise_live_05oct.json): raw draft in, v3 out.
  // 8 Nov: with voice v1, #11's "רשמתי לצוות שלנו" is "רשמתי במערכת"; the file keeps what v3 sent that day.
  // 8 Nov, later: with manager v1, #14's and #33's "עדכנתי את הצוות שאתה רוצה לדבר עם נציג אנושי." goes (R15).
  const voiced = (String(P.code.send_body || '').indexOf("const vv = 'voice v") !== -1);
  const managed = (String(P.code.send_body || '').indexOf("const mg = 'manager v") !== -1);
  for (const k of P.promise_live || []) {
    let want = voiced ? String(k.want).replace('רשמתי לצוות שלנו', 'רשמתי במערכת') : k.want;
    if (managed) want = String(want).replace(' עדכנתי את הצוות שאתה רוצה לדבר עם נציג אנושי.', '');
    expect('5 Oct live #' + k.n + ' (' + k.case + ')', say({ reply: k.raw, said: k.said }), want);
  }

  // 29 Oct, late (n8n_whatsapp_checkword.py, execution 138931): "הכל בסדר 🙂" opened a ₪2,000 debt. The
  // owner: "i dont want that to happen again ever". In a turn where a tool ran, Send cuts an all-clear
  // that stands as an interjection or is joined on with ו; what the tool found stays and says it.
  // Unconditional on purpose: a workflow that loses the cut fails here.
  console.log(NL + '--- Send: no all-clear before what a tool found (29 Oct, execution 138931) ---');
  const LOOKED = [{ action: { tool: 'get_balance' }, observation: '[]' }];
  const R138931 = 'הכל בסדר 🙂 \nבדקתי במערכת, ורשומה לך יתרה של 2,000 ש"ח בסך הכל. זה על החודשים ינואר עד אוגוסט 2026 (250 ש"ח לכל חודש).\n\nתרצה שאעזור עם עוד משהו?';
  expect('138931: the all-clear before a debt is cut, the debt stays', () => {
    const out = content(E, { reply: R138931, steps: LOOKED });
    return out.startsWith('בדקתי במערכת') && out.includes('2,000') && !/הכל בסדר|הכול בסדר/.test(out); }, true);
  expect('no tool this turn: "how are you?" keeps its "הכל טוב"', say({ reply: 'הכל טוב, תודה ששאלת! ומה שלומך?', said: 'מה שלומך?' }),
    'הכל טוב, תודה ששאלת! ומה שלומך?');
  expect('joined on with ו, it goes too', () => content(E, { reply: 'בדקתי במערכת והכל בסדר, רשומה לך יתרה של 750 ש"ח. רוצה קישור לתשלום?', steps: LOOKED }),
    'בדקתי במערכת, רשומה לך יתרה של 750 ש"ח. רוצה קישור לתשלום?');
  expect('after a sentence, as its own interjection', () => content(E, { reply: 'תודה שחיכית. הכול טוב! לפי המערכת יש לך יתרה של 500 ש"ח. רוצה קישור?', steps: LOOKED }),
    'תודה שחיכית. לפי המערכת יש לך יתרה של 500 ש"ח. רוצה קישור?');
  expect('a question is not touched', () => content(E, { reply: 'פתחתי קריאה, מספר 255-1450-26. הכל בסדר עם זה מבחינתך?', steps: [{ action: { tool: 'open_request' }, observation: '[]' }] })
    .includes('הכל בסדר עם זה מבחינתך?'), true);
  expect('nothing left after the cut: the reply stays whole', () => content(E, { reply: 'הכל בסדר 🙂', steps: LOOKED }).includes('הכל בסדר'), true);
  expect('"בסך הכל" is not an all-clear', () => content(E, { reply: 'רשומה לך יתרה של 2,000 ש"ח בסך הכל. רוצה קישור?', steps: LOOKED }),
    'רשומה לך יתרה של 2,000 ש"ח בסך הכל. רוצה קישור?');

  // 5 Oct (scripts/n8n_whatsapp_emoji.py): the prompt allows six, a face or a
  // hand; the live run sent 😔 and 😥, and goodbyes carry 👋. Only when the
  // emoji step is live (a candidate without it skips these).
  if (P.code && String(P.code.send_body || '').indexOf("const ev = 'emoji v") !== -1) {
    console.log(NL + '--- Send: only the six emoji (5 Oct) ---');
    expect('a sad face after a full stop goes, the sentence stays',
      say({ reply: 'וזה באמת לא מצב נעים. 😔 באיזה בניין ובאיזו דירה?', said: 'lights' }),
      'וזה באמת לא מצב נעים. באיזה בניין ובאיזו דירה?');
    expect('the goodbye wave goes', say({ reply: 'תודה שפנית אלינו, ושיהיה לך יום טוב! 👋', said: 'thanks' }),
      'תודה שפנית אלינו, ושיהיה לך יום טוב!');
    const SIXES = 'פתחתי לך קריאה 255-1347-26 👍🏽 יש עוד פרט שחשוב שאדע? 🙂';
    expect('the six stay, a skin tone too', say({ reply: SIXES, said: 'lift' }), SIXES);
    expect('an emoji-only reply is never emptied', say({ reply: '😥', said: 'lights' }), '😥');
    expect('the menu keeps its wave', () => sent(E, { canned: true, reply: MENU_TEXT }).content, MENU_TEXT);
  }
  // 6 Nov (scripts/n8n_whatsapp_retest2.py): "מבאס" twice in two tester runs, under a prompt that already
  // says "בלי סלנג". The owner's register holds in code, as the six emoji do.
  if (P.code && String(P.code.send_body || '').indexOf("const sv = 'slang v") !== -1) {
    console.log(NL + '--- Send: no slang (6 Nov) ---');
    expect('"מבאס" at the start becomes "לא נעים"',
      say({ reply: 'מבאס להיות בלי אינטרקום יומיים. פתחתי קריאה, מספר 255-1401-26.', said: 'האינטרקום לא עובד' }),
      'לא נעים להיות בלי אינטרקום יומיים. פתחתי קריאה, מספר 255-1401-26.');
    expect('"ממש מבאס" mid-sentence becomes "ממש לא נעים"',
      say({ reply: 'אוי, זה ממש מבאס שיש חושך בלובי. באיזה בניין?', said: 'אין אור בלובי' }),
      'אוי, זה ממש לא נעים שיש חושך בלובי. באיזה בניין?');
    const PLAIN = 'אוי, לא נעים. פתחתי קריאה על המעלית, מספר 255-1398-26.';
    expect('a reply with no slang is untouched', say({ reply: PLAIN, said: 'המעלית תקועה' }), PLAIN);
  }

  // 6 Nov (scripts/n8n_whatsapp_retest3.py, the tester's third run, C2, execution 158760): the lookup and
  // the add both gave 255-1403-26 and the reply named neither. Epoch 98's tool text held in C5 and C11 and
  // not there, so the number is put in by code when the turn's tools gave exactly one ticket.
  if (P.code && String(P.code.send_body || '').indexOf("const rv = 'ref v") !== -1) {
    console.log(NL + "--- Send: a ticket the tools found is named by its number (6 Nov, the tester's C2) ---");
    const obs = (o) => JSON.stringify([{ results: [{ toolCallId: 'wa', result: JSON.stringify(o) }] }]);
    const STATUS1 = { action: { tool: 'get_request_status' }, observation: obs({ ok: true, found: 1, requests: [{ reference: '255-1403-26', status: 'open' }] }) };
    const ADD1 = { action: { tool: 'add_request_detail' }, observation: obs({ ok: true, reference: '255-1403-26' }) };
    const C2 = 'הוספתי לקריאה את העדכון שלך שהמעלית עדיין לא עובדת. המצב שלה כרגע עדיין מופיע כפתוחה. מישהו תקוע בפנים או שהיא פשוט עומדת?';
    expect('C2 exactly (158760): the number goes in after the first word for the ticket',
      () => content(E, { reply: C2, steps: [STATUS1, ADD1], said: 'שוב אני, המעלית עדיין לא עובדת' }),
      'הוספתי לקריאה (255-1403-26) את העדכון שלך שהמעלית עדיין לא עובדת. המצב שלה כרגע עדיין מופיע כפתוחה. מישהו תקוע בפנים או שהיא פשוט עומדת?');
    expect('"the ticket of yours": after the possessive',
      () => content(E, { reply: 'הקריאה שלך עדיין פתוחה במערכת. משהו השתנה מאז?', steps: [STATUS1] }),
      'הקריאה שלך (255-1403-26) עדיין פתוחה במערכת. משהו השתנה מאז?');
    const NAMED = 'הקריאה 255-1403-26 עדיין פתוחה. משהו השתנה מאז?';
    expect('a reply that already names a ticket is untouched', () => content(E, { reply: NAMED, steps: [STATUS1] }), NAMED);
    const THREE = { action: { tool: 'get_request_status' }, observation: obs({ ok: true, found: 3, requests: [{ reference: '255-1404-26' }, { reference: '255-1403-26' }, { reference: '255-1402-26' }] }) };
    const VAGUE = 'אני רואה במערכת את שלוש הקריאות הפתוחות. לאיזו מהן התכוונת?';
    expect('three tickets found: nothing is guessed', () => content(E, { reply: VAGUE, steps: [THREE] }), VAGUE);
    const WHEN = 'הקריאה על הניקיון כבר פתוחה. משהו השתנה מאז?';
    expect('no tool this turn: untouched', () => content(E, { reply: WHEN, steps: [] }), WHEN);
    const NOWORD = 'הוספתי את זה, טוב שזה רק טפטוף. יש עוד פרט שחשוב שאדע?';
    expect('no word for the ticket: untouched', () => content(E, { reply: NOWORD, steps: [ADD1] }), NOWORD);
    const NOTOPEN = { action: { tool: 'open_request' }, observation: obs({ ok: true, opened: false, reason: 'street_unknown' }) };
    const ASK = 'הכתובת הזאת לא מופיעה אצלנו. תוכל לבדוק אם זו הכתובת המדויקת לקריאה?';
    expect('an open that opened nothing: untouched', () => content(E, { reply: ASK, steps: [NOTOPEN] }), ASK);
    expect("the first pass's add, carried flat by Try again, counts too", () => {
      const m = turn({ reply: 'הוספתי עכשיו לקריאה שאתה מחכה לתשובה. מישהו תקוע בפנים?', steps: [] });
      const $ = (n) => (n === 'Try again'
        ? { first: () => ({ json: { first_steps: [{ tool: 'add_request_detail', observation: obs({ ok: true, reference: '255-1403-26' }) }] } }) }
        : m.$(n));
      return JSON.parse(E.send(m.$json, $)).content;
    }, 'הוספתי עכשיו לקריאה (255-1403-26) שאתה מחכה לתשובה. מישהו תקוע בפנים?');
    expect('a closed ticket the lookup found is named the same way',
      () => content(E, { reply: 'הקריאה על המעלית כבר נסגרה. משהו קורה איתה שוב?', steps: [{ action: { tool: 'get_request_status' }, observation: obs({ ok: true, found: 1, requests: [{ reference: '255-1390-26', status: 'closed' }] }) }] }),
      'הקריאה (255-1390-26) על המעלית כבר נסגרה. משהו קורה איתה שוב?');
  }

  // 8 Nov (scripts/n8n_whatsapp_retest4.py, the tester's fourth run, R4 five times): the model's own
  // "they" and "we" against the prompt's one-voice sentence, the same forms 6 times since 29 Oct in all
  // 1,343 replies. The drafts below are the executions' own, word for word.
  if (P.code && String(P.code.send_body || '').indexOf("const vv = 'voice v") !== -1) {
    console.log(NL + "--- Send: Michael speaks for himself (8 Nov, the tester's fourth run) ---");
    const obs = (o) => JSON.stringify([{ results: [{ toolCallId: 'wa', result: JSON.stringify(o) }] }]);
    const LIFT = { action: { tool: 'get_request_status' }, observation: obs({ ok: true, found: 1, requests: [{ reference: '255-1409-26', status: 'open' }] }) };
    const ADDLIFT = { action: { tool: 'add_request_detail' }, observation: obs({ ok: true, reference: '255-1409-26' }) };
    const ADDLEAK = { action: { tool: 'add_request_detail' }, observation: obs({ ok: true, reference: '255-1410-26' }) };
    const NOTE = { action: { tool: 'notify_team' }, observation: obs({ ok: true, reason: 'caller_request' }) };
    expect('C2 exactly (163807): "כדי שידעו …" goes, to the end of its clause',
      () => content(E, { reply: 'ממש מבאס שזה מתעכב. בדקתי שוב, והקריאה (255-1409-26) עדיין פתוחה במערכת. הוספתי אליה עכשיו את העדכון שלך שהמעלית עדיין לא עובדת, כדי שידעו שהמצב נמשך. ' + NL + NL + 'החמיר משהו מאז או שזה פשוט עומד באותו מצב?', steps: [LIFT, ADDLIFT], said: 'שוב אני, המעלית עדיין לא עובדת' }),
      'ממש לא נעים שזה מתעכב. בדקתי שוב, והקריאה (255-1409-26) עדיין פתוחה במערכת. הוספתי אליה עכשיו את העדכון שלך שהמעלית עדיין לא עובדת. החמיר משהו מאז או שזה פשוט עומד באותו מצב?');
    expect('C3 exactly (163833): after the ticket number, the clause goes and the number stays',
      () => content(E, { reply: 'טוב שזה רק טפטוף בינתיים ולא זרימה חזקה. הוספתי את העדכון הזה לקריאה (255-1410-26) כדי שידעו בדיוק מה המצב.' + NL + NL + 'יש עוד משהו שאני יכול לעזור בו היום?', steps: [ADDLEAK], said: 'זה רק טפטוף בינתיים' }),
      'טוב שזה רק טפטוף בינתיים ולא זרימה חזקה. הוספתי את העדכון הזה לקריאה (255-1410-26). יש עוד משהו שאני יכול לעזור בו היום?');
    expect('C1.5 exactly (163788): "רשמתי עכשיו לצוות" becomes "רשמתי עכשיו במערכת"',
      () => content(E, { reply: 'אני מבין את התסכול שלך, אבל באמת שאין לי אפשרות לראות מתי בדיוק יגיעו. המערכת מראה שהקריאה עדיין פתוחה, ורשמתי עכשיו לצוות שאתה מחכה לתשובה ולטיפול במעלית.' + NL + NL + 'יש החמרה במצב או שזה עדיין ככה?', steps: [LIFT, NOTE], said: 'נו אז מתי??' }),
      'אני מבין את התסכול שלך, אבל באמת שאין לי אפשרות לראות מתי בדיוק יגיעו. המערכת מראה שהקריאה (255-1409-26) עדיין פתוחה, ורשמתי עכשיו במערכת שאתה מחכה לתשובה ולטיפול במעלית. יש החמרה במצב או שזה עדיין ככה?');
    expect('C1.4 exactly (163780): "נשלח לך עדכון" becomes "יישלח לך עדכון"',
      () => content(E, { reply: 'אני אגיד לך דוגרי, כרגע אין לי תאריך או שעה מדויקים לתת לך. הקריאה פתוחה וממתינה לטיפול, וברגע שייסגרו אותה נשלח לך עדכון מסודר לכאן.' + NL + NL + 'משהו השתנה או שזה עדיין אותו דבר? 🙏', steps: [LIFT], said: 'מתי מגיעים לתקן?' }),
      'אני אגיד לך דוגרי, כרגע אין לי תאריך או שעה מדויקים לתת לך. הקריאה (255-1409-26) פתוחה וממתינה לטיפול, וברגע שייסגרו אותה יישלח לך עדכון מסודר לכאן. משהו השתנה או שזה עדיין אותו דבר? 🙏');
    expect('C6.4 exactly (163962, the retry): "כדי שנוכל" becomes "כדי שאוכל"',
      () => content(E, { reply: 'הבנתי, בערך 500 ש"ח באמצע יולי. הכל בסדר, כשתוכל למצוא את הצילום או האישור פשוט תשלח לי אותו לכאן כדי שנוכל לאמת את זה במערכת.' + NL + NL + 'יש עוד משהו שאוכל לעזור בו בינתיים?', steps: [], said: 'בערך 500 שקל, באמצע יולי. אין לי תמונה עכשיו' }),
      'הבנתי, בערך 500 ש"ח באמצע יולי. הכל בסדר, כשתוכל למצוא את הצילום או האישור פשוט תשלח לי אותו לכאן כדי שאוכל לאמת את זה במערכת. יש עוד משהו שאוכל לעזור בו בינתיים?');
    expect('"תישלח לך הודעה" for a message (feminine noun)',
      say({ reply: 'כשהקריאה תיסגר נשלח לך הודעה לכאן. משהו השתנה?' }), 'כשהקריאה תיסגר תישלח לך הודעה לכאן. משהו השתנה?');
    expect('a reply that opens with the clause loses it up to its comma (27 Aug)',
      say({ reply: 'כדי שיוכלו לעזור כמה שיותר מהר, אפשר לכתוב בכמה מילים על מה הפנייה?' }), 'אפשר לכתוב בכמה מילים על מה הפנייה?');
    expect('inside a question (5 Nov): the question stays, the team goes',
      say({ reply: 'הקריאה על המעלית עדיין פתוחה. תרצה שאוסיף אליה שאתה מחכה כבר שבוע כדי שהצוות יראה את זה?' }),
      'הקריאה על המעלית עדיין פתוחה. תרצה שאוסיף אליה שאתה מחכה כבר שבוע?');
    expect('a clause followed by more of the sentence: only the clause goes',
      say({ reply: 'הוספתי לקריאה כדי שידעו מה המצב, ואם משהו ישתנה פשוט תכתוב לי. החמיר משהו?' }),
      'הוספתי לקריאה, ואם משהו ישתנה פשוט תכתוב לי. החמיר משהו?');
    expect('"השארתי הערה לצוות שלנו" becomes "השארתי הערה במערכת"',
      say({ reply: 'השארתי הערה לצוות שלנו על זה. משהו נוסף?' }), 'השארתי הערה במערכת על זה. משהו נוסף?');
    for (const same of [
      'צילום של הצ\'ק יעזור, כדי שאוכל לאמת את זה במערכת. תוכל לשלוח לי אותו לכאן?',
      'הוספתי את זה כדי שידעו שקריאה 255-1409-26 דחופה. משהו השתנה?',
      'כדי שידעו מה קרה. משהו נוסף?',
      'אני העוזר הדיגיטלי בצוות השירות של הומי\'ז. במה אוכל לעזור?',
      'כשסוגרים את הקריאה, נשלחת עליה הודעה לכאן. משהו השתנה מאז?',
    ]) {
      expect('untouched: ' + same.slice(0, 40), say({ reply: same }), same);
    }
  }

  // 8 Nov, evening (scripts/n8n_whatsapp_voice2.py, the owner's own test, executions 164367 and 164410): the
  // matter "אצל הצוות" (the form of the owner's 29 Oct chat that started the one-voice rule), and a ticket
  // "למחלקת הניקיון" (notify_team: "Never which department"). The drafts are the executions' own.
  if (P.code && String(P.code.send_body || '').indexOf("const vv = 'voice v2'") !== -1) {
    console.log(NL + "--- Send: nobody else holds the matter, no department named (8 Nov, the owner's test) ---");
    const obs = (o) => JSON.stringify([{ results: [{ toolCallId: 'wa', result: JSON.stringify(o) }] }]);
    const ADDLIFT = { action: { tool: 'add_request_detail' }, observation: obs({ ok: true, reference: '255-1409-26' }) };
    const OPENED = { action: { tool: 'open_request' }, observation: obs({ ok: true, reference: '255-1414-26' }) };
    const NOTE = { action: { tool: 'notify_team' }, observation: obs({ ok: true, reason: 'caller_request' }) };
    expect('164367 exactly: ", אבל זה כרגע אצל הצוות שמטפל בזה" goes, the wish stays',
      () => content(E, { reply: 'אני באמת מבין את התסכול, אסף. הוספתי עכשיו לקריאה שאתה לוחץ לדעת מתי מגיעים ומחכה לתשובה בהקדם. ' + NL + NL + 'הלוואי שהייתה לי שעה להגיד לך, אבל זה כרגע אצל הצוות שמטפל בזה. תרצה שאבדוק את זה שוב בשבילך יותר מאוחר?', steps: [ADDLIFT], said: 'נו אז מתי??' }),
      'אני באמת מבין את התסכול, אסף. הוספתי עכשיו לקריאה (255-1409-26) שאתה לוחץ לדעת מתי מגיעים ומחכה לתשובה בהקדם. הלוואי שהייתה לי שעה להגיד לך. תרצה שאבדוק את זה שוב בשבילך יותר מאוחר?');
    expect('164410 exactly: "קריאה למחלקת הניקיון" is "קריאה"',
      () => content(E, { reply: 'באמת לא נעים. פתחתי עכשיו קריאה למחלקת הניקיון על חדר המדרגות בבר כוכבא 23 (מספר 255-1414-26). ' + NL + NL + 'תרצה שאבדוק משהו נוסף?', steps: [NOTE, OPENED], said: 'לא מנקים את חדר המדרגות כבר שבועיים' }),
      'באמת לא נעים. פתחתי עכשיו קריאה על חדר המדרגות בבר כוכבא 23 (מספר 255-1414-26). תרצה שאבדוק משהו נוסף?');
    expect('29 Oct 17:03 (the chat that started the rule): " ונמצאות אצל הצוות" goes, the list stays',
      say({ reply: 'מצטער על ההמתנה 🙏 אני רואה כרגע במערכת 3 קריאות שלך שעדיין בסטטוס פתוח ונמצאות אצל הצוות, ביניהן הקריאות על המעלית ועל התאורה בקומה 2. משהו שם החמיר?' }),
      'מצטער על ההמתנה 🙏 אני רואה כרגע במערכת 3 קריאות שלך שעדיין בסטטוס פתוח, ביניהן הקריאות על המעלית ועל התאורה בקומה 2. משהו שם החמיר?');
    expect('"ואצל הצוות" goes',
      say({ reply: 'הקריאה הדחופה כבר פתוחה ואצל הצוות. משהו השתנה מאז?' }), 'הקריאה הדחופה כבר פתוחה. משהו השתנה מאז?');
    expect('"ובטיפול אצל הצוות" goes',
      say({ reply: 'בדקתי במערכת: הקריאה על הנזילה בלובי עדיין פתוחה ובטיפול אצל הצוות. משהו החמיר?' }),
      'בדקתי במערכת: הקריאה על הנזילה בלובי עדיין פתוחה. משהו החמיר?');
    expect('", היא אצל הצוות" goes',
      say({ reply: 'הקריאה על הנזילה בלובי עדיין פתוחה, היא אצל הצוות. יש משהו חדש שחשוב שאוסיף?' }),
      'הקריאה על הנזילה בלובי עדיין פתוחה. יש משהו חדש שחשוב שאוסיף?');
    for (const same of [
      'מה שרשום אצלנו במערכת הוא 2,000 ש"ח. זה מסתדר עם מה שידוע לך?',
      'אני העוזר הדיגיטלי בצוות השירות של הומי\'ז. במה אוכל לעזור?',
      'פתחתי קריאה, מספרה 255-1414-26. היא אצל צוות החשמל.',
      'הקריאה פתוחה, וזה אצל הצוות לפי 255-1409-26. משהו השתנה?',
      // A cut that would leave "מה שבטוח." alone is no cut (the v4 case above has the same sentence).
      'אין לי שעה. מה שבטוח, שתי השאלות כבר אצל הצוות. יש עוד משהו?',
    ]) {
      expect('untouched: ' + same.slice(0, 40), say({ reply: same }), same);
    }
  }

  // 8 Nov, later (scripts/n8n_whatsapp_retest5.py, the tester's fifth run, C9.4 R15, execution 164822): the
  // retry answered "ומתי המנהל יחזור אליי?" with "וגם הבקשה שלך לדבר עם מנהל רשומה", from C9.1's quiet
  // notify_team; the prompt says never to tell it. The same claim on 29 Oct and in the 5 Nov run's C9.4.
  if (P.code && String(P.code.send_body || '').indexOf("const mg = 'manager v") !== -1) {
    console.log(NL + "--- Send: a manager request is never \"recorded\" (8 Nov, the tester's fifth run) ---");
    const obs = (o) => JSON.stringify([{ results: [{ toolCallId: 'wa', result: JSON.stringify(o) }] }]);
    const OPENED = { action: { tool: 'open_request' }, observation: obs({ ok: true, reference: '255-1418-26' }) };
    const R164822 = 'האמת שאין לי שעה מדויקת לתת לך, כי המערכת פשוט לא מראה לי זמנים או מתי יחזרו. מה שכן בטוח כרגע זה שהקריאה פתוחה ומטופלת, וגם הבקשה שלך לדבר עם מנהל רשומה. כשיסגרו את הקריאה אתה תקבל על זה עדכון אוטומטי ממש לכאן, ואם תרצה תוכל תמיד לכתוב לי ואני אבדוק בשמחה מה קורה איתה. ';
    expect('164822 exactly (the retry): ", וגם הבקשה שלך לדבר עם מנהל רשומה" goes, the rest stays',
      () => content(E, { reply: R164822 + NL + NL + 'יש עוד קומה בבניין או אזור ששמת לב שמלוכלך במיוחד עכשיו?', steps: [], said: 'ומתי המנהל יחזור אליי?' }),
      'האמת שאין לי שעה מדויקת לתת לך, כי המערכת פשוט לא מראה לי זמנים או מתי יחזרו. מה שכן בטוח כרגע זה שהקריאה פתוחה ומטופלת. כשיסגרו את הקריאה אתה תקבל על זה עדכון אוטומטי ממש לכאן, ואם תרצה תוכל תמיד לכתוב לי ואני אבדוק בשמחה מה קורה איתה. יש עוד קומה בבניין או אזור ששמת לב שמלוכלך במיוחד עכשיו?');
    expect('the 5 Nov run\'s C9.4: ", אבל הבקשה … רשומה …" goes, the honest no-time stays',
      say({ reply: 'זמן מדויק אין לי, אבל הבקשה שלך לדבר עם מנהל רשומה אצלנו מסודר יחד עם התלונה על הניקיון. יש עוד משהו שקשור לניקיון שאוסיף?', said: 'ומתי המנהל יחזור אליי?' }),
      'זמן מדויק אין לי. יש עוד משהו שקשור לניקיון שאוסיף?');
    expect('29 Oct: a sentence that opens with it loses it up to its comma, and the "אבל" after it',
      say({ reply: 'רשמתי את הבקשה שלך לדבר עם מנהל אצלנו במערכת, אבל חשוב לי לבדוק איתך אם אוכל לעזור בעצמי. מה קרה?' }),
      'חשוב לי לבדוק איתך אם אוכל לעזור בעצמי. מה קרה?');
    expect('a sentence that is only that goes whole',
      say({ reply: 'עדכנתי את ההנהלה שביקשת לדבר עם מנהל. כדי שאוכל לעזור כמה שיותר מהר, מה מטריד אותך?' }),
      'כדי שאוכל לעזור כמה שיותר מהר, מה מטריד אותך?');
    expect('joined by "ו" after the ticket: the number stays, the claim goes',
      () => content(E, { reply: 'פתחתי קריאה (255-1418-26) ורשמתי גם שביקשת לדבר עם מנהל. יש עוד מקומות בבניין שלא נוקו?', steps: [OPENED] }),
      'פתחתי קריאה (255-1418-26). יש עוד מקומות בבניין שלא נוקו?');
    expect('"וגם" with no comma: the claim goes',
      say({ reply: 'הקריאה על הניקיון פתוחה וגם הבקשה שלך למנהל נרשמה. משהו השתנה מאז?' }),
      'הקריאה על הניקיון פתוחה. משהו השתנה מאז?');
    expect('on one line after other words: the claim goes from its verb, "שוב ושוב" stays',
      say({ reply: 'אני מבין את התסכול כשזה עולה שוב ושוב רשמתי את הבקשה שלך לדבר עם מנהל, אבל חשוב לי לבדוק איתך אם אוכל לעזור. מה קרה?' }),
      'אני מבין את התסכול כשזה עולה שוב ושוב, אבל חשוב לי לבדוק איתך אם אוכל לעזור. מה קרה?');
    expect('"כבר עדכנתי" alone before it: the sentence goes',
      say({ reply: 'כבר עדכנתי את ההנהלה שביקשת לדבר עם מנהל. מה מטריד אותך?' }), 'מה מטריד אותך?');
    expect('a lead-in that would stand alone takes the sentence with it',
      say({ reply: 'אין לי שעה. מה שבטוח, הבקשה שלך לדבר עם מנהל רשומה. יש עוד משהו שתרצה שאוסיף לקריאה?' }),
      'אין לי שעה. יש עוד משהו שתרצה שאוסיף לקריאה?');
    for (const same of [
      // C9.1 and C9.2 of the fifth run, word for word.
      'הבנתי, אני לגמרי מבין אותך וממש רוצה לעזור לך עם זה כמה שיותר מהר. כדי שאוכל לעשות את זה על הצד הטוב ביותר, יעזור מאוד אם תוכל לספר לי בקצרה על מה העניין?',
      'אני באמת העוזר הדיגיטלי בצוות השירות של הומי\'ז. אני מבין לגמרי שאתה רוצה לדבר עם בן אדם, ואני כאן כדי לעזור לזה לקרות הכי מהר שאפשר. גם כמה מילים ממש יעזרו לי לקדם את זה בשבילך, אפשר לקבל רק כיוון כללי של מה שמטריד אותך?',
      'אני מבין שאתה רוצה לדבר עם מנהל, ורשמתי את התלונה על הניקיון במערכת. מה עוד קורה שם?',
      'רשמתי את התלונה על הניקיון ואני מבין שחשוב לך מאוד לדבר עם מנהל. מה עוד קורה שם?',
      'רשמתי בקריאה 255-1418-26 גם את הבקשה שלך לדבר עם מנהל. משהו נוסף?',
      'רשמתי את התלונה במערכת. יש עוד משהו שתרצה שאוסיף?',
    ]) {
      expect('untouched: ' + same.slice(0, 40), say({ reply: same }), same);
    }
  }

  // 8 Nov, night (scripts/n8n_whatsapp_manager2.py, the C5/C9 retest, execution 165118): the first draft for
  // "ומתי המנהל יחזור אליי?" said "וגם רשמתי במערכת את הבקשה שלך", with no "manager" in it. The truth check
  // sent it back; on a retry, or in the passive, manager v1 would have let it through.
  if (P.code && String(P.code.send_body || '').indexOf("const mg = 'manager v2'") !== -1) {
    console.log(NL + "--- Send: \"your request\" is the manager request when he asked for one (8 Nov, the retest) ---");
    const ASK = 'ומתי המנהל יחזור אליי?';
    expect('165118\'s first draft exactly: ", וגם רשמתי במערכת את הבקשה שלך" goes, the ticket stays',
      say({ reply: 'אין לי זמן מדויק לתת לך. מה שכן נכון עכשיו זה שהקריאה על הניקיון פתוחה ונמצאת אצלנו בטיפול, וגם רשמתי במערכת את הבקשה שלך. יש לכלוך ספציפי בקומה שלך או בחדר המדרגות שכדאי שאוסיף עליו עדכון לקריאה הקיימת בינתיים?', said: ASK }),
      'אין לי זמן מדויק לתת לך. מה שכן נכון עכשיו זה שהקריאה על הניקיון פתוחה ונמצאת אצלנו בטיפול. יש לכלוך ספציפי בקומה שלך או בחדר המדרגות שכדאי שאוסיף עליו עדכון לקריאה הקיימת בינתיים?');
    expect('the passive with no "manager": the sentence goes',
      say({ reply: 'אין לי שעה לתת לך. הבקשה שלך רשומה אצלי. יש עוד משהו שתרצה שאוסיף לקריאה?', said: ASK }),
      'אין לי שעה לתת לך. יש עוד משהו שתרצה שאוסיף לקריאה?');
    expect('"והפנייה שלך הועברה" after he asked for a person: the clause goes',
      say({ reply: 'אני מבין אותך לגמרי והפנייה שלך הועברה. מה קרה בבניין?', said: 'תביא לי בן אדם' }),
      'אני מבין אותך לגמרי. מה קרה בבניין?');
    expect('", אבל העברתי לצוות את הבקשה …" goes from its comma, the honest half stays',
      say({ reply: 'אני לא יכול להבטיח מתי בדיוק יחזרו אליך, אבל העברתי לצוות את הבקשה הדחופה שלך. יש משהו נוסף שאוכל לעזור לך בו?', said: 'תביא לי בן אדם' }),
      'אני לא יכול להבטיח מתי בדיוק יחזרו אליך. יש משהו נוסף שאוכל לעזור לך בו?');
    for (const [same, said] of [
      // A request for something named stays, even when he asked for a person in the same breath.
      ['בטח 👍 רשמתי את הבקשה שלך להוראת קבע, מספר הבקשה הוא 255-1417-26. יש עוד משהו שאוכל לעזור איתו?', 'לדבר עם נציג'],
      ['הבקשה שלך להוראת קבע כבר רשומה אצלנו במערכת, מספר הבקשה הוא 255-1395-26. יש עוד משהו?', 'לדבר עם נציג'],
      // No manager in what he wrote: "the request" is his own matter (the standing order, 255-1417-26's turn).
      ['רשמתי את הבקשה שלך במערכת. יש עוד משהו שאוכל לעזור בו?', 'אפשר לעשות הוראת קבע?'],
      ['בטח, רשמתי את הבקשה שלך להוראת קבע, מספר הבקשה הוא 255-1417-26. יש עוד משהו?', 'אפשר לעשות הוראת קבע?'],
      // "בבקשה" is "please", never the request.
      ['רשמתי את מה שאמרת, תכתוב לי בבקשה אם יש עוד משהו. מה עוד קורה שם?', 'אני רוצה מנהל'],
      // The retest's sent C9.4, word for word.
      ['זמן מדויק למתי יחזרו אליך אין לי כרגע, אני אומר לך בפשטות. מה שכן, הקריאה על הניקיון באמת נמצאת בטיפול אצלנו, ואני פה עושה כל מה שאפשר כדי לעזור לך עם זה. יש עוד אזור בבניין חוץ מחדר המדרגות שתרצה שאציין שלא נוקה?', ASK],
    ]) {
      expect('untouched: ' + same.slice(0, 40), say({ reply: same, said }), same);
    }
  }

  // 8 Nov, later (scripts/n8n_whatsapp_retest5.py, the tester's fifth run, C5 R2, execution 164670): after the
  // menu, a tap on "מצב קריאה קיימת" got "בשמחה, בוא נראה." with no name; the prompt asks for it twice. Of the
  // first replies after the menu since 25 Oct, 7 of 24 had no name. The draft below is the execution's own.
  if (P.code && String(P.code.send_body || '').indexOf("const iv = 'intro v1'") !== -1) {
    console.log(NL + "--- Send: after the system's greeting, he says who he is (8 Nov, the tester's fifth run) ---");
    const obs = (o) => JSON.stringify([{ results: [{ toolCallId: 'wa', result: JSON.stringify(o) }] }]);
    const STATUS = { action: { tool: 'get_request_status' }, observation: obs({ ok: true, found: 3, requests: [{ reference: '255-1416-26', status: 'open' }, { reference: '255-1415-26', status: 'open' }, { reference: '255-1414-26', status: 'cancelled' }] }) };
    const R164670 = 'בשמחה, בוא נראה.' + NL + NL + 'מצאתי שלוש קריאות פתוחות שרשומות עליך. קריאה 255-1416-26 על המים שיורדים מהתקרה באמבטיה נמצאת בסטטוס \'פתוחה\'. גם קריאה 255-1415-26 על המעלית התקועה עדיין פתוחה, וקריאה 255-1414-26 על הניקיון בחדר המדרגות בוטלה.' + NL + NL + 'האם תרצה שאבדוק על אחת מהן משהו ספציפי או שתרצה להוסיף להן פרטים?';
    const TAP = { last_bot: MENU_TEXT, tap: 'status', tap_now: true };
    expect('164670 exactly: the status tap after the menu opens with his name',
      () => content(E, { reply: R164670, steps: [STATUS], said: 'מצב קריאה קיימת', S: TAP }),
      'כאן מיכאל מהומי\'ז. בשמחה, בוא נראה. מצאתי שלוש קריאות פתוחות שרשומות עליך. קריאה 255-1416-26 על המים שיורדים מהתקרה באמבטיה נמצאת בסטטוס \'פתוחה\'. גם קריאה 255-1415-26 על המעלית התקועה עדיין פתוחה, וקריאה 255-1414-26 על הניקיון בחדר המדרגות בוטלה. האם תרצה שאבדוק על אחת מהן משהו ספציפי או שתרצה להוסיף להן פרטים?');
    expect('typed after the menu (6 Nov, the C11 burst): the name, then the reply',
      say({ reply: 'לא נעים להיות בלי אינטרקום. תוכל להגיד לי אם זה בפאנל למטה או רק אצלך בדירה?', said: 'האינטרקום לא עובד כבר יומיים', S: { last_bot: MENU_TEXT } }),
      'כאן מיכאל מהומי\'ז. לא נעים להיות בלי אינטרקום. תוכל להגיד לי אם זה בפאנל למטה או רק אצלך בדירה?');
    expect('the menu as the chat\'s last outbound message, Sort\'s note spent: the name too',
      say({ reply: 'אוי, לא נעים. איפה בדיוק זה קורה?', said: 'יש נזילה', rows: [{ direction: 'outbound', body: MENU_TEXT }] }),
      'כאן מיכאל מהומי\'ז. אוי, לא נעים. איפה בדיוק זה קורה?');
    expect('a greeting the draft kept comes first, then the name',
      say({ reply: 'היי, מה שלומך היום? 😊', said: 'לדבר עם נציג', S: { last_bot: MENU_TEXT, tap: 'other', tap_now: true } }),
      'היי, כאן מיכאל מהומי\'ז. מה שלומך היום? 😊');
    expect('the old menu line counts as the menu',
      say({ reply: 'אוי, לא נעים. איפה בדיוק?', said: 'יש נזילה', S: { last_bot: MENU_TEXT_BEFORE } }),
      'כאן מיכאל מהומי\'ז. אוי, לא נעים. איפה בדיוק?');
    expect('already named: untouched (C1\'s tap, word for word)',
      say({ reply: 'כאן מיכאל מצוות השירות של הומי\'ז. בשמחה אסף, אני כאן בדיוק בשביל זה 😊 ספר לי, מה קרה?', said: 'פתיחת קריאת שירות', S: { last_bot: MENU_TEXT, tap: 'open', tap_now: true } }),
      'כאן מיכאל מצוות השירות של הומי\'ז. בשמחה אסף, אני כאן בדיוק בשביל זה 😊 ספר לי, מה קרה?');
    expect('"who are you?" right after the menu: the digital-assistant answer is who he is',
      say({ reply: 'אני העוזר הדיגיטלי בצוות השירות של הומי\'ז. במה אוכל לעזור?', said: 'אתה בוט?', S: { last_bot: MENU_TEXT } }),
      'אני העוזר הדיגיטלי בצוות השירות של הומי\'ז. במה אוכל לעזור?');
    expect('mid-conversation, no menu before it: untouched',
      say({ reply: 'אוי, לא נעים. איפה בדיוק?', said: 'יש נזילה' }), 'אוי, לא נעים. איפה בדיוק?');
    expect('a short "I\'m checking" already went out this turn: untouched',
      say({ reply: 'זה הקישור לתשלום שלך.', said: 'איך משלמים?', S: { last_bot: MENU_TEXT }, acked: 'רגע, אני בודק.', ackSent: true }),
      'זה הקישור לתשלום שלך.');
    expect('the system\'s own greeting: untouched',
      say({ reply: MENU_TEXT, canned: true, S: { last_bot: MENU_TEXT } }), MENU_TEXT);
    expect('a follow-up menu ("אפשר לעזור בעוד משהו?") is no greeting: untouched',
      say({ reply: 'אוי, לא נעים. איפה בדיוק?', said: 'יש נזילה', rows: [{ direction: 'outbound', body: 'אפשר לעזור בעוד משהו?' }] }),
      'אוי, לא נעים. איפה בדיוק?');
  }

  // 8 Nov (scripts/n8n_whatsapp_retest4.py, the tester's C9.4, execution 164030): "ומתי המנהל יחזור אליי?"
  // was answered "תאריך או שעה מדויקת למתי יחזרו אליך אין לי, …", and promise v4, which lets "יחזרו אליך"
  // through after "מתי", did not know "למתי": the sentence was cut whole and "מה שכן, …" went alone.
  if (P.code && promiseV(P.code.send_body) >= 5) {
    console.log(NL + "--- Send: \"for when\" is asking when, not promising (8 Nov, the tester's C9.4) ---");
    const C94 = 'תאריך או שעה מדויקת למתי יחזרו אליך אין לי, אני אומר את זה בפשטות. מה שכן, הקריאה על הניקיון בחדר המדרגות כבר פתוחה ומעודכנת אצלנו. ';
    expect('C9.4 exactly (164030): the honest sentence stays',
      () => content(E, { reply: C94 + NL + NL + 'יש עוד משהו שקשור לניקיון שחשוב לך שאוסיף לקריאה בינתיים?', steps: [], said: 'ומתי המנהל יחזור אליי?' }),
      C94.trim() + ' יש עוד משהו שקשור לניקיון שחשוב לך שאוסיף לקריאה בינתיים?');
    expect('the promise itself is still cut',
      say({ reply: 'הקריאה על הניקיון פתוחה. יחזרו אליך מחר בבוקר. משהו השתנה מאז?' }),
      'הקריאה על הניקיון פתוחה. משהו השתנה מאז?');
  }

  // 11 Nov (scripts/n8n_whatsapp_hiintro.py, manners v5; owner: "lets remove the button each hi so every opening
  // message will receive the intro only", then "Hi good morning or good afternoon. this is michael from homies how
  // can i help you today"): a bare hello gets "היי, <clock> 👋 כאן מיכאל מהומי'ז. במה אוכל לעזור לך היום?" with no
  // buttons. Right after it the reply neither greets nor says who he is: the system said both.
  if (mannersV(P.code && P.code.send_body) >= 5) {
    console.log(NL + "--- Send: after the intro that names Michael (11 Nov, manners v5) ---");
    const INTRO = 'היי, צהריים טובים 👋 כאן מיכאל מהומי' + "'" + 'ז. במה אוכל לעזור לך היום?';
    const LIFT = 'אוי, לא נעים להיתקע בלי מעלית. באיזה בניין ובאיזו דירה זה?';
    const OUT = [{ direction: 'outbound', body: INTRO }];
    expect('after the intro (Sort says so): a second hello and the name are cut',
      say({ reply: "היי, כאן מיכאל מהומי'ז. " + LIFT, said: 'המעלית תקועה', S: { last_bot: INTRO } }), LIFT);
    expect("after the intro (the last message out says so): the hour's greeting is cut",
      say({ reply: 'צהריים טובים! ' + LIFT, said: 'המעלית תקועה', rows: OUT }), LIFT);
    expect('after the intro: a name alone is cut too',
      say({ reply: "כאן מיכאל מהומי'ז. " + LIFT, said: 'המעלית תקועה', rows: OUT }), LIFT);
    expect('after the intro: no name is added (intro v1 keys on the old menu only)',
      say({ reply: LIFT, said: 'המעלית תקועה', S: { last_bot: INTRO } }), LIFT);
    expect('after the intro: asked who he is, the name stays',
      say({ reply: "כאן מיכאל מצוות השירות של הומי'ז. במה אוכל לעזור?", said: 'מי זה?', S: { last_bot: INTRO } }),
      "כאן מיכאל מצוות השירות של הומי'ז. במה אוכל לעזור?");
    expect('after the OLD menu the name is still added (a chat whose last menu went out before 11 Nov)',
      say({ reply: LIFT, said: 'המעלית תקועה', S: { last_bot: MENU_TEXT } }), "כאן מיכאל מהומי'ז. " + LIFT);
    // The greeting goes out Canned reply? -> Type for a moment -> Send (execution 173085, 11 Nov 12:04 UTC), and
    // the first write left Send's own `greeting ||` branch: the owner's hello got the intro WITH the buttons.
    expect('the canned intro passes Send untouched, with no buttons',
      () => { const b = sent(E, { canned: true, reply: INTRO }); return b.content + '|' + (b.content_type === 'input_select'); },
      INTRO + '|false');
    expect('a menu sentence of before 11 Nov still gets its buttons (the old tail)',
      () => sent(E, { canned: true, reply: MENU_TEXT }).content_type, 'input_select');
    if (P.code.send_menu_body !== undefined) {
      expect('Send menu posts plain text', () => /input_select|content_attributes/.test(P.code.send_menu_body), false);
    }
    if (P.code.sort_menu !== undefined) {
      expect("Sort: the greeting is \"היי, \" + the clock's word + the intro",
        () => P.code.sort_menu.indexOf("const HI = HH < 5 ? 'היי' : 'היי, ' + HELLO;") !== -1
          && P.code.sort_menu.indexOf('content: HI + " 👋 כאן מיכאל מהומי' + "'" + 'ז. במה אוכל לעזור לך היום?",') !== -1, true);
    }
    if (E.lastWord) {
      const lw = (S, rows) => {
        const $ = (name) => { if (name === 'Sort') return { first: () => ({ json: S }) }; throw new Error('no node ' + name); };
        return E.lastWord({ all: () => rows.map((r) => ({ json: r })) }, $);
      };
      const INTRO_ROW = { direction: 'outbound', body: INTRO, external_id: '40002', message_type: 'text' };
      const LIFT_IN = { direction: 'inbound', body: 'המעלית תקועה', external_id: '40003', message_type: 'text' };
      const HI_IN = { direction: 'inbound', body: 'היי', external_id: '40001', message_type: 'text' };
      const S1 = { message_id: '40003', text: 'המעלית תקועה', last_bot: '', photo: false };
      expect('last word: right after the intro, the model is told what the system sent',
        () => { const r = lw(S1, [LIFT_IN, INTRO_ROW, HI_IN]); return r.length === 1 ? r[0].json.last_bot : 'none'; }, INTRO);
      expect('last word: the intro on top of a burst is read past, and the hello it answered left out',
        () => { const r = lw(S1, [INTRO_ROW, LIFT_IN, HI_IN]); return r.length === 1 ? r[0].json.text : 'none'; }, 'המעלית תקועה');
    }
  }

  // 6 Nov (scripts/n8n_whatsapp_retest3.py, the tester's C11, executions 159008-159015): "שלום", "יש בעיה"
  // and the fault, seconds apart. The menu was logged after the other two, so the backlog stopped on it at
  // once, and Sort's note that the menu went out had been spent by a silenced run.
  if (E.lastWord && String((P.code || {}).last_word || '').indexOf('lastword v2') !== -1) {
    console.log(NL + "--- Still the last word?: a burst after the menu (6 Nov, the tester's C11) ---");
    const lw = (S, rows) => {
      const $ = (name) => { if (name === 'Sort') return { first: () => ({ json: S }) }; throw new Error('no node ' + name); };
      return E.lastWord({ all: () => rows.map((r) => ({ json: r })) }, $);
    };
    const one = (S, rows) => { const r = lw(S, rows); return r.length === 1 ? r[0].json : { none: true }; };
    const MENU_ROW2 = { direction: 'outbound', body: MENU_TEXT, external_id: '37315', message_type: 'text' };
    const INTERCOM = { direction: 'inbound', body: 'האינטרקום לא עובד כבר יומיים', external_id: '37313', message_type: 'text' };
    const PROBLEM = { direction: 'inbound', body: 'יש בעיה', external_id: '37307', message_type: 'text' };
    const SHALOM = { direction: 'inbound', body: 'שלום', external_id: '37305', message_type: 'text' };
    const PREV = { direction: 'outbound', body: 'זמן מדויק אין לי. משהו השתנה מאז?', external_id: '37295', message_type: 'text' };
    const S11 = { message_id: '37313', text: 'האינטרקום לא עובד כבר יומיים', last_bot: '', photo: false };
    const BOTH = 'יש בעיה' + NL + 'האינטרקום לא עובד כבר יומיים';
    expect('C11 exactly (the menu logged after the burst): both messages reach the model',
      () => one(S11, [MENU_ROW2, INTERCOM, PROBLEM, SHALOM, PREV]).text, BOTH);
    expect('C11 exactly: the model is told the menu went out',
      () => one(S11, [MENU_ROW2, INTERCOM, PROBLEM, SHALOM, PREV]).last_bot, MENU_TEXT);
    expect('the menu logged in its place: the same text',
      () => one(S11, [INTERCOM, PROBLEM, MENU_ROW2, SHALOM, PREV]).text, BOTH);
    expect('the menu logged in its place: told too',
      () => one(S11, [INTERCOM, PROBLEM, MENU_ROW2, SHALOM, PREV]).last_bot, MENU_TEXT);
    expect("the last thing sent was Michael's own reply: no word of a menu",
      () => one(S11, [INTERCOM, PROBLEM, PREV]).last_bot, '');
    expect("Sort's own note stands when it has one",
      () => one(Object.assign({}, S11, { last_bot: 'אפשר לעזור בעוד משהו?' }), [INTERCOM, PREV]).last_bot, 'אפשר לעזור בעוד משהו?');
    expect('a later message arrived: this run says nothing',
      () => lw(Object.assign({}, S11, { message_id: '37307', text: 'יש בעיה' }), [MENU_ROW2, INTERCOM, PROBLEM, SHALOM, PREV]).length, 0);
    expect('a hello with more in it is not left out',
      () => one(S11, [MENU_ROW2, INTERCOM, { direction: 'inbound', body: 'שלום, יש בעיה', external_id: '37307' }, PREV]).text,
      'שלום, יש בעיה' + NL + 'האינטרקום לא עובד כבר יומיים');
    expect("a tap and the fault two seconds later still read as one (the join's first job)",
      () => one({ message_id: '21', text: 'המעלית תקועה', last_bot: '' },
        [{ direction: 'inbound', body: 'המעלית תקועה', external_id: '21' }, { direction: 'inbound', body: 'פתיחת קריאת שירות', external_id: '20' }, MENU_ROW2, SHALOM]).text,
      'פתיחת קריאת שירות' + NL + 'המעלית תקועה');
  }

  // 6 Oct (scripts/n8n_whatsapp_danger.py): in an emergency Michael says the
  // urgent ticket and its number, nothing else. The owner: "we dont order them
  // around we just open a ticket ... dont advise anything and dont tell them that
  // the team is on the way". Chat 6 of the 5 Oct evening live test.
  if (P.code && String(P.code.send_body || '').indexOf("const dv = 'danger v") !== -1) {
    console.log(NL + '--- Send: an emergency gets the urgent ticket and its number only (6 Oct) ---');
    const ob = (o) => JSON.stringify([{ results: [{ toolCallId: 'wa', result: JSON.stringify(o) }] }]);
    const URGENT = [{ action: { tool: 'open_request', toolInput: { urgency: 'emergency' } }, observation: ob({ ok: true, reference: '255-1349-26' }) }];
    const ALERT = [{ action: { tool: 'notify_team', toolInput: { reason: 'emergency' } }, observation: ob({ ok: true }) }];
    const OPENED_LINE = 'הבנתי, תודה! פתחתי קריאת חירום עבורך, מספר הקריאה הוא 255-1349-26. אני כאן לכל עדכון.';
    const PUSHED = 'פתחתי לך קריאה דחופה, מספר 255-1349-26, וזה הדבר היחיד שאני יכול לעשות מכאן.';
    // 11 Nov, danger v7: the turn that opened the urgent ticket or the emergency note always carries our line.
    const V7 = dangerV(P.code.send_body) >= 7;
    expect('the first word of an emergency: "right away" goes, the question for the address stays'
      + (V7 ? ', and our emergency line comes before it' : ''),
      say({ reply: 'אוי ואבוי! זה נשמע מסוכן מאוד! אני מעביר את זה לצוות החירום שלנו באופן מיידי. באיזה בניין מדובר?',
        said: 'יש מים שנוזלים מהתקרה בחדר מדרגות ישר על המנורה!!! מה עושים??', steps: ALERT }),
      V7 ? 'אוי ואבוי! זה נשמע מסוכן מאוד! ' + HOTS + ' באיזה בניין מדובר?' : 'אוי ואבוי! זה נשמע מסוכן מאוד! באיזה בניין מדובר?');
    expect('the ticket opened: "on the way" and every instruction go, the ticket and its number stay'
      + (V7 ? ', our emergency line right after the ticket' : ''),
      say({ reply: 'הבנתי, תודה! פתחתי קריאת חירום עבורך, מספר הקריאה הוא 255-1349-26. הצוות שלנו כבר בדרך לטפל בזה. לגבי כיבוי חשמל - '
        + 'אל תנסה לגעת בשום דבר שקשור לחשמל או למים בעצמך. בבקשה תתרחק מהאזור הרטוב. הבטיחות שלך היא הכי חשובה עכשיו. אני כאן לכל עדכון.',
        said: 'בר כוכבא 23. מה אני עושה בינתיים, לכבות חשמל??', steps: URGENT }),
      V7 ? 'הבנתי, תודה! פתחתי קריאת חירום עבורך, מספר הקריאה הוא 255-1349-26. ' + HOTS + ' אני כאן לכל עדכון.' : OPENED_LINE);
    // 6 Nov, danger v5 (n8n_whatsapp_retest.py): the step appends one line only, the plain one. "וזה הדבר
    // היחיד שאני יכול לעשות מכאן" was the line the owner disliked on 5 Nov; v4 still appended it to a question.
    const V5 = dangerV(P.code.send_body) >= 5;  // v6 (9 Nov) and v7 (11 Nov) keep v5's line
    const APPENDED = V5 ? 'הקריאה הדחופה שלך פתוחה, מספר 255-1349-26.' : PUSHED;
    expect('pushed for a number to call: only the ticket line',
      say({ reply: 'אין לי מספר לתת לך להתקשר אליו ישירות, אבל הצוות עודכן ומטפל בזה. בבקשה תמשיך להישאר רחוק מהאזור המסוכן.',
        said: 'יש מספר של מישהו שאני יכול להתקשר אליו עכשיו?', S: { last_bot: OPENED_LINE } }), APPENDED);
    expect('pushed about an electrician: the promise goes, the ticket line comes',
      say({ reply: 'אני מבין את התסכול שלך, אסף. הצוות שלנו בדרך. אין צורך להזמין חשמלאי בעצמך, הומי\'ז מטפלת בזה.',
        said: 'אז מה, להזמין חשמלאי לבד או שאתם שולחים מישהו?', S: { last_bot: PUSHED } }),
      'אני מבין את התסכול שלך, אסף. ' + APPENDED);
    if (V5) {
      // 6 Nov, danger v5: the Grok tester's C9 (156623, 156650). A turn whose tools handled another matter is
      // not an emergency turn, so the model's reply goes whole; with no such tool the step still guards.
      const SMOKE = 'פתחתי מיד קריאה דחופה על זה, המספר שלה הוא 255-1396-26.';
      const MGR = [{ action: { tool: 'notify_team', toolInput: { reason: 'caller_request' } }, observation: ob({ ok: true }) }];
      const CLEAN = [{ action: { tool: 'open_request', toolInput: { urgency: 'normal', type: 'cleaning' } }, observation: ob({ ok: true, reference: '255-1398-26' }) }];
      const C91 = 'אני רואה שאתה בלחץ ומבין לגמרי למה. אני כאן כדי לעשות כל מה שאפשר כדי לעזור. כדי שאוכל להבין בדיוק ולטפל בזה הכי מהר שאפשר, תוכל לספר לי עוד מה קורה עכשיו בבניין?';
      expect('v5: a manager request after an urgent ticket, noted this turn, goes whole (C9.1)',
        say({ reply: C91, said: 'אני רוצה לדבר עם מנהל', S: { last_bot: SMOKE }, steps: MGR }), C91);
      const C93 = 'הבנתי אותך. פתחתי קריאה על הניקיון בחדר המדרגות, מספר 255-1398-26. ורציתי לשאול בזהירות, מה קורה עם העשן עכשיו?';
      expect('v5: a new complaint after an urgent ticket, ticketed this turn, goes whole (C9.3)',
        say({ reply: C93, said: 'טוב. לא מנקים את חדר המדרגות כבר שבועיים.', S: { last_bot: SMOKE }, steps: CLEAN }), C93);
      expect('v5: a reply that names the urgent ticket is still guarded, whatever the tools did',
        say({ reply: 'הקריאה הדחופה שלך פתוחה, 255-1396-26. הצוות כבר בדרך.', said: 'אני רוצה לדבר עם מנהל', S: { last_bot: SMOKE }, steps: MGR }),
        'הקריאה הדחופה שלך פתוחה, 255-1396-26.');
      expect('v5: with no tool this turn, advice after an urgent ticket still goes and the ticket is named',
        say({ reply: 'אני מבין לגמרי את הלחץ. כדאי לצאת מהבניין עכשיו.', said: 'לא רוצה להסביר לבוט, תביא לי בן אדם', S: { last_bot: SMOKE } }),
        'אני מבין לגמרי את הלחץ. הקריאה הדחופה שלך פתוחה, מספר 255-1396-26.');
      expect('v5: a note about another matter does not let advice through when the reply names the urgent ticket',
        say({ reply: 'הקריאה הדחופה שלך פתוחה, 255-1396-26. כדאי לצאת מהבניין עכשיו.', said: 'אני רוצה לדבר עם מנהל', S: { last_bot: SMOKE }, steps: MGR }),
        'הקריאה הדחופה שלך פתוחה, 255-1396-26.');
    }
    expect('a goodbye in an emergency: the wish that they come soon goes, the ticket is named',
      say({ reply: 'בכיף, אסף. תודה רבה על הסבלנות. אני מקווה שהצוות יגיע במהרה.', said: 'טוב, תודה. אני מחכה להם למטה',
        S: { last_bot: PUSHED } }), 'בכיף, אסף. תודה רבה על הסבלנות. הקריאה הדחופה שלך פתוחה, מספר 255-1349-26.');
    const HONEST = 'אין לי תאריך מדויק מתי יגיעו, אבל הקריאה הדחופה שלך פתוחה, מספר 255-1349-26.';
    expect('"I don\'t know when they will come" stays whole', say({ reply: HONEST, said: 'מתי הם מגיעים?', S: { last_bot: PUSHED } }), HONEST);
    // 5 Nov (n8n_whatsapp_gas.py, Yariv's change 2): gas gets no ticket, only the gas company line, word
    // for word. It reaches the resident whole even right after an urgent ticket in the same chat, where
    // this step is awake. Line 1 of the two offered ("בגז מטפלת ישירות חברת הגז ...") lost its sentence
    // here to "מטפלת", read as a promise of action.
    const GAS = 'במקרה של גז, צריך לפנות לחברת הגז שמספקת את הגז לבניין ולדווח לה ישירות. יש עוד משהו בבניין שאני יכול לבדוק בשבילך?';
    expect('the gas company line stays whole, even right after an urgent ticket',
      say({ reply: GAS, said: 'יש ריח של גז בחדר המדרגות', S: { last_bot: PUSHED } }), GAS);
    // 19 Oct, danger v4 (the "when will they come?" paragraph): who and whether,
    // under "I can't see / know", and a fronted "I can't promise", are honest.
    if (dangerV(P.code.send_body) >= 4) {
      const WHO = 'פתחתי קריאה דחופה, 255-1349-26, והצוות כבר יודע על העשן. מי יבוא ומתי, את זה אני לא רואה מכאן. אני כאן איתך.';
      expect('v4: "who is coming and when, I can\'t see from here" stays whole', say({ reply: WHO, said: 'מישהו בא??', S: { last_bot: PUSHED } }), WHO);
      const WHETHER = 'אם ומתי מישהו מגיע, את זה אני לא יכול לדעת מכאן, כי את זה קובעים בצוות. ' + PUSHED;
      expect('v4: "whether and when someone comes, I can\'t know" stays whole', say({ reply: WHETHER, said: 'מישהו בא??', S: { last_bot: PUSHED } }), WHETHER);
      const FRONTED = 'הקריאה הדחופה שלך פתוחה, 255-1349-26, והצוות יודע. להבטיח שיגיעו עכשיו אני לא יכול, את זה קובעים שם.';
      expect('v4: a fronted "I can\'t promise they come now" stays whole', say({ reply: FRONTED, said: 'מתי??', S: { last_bot: PUSHED } }), FRONTED);
      expect('v4: "the team is on the way" still goes',
        say({ reply: 'הצוות בדרך אלייך. ' + PUSHED, said: 'מישהו בא??', S: { last_bot: PUSHED } }), PUSHED);
      expect('v4: "if needed, someone will come today" still goes',
        say({ reply: 'אם צריך, מישהו יגיע אלייך עוד היום. ' + PUSHED, said: 'מתי??', S: { last_bot: PUSHED } }), PUSHED);
      // v4, later (run 3): whether someone ALREADY, a verb of saying, and the done
      // message stay whole in an emergency; a conditional or an arrival still goes.
      const ALREADY = 'אני לא יכול לדעת אם מישהו כבר בדרך, את זה קובעים שם ולא אני. ' + PUSHED;
      expect('v4, later: I cannot know whether someone is already on the way, stays whole', say({ reply: ALREADY, said: 'מישהו בא??', S: { last_bot: PUSHED } }), ALREADY);
      const TELL = 'אני לא יכול להגיד לך שמישהו כבר בדרך. ' + PUSHED;
      expect('v4, later: I cannot tell you someone is already on the way, stays whole', say({ reply: TELL, said: 'מישהו בא??', S: { last_bot: PUSHED } }), TELL);
      const DONE = 'שעה אין לי, ואני לא רוצה לנחש כשמדובר בגז. כשהקריאה תיסגר, תגיע על זה הודעה לכאן. ' + PUSHED;
      expect('v4, later: the done message is a message arriving, not help, stays whole', say({ reply: DONE, said: 'מתי??', S: { last_bot: PUSHED } }), DONE);
      expect('v4, later: if needed someone is already on the way, still goes',
        say({ reply: 'אם צריך, מישהו כבר בדרך. ' + PUSHED, said: 'מתי??', S: { last_bot: PUSHED } }), PUSHED);
      expect('v4, later: the team will arrive and update you, still goes',
        say({ reply: 'הצוות יגיע ויעדכן אותך, ותקבל הודעה. ' + PUSHED, said: 'מתי??', S: { last_bot: PUSHED } }), PUSHED);
      expect('v4, later: no matter, the team is already on the way, still goes',
        say({ reply: 'לא נורא, הצוות כבר בדרך. ' + PUSHED, said: 'מתי??', S: { last_bot: PUSHED } }), PUSHED);
    }
    // v2 (the run again, 84781-84801): the model's own words for the ticket,
    // a phone number, and "I'm on it" before the ticket existed.
    const SERVICE = 'פתחתי קריאת שירות דחופה (מספר 255-1349-26) והצוות שלנו כבר מעודכן.';
    expect('"קריאת שירות דחופה" in the last message is an emergency: the electrician and the safety go, "it will be handled" stays',
      say({ reply: 'אני לא יכול לתת לך הנחיות לגבי ניתוק חשמל, כי זה משהו שרק חשמלאי מוסמך יכול להחליט עליו. ' + SERVICE
        + ' אין לי שעה לומר לך מתי מישהו יגיע, אבל זה יטופל כמו שצריך. שוב, הכי חשוב עכשיו זה לשמור על הבטיחות שלך.',
        said: 'לנתק את החשמל או לא? ומתי מישהו מגיע?',
        S: { last_bot: 'הבנתי! פתחתי עכשיו קריאת שירות דחופה, מספר הקריאה שלך הוא 255-1349-26.' } }),
      SERVICE + ' אין לי שעה לומר לך מתי מישהו יגיע, אבל זה יטופל כמו שצריך.');
    expect('a phone number in an emergency goes (an instruction to call)',
      say({ reply: 'המספר היחיד שאני יכול לתת לך הוא 03-1234567, של המשרד שלנו. ' + SERVICE,
        said: 'אין מספר שאפשר להתקשר אליו עכשיו??', S: { last_bot: SERVICE } }), SERVICE);
    expect('the reply naming the urgent ticket is an emergency before any tool: "I\'m on it right away" goes',
      say({ reply: 'אוי, זה ממש לא נעים לשמוע! אני מיד מטפל בזה. כדי שאוכל לפתוח קריאת שירות דחופה, באיזה בניין זה קרה?',
        said: 'דחוף!!! יש מים שנוטפים מהתקרה ישר על המנורה' }),
      'אוי, זה ממש לא נעים לשמוע! כדי שאוכל לפתוח קריאת שירות דחופה, באיזה בניין זה קרה?');
    const CALM = 'אין לי תאריך מדויק מתי יגיעו לתקן, אבל הקריאה שלך נפתחה והצוות יטפל בזה כמו שצריך. יש משהו נוסף שאוכל לעזור לך בו?';
    expect('outside an emergency nothing changes', say({ reply: CALM, said: 'מתי יבואו לתקן?',
      S: { last_bot: 'פתחתי קריאת שירות בנושא, מספרה 255-1347-26.' } }), CALM);
  }

  console.log(NL + '--- Reply usable?: echo and clerk (first pass only; exempt when the turn did work) ---');
  const obs = (o) => JSON.stringify([{ results: [{ toolCallId: 'wa', result: JSON.stringify(o) }] }]);
  const REFUSED = [{ action: { tool: 'open_request' }, observation: obs({ ok: true, opened: false, reason: 'street_unknown' }) }];
  const OPENED = [{ action: { tool: 'open_request' }, observation: obs({ ok: true, reference: '255-1331-26' }) }];
  const FULL = "צהריים טובים, מיכאל מהומי'ז. אני מבין שיש תקלה בתאורה בחדר המדרגות. כדי שאוכל לפתוח קריאת שירות, אצטרך לדעת באיזה בניין מדובר.";
  const g = (id, output, steps, run) => () => E.reply[id]({ output, intermediateSteps: steps }, run, turn({ steps }).$);
  expect('the 27 Sep morning reply, refused open_request: echo sends it back', g('echo', FULL, REFUSED, 0), false);
  expect('the 27 Sep morning reply, refused open_request: clerk sends it back', g('clerk', FULL, REFUSED, 0), false);
  expect('pass 1 always goes out (echo)', g('echo', FULL, [], 1), true);
  expect('pass 1 always goes out (clerk)', g('clerk', FULL, [], 1), true);
  expect('a real ticket was opened: exempt (echo)', g('echo', FULL, OPENED, 0), true);
  expect('a real ticket was opened: exempt (clerk)', g('clerk', FULL, OPENED, 0), true);
  expect('a link was returned: exempt', g('clerk', 'כדי שאוכל… הנה הקישור', [{ action: { tool: 'get_payment_link' } }], 0), true);
  expect('the team was told: exempt', g('echo', 'אני מבין שזה דחוף', [{ action: { tool: 'notify_team' } }], 0), true);
  expect('the payment two-beat is exempt', g('echo', 'אני מבין שאתם מחכים לקישור §§§ הנה הוא', [], 0), true);
  expect('an echo after a greeting and a comma is caught', g('echo', 'היי, אני מבין שיש נזילה.', [], 0), false);
  expect('a clean reply passes both', () => g('echo', 'איזה מעצבן. באיזה בניין ובאיזו דירה?', [], 0)()
    && g('clerk', 'איזה מעצבן. באיזה בניין ובאיזו דירה?', [], 0)(), true);
  // 29 Oct, evening (n8n_whatsapp_ionly.py): the owner, "please send a screenshot so that i can verify it
  // through our system". A claimed payment reads only get_balance, so the clerk saw no work this turn and
  // sent the sentence back; "so I can verify / check it" is the bot checking, and goes out.
  const BAL = [{ action: { tool: 'get_balance' }, observation: obs({ ok: true, found: 1, owed_total: 750 }) }];
  expect("the owner's 'so that I can verify it in our system' passes the clerk on a balance turn",
    g('clerk', 'אני רואה במערכת שלנו שעדיין רשום חוב של 750 ש"ח, והתשלום מאתמול לא מופיע. תוכל לשלוח לי צילום מסך של אישור התשלום, כדי שאוכל לאמת אותו במערכת?', BAL, 0), true);
  expect("'so I can check it' passes too, one word between", g('clerk', 'כדי שאוכל באמת לבדוק את זה, תוכל לשלוח לי את האישור?', [], 0), true);
  expect('an explanation before a question still goes back', g('clerk', 'כדי שאוכל לפתוח לך קריאה, באיזה בניין זה?', [], 0), false);
  expect('"so I can make sure it reaches the right person" still goes back', g('clerk', 'כדי שאוכל לוודא שהפנייה שלך מגיעה לאדם הנכון, מה העניין?', [], 0), false);
  // 18 Oct, late (executions 112601-112635, n8n_whatsapp_procedure.py): the owner asked
  // for a manager five times and got "what is it about?" five times. The first drafts
  // explained why the details are needed -- what he wants -- and these two sent them
  // back. In a chat about a manager or a person (the resident's own rows, the tap's
  // row aside; this message when the rows cannot be read) both pass.
  const gm = (id, output, rows, said) => () => E.reply[id]({ output, intermediateSteps: [] }, 0, turn({ rows, said }).$);
  const D112609 = 'אני מבין שחשוב לך לדבר עם מנהל. כדי שאוכל לוודא שהפנייה שלך מגיעה לאדם הנכון ושיוכלו לעזור לך במהירות, אני צריך להבין מה המצב. תוכל בכל זאת לשתף אותי במה מדובר? זה יעזור לי מאוד.';
  const D112635 = 'אני מקשיב היטב. כדי שאוכל להעביר את הבקשה שלך למנהל, אני צריך לדעת במה מדובר. ברגע שאדע את הנושא, אוכל ליידע את הצוות המתאים.';
  const MGR_ROWS = [{ direction: 'inbound', body: 'no i just need a manager' },
    { direction: 'outbound', body: 'אני מבין שאתה רוצה לדבר עם מנהל. כדי שאוכל לעזור לך...' },
    { direction: 'inbound', body: 'אני רוצה לדבר עם מנהל' }];
  expect('112609: in a chat about a manager the echo passes', gm('echo', D112609, MGR_ROWS, 'no i just need a manager'), true);
  expect('112609: and so does the clerk', gm('clerk', D112609, MGR_ROWS, 'no i just need a manager'), true);
  const WHY_TELL = [{ direction: 'inbound', body: 'למה שאספר לך?' }].concat(MGR_ROWS);
  expect('a follow-up with no manager word: the chat is still about one (112635)',
    gm('clerk', D112635, WHY_TELL, 'למה שאספר לך?'), true);
  expect('the rows cannot be read: this message alone decides', gm('clerk', D112635, [], 'i want to talk with the manager'), true);
  const FAULT_ECHO = 'אני מבין שיש נזילה בלובי. כדי שאוכל לפתוח קריאה, אצטרך את הבניין והדירה.';
  const TAPPED = [{ direction: 'inbound', body: 'יש נזילה בלובי' }, { direction: 'outbound', body: "היי, כאן מיכאל מהומי'ז! מה שלומך היום?" },
    { direction: 'inbound', body: 'לדבר עם נציג' }];
  expect('the לדבר עם נציג tap is not a chat about a manager: the echo still goes back',
    gm('echo', FAULT_ECHO, TAPPED, 'יש נזילה בלובי'), false);
  expect('...and the clerk too', gm('clerk', FAULT_ECHO, TAPPED, 'יש נזילה בלובי'), false);
  expect("the bot's own word מנהל does not count", gm('clerk', FAULT_ECHO,
    [{ direction: 'inbound', body: 'יש נזילה בלובי' }, { direction: 'outbound', body: 'אנחנו לא מנהלים את הבניין הזה' }], 'יש נזילה בלובי'), false);
  expect('"personal information" is not a person', gm('clerk', FAULT_ECHO,
    [{ direction: 'inbound', body: 'i dont want to share personal information' }], 'i dont want to share personal information'), false);
  // The replay of 112626's first draft: a promise inside the reason ("ולדאוג שיחזרו
  // אליך"). Let through, Send cuts its sentence and leaves "אני מבין שאתה רוצה לדבר עם
  // מנהל." with no question. With a promise the two still send it back.
  const D112626 = 'אני מבין שאתה רוצה לדבר עם מנהל. כדי שאוכל לעדכן את הצוות ולדאוג שיחזרו אליך, מה הנושא שבו תרצה לדבר איתם?';
  expect('112626: a promise in a chat about a manager still goes back (echo)', gm('echo', D112626, MGR_ROWS, 'i want to talk with the manager'), false);
  expect('112626: ...and (clerk)', gm('clerk', D112626, MGR_ROWS, 'i want to talk with the manager'), false);

  console.log(NL + '--- Reply usable?: deeds (27 Sep, "why is it inventing") ---');
  const tools = (k) => Array.from({ length: k }, () => ({ action: { tool: 'open_request' } }));
  const BULBS = 'היי, בדקתי את התאורה בחדרי המדרגות 1, 2 ו-3. החלפתי את הנורות שהבהבו ועכשיו הכל תקין. אם יש משהו נוסף שאוכל לעזור בו, אתם מוזמנים לכתוב לי.';
  const d = (output, k) => () => E.reply.deeds({ output, intermediateSteps: tools(k) }, 0, turn({}).$);
  expect('the invented repair, no tool', d(BULBS, 0), false);
  expect('the invented repair, even WITH a tool', d(BULBS, 1), false);
  expect('"checked the lighting", no tool', d('בדקתי את התאורה בחדר המדרגות.', 0), false);
  expect('opened a call with its number, tool ran', d('פתחתי קריאת שירות מספר 255-1307-26 בנוגע לפח המלא.', 1), true);
  expect('opened a call, NO tool ran', d('פתחתי קריאת שירות מספר 255-1307-26.', 0), false);
  expect('a status read with the status tool', d('בדקתי במערכת: הקריאה על הנזילה בלובי (255-1152-26) עדיין פתוחה.', 1), true);
  expect('a question, no deed, no tool', d('איזה מעצבן. באיזה בניין ובאיזו דירה זה?', 0), true);
  expect('"I told the team" is left to the team-note backstop', d('העברתי את זה לצוות שלנו.', 0), true);
  expect('"and I replaced"', d('ראיתי והחלפתי את הנורה.', 1), false);
  expect('"was fixed" without a tool', d('התקלה במעלית תוקנה.', 0), false);
  expect('"you are welcome" is not "was ordered"', d('אתם מוזמנים לכתוב לי בכל שאלה.', 0), true);
  expect('"all fine" is not "was arranged"', d('הכל בסדר, במה עוד אפשר לעזור?', 0), true);
  expect('a verb in quotes is still caught', d('כתבתי "החלפתי" בטעות.', 1), false);
  expect('a greeting is untouched', d("בוקר טוב! מיכאל מהומי'ז כאן. במה אוכל לעזור לכם?", 0), true);
  // 6 Nov (scripts/n8n_whatsapp_retest3.py, the tester's C6.4, execution 158913): "I recorded the details"
  // with no tool that turn went out, because "רשמתי" was never one of the verbs. Only where it now is.
  if (String(((P.code || {}).reply_usable || {}).deeds || '').indexOf('רשמתי') !== -1) {
    const C64 = 'אין בעיה. רשמתי את הפרטים שנתת לי (צ\'ק של כ-500 ש"ח מאמצע יולי). כשיהיה לך את הצילום או הקבלה, פשוט תשלח לי לכאן. יש עוד משהו שאוכל לעשות בשבילך היום?';
    expect('C6.4 exactly: "I recorded the details", no tool', d(C64, 0), false);
    expect('the same, with the tool that recorded them', d(C64, 1), true);
    expect('"I added it to the ticket", no tool', d('הוספתי את זה לקריאה, טוב שזה רק טפטוף. יש עוד משהו?', 0), false);
    expect('"I updated the ticket", no tool', d('עדכנתי את הקריאה שהמעלית עדיין לא עובדת. משהו השתנה?', 0), false);
    expect('"already recorded" is a state, not a deed', d('הבקשה שלך להוראת קבע כבר רשומה, מספר 255-1395-26. יש עוד משהו?', 0), true);
    expect('"I have not recorded anything" is not a deed', d('לא רשמתי שום דבר עדיין. מה הסכום ששילמת?', 0), true);
  }

  // 5 Oct: `Second try usable?` is gone with `Say it again`
  // (scripts/n8n_whatsapp_safetynet.py); these run only where it still exists.
  if (E.second.deeds) {
    console.log(NL + '--- Second try usable?: deeds (the rescue) ---');
    const r = (output) => () => E.second.deeds({ output }, 0, turn({}).$);
    expect('a stub ticket with its number', r('פתחתי לכם קריאה מספר 255-1330-26 על התאורה בחדר המדרגות. במה עוד אפשר לעזור?'), true);
    expect('handled + opened, with a number', r('טיפלתי בזה ופתחתי קריאה 255-1330-26.'), true);
    expect('checked + opened, with a number', r('בדקתי ופתחתי קריאה 255-1330-26.'), false);
    expect('opened, NO number', r('פתחתי לכם קריאה על התאורה.'), false);
    expect('the invented repair', r(BULBS), false);
    expect('a plain honest line', r('ההודעה שלכם לא יצאה כמו שצריך, אפשר לכתוב לי שוב מה קרה?'), true);
  }

  console.log(NL + '--- Outage reply usable? (all its conditions) ---');
  const all = (j) => () => Object.values(E.outage).every((f) => f(j, 0, turn({}).$) === true);
  expect('the honest outage line', all({ output: 'יש אצלנו כרגע תקלה טכנית. ההודעה שלכם הגיעה אלינו והצוות שלנו יודע עליה.' }), true);
  expect('"I passed it to the team" (true: the note fires)', all({ output: 'יש כרגע תקלה טכנית אצלנו, והעברתי את ההודעה שלכם לצוות.' }), true);
  expect('claims a check', all({ output: 'בדקתי ויש תקלה, הצוות יודע.' }), false);
  expect('carries a reference', all({ output: 'יש תקלה טכנית, מספר הפנייה 255-1330-26.' }), false);
  expect('carries a link', all({ output: 'יש תקלה טכנית, אפשר לשלם כאן https://x.example/pay' }), false);
  expect('the model died: no output at all', all({ error: 'Payment required' }), false);
  expect('one word', all({ output: 'תקלה.' }), false);

  console.log(NL + "--- Worth a word?: the note the payment ack's model is handed ---");
  const MID = '[אתם כבר באמצע שיחה. בלי ברכה ובלי להציג את עצמך שוב.]';
  const note = (j) => () => String(E.worth(j)).split(NL)[0];
  // 27 Sep: a note that told this model how to write a greeting made it answer
  // "hello good afternoon" with an invented payment request. Mid-conversation
  // it is told not to greet, whatever the resident wrote.
  expect('mid-conversation hello: no greeting, no instruction to write one', note({ greeted: true, text: 'hello good afternoon' }), MID);
  expect('mid-conversation payment ask: the same note', note({ greeted: true, text: "I didn't receive anything about the payment link" }), MID);
  expect('first contact: the first-contact note', () => note({ greeted: false, text: 'hi, I want to pay' })().startsWith('[זאת הפנייה הראשונה שלו אליך.'), true);
  expect("the resident's words follow the note", () => String(E.worth({ greeted: true, text: 'hello' })).split(NL)[1], 'hello');

  console.log(NL + '--- A word first?: what may go out before the answer ---');
  const PAYS = 'אני רוצה לשלם את הוועד';
  const w = (output, said) => () => E.word({ output }, turn({ said: said === undefined ? PAYS : said }).$);
  expect('NONE stays silent', w('NONE'), false);
  expect('"none" stays silent', w('none'), false);
  expect('empty stays silent', w(''), false);
  expect('a runaway stays silent', w('x'.repeat(330)), false);
  expect('a link never goes out early', w('רגע, בודק https://x.example'), false);
  expect('a short line goes out', w('רגע, אני בודק את זה עכשיו.'), true);
  // 1 Oct evening, execution 74654 (owner: "wth is this"): the ack model wrote a
  // payment note on a goodbye, as it had on "hello good afternoon" (65683, 65694).
  // Every sentence it wrote since 27 Sep was that invention. The note now goes out
  // only when the resident's own message has a payment word.
  const INVENTED = 'אני רואה שאתה מחפש קישור לתשלום. אני בודק את זה עכשיו.';
  expect('74654: a payment note on a goodbye stays silent', w(INVENTED, 'nothing so far thats about it thanks'), false);
  expect('65683: a payment note on a hello stays silent', w(INVENTED, 'hello good afternoon'), false);
  expect('a payment note on a fault stays silent', w(INVENTED, 'השער של החניה לא ננעל'), false);
  expect('"blinking" is not "link"', w(INVENTED, 'the light keeps blinking'), false);
  expect('"רחוב" is not a payment word', w(INVENTED, 'יש נזילה ברחוב הרצל'), false);
  expect('no resident text to read: silent', () => E.word({ output: INVENTED }, (n) => { throw new Error('no node ' + n); }), false);
  for (const said of ['אני רוצה לשלם', 'איך משלמים?', 'לא קיבלתי את הקישור', 'שלח לי לינק לתשלום', 'שילמתי כבר את הוועד?',
    'can i pay online?', 'send me the payment link', 'where do i pay the fee']) {
    expect('a payment word lets the note out: ' + JSON.stringify(said), w('רגע, אני בודק את זה עכשיו.', said), true);
  }
  // Carry on tells the answering model what was already sent: only what was.
  const carried = (out, sent) => () => {
    const nodes = {
      'Still the last word?': { first: () => ({ json: { text: PAYS, greeted: true } }) },
      'Worth a word?': { first: () => ({ json: { output: out } }) },
      'Say it now': { all: () => { if (!sent) throw new Error('unexecuted'); return [{ json: {} }]; } },
    };
    const $ = (n) => { if (!nodes[n]) throw new Error('no node ' + n); return nodes[n]; };
    const j = JSON.parse(E.carry({}, $));
    return j.text === PAYS ? j.acked : 'LOST THE ITEM';
  };
  expect('Carry on: a note that went out is what the answer hears', carried('רגע, אני בודק.', true), 'רגע, אני בודק.');
  expect('Carry on: a note the gate held back is not reported as sent', carried(INVENTED, false), '');
  expect('Carry on: NONE is nothing', carried('NONE', true), '');

  console.log(NL + '--- Try again: the rewrite names what was wrong (27 Sep, execution 65856) ---');
  const still = { first: () => ({ json: { text: 'hi, the stair lights flicker', greeted: true } }) };
  const $t = (name) => { if (name === 'Still the last word?') return still; throw new Error('no node ' + name); };
  const why = (output) => JSON.parse(E.tryAgain({ output }, $t)).retry_note;
  const REJ = "צהריים טובים! אני מיכאל מהומי'ז. אני מבין שיש לכם בעיה עם התאורה בחדר המדרגות בבניין, וזה מקשה עליכם לעלות במדרגות. אני אטפל בזה. באיזה בניין מדובר ומה מספר הדירה שלכם?";
  expect('65856: the echo is named, not a list of eight', () => why(REJ).includes('נפתחה בזה שהבנת אותו') && !why(REJ).includes('או שנתנה קישור'), true);
  expect('the clerk is named', () => why('כדי שאוכל לפתוח קריאה, אצטרך את הבניין.').includes('הסבירה לו למה אתה צריך פרט'), true);
  // (Named, the clerk adds "ובמקום זה פשוט תשאל"; unnamed, the note keeps its full list of eight.)
  expect('29 Oct: "so that I can verify it" is not named as the clerk',
    () => why('תוכל לשלוח לי צילום מסך של האישור, כדי שאוכל לאמת אותו במערכת?').includes('ובמקום זה פשוט תשאל'), false);
  expect('...while the clerk named still says "just ask"',
    () => why('כדי שאוכל לפתוח קריאה, אצטרך את הבניין.').includes('ובמקום זה פשוט תשאל'), true);
  expect('both are named', () => { const w = why('אני מבין שיש נזילה. כדי שאוכל לעזור אצטרך את הדירה.'); return w.includes('נפתחה בזה שהבנת') && w.includes('וגם היא הסבירה'); }, true);
  // 5 Oct: a truth guard's reason is read off the draft too (wa_truth.truth_js),
  // so an invented repair is named; the full list stays for what the node cannot see.
  expect('an invented repair is named, with the tools line',
    () => { const w = why('החלפתי את הנורה בחדר המדרגות.'); return w.includes('ושום כלי לא עשה את זה') && w.includes('open_request') && !w.includes('או שנתנה קישור'); }, true);
  expect('a reason the node cannot see keeps the full list', () => why('ספר/י לי מה קרה בבקשה').includes('או שנתנה קישור'), true);
  expect('the tools line is always there', () => why(REJ).includes('open_request') && why('x').includes('open_request'), true);
  // 19 Oct: the note opens "a draft you wrote for this message was not sent" (the
  // draft is out of the memory now), not "your previous answer".
  expect('no output at all: the full list, never a throw', () => why(undefined).startsWith('[טיוטה שכתבת להודעה הזאת לא יצאה לדייר'), true);
  expect("the resident's turn is carried through", () => JSON.parse(E.tryAgain({ output: REJ }, $t)).text, 'hi, the stair lights flicker');

  console.log(NL + '--- the inject: facts the answering model is handed ---');
  const now = { setZone: () => ({ toFormat: () => '12:20', weekday: 7 }) };
  // n8n's `$('Add who')`: not run (a number not on file, or live before section 6) unless `who` is given.
  const who$ = (who) => (n) => ({ isExecuted: who !== undefined, first: () => ({ json: { who_text: who || '' } }) });
  const inj = (greeted, text, who) => () => String(E.inject({ greeted, text, tap_now: false }, now, who$(who)));
  expect('mid-conversation + "hi, …" gets the fact', () => inj(true, 'hi, so i want to let you know')().includes('הדייר פתח את ההודעה הזאת בברכה'), true);
  expect('mid-conversation + no hello: no fact', () => inj(true, 'the elevator is stuck')().includes('הדייר פתח'), false);
  expect('first message: no fact', () => inj(false, 'hi, lights')().includes('הדייר פתח'), false);
  expect('"מה קורה עם הקריאה" is not a greeting', () => inj(true, 'מה קורה עם הקריאה שלי?')().includes('הדייר פתח'), false);
  expect('the false "you introduced yourself" stays gone', () => inj(true, 'x')().includes('והצגת את עצמך'), false);
  // 29 Oct, section 6 B: a sender on file is named to the model; on a workflow without `Add who` nothing changes.
  if (inj(true, 'x', ' [WHO-PROBE]')().includes('WHO-PROBE')) {
    expect('a sender on file: the model is told who is writing',
      () => inj(true, 'המעלית תקועה', ' [הפונה מזוהה במערכת: עידו, בר כוכבא 23, דירה 1.]')().includes('הפונה מזוהה במערכת: עידו'), true);
    expect('a number not on file: no such line', () => inj(true, 'המעלית תקועה')().includes('הפונה מזוהה'), false);
  }

  // 2 Nov (scripts/n8n_whatsapp_photo.py): a photo put on the item is said to be seen; one that could
  // not be fetched keeps "you do not see its content".
  const shownNote = (shown) => String(E.inject({ greeted: true, text: 'x', tap_now: false, photo: true, photos_shown: shown }, now, who$()));
  if (shownNote(1) !== shownNote(0)) {
    expect('a photo shown: the model is told it sees it', () => shownNote(1).includes('היא מצורפת כאן ואתה רואה אותה'), true);
    expect('a photo shown: nothing says it cannot be seen', () => shownNote(1).includes('אתה לא רואה את התוכן שלה'), false);
    expect('two photos shown: said in the plural', () => shownNote(2).includes('התמונות מצורפות כאן ואתה רואה אותן'), true);
    expect('a photo that could not be fetched: the model is told it cannot see it', () => shownNote(0).includes('אתה לא רואה את התוכן שלה'), true);
    expect('no photo: no photo note at all', () => String(E.inject({ greeted: true, text: 'x', tap_now: false, photos_shown: 0 }, now, who$())).includes('צירף תמונה'), false);
  }

  // 1 Oct evening (scripts/n8n_whatsapp_gender.py): the owner, "it still uses
  // how can i help you all which is awkward". The bot writes to one person now,
  // so every piece of code that reads "you" must know the singular, masculine
  // and feminine, and still match the plural exactly as before.
  console.log(NL + '--- one person, in the singular (1 Oct evening) ---');
  expect('promise v2: "נעדכן אותך" goes, the ticket stays',
    say({ reply: 'פתחתי לך קריאה מספר 255-1339-26. נעדכן אותך כשיהיה משהו חדש. אפשר לעזור בעוד משהו?', said: 'lights' }),
    'פתחתי לך קריאה מספר 255-1339-26. אפשר לעזור בעוד משהו?');
  expect('promise v2: "בדרך אלייך" goes with its clause',
    say({ reply: 'העברתי את זה לצוות שלנו, והם בדרך אלייך. יש עוד משהו?', said: 'help' }),
    'העברתי את זה לצוות שלנו. יש עוד משהו?');
  expect('promise v2: "ונשלח אליך טכנאי" is cut at its ו',
    say({ reply: 'פתחתי לך קריאה 255-1339-26 ונשלח אליך טכנאי. יש עוד משהו?', said: 'lift' }),
    'פתחתי לך קריאה 255-1339-26. יש עוד משהו?');
  expect('promise v2: "יגיע אלייך היום" goes',
    say({ reply: 'העברתי את זה לצוות. מישהו מהצוות יגיע אלייך היום. יש עוד משהו?', said: 'help' }),
    'העברתי את זה לצוות. יש עוד משהו?');
  const FEM = 'איזה מעצבן. תוכלי לכתוב לי באיזה בניין ובאיזו דירה?';
  expect('a feminine reply with nothing to remove: byte-identical', say({ reply: FEM, said: 'אני צריכה עזרה' }), FEM);
  const tn = (output, steps) => () => E.teamNote({ output }, turn({ steps }).$);
  expect('team note: "יחזור אלייך" makes the note', tn('נציג מהצוות יחזור אלייך בהקדם.'), true);
  expect('team note: "ניצור איתך קשר" makes the note', tn('ניצור איתך קשר בהמשך היום.'), true);
  expect('team note: the plural still makes it', tn('נציג יחזור אליכם בהקדם.'), true);
  expect('team note: "I passed it to the team" still makes it', tn('העברתי את זה לצוות שלנו.'), true);
  expect('team note: "רוצה שנעביר...?" is an offer, no note', tn('רוצה שנעביר את הפנייה לצוות, שיחזרו אליכם?'), false);
  expect('team note: a plain question makes none', tn('איזה מעצבן. באיזה בניין ובאיזו דירה?'), false);
  expect('team note: notify_team ran', tn('תודה.', [{ action: { tool: 'notify_team' } }]), true);
  // 18 Oct (n8n_whatsapp_askfirst.py): a request for a manager gets "tell me what it
  // is about, and I'll try to help or pass it on" before any note. An offer or a
  // condition in front of the verb is not a report; a report or a call-back promise is.
  expect('team note: "כדי שאוכל לעזור, או להעביר את זה לצוות…?" asks first, no note',
    tn('אני כאן בשביל זה 🙂 כדי שאוכל לעזור, או להעביר את זה לצוות עם כל הפרטים, מה בדיוק אתה צריך מהם?'), false);
  expect('team note: "ואם לא אוכל, אדאג להעביר את זה לצוות" is a condition, no note',
    tn('ספר לי מה המצב, ואנסה לעזור בעצמי. ואם לא אוכל, אדאג להעביר את זה לצוות או למנהל. מה קרה?'), false);
  expect('team note: "אשמח לעדכן את הצוות" before the details is an offer, no note',
    tn('אשמח לעדכן את הצוות, רק ספר לי קודם מה קרה?'), false);
  expect('team note: a report beside an offer still makes it',
    tn('העברתי את זה לצוות, ואם תרצה אוכל לעדכן גם את הגבייה.'), true);
  expect('team note: a call-back promise beside an offer still makes it',
    tn('אוכל להעביר את זה לצוות, והם יחזרו אליך.'), true);
  // 18 Oct, late (n8n_whatsapp_procedure.py): sentence by sentence. The chat about a
  // manager explains the procedure now; a condition, a "לא" before the verb or "אין
  // לי מה" holds back its own sentence, and a report in another sentence still counts.
  expect('team note: "לפני שמעבירים משהו לצוות" is the procedure, no note',
    tn('לפני שמעבירים משהו לצוות, צריך לדעת במה מדובר. מה קרה?'), false);
  expect('team note: "ברגע שתספר לי..., אעדכן את הצוות" is a condition, no note',
    tn('אני מבין אותך. ברגע שתספר לי במה מדובר, אעדכן את הצוות. על מה זה?'), false);
  expect('team note: "אין לי מה להעביר לצוות" is nothing passed on',
    tn('בלי לדעת במה מדובר, אין לי מה להעביר לצוות. אפילו משפט אחד מספיק, מה קרה?'), false);
  expect('team note: "אני לא מעביר בקשה ריקה לצוות" is a no, no note',
    tn('אני לא מעביר בקשה ריקה לצוות, ככה זה עובד אצלנו. במה מדובר?'), false);
  expect('team note: "כשתכתוב לי..., אני מעביר את זה לצוות" is a condition, no note',
    tn('כשתכתוב לי על מה מדובר, אני מעביר את זה לצוות מיד. מה הנושא?'), false);
  expect('team note: a present-tense report beside a condition still makes it',
    tn('אני מעביר את זה לצוות עכשיו. אם יהיה צורך, אעדכן אותך?'), true);
  expect('team note: "עכשיו אני מעביר" is a report (the כש inside עכשיו is not "when")',
    tn('עכשיו אני מעביר את זה לצוות.'), true);
  expect('team note: a promise to tell the team beside an offer in another sentence makes it',
    tn('אעדכן את הצוות בזה. אם תרצה, אוכל גם לפתוח קריאה?'), true);
  expect('team note: 112626, a call-back inside a purpose clause, is no note',
    tn('אני מבין שאתה רוצה לדבר עם מנהל. כדי שאוכל לעדכן את הצוות ולדאוג שיחזרו אליך, מה הנושא שבו תרצה לדבר איתם?'), false);
  expect('team note: "אם תרצה, ...שיחזרו אליך" is an offer, no note (5 Oct, 12:34)',
    tn('אם תרצה, אני יכול לעדכן את הצוות שיחזרו אליך טלפונית.'), false);
  expect('team note: a condition AFTER the promise does not hold it back',
    tn('הצוות עודכן שאתה רוצה שיחזרו אליך למספר הזה, ושזה חשוב לך לפני שהשיפוץ מתחיל.'), true);
  expect('team note: a purpose clause AFTER the report does not hold it back',
    tn('אני מעביר את זה לצוות עכשיו, כדי שיוכלו לבדוק את זה.'), true);
  // The Claude-played replay of tonight's chat (manager_parrot): explaining the
  // procedure, Michael talks about passing things on in every reply, and two of
  // them would have noted an empty request. In a chat about a manager the note
  // needs a past-tense report, an explicit "אני מעביר את...", or a call-back promise.
  const MGR_CHAT = [{ direction: 'inbound', body: 'i want to talk with the manager' },
    { direction: 'outbound', body: 'אני מבין שזה מתסכל...' }, { direction: 'inbound', body: 'אני רוצה לדבר עם מנהל' }];
  const tnm = (output, rows, said) => () => E.teamNote({ output }, turn({ rows, said }).$);
  expect('team note, a chat about a manager: "אני זה שמעביר פניות לצוות" is his job, not a report',
    tnm("לא, אני לא המנהל, אני מיכאל מצוות השירות של הומי'ז. אני זה שמעביר פניות לצוות, והרבה דברים אפשר גם לסדר כבר מכאן. מה העניין?",
      MGR_CHAT, 'why would i tell you are you the manager?'), false);
  expect('team note, a chat about a manager: "להעביר את הפנייה שלך לצוות אני כן" is what he can do, not a report',
    tnm('לחבר אותך ישירות למנהל אני לא יכול מכאן, אבל להעביר את הפנייה שלך לצוות אני כן, ובשביל זה צריך שיהיה כתוב בה על מה היא. על מה מדובר?',
      MGR_CHAT, 'i told you i want a manager just get me one are you not listening'), false);
  expect('team note, a chat about a manager: a past-tense report still makes it',
    tnm('רשמתי לצוות את החיוב הכפול על ספטמבר, אז זה כבר אצלם.', MGR_CHAT, 'i was charged twice'), true);
  expect('team note, a chat about a manager: an explicit "אני מעביר את זה לצוות" still makes it (23 Aug)',
    tnm('אני מעביר את זה לצוות, נחזור בהקדם.', MGR_CHAT, 'אני רוצה לדבר עם נציג אנושי בבקשה'), true);
  const op = (output, S) => () => E.reply.opener({ output }, 0, turn({ S }).$);
  expect('opener: "במה אוכל לעזור לך היום?" after a concrete message is sent back', op('היי! במה אוכל לעזור לך היום?'), false);
  expect('opener: the plural shape is still sent back', op('היי! במה אוכל לעזור לכם היום?'), false);
  expect('opener: a real answer passes', op('איזה מעצבן. באיזה בניין ובאיזו דירה?'), true);
  expect('opener: the נציג tap is exempt', op('היי! במה אוכל לעזור לך היום?', { tap: 'other' }), true);
  // 11 Nov (n8n_whatsapp_hiintro.py, manners v5): the greeting introduces Michael and carries no buttons, so a
  // reply that is only that intro gets none either. Before v5 it got the menu's two.
  if (mannersV(P.code && P.code.send_body) >= 5) {
    expect('menu rule (manners v5): the bare singular opener with the name, first contact, gets no buttons',
      () => sent(E, { reply: "היי, כאן מיכאל מהומי'ז. במה אוכל לעזור לך היום?", S: { greeted: false }, said: 'hi' }).content_type !== 'input_select', true);
  } else {
    expect('menu rule: the bare singular opener with the name, first contact, gets the buttons',
      () => sent(E, { reply: "היי, כאן מיכאל מהומי'ז. במה אוכל לעזור לך היום?", S: { greeted: false }, said: 'hi' }).content_type, 'input_select');
  }


  console.log(NL + '--- the representative says hi (1 Oct evening, execution 74529) ---');
  // Owner, on "כאן מיכאל מהומי'ז! 😊 במה אוכל לעזור לך?" (the model's "היי, " cut by
  // the filter): "the agent should be like hi how are you this is michael from
  // homies...". The one exception to "no greeting right after the menu" is the
  // לדבר עם נציג tap (n8n_whatsapp_rephello.py, manners v3). Every other row stays.
  const REP = "היי, מה שלומך? כאן מיכאל מהומי'ז. במה אוכל לעזור לך?";
  const REP_TAP = { last_bot: MENU_TEXT, tap: 'other', tap_now: true };
  expect('rep tap right after the menu: hi, how are you and the name go out whole',
    say({ reply: REP, said: 'לדבר עם נציג', S: REP_TAP }), REP);
  expect('rep tap, race: last_bot empty but Anything newer? shows the menu: the same',
    say({ reply: REP, said: 'לדבר עם נציג', S: { tap: 'other', tap_now: true },
      rows: [{ direction: 'inbound', body: 'לדבר עם נציג' }, MENU_ROW, HI_ROW] }), REP);
  expect('rep tap: two hellos, one kept',
    say({ reply: "היי! צהריים טובים, מה שלומך? כאן מיכאל מהומי'ז. במה אוכל לעזור לך?", said: 'לדבר עם נציג', S: REP_TAP }),
    "היי! מה שלומך? כאן מיכאל מהומי'ז. במה אוכל לעזור לך?");
  expect('rep tap from an old menu, mid-conversation: the hello and the name stay',
    say({ reply: REP, said: 'לדבר עם נציג', S: { tap: 'other', tap_now: true } }), REP);
  expect('the open-a-ticket tap right after the menu: still no hello, name kept',
    say({ reply: "היי! כאן מיכאל מהומי'ז, טוב שפנית. מה קרה?", said: 'פתיחת קריאת שירות',
      S: { last_bot: MENU_TEXT, tap: 'open', tap_now: true } }), "כאן מיכאל מהומי'ז, טוב שפנית. מה קרה?");
  expect('the status tap right after the menu: still no hello, name kept',
    say({ reply: "היי, כאן מיכאל מהומי'ז. מה מספר הקריאה?", said: 'מצב קריאה קיימת',
      S: { last_bot: MENU_TEXT, tap: 'status', tap_now: true } }), "כאן מיכאל מהומי'ז. מה מספר הקריאה?");
  expect('the turn after the rep tap: no hello',
    say({ reply: 'היי, שמח לשמוע! במה אוכל לעזור?', said: 'טוב תודה' }), 'שמח לשמוע! במה אוכל לעזור?');
  expect('rep tap after an ack that greeted (not a real path): the ack keeps the only hello',
    say({ reply: REP, said: 'לדבר עם נציג', S: REP_TAP, acked: 'צהריים טובים, רגע אני בודק.', ackSent: true }),
    "מה שלומך? כאן מיכאל מהומי'ז. במה אוכל לעזור לך?");
  expect('opener guard: the rep opener passes on the tap',
    () => E.reply.opener({ output: REP }, 0, turn({ S: REP_TAP }).$), true);
  expect('menu rule: the rep opener does not bring the menu back',
    () => sent(E, { reply: REP, said: 'לדבר עם נציג', S: REP_TAP }).content_type || 'text', 'text');

  console.log(NL + '--- the representative asks how you are, and only that (4 Oct, execution 80740) ---');
  // Owner, on "היי, אני מיכאל מהומי'ז. במה אוכל לעזור לך?": "didnt i told you to make
  // michael to be hi this is michael from homies how are you doing today?". The tap
  // paragraph asks for one question now, and `rephay` sends a tap reply with no
  // how-are-you back once (n8n_whatsapp_rephay.py, epoch 72).
  const REP_TODAY = "היי, אני מיכאל מהומי'ז. במה אוכל לעזור לך?";
  const REP_WANTED = "היי, כאן מיכאל מהומי'ז! מה שלומך היום?";
  const repHay = (output, runIndex, S) => () => E.reply.rephay({ output }, runIndex, turn({ S }).$);
  expect('rephay: 80740, the tap answered with no how-are-you, goes back', repHay(REP_TODAY, 0, REP_TAP), false);
  expect('rephay: hi, the name, how are you doing today passes', repHay(REP_WANTED, 0, REP_TAP), true);
  expect('rephay: the feminine "איך את היום?" passes', repHay("היי, כאן מיכאל מהומי'ז! איך את היום?", 0, REP_TAP), true);
  expect('rephay: English passes', repHay('Hi, this is Michael from Homies, how are you doing today?', 0, REP_TAP), true);
  // 5 Oct evening (n8n_whatsapp_hayday.py, the owner's "how are you today?"):
  // the Claude-played evening hello used the past form, and the guard sent it back.
  expect('rephay: the evening "איך עבר עליך היום?" passes',
    repHay("היי, מיכאל מהומי'ז כאן 🙂 איך עבר עליך היום?", 0, REP_TAP), true);
  expect('rephay: "מה שלומך היום?" passes', repHay("היי, כאן מיכאל מהומי'ז 😊 מה שלומך היום?", 0, REP_TAP), true);
  expect('rephay: the 1 Oct shape (both questions) still passes', repHay(REP, 0, REP_TAP), true);
  expect('rephay: the second pass goes out whatever it says', repHay(REP_TODAY, 1, REP_TAP), true);
  expect('rephay: the open-a-ticket tap is not asked', repHay("כאן מיכאל מהומי'ז, טוב שפנית. מה קרה?", 0,
    { last_bot: MENU_TEXT, tap: 'open', tap_now: true }), true);
  expect('rephay: a typed message is not asked', repHay('איזה מעצבן. באיזה בניין ובאיזו דירה?', 0, {}), true);
  expect('rep tap right after the menu: the wanted shape goes out whole',
    say({ reply: REP_WANTED, said: 'לדבר עם נציג', S: REP_TAP }), REP_WANTED);
  expect('rep tap: the hour word before it is still taken out',
    say({ reply: "היי, בוקר טוב! כאן מיכאל מהומי'ז! מה שלומך היום?", said: 'לדבר עם נציג', S: REP_TAP }),
    "היי, כאן מיכאל מהומי'ז! מה שלומך היום?");
  expect('opener guard: the wanted shape passes on the tap',
    () => E.reply.opener({ output: REP_WANTED }, 0, turn({ S: REP_TAP }).$), true);
  const repStill = { first: () => ({ json: { text: 'לדבר עם נציג', tap: 'other', greeted: true } }) };
  const $rep = (name) => { if (name === 'Still the last word?') return repStill; throw new Error('no node ' + name); };
  const repWhy = (output) => JSON.parse(E.tryAgain({ output }, $rep)).retry_note;
  expect('Try again: 80740 is named as the missing how-are-you, without the tools line',
    () => repWhy(REP_TODAY).includes('לא שאלה אותו לשלומו') && !repWhy(REP_TODAY).includes('open_request'), true);
  expect('Try again: a tap reply that asked keeps the full list',
    () => repWhy(REP_WANTED).includes('או שנתנה קישור'), true);

  console.log(NL + '--- "how are you" nobody asked for (18 Oct, executions 112521 and 112529) ---');
  // The owner typed "אני רוצה לדבר עם מנהל" and got "מה שלומך היום? 😊" twice: the
  // model answered the typed request as the tap. `unasked` (n8n_whatsapp_unasked.py)
  // sends such a reply back once; HAY_STRICT leaves "מה המצב" and "איך אתה מעדיף" alone.
  const BAD_HAY = "היי, כאן מיכאל מהומי'ז. מה שלומך היום? 😊";
  const MGR = { text: 'אני רוצה לדבר עם מנהל' };
  const unasked = (output, runIndex, S) => () => E.reply.unasked({ output }, runIndex, turn({ S }).$);
  expect('unasked: 112521, a typed request for a manager answered with how-are-you, goes back',
    unasked(BAD_HAY, 0, MGR), false);
  expect('unasked: the tap still asks how he is', unasked(REP_WANTED, 0, Object.assign({ text: 'לדבר עם נציג' }, REP_TAP)), true);
  expect('unasked: he asked first, so the ask-back passes',
    unasked('הכול טוב, תודה! ומה שלומך?', 0, { text: 'היי מיכאל, מה שלומך?' }), true);
  expect('unasked: "what is the situation" is about the matter and passes',
    unasked('אני איתך. ספר לי מה המצב ומה אתה צריך?', 0, MGR), true);
  expect('unasked: "how do you prefer to pay" is not how-are-you',
    unasked('איך אתה מעדיף לשלם, בהעברה או באשראי?', 0, { text: 'איך משלמים' }), true);
  expect('unasked: the second pass goes out whatever it says', unasked(BAD_HAY, 1, MGR), true);
  const mgrStill = { first: () => ({ json: { text: 'אני רוצה לדבר עם מנהל', tap: '', greeted: true } }) };
  const $mgr = (name) => { if (name === 'Still the last word?') return mgrStill; throw new Error('no node ' + name); };
  const mgrWhy = (output) => JSON.parse(E.tryAgain({ output }, $mgr)).retry_note;
  expect('Try again: 112521 is named as a how-are-you he did not ask for, without the tools line',
    () => mgrWhy(BAD_HAY).includes('והוא לא שאל אותך לשלומך') && !mgrWhy(BAD_HAY).includes('open_request'), true);
  expect('Try again: a reply with no how-are-you keeps the full list',
    () => mgrWhy('אני איתך. ספר לי מה קרה?').includes('או שנתנה קישור'), true);
  // 18 Oct, late: in a chat about a manager the echo and the clerk are not named, and
  // the unnamed list drops both and its "ask in one short question, no reason" tail.
  expect('Try again: 112609 in a chat about a manager names neither the echo nor the clerk',
    () => { const w = mgrWhy(D112609); return !w.includes('נפתחה בזה שהבנת') && !w.includes('הסבירה לו למה'); }, true);
  expect('Try again: there the list asks for no bare question',
    () => { const w = mgrWhy(D112609); return w.includes('או שנתנה קישור') && !w.includes('בלי הקדמה ובלי הסבר') && !w.includes('שהסבירה לו למה'); }, true);
  const whyAt = (output, text, rows) => JSON.parse(E.tryAgain({ output }, (name) => {
    if (name === 'Still the last word?') return { first: () => ({ json: { text, tap: '', greeted: true } }) };
    if (name === 'Anything newer?') return { all: () => rows.map((r) => ({ json: r })) };
    throw new Error('no node ' + name); })).retry_note;
  expect('Try again: the rows say the chat is about a manager though this message does not',
    () => !whyAt(D112635, 'למה שאספר לך?', WHY_TELL).includes('הסבירה לו למה'), true);
  expect('Try again: a fault after the tap still names the clerk',
    () => whyAt(FAULT_ECHO, 'יש נזילה בלובי', TAPPED).includes('הסבירה לו למה'), true);
  expect('Try again: 112626 names the promise, not the echo or the clerk',
    () => { const w = whyAt(D112626, 'i want to talk with the manager', MGR_ROWS);
      return w.includes('היא הבטיחה לו') && !w.includes('נפתחה בזה שהבנת') && !w.includes('הסבירה לו למה'); }, true);
  expect('Try again: a promise outside a chat about a manager is not named (Send cuts it there)',
    () => !whyAt('נציג יחזור אליך בהקדם.', 'יש נזילה בלובי', TAPPED).includes('היא הבטיחה לו'), true);
  // 5 Oct (scripts/n8n_whatsapp_safetynet.py, scripts/wa_truth.py). The live run
  // as Assaf Clix (docs/assistant/transcripts/2026-10-05-whatsapp-live-assaf.md):
  // the worst failures came from these checks. The drafts below are his, word
  // for word, where they were the bot's.
  console.log(NL + '--- the safety net stops making things worse (5 Oct, the live run as Assaf) ---');
  const obs5 = (o) => JSON.stringify([{ results: [{ toolCallId: 'wa', result: JSON.stringify(o) }] }]);
  const STATUS0 = { action: { tool: 'get_request_status' }, observation: obs5({ ok: true, found: 0, other_open: 5, requests: [] }) };
  const OPEN7 = { action: { tool: 'open_request' }, observation: obs5({ ok: true, reference: '255-1347-26' }) };
  const flat = (s) => ({ tool: s.action.tool, observation: s.observation });
  // The world a check sees: the last twelve messages (null: unreadable), Try
  // again's item (null: not run), and the agent's latest run.
  const world = (o) => (name) => {
    if (name === 'Anything newer?') { if (o.rows === null) throw new Error('unexecuted'); return { all: () => (o.rows || []).map((b) => ({ json: { direction: 'outbound', body: b } })) }; }
    if (name === 'Try again') { if (!o.T) throw new Error('unexecuted'); return { first: () => ({ json: o.T }) }; }
    if (name === 'Answer the resident') return { first: () => ({ json: { output: o.retry, intermediateSteps: o.steps2 || [] } }) };
    if (name === 'Sort') return { first: () => ({ json: { greeting: false, photo: false } }) };
    if (name === 'Still the last word?') return { first: () => ({ json: { text: o.said || 'x', greeted: true } }) };
    throw new Error('no node ' + name);
  };
  const NEG = 'אני מצטער אם בלבלתי אותך. לא פתחתי קריאה חדשה. רק שאלתי אם תרצה שאפתח. לגבי מתי מישהו יגיע, אני לא יכול לתת לך הערכת זמן מדויקת. אז, לפתוח קריאה חדשה על העובש במעלית בבר כוכבא 23 דירה 2?';
  const OLDREF = 'אני לא יכול לתת הנחיות בטיחות או עצות לגבי מה לעשות עם החשמל. מה שאני כן יכול להגיד לך זה שפתחנו קריאת שירות דחופה (מספר 255-1344-26) והצוות שלנו כבר יודע על הבעיה. יש משהו נוסף שאוכל לעזור לך בו?';
  const CHECKED = 'אוי, זה ממש לא נעים! 😔 בדקתי ולא מצאתי קריאה פתוחה על עובש במעלית בבר כוכבא 23 דירה 2. אני יכול לפתוח עכשיו קריאת שירות חדשה בנושא. מה דעתך?';
  const ECHOED = 'אני מבין שאתה מתוסכל מזה שאף אחד לא חזר אליך. 😔 בדקתי ולא מצאתי קריאה פתוחה על עובש במעלית בבר כוכבא 23 דירה 2. אני יכול לפתוח עכשיו קריאת שירות חדשה בנושא. מה דעתך?';
  const said5 = (id, output, o) => () => E.reply[id]({ output, intermediateSteps: o.steps || [] }, o.run || 0, world(o));
  expect('phantom: "לא פתחתי קריאה חדשה" is not a claim (blocked twice live)', said5('phantom', NEG, {}), true);
  expect('deeds: the same', said5('deeds', NEG, {}), true);
  expect('phantom: "פותח לך קריאה?" is a question, not a claim', said5('phantom', 'פותח לך קריאה?', {}), true);
  expect('phantom: "לא, פתחתי קריאה" is a claim, and with no number fails', said5('phantom', 'לא, פתחתי קריאה כבר הבוקר.', {}), false);
  expect('phantom: a claim with no number fails', said5('phantom', 'פתחתי לך קריאה על העובש. במה עוד?', {}), false);
  expect('phantom: the number a tool returned this turn backs it', said5('phantom', 'פתחתי לך קריאה 255-1347-26.', { steps: [OPEN7] }), true);
  expect('phantom: an invented number does not', said5('phantom', 'פתחתי לך קריאה 255-9999-26.', { rows: ['שלום'] }), false);
  expect('phantom: messages unreadable, so any number in the shape, as before 5 Oct', said5('phantom', 'פתחתי לך קריאה 255-9999-26.', { rows: null }), true);
  expect('phantom: on the second pass, the first pass\'s ticket backs it', said5('phantom', 'פתחתי לך קריאה 255-1347-26.', { run: 1, T: { first_steps: [flat(OPEN7)] } }), true);
  expect('phantom: the number in the next sentence backs the claim', said5('phantom', 'פתחתי לך קריאה דחופה על המעלית. מספר הקריאה שלך הוא 255-1347-26. משהו נוסף?', { steps: [OPEN7] }), true);
  // The offline run of 5 Oct: the only number was the OLD ticket's, three sentences away.
  expect('phantom: a NEW ticket claimed beside an old ticket\'s number fails',
    said5('phantom', 'אוי, לא נעים. אני רואה שהקריאה שלך 255-1460-26 מסומנת כמטופלת אצלנו. התאורה עדיין לא עובדת, וזה לא בסדר. אני פותח לך קריאת שירות חדשה כדי שהצוות יטפל בזה שוב. במה אוכל לעזור עוד?',
      { rows: ['255-1460-26. התאורה בחדר מדרגות קומה 3.'] }), false);
  expect('deeds: a ticket from two turns back, with its number, no tool now (live 83362)',
    said5('deeds', OLDREF, { rows: ['פתחתי עכשיו קריאת שירות דחופה, מספר 255-1344-26'] }), true);
  expect('deeds: the same sentence with an invented number', said5('deeds', OLDREF, { rows: ['שלום'] }), false);
  // 5 Nov (n8n_whatsapp_standing.py, Yariv's change 3): a standing order is recorded by
  // request_standing_order, whose own answer carries the number, so neither check sends the reply back,
  // in the words it is asked for or as a "ticket".
  const SO = { action: { tool: 'request_standing_order' },
    observation: obs5({ ok: true, recorded: true, recorded_now: true, reference: '255-1392-26' }) };
  const SO_SAID = 'רשמתי את הבקשה שלך להוראת קבע, מספר 255-1392-26. יש עוד משהו שאני יכול לעזור בו?';
  const SO_OPENED = 'פתחתי לך בקשה להוראת קבע, מספר 255-1392-26. יש עוד משהו שאני יכול לעזור בו?';
  expect('phantom: a standing order recorded this turn, with its number', said5('phantom', SO_SAID, { steps: [SO], rows: ['שלום'] }), true);
  expect('deeds: the same', said5('deeds', SO_SAID, { steps: [SO], rows: ['שלום'] }), true);
  expect('phantom: the same said as opened', said5('phantom', SO_OPENED, { steps: [SO], rows: ['שלום'] }), true);
  expect('deeds: the same said as opened', said5('deeds', SO_OPENED, { steps: [SO], rows: ['שלום'] }), true);
  expect('phantom: a standing order called a ticket ("פתחתי לך קריאה") is backed by the same number',
    said5('phantom', 'פתחתי לך קריאה להוראת קבע, מספר 255-1392-26.', { steps: [SO], rows: ['שלום'] }), true);
  expect('phantom: called a ticket with a number no tool gave, it is sent back',
    said5('phantom', 'פתחתי לך קריאה להוראת קבע, מספר 255-9999-26.', { steps: [SO], rows: ['שלום'] }), false);
  // 5 Oct, fix 4 (Claude-played check): the owner's line for a resident who
  // presses in danger passes only with the ticket's number, so the prompt asks
  // for it; without it this guard sends it back.
  const PUSHED = 'פתחתי לך קריאה דחופה, מספר 255-1344-26, וזה הדבר היחיד שאני יכול לעשות מכאן.';
  const URGENT_ROWS = { rows: ['פתחתי לך קריאה דחופה על הנזילה ליד גוף התאורה בלובי, מספר 255-1344-26.'] };
  expect('phantom: the pushed danger line, with its number from earlier in the chat', said5('phantom', PUSHED, URGENT_ROWS), true);
  expect('deeds: the same', said5('deeds', PUSHED, URGENT_ROWS), true);
  expect('phantom: the pushed danger line without its number is sent back',
    said5('phantom', 'פתחתי לך קריאה דחופה, וזה הדבר היחיד שאני יכול לעשות מכאן.', URGENT_ROWS), false);
  expect('deeds: the second pass\'s "בדקתי" after the first pass\'s lookup (live 83668)',
    said5('deeds', CHECKED, { run: 1, T: { first_steps: [flat(STATUS0)] } }), true);
  expect('deeds: "בדקתי" with no lookup in either pass', said5('deeds', CHECKED, { run: 1, T: { first_steps: [] } }), false);
  expect('deeds: "לא החלפתי" is not a repair', said5('deeds', 'לא החלפתי שום נורה, אני רק פותח קריאות. מה קרה?', {}), true);
  expect('deeds: the invented repair still fails, tool or not', said5('deeds', BULBS, { steps: [STATUS0] }), false);

  // Try again judges the first draft with the guards' own code, and carries it.
  const tj = (output, steps) => JSON.parse(E.tryAgain({ output, intermediateSteps: steps || [] }, world({})));
  expect('Try again: live 83668, an echo with a real lookup behind it, is a style fault only',
    () => tj(ECHOED, [STATUS0]).first_truth_ok, true);
  expect('Try again: it carries the lookup, and the note says what it returned',
    () => { const j = tj(ECHOED, [STATUS0]); return j.first_steps[0].tool + '|' + j.retry_note.includes('מה שהכלים כבר החזירו לך בתור הזה') + '|' + j.retry_note.includes('"found":0'); },
    'get_request_status|true|true');
  expect('Try again: a numberless ticket claim is untrue, and named',
    () => { const j = tj('פתחתי לך קריאה על העובש. במה עוד?', []); return j.first_truth_ok + '|' + j.retry_note.includes('ולא חזר מספר'); }, 'false|true');
  expect('Try again: the first draft rides along', () => tj(ECHOED, [STATUS0]).first_output, ECHOED);

  // Claimed a ticket? and Mend the reply: the last resort, no model.
  if (E.mend && E.claimed.claimed) {
    const cl = (output, o) => () => E.claimed.claimed({ output, intermediateSteps: o.steps || [] }, 1, world(o));
    expect('claimed: the first draft goes out instead, so no rescue ticket', cl('פתחתי לך קריאה על העובש.', { T: { first_truth_ok: true } }), false);
    expect('claimed: a numberless claim, nothing opened: the rescue ticket', cl('פתחתי לך קריאה על העובש. במה עוד?', { T: { first_truth_ok: false, first_steps: [flat(STATUS0)] } }), true);
    expect('claimed: a ticket really opened this turn: its number is used, no rescue', cl('פתחתי לך קריאה על העובש.', { T: { first_truth_ok: false, first_steps: [flat(OPEN7)] } }), false);
    expect('claimed: no claim at all: no rescue', cl('סליחה על הבלבול. מה קרה?', { T: { first_truth_ok: false } }), false);
    const md = (o, results) => () => JSON.parse(E.mend({ output: o.retry, results }, world(o))).output;
    const FIX = 'סליחה, משהו השתבש לי בתשובה. אפשר לכתוב לי את זה שוב?';
    expect('mend: a style-only first draft goes out (live 83668 would have)',
      md({ T: { first_truth_ok: true, first_output: ECHOED }, retry: 'פתחתי לך קריאה.' }), ECHOED);
    expect('mend: the rescue ticket\'s number stands where the false claim stood',
      md({ T: { first_truth_ok: false }, retry: 'אוי, לא נעים. פתחתי לך קריאה על העובש. יש עוד משהו שחשוב שאדע?' },
        [{ result: JSON.stringify({ ok: true, reference: '255-1348-26', rescued: true }) }]),
      'אוי, לא נעים. פתחתי על זה קריאה, מספר 255-1348-26. יש עוד משהו שחשוב שאדע?');
    expect('mend: a ticket really opened this turn: its number replaces the numberless claim',
      md({ T: { first_truth_ok: false, first_steps: [flat(OPEN7)] }, retry: 'פתחתי לך קריאה על העובש. משהו נוסף?' }),
      'פתחתי על זה קריאה, מספר 255-1347-26. משהו נוסף?');
    expect('mend: an invented repair goes, the rest stays',
      md({ T: { first_truth_ok: false }, retry: 'אוי, לא נעים. החלפתי את הנורה בחדר המדרגות. באיזה בניין זה?' }), 'אוי, לא נעים. באיזה בניין זה?');
    expect('mend: an invented link goes with its sentence',
      md({ T: { first_truth_ok: false }, retry: 'הנה הקישור שלך: https://pay.example.co.il/zz9. הוא אישי לדירה שלך. משהו נוסף?' }), 'הוא אישי לדירה שלך. משהו נוסף?');
    expect('mend: nothing true left: the one fixed line, never silence', md({ T: { first_truth_ok: false }, retry: 'החלפתי את הנורה.' }), FIX);
    expect('mend: an empty second pass: the fixed line', md({ T: { first_truth_ok: false }, retry: '' }), FIX);
    expect('mend: Try again unreadable: still the fixed line, never a throw', md({ retry: '' }), FIX);
    expect('mend: an honest second draft goes out as it is',
      md({ T: { first_truth_ok: false }, retry: NEG }), NEG);
  } else {
    console.log('(Claimed a ticket? / Mend the reply are not on this workflow: their cases are not run)');
  }

  // 19 Oct (scripts/n8n_whatsapp_norepeat.py): the bot sent back what the phone
  // already had. "מה קורה עם הקריאה שפתחתי?" twice got ASK_NUM twice, word for word
  // (114528, 114536); on another number the second pass sent the bot's previous
  // message back entire (114483). Rows are newest first, as `Anything newer?`
  // hands them (order=created_at.desc).
  console.log(NL + '--- `repeat`: what the phone already got is not sent again (19 Oct, executions 114483, 114528, 114536) ---');
  const ASK_NUM = 'אני מבין שאתה רוצה לברר מה קורה עם הקריאה שפתחת. תוכל לשלוח לי את מספר הקריאה, או את הכתובת המלאה בבקשה?';
  const HAY_OPEN = "היי 😊 כאן מיכאל מהומי'ז. הכל בסדר תודה, מה שלומך היום?";
  const TICKET_Q = 'הכל טוב תודה. מה קורה עם הקריאה שפתחתי אני לא מבין';
  const GLUED = 'לדבר עם נציג' + TICKET_Q;
  const inb = (b) => ({ direction: 'inbound', body: b });
  const outb = (b) => ({ direction: 'outbound', body: b });
  const rp = (output, rows, run, steps) => () => E.reply.repeat({ output, intermediateSteps: steps || [] }, run || 0, turn({ rows, steps }).$);
  const ROWS_114536 = [inb(TICKET_Q), outb(ASK_NUM), inb(GLUED), outb('היי, שלומי מצוין תודה! מה שלומך אתה ואיך אני יכול לעזור לך?'), inb('היי מה שלומך')];
  expect('114536: word for word what the phone got a minute ago goes back', rp(ASK_NUM, ROWS_114536), false);
  expect('114483: on the second pass too (no first-pass-only way out)',
    rp(HAY_OPEN, [inb(TICKET_Q), outb(HAY_OPEN), inb('היי מה קורה?')], 1), false);
  expect('nearly the same (one word changed, the emoji gone) is still a copy',
    rp("היי, כאן מיכאל מהומי'ז. הכל טוב תודה, מה שלומך היום?", [inb(TICKET_Q), outb(HAY_OPEN)]), false);
  expect('a different answer passes',
    rp('הקריאה שלך על התאורה, 255-1402-26, בטיפול מאז ה-12 באוקטובר. רוצה שאבדוק עוד משהו?', ROWS_114536), true);
  expect('a copy on a turn that did work is exempt, like the other style guards', rp(ASK_NUM, ROWS_114536, 0, OPENED), true);
  expect('a copy of a message older than the last three sent is not a repeat',
    rp(ASK_NUM, [outb('א'), outb('ב'), outb('ג'), outb(ASK_NUM)]), true);
  expect('the rows cannot be read: nothing is a repeat, never a throw',
    () => E.reply.repeat({ output: ASK_NUM, intermediateSteps: [] }, 0, world({ rows: null })), true);
  expect("the resident's own words are not the bot's: a reply that quotes them passes",
    rp('ok, "' + TICKET_Q + '" — בודק עכשיו, רגע.', [inb(TICKET_Q)]), true);
  // Try again names it, speaks of a draft that was not sent (the draft is out of the
  // memory now: Forget the draft), says what was sent arrived, and its tools line
  // names the status lookup.
  const noteOf = (output, text, rows, steps) => JSON.parse(E.tryAgain({ output, intermediateSteps: steps || [] }, (name) => {
    if (name === 'Still the last word?') return { first: () => ({ json: { text, tap: '', greeted: true } }) };
    if (name === 'Anything newer?') return { all: () => rows.map((r) => ({ json: r })) };
    throw new Error('no node ' + name); })).retry_note;
  expect('Try again: 114536 names the copy', () => noteOf(ASK_NUM, TICKET_Q, ROWS_114536).includes('חזרה כמעט מילה במילה'), true);
  expect('Try again: a copy on a turn that did work is not named',
    () => noteOf(ASK_NUM, TICKET_Q, ROWS_114536, [OPEN7]).includes('חזרה כמעט מילה במילה'), false);
  expect('Try again: the note speaks of a draft he never got, not of "your previous answer"',
    () => { const w = noteOf(ASK_NUM, TICKET_Q, ROWS_114536); return w.startsWith('[טיוטה שכתבת להודעה הזאת לא יצאה לדייר') && !w.includes('התשובה הקודמת שלך'); }, true);
  expect('Try again: ...and says what was sent before did arrive (the named note, the full list, the manager list)',
    () => [noteOf(ASK_NUM, TICKET_Q, ROWS_114536), why('ספר/י לי מה קרה בבקשה'), mgrWhy('אני איתך. ספר לי מה קרה?')]
      .every((w) => w.includes('ההודעות שכן שלחת לו קודם בשיחה הגיעו אליו') && w.endsWith(']')), true);
  expect('Try again: the tools line names the status lookup in all three',
    () => [noteOf(ASK_NUM, TICKET_Q, ROWS_114536), why('ספר/י לי מה קרה בבקשה'), mgrWhy('אני איתך. ספר לי מה קרה?')]
      .every((w) => w.includes('get_request_status') && w.includes('open_request')), true);
  // The chat about a manager is this message and the one before it, a pasted tap
  // text taken off: the glued "לדבר עם נציג" of 11:38 switched the echo guard off for
  // the rest of the chat.
  expect('114528: a pasted tap text glued to a ticket question is not a request for a person: the echo goes back',
    gm('echo', ASK_NUM, ROWS_114536.slice(2), GLUED), false);
  expect('114536: a minute later it is not one either', gm('echo', ASK_NUM, ROWS_114536, TICKET_Q), false);
  expect('a request for a manager three messages back no longer counts',
    gm('echo', FAULT_ECHO, [inb('יש נזילה בלובי'), outb('x'), inb('בר כוכבא 23 דירה 2'), outb('y'), inb('אני רוצה לדבר עם מנהל')], 'יש נזילה בלובי'), false);
  expect('the message before this one asked for a manager: still a chat about one', gm('clerk', D112635, WHY_TELL, 'למה שאספר לך?'), true);
  if (E.mend && E.claimed.claimed) {
    const cl2 = (output, o) => () => E.claimed.claimed({ output, intermediateSteps: o.steps || [] }, 1, world(o));
    const md2 = (o) => () => JSON.parse(E.mend({ output: o.retry }, world(o))).output;
    const FIX2 = 'סליחה, משהו השתבש לי בתשובה. אפשר לכתוב לי את זה שוב?';
    expect('claimed: a first draft that copies what was sent does not stand in, so the second draft is judged',
      cl2('פתחתי לך קריאה על העובש. במה עוד?', { T: { first_truth_ok: true, first_output: ASK_NUM, first_steps: [] }, rows: [ASK_NUM] }), true);
    expect('mend: a first draft that copies what was sent gives way to the second',
      md2({ T: { first_truth_ok: true, first_output: ASK_NUM }, retry: 'הקריאה שלך בטיפול. רוצה שאבדוק עוד משהו?', rows: [ASK_NUM] }), 'הקריאה שלך בטיפול. רוצה שאבדוק עוד משהו?');
    expect('mend: a second draft that is a copy too: the fixed line, never the copy',
      md2({ T: { first_truth_ok: false }, retry: ASK_NUM, rows: [ASK_NUM] }), FIX2);
    expect('mend: the same second draft with nothing sent before goes out', md2({ T: { first_truth_ok: false }, retry: ASK_NUM, rows: [] }), ASK_NUM);
  }
  // 11 Nov, night (n8n_whatsapp_confirm.py, repeat v2, epoch 106). The owner's lift test at 16:31 UTC (173705) got
  // "סליחה, משהו השתבש לי בתשובה": his reply, a caring word and our line word for word, was a near-copy of the smoke
  // reply sent minutes before, so `repeat` sent both drafts back and Mend put the fixed line in their place. A reply
  // that gives our emergency line is never a copy. The same write: a ticket only after his yes, and an emergency is
  // anything urgent that cannot wait (Yariv's "כל הבניין נזילת מים" got urgent ticket 255-1445-26 at 16:19, 173670).
  if (repeatV(((P.code || {}).reply_usable || {}).repeat) >= 2) {
    console.log(NL + '--- `repeat`: a reply that gives our emergency line is never a copy (11 Nov, night, 173705) ---');
    const SMOKE10 = 'זה נשמע מסוכן. ' + HOTS;
    const LIFT10 = 'זה מלחיץ מאוד. ' + HOTS;
    const LIFT10B = 'זה מצב חירום. ' + HOTS;
    expect('173705: the lift reply right after the smoke reply passes',
      rp(LIFT10, [inb('המעלית נתקעה בין הקומות ויש מישהו בפנים!!'), outb(SMOKE10)]), true);
    expect('the same line word for word, twice, passes too', rp(SMOKE10, [inb('עדיין יש עשן!!'), outb(SMOKE10)]), true);
    expect('a copy without our line is still a copy', rp(ASK_NUM, ROWS_114536), false);
    expect('Try again does not name a copy that gives our line',
      () => noteOf(LIFT10, 'המעלית נתקעה', [inb('המעלית נתקעה'), outb(SMOKE10)]).includes('חזרה כמעט מילה במילה'), false);
    if (E.mend && E.claimed.claimed) {
      const md3 = (o) => () => JSON.parse(E.mend({ output: o.retry }, world(o))).output;
      expect('173705: mend keeps a first draft with our line, even beside the same line sent',
        md3({ T: { first_truth_ok: true, first_output: LIFT10 }, retry: LIFT10B, rows: [SMOKE10] }), LIFT10);
      expect('mend: a second draft with our line goes out, never the fixed line',
        md3({ T: { first_truth_ok: false }, retry: LIFT10B, rows: [SMOKE10] }), LIFT10B);
    }
    const TA10 = String((P.code || {}).try_again || '');
    expect('Try again: "open it now" only once he said yes',
      () => TA10.indexOf('אם יש מה לפתוח, תפתח עכשיו') === -1 && TA10.indexOf('אם יש מה לפתוח והוא כבר אמר כן, תפתח עכשיו') !== -1, true);
    const PR10 = String((P.code || {}).prompt || '');
    if (PR10) {
      expect('prompt: a service call only after his yes, asked briefly before any ticket',
        () => PR10.indexOf('אבל רק אחרי שהוא אמר שהוא רוצה אותה') !== -1 && PR10.indexOf('לפני כל קריאה אתה שואל אותו בקצרה אם לפתוח אותה') !== -1
          && PR10.indexOf('וכשיש לך מה קרה, באיזה בניין, והכן שלו, הכלי בא לפני המילים') !== -1, true);
      expect('prompt: an emergency is anything urgent that cannot wait, a big leak and water running in the building included',
        () => PR10.indexOf('מקרה חירום, כלומר כל דבר דחוף שלא יכול לחכות') !== -1 && PR10.indexOf('נזילה גדולה או מים שזורמים בבניין') !== -1, true);
      expect('prompt: a lift that is down with nobody stuck stays a fault',
        () => PR10.indexOf('מעלית שלא עובדת כשאף אחד לא תקוע בה היא לא מקרה חירום') !== -1, true);
    }
  }
  // 9 Nov (scripts/n8n_whatsapp_feedback9.py): Yariv's written review of the simulated run.
  const SB9 = String((P.code || {}).send_body || '');
  const ob9 = (o) => JSON.stringify([{ results: [{ toolCallId: 'wa', result: JSON.stringify(o) }] }]);
  const clock9 = (time, weekday) => ({ setZone: () => ({ toFormat: () => time, weekday }) });
  if (dangerV(SB9) >= 6) {
    // 11 Nov (n8n_whatsapp_hotline.py, danger v7). The owner: "0776687949 this is the hotline so all the emergency
    // service redirect them here in a polite way". The line stays at any hour, and the turn whose tools opened the
    // urgent ticket or the emergency note always carries it: HOTS, when the reply has none. v6 keeps its own answers.
    const V7 = dangerV(SB9) >= 7;
    console.log(NL + (V7 ? '--- Send: an urgent call gets our emergency line at any hour (11 Nov, the owner) ---'
      : "--- Send: after hours an urgent call gets our emergency line too (9 Nov, Yariv's 6.2 / 6.3) ---"));
    const FRI = clock9('21:10', 5);
    const EARLY = clock9('08:30', 1);
    const SUN = clock9('12:20', 7);
    const URG = [{ action: { tool: 'open_request', toolInput: { urgency: 'emergency' } }, observation: ob9({ ok: true, reference: '255-1349-26' }) }];
    const OPEN9 = 'פתחתי לך קריאה דחופה, מספר 255-1349-26.';
    const HOTL = 'מכיוון שעכשיו מחוץ לשעות הפעילות, אפשר להתקשר עכשיו למוקד החירום הטלפוני שלנו, 077-6687949.';
    expect('after hours (Friday night): the ticket and our emergency line both stay',
      () => content(E, { reply: OPEN9 + ' ' + HOTL, said: 'בר כוכבא 23 דירה 2', steps: URG, now: FRI }), OPEN9 + ' ' + HOTL);
    expect('before 09:00 on a weekday: the same',
      () => content(E, { reply: OPEN9 + ' ' + HOTL, said: 'בר כוכבא 23 דירה 2', steps: URG, now: EARLY }), OPEN9 + ' ' + HOTL);
    expect(V7 ? 'in office hours the line stays too' : 'in office hours the line goes and the ticket stays',
      () => content(E, { reply: OPEN9 + ' ' + HOTL, said: 'בר כוכבא 23 דירה 2', steps: URG, now: SUN }), V7 ? OPEN9 + ' ' + HOTL : OPEN9);
    expect(V7 ? 'no clock (a replay, an old test): the line stays' : 'no clock (a replay, an old test) reads as open: the line goes',
      () => content(E, { reply: OPEN9 + ' ' + HOTL, said: 'בר כוכבא 23 דירה 2', steps: URG }), V7 ? OPEN9 + ' ' + HOTL : OPEN9);
    expect(V7 ? 'any other number still goes, and our line takes its place' : 'after hours, any other number still goes',
      () => content(E, { reply: OPEN9 + ' אפשר גם להתקשר למד"א ב-101.', said: 'בר כוכבא 23 דירה 2', steps: URG, now: FRI }),
      V7 ? OPEN9 + ' ' + HOTS : OPEN9);
    expect(V7 ? 'advice in the same sentence as our line still goes, and our line comes back on its own'
      : 'after hours, advice in the same sentence as our line still goes',
      () => content(E, { reply: OPEN9 + ' תתרחק מהמים ותתקשר למוקד שלנו, 077-6687949.', said: 'מה לעשות?', steps: URG, now: FRI }),
      V7 ? OPEN9 + ' ' + HOTS : OPEN9);
    expect('after hours, pressed with no tool this turn: the line stays beside the urgent ticket',
      () => content(E, { reply: 'הקריאה הדחופה שלך פתוחה, מספר 255-1349-26. ' + HOTL, said: 'מה לעשות??', S: { last_bot: OPEN9 }, now: FRI }),
      'הקריאה הדחופה שלך פתוחה, מספר 255-1349-26. ' + HOTL);
    expect(V7 ? '"someone is on the way" still goes, and our line comes' : 'after hours, "someone is on the way" still goes',
      () => content(E, { reply: OPEN9 + ' הצוות כבר בדרך אלייך.', said: 'בר כוכבא 23 דירה 2', steps: URG, now: FRI }),
      V7 ? OPEN9 + ' ' + HOTS : OPEN9);
    if (V7) {
      const LINE7 = 'אפשר להתקשר עכשיו למוקד החירום הטלפוני שלנו, 077-6687949.';
      expect('v7: in office hours, pressed with no tool this turn: the line stays beside the urgent ticket',
        () => content(E, { reply: 'הקריאה הדחופה שלך פתוחה, מספר 255-1349-26. ' + LINE7, said: 'מה לעשות??', S: { last_bot: OPEN9 }, now: SUN }),
        'הקריאה הדחופה שלך פתוחה, מספר 255-1349-26. ' + LINE7);
      expect('v7: an urgent ticket whose reply has no line: our line right after the ticket, before the question',
        () => content(E, { reply: OPEN9 + ' יש עוד משהו שחשוב שאדע על המצב שם?', said: 'בר כוכבא 23 דירה 2', steps: URG, now: SUN }),
        OPEN9 + ' ' + HOTS + ' יש עוד משהו שחשוב שאדע על המצב שם?');
      const ALERT7 = [{ action: { tool: 'notify_team', toolInput: { reason: 'emergency' } }, observation: ob9({ ok: true }) }];
      expect('v7: the emergency note before any ticket (no building yet): our line comes before the question',
        () => content(E, { reply: 'זה נשמע מסוכן. באיזה בניין זה קורה?', said: 'יש עשן בחדר המדרגות!!', steps: ALERT7, now: SUN }),
        'זה נשמע מסוכן. ' + HOTS + ' באיזה בניין זה קורה?');
      const OWN7 = OPEN9 + ' אני ממליץ להתקשר עכשיו למוקד החירום הטלפוני שלנו, 077-6687949. יש עוד משהו שחשוב שאדע?';
      expect('v7: his own polite line stays, "I recommend" included, and none is added',
        () => content(E, { reply: OWN7, said: 'בר כוכבא 23 דירה 2', steps: URG, now: SUN }), OWN7);
      const BARE7 = OPEN9 + ' אפשר להתקשר למוקד החירום שלנו בטלפון 0776687949.';
      expect('v7: the number written without a dash counts: none is added',
        () => content(E, { reply: BARE7, said: 'בר כוכבא 23 דירה 2', steps: URG, now: SUN }), BARE7);
      expect('v7: "I recommend" with advice in the same sentence still goes, and our line comes on its own',
        () => content(E, { reply: OPEN9 + ' כדאי לצאת מהבניין ולהתקשר למוקד שלנו, 077-6687949.', said: 'מה לעשות?', steps: URG, now: SUN }),
        OPEN9 + ' ' + HOTS);
      expect('v7: everything cut: the urgent ticket line, then our line',
        () => content(E, { reply: 'הצוות כבר בדרך אלייך.', said: 'בר כוכבא 23 דירה 2', steps: URG, now: SUN }),
        'הקריאה הדחופה שלך פתוחה, מספר 255-1349-26. ' + HOTS);
      const NORM7 = [{ action: { tool: 'open_request', toolInput: { urgency: 'normal', type: 'cleaning' } }, observation: ob9({ ok: true, reference: '255-1398-26' }) }];
      const CLEAN7 = 'פתחתי קריאה על הניקיון בחדר המדרגות, מספר 255-1398-26. יש עוד משהו שאוכל לעזור בו?';
      expect('v7: a ticket that is not urgent gets no line',
        () => content(E, { reply: CLEAN7, said: 'לא ניקו את חדר המדרגות', steps: NORM7, now: SUN }), CLEAN7);
      const AGAIN7 = 'הקריאה הדחופה שלך פתוחה, מספר 255-1349-26. משהו השתנה מאז?';
      expect('v7: a later turn with no tool and no line: none is added (it came with the ticket)',
        () => content(E, { reply: AGAIN7, said: 'עדיין יש עשן', S: { last_bot: OPEN9 + ' ' + HOTS }, now: SUN }), AGAIN7);
      const GAS7 = 'במקרה של גז, צריך לפנות לחברת הגז שמספקת את הגז לבניין ולדווח לה ישירות. '
        + 'אפשר גם להתקשר למוקד החירום הטלפוני שלנו, 077-6687949. יש עוד משהו בבניין שאני יכול לבדוק בשבילך?';
      expect('v7: the gas sentence with our line goes whole, even right after an urgent ticket, in office hours',
        () => content(E, { reply: GAS7, said: 'יש ריח של גז בחדר המדרגות', S: { last_bot: OPEN9 }, now: SUN }), GAS7);
      const PR7 = String((P.code || {}).prompt || '');
      if (PR7) {
        expect('v7 prompt: our line is no longer tied to the office hours',
          () => PR7.indexOf('רק כשכתוב לך שעכשיו מחוץ לשעות הפעילות') === -1 && PR7.indexOf('ומחוץ לשעות הפעילות גם את המוקד') === -1
            && PR7.indexOf('ומתקלה דחופה מחוץ לשעות הפעילות') === -1, true);
        if (dangerV(SB9) < 8) {   // v8's prompt has no urgent ticket in it (the block below)
          expect('v7 prompt: every urgent fault, at any hour, politely, from his first message about it',
            () => PR7.indexOf('על כל תקלה דחופה, בכל שעה, אתה גם מפנה אותו בנימוס למוקד החירום הטלפוני שלנו, 077-6687949') !== -1
              && PR7.indexOf('כבר בהודעה הראשונה שלך על המקרה, גם אם עוד לא פתחת את הקריאה') !== -1, true);
        }
        expect('v7 prompt: the gas sentence, word for word, carries our line', () => PR7.indexOf('"' + GAS7 + '"') !== -1, true);
      }
    }
    if (dangerV(SB9) >= 8) {
      // 11 Nov, night (n8n_whatsapp_lineonly.py, danger v8). The owner, on seeing 255-1444-26 open in OXS: "I DONT WANT
      // IT TO OPEN A TICKET CALL IN OXS JUST POINT THEM TO THE EMERGENCY HOTLINE WE HAVE". An emergency gets no ticket
      // and no note now, so its turn has no tool at all: the step wakes on our line in the reply instead, and still
      // cuts advice, other numbers and "on the way". A cut that takes the line gives it back, and an old urgent ticket
      // in the chat adds no number to a new emergency.
      console.log(NL + '--- Send: an emergency gets our line only, no ticket (11 Nov, night, the owner) ---');
      const SAY8 = 'זה נשמע מסוכן. ' + HOTS;
      expect('v8: an emergency with no tool: his line goes whole',
        () => content(E, { reply: SAY8, said: 'יש עשן בחדר המדרגות, ממש מריח שרוף', now: SUN }), SAY8);
      expect('v8: advice beside the line, no tool: the advice goes, the line stays',
        () => content(E, { reply: 'זה נשמע מסוכן. תתרחק מהעשן ותצא מהבניין. ' + HOTS, said: 'יש עשן בחדר המדרגות', now: SUN }), SAY8);
      expect('v8: another number, no tool: it goes, our line stays',
        () => content(E, { reply: 'זה נשמע מסוכן. אפשר להתקשר גם לכיבוי אש ב-102. ' + HOTS, said: 'יש עשן בחדר המדרגות', now: SUN }), SAY8);
      expect('v8: "on the way", no tool: it goes',
        () => content(E, { reply: SAY8 + ' הצוות כבר בדרך אליך.', said: 'יש עשן בחדר המדרגות', now: SUN }), SAY8);
      expect("v8: advice in the line's own sentence: the sentence goes and our line comes back",
        () => content(E, { reply: 'זה נשמע מסוכן. תתרחק מהעשן ותתקשר למוקד שלנו, 077-6687949.', said: 'יש עשן בחדר המדרגות', now: SUN }), SAY8);
      expect('v8: everything cut, no tool: our line alone',
        () => content(E, { reply: 'תצא מהבניין ותתקשר ל-102 או למוקד שלנו, 077-6687949.', said: 'יש עשן בחדר המדרגות', now: SUN }), HOTS);
      const OLD8 = 'פתחתי קריאה דחופה, מספר 255-1444-26. ' + HOTS;
      expect('v8: an old urgent ticket in the chat and a new emergency: no old number is added',
        () => content(E, { reply: 'זה נשמע מסוכן. תתרחק מהעשן. ' + HOTS, said: 'יש עשן בחדר המדרגות', S: { last_bot: OLD8 }, now: SUN }), SAY8);
      const PRESS8 = 'זה באמת מלחיץ. המוקד הטלפוני שלנו למקרי חירום הוא המקום לזה עכשיו, 077-6687949.';
      expect('v8: pressed, no tool: the line again, and no question is added',
        () => content(E, { reply: PRESS8, said: 'מה אני עושה עכשיו? שמישהו יבוא מהר!', S: { last_bot: SAY8 }, now: SUN }), PRESS8);
      const PR8 = String((P.code || {}).prompt || '');
      if (PR8) {
        expect('v8 prompt: an emergency opens no ticket and no note, and asks no building',
          () => PR8.indexOf('אתה לא פותח קריאה, גם כשזאת תקלה ברכוש המשותף, לא רושם הערה ולא שואל באיזה בניין או באיזו דירה') !== -1, true);
        expect('v8 prompt: our line word for word, in his first message about it, and the message ends there',
          () => PR8.indexOf('מילה במילה: "' + HOTS + '" ושם ההודעה נגמרת, בלי שאלה') !== -1
            && PR8.indexOf('כבר בהודעה הראשונה שלך על המקרה') !== -1, true);
        expect('v8 prompt: no urgent ticket and no urgent note asked for anywhere',
          () => ['קריאת שירות דחופה', 'רושם הערה דחופה', 'שפתחת קריאה דחופה', 'מה המספר של הקריאה, וגם את המוקד']
            .every((w) => PR8.indexOf(w) === -1), true);
        expect('v8 prompt: a message about an emergency may end without a question',
          () => PR8.indexOf('חוץ מההודעות על מקרה חירום') !== -1, true);
      }
    }
    // Yariv's own lift sentences (2.2 and 2.3) go out whole, even where this step is awake.
    const HIGH = [{ action: { tool: 'open_request', toolInput: { urgency: 'high', type: 'elevator' } }, observation: ob9({ ok: true, reference: '255-1600-26' }) }];
    const Y22 = "פתחתי את הקריאה בדחיפות גבוהה על המעלית בבר כוכבא 23, רשמתי אותה על דירה 2, מספר הקריאה בהומי'ז הוא 255-1600-26. "
      + 'אנחנו מעבירים את המידע והמשך הטיפול לחברת המעליות, ועוקבים אחריה. יש עוד משהו שאפשר לעזור בו בינתיים?';
    expect("Yariv's 2.2: the lift company sentence goes whole", () => content(E, { reply: Y22, said: 'בר כוכבא 23 דירה 2', steps: HIGH }), Y22);
    const Y23 = 'אני מצטער, אבל זה לא תלוי בנו, זה תלוי בחברת המעליות האחראית על השירות והתחזוקה של המעלית, ואנחנו עושים את מירב המאמצים מולם. משהו השתנה מאז הבוקר?';
    const LOOK = [{ action: { tool: 'get_request_status' }, observation: ob9({ ok: true, found: 1, requests: [{ reference: '255-1600-26', status: 'open' }] }) }];
    expect("Yariv's 2.3: right after the lift ticket, his answer goes whole",
      () => content(E, { reply: Y23, said: 'מתי מגיעים לתקן?', S: { last_bot: Y22 }, steps: LOOK }), Y23);
  }
  if (lineV(SB9) >= 1) {
    // 11 Nov, evening (n8n_whatsapp_line.py, line v1). The owner's Grok run of the emergency line, 16:02-16:16 Israel:
    // the line came with every emergency, but as an order, three times in the plural ("תתקשרו עכשיו", executions
    // 173373, 173391, 173403) and once bare ("תתקשר עכשיו", 173419). The owner asked for the line "in a polite way",
    // and his address rule is one person, never the plural. Wherever Michael gives 077-6687949, an order to call
    // becomes "אפשר להתקשר", and a plural "you" calling there is singular.
    console.log(NL + '--- Send: our emergency line comes as an invitation, never an order (11 Nov, the Grok run) ---');
    const WED = clock9('16:11', 3);
    const em = (ref) => [{ action: { tool: 'open_request', toolInput: { urgency: 'emergency' } }, observation: ob9({ ok: true, reference: ref }) },
      { action: { tool: 'notify_team', toolInput: { reason: 'emergency' } }, observation: ob9({ ok: true, reason: 'emergency' }) }];
    const LIFT1 = 'פתחתי קריאה דחופה על המעלית (255-1441-26). תתקשרו עכשיו למוקד החירום שלנו, 077-6687949. באיזו קומה היא נתקעה?';
    expect('173373 (the lift): "תתקשרו עכשיו" becomes "אפשר להתקשר עכשיו", the ticket and the question stay',
      () => content(E, { reply: 'פתחתי קריאה דחופה על המעלית (255-1441-26). תתקשרו עכשיו למוקד החירום שלנו, 077-6687949, כדי שיטפלו בזה מיד. באיזו קומה היא נתקעה?',
        said: 'המעלית נתקעה בין הקומות ויש מישהו בפנים!!', steps: em('255-1441-26'), now: WED }),
      'פתחתי קריאה דחופה על המעלית (255-1441-26). אפשר להתקשר עכשיו למוקד החירום שלנו, 077-6687949. באיזו קומה היא נתקעה?');
    const ADDED = [{ action: { tool: 'add_request_detail', toolInput: { detail: 'בין 2 ל3', reference: '255-1441-26' } }, observation: ob9({ ok: true, reference: '255-1441-26' }) }];
    expect('173391 (the floor added): "בבקשה תתקשרו" becomes "אפשר להתקשר"',
      () => content(E, { reply: 'הוספתי את זה לקריאה, תודה. בבקשה תתקשרו עכשיו למוקד החירום שלנו, 077-6687949.',
        said: 'בין 2 ל3', S: { last_bot: LIFT1 }, steps: ADDED, now: WED }),
      'הוספתי את זה לקריאה (255-1441-26), תודה. אפשר להתקשר עכשיו למוקד החירום שלנו, 077-6687949.');
    const SMOKE1 = 'פתחתי מיד קריאה דחופה (מספר 255-1442-26). בבקשה תתקשרו עכשיו למוקד החירום שלנו במספר 077-6687949, הם זמינים בדיוק למקרים כאלה.';
    expect('173403 (smoke): the same, and the rest of his sentence stays',
      () => content(E, { reply: SMOKE1, said: 'יש עשן בחדר המדרגות, ממש מריח שרוף', steps: em('255-1442-26'), now: WED }),
      'פתחתי מיד קריאה דחופה (מספר 255-1442-26). אפשר להתקשר עכשיו למוקד החירום שלנו במספר 077-6687949, הם זמינים בדיוק למקרים כאלה.');
    expect('173419 (pressed, no tool): the bare order "תתקשר עכשיו" becomes "אפשר להתקשר עכשיו"',
      () => content(E, { reply: 'פתחתי קריאה דחופה שמספרה 255-1442-26. תתקשר עכשיו למוקד החירום שלנו, 077-6687949.',
        said: 'מה אני עושה עכשיו? שמישהו יבוא מהר!', S: { last_bot: SMOKE1 }, now: WED }),
      'פתחתי קריאה דחופה שמספרה 255-1442-26. אפשר להתקשר עכשיו למוקד החירום שלנו, 077-6687949.');
    expect('the formal order to dial becomes "אפשר לחייג"',
      () => content(E, { reply: 'פתחתי לך קריאה דחופה, מספר 255-1349-26. חייגו עכשיו למוקד החירום שלנו, 077-6687949.',
        said: 'בר כוכבא 23 דירה 2', steps: em('255-1349-26'), now: WED }),
      'פתחתי לך קריאה דחופה, מספר 255-1349-26. אפשר לחייג עכשיו למוקד החירום שלנו, 077-6687949.');
    expect('"כדאי שתתקשרו" is singular: "כדאי שתתקשר"',
      () => content(E, { reply: 'פתחתי לך קריאה דחופה, מספר 255-1349-26. כדאי שתתקשרו עכשיו למוקד החירום שלנו, 077-6687949.',
        said: 'בר כוכבא 23 דירה 2', steps: em('255-1349-26'), now: WED }),
      'פתחתי לך קריאה דחופה, מספר 255-1349-26. כדאי שתתקשר עכשיו למוקד החירום שלנו, 077-6687949.');
    expect('"if you call" keeps its meaning, in the singular',
      () => content(E, { reply: 'פתחתי לך קריאה דחופה, מספר 255-1349-26. אם תתקשרו למוקד החירום שלנו, 077-6687949, יענו שם בכל שעה.',
        said: 'בר כוכבא 23 דירה 2', steps: em('255-1349-26'), now: WED }),
      'פתחתי לך קריאה דחופה, מספר 255-1349-26. אם תתקשר למוקד החירום שלנו, 077-6687949, יענו שם בכל שעה.');
    const GAS2 = 'על גז צריך לדווח ישר לחברת הגז של הבניין. אתה מוזמן גם להתקשר עכשיו למוקד החירום שלנו במספר 077-6687949 והם יעזרו לך.';
    expect('173361 (gas, "what do I do?"): an invitation already, it goes whole',
      () => content(E, { reply: GAS2, said: 'מה לעשות? לפתוח חלונות?', now: WED }), GAS2);
    expect('the office number on request, no emergency: an order to call becomes an invitation there too',
      () => content(E, { reply: 'הטלפון של המשרד הוא 077-6687949, תתקשר בשעות הפעילות. יש עוד משהו שאוכל לעזור בו?',
        said: 'מה הטלפון של המשרד?', now: WED }),
      'הטלפון של המשרד הוא 077-6687949, אפשר להתקשר בשעות הפעילות. יש עוד משהו שאוכל לעזור בו?');
  }
  if (promiseV(SB9) >= 6) {
    console.log(NL + "--- Send: a standing order's call from collections is no promise (9 Nov, Yariv's 5.2) ---");
    const SOREC = { action: { tool: 'request_standing_order' }, observation: ob9({ ok: true, recorded: true, recorded_now: true, reference: '255-1392-26' }) };
    const SOAGAIN = { action: { tool: 'request_standing_order' }, observation: ob9({ ok: true, already_recorded: true, reference: '255-1392-26' }) };
    const CBK = 'רשמתי את הבקשה שלך להוראת קבע, מספר 255-1392-26, ומישהו מצוות הגבייה ייצור איתך קשר בטלפון. יש עוד משהו שאוכל לעזור בו?';
    const BACK = 'רשמתי את הבקשה שלך להוראת קבע, מספר 255-1392-26, ומישהו מצוות הגבייה יחזור אליך בטלפון. יש עוד משהו שאוכל לעזור בו?';
    expect('recorded this turn: "someone from collections will call you" stays', () => content(E, { reply: CBK, said: 'אפשר לעשות הוראת קבע?', steps: [SOREC] }), CBK);
    expect('"will get back to you by phone" stays the same way', () => content(E, { reply: BACK, said: 'אפשר לעשות הוראת קבע?', steps: [SOREC] }), BACK);
    expect('already recorded: the same', () => content(E, { reply: CBK, said: 'אפשר לעשות הוראת קבע?', steps: [SOAGAIN] }), CBK);
    expect('recorded by the first pass, carried by Try again: the same', () => {
      const m = turn({ reply: CBK, said: 'אפשר לעשות הוראת קבע?', steps: [] });
      const $ = (nm) => (nm === 'Try again'
        ? { first: () => ({ json: { first_steps: [{ tool: 'request_standing_order', observation: ob9({ ok: true, recorded: true, reference: '255-1392-26' }) }] } }) }
        : m.$(nm));
      return JSON.parse(E.send(m.$json, $)).content;
    }, CBK);
    expect('no standing order this turn: the same promise is still cut',
      () => content(E, { reply: CBK, said: 'אפשר לעשות הוראת קבע?', steps: [] }).indexOf('ייצור איתך קשר') === -1, true);
    expect('a standing order turn does not let "soon" through',
      () => content(E, { reply: CBK.replace('בטלפון', 'בקרוב'), said: 'אפשר לעשות הוראת קבע?', steps: [SOREC] }).indexOf('בקרוב') === -1, true);
    expect('a standing order turn does not let "we will call you" through',
      () => content(E, { reply: CBK.replace('ומישהו מצוות הגבייה ייצור איתך קשר', 'וניצור איתך קשר'), said: 'אפשר לעשות הוראת קבע?', steps: [SOREC] }).indexOf('ניצור איתך קשר') === -1, true);
  }
  // 10 Nov (scripts/n8n_whatsapp_retest7.py): the tester's seventh run, C3.3 (170031). A main-pipe ticket
  // went out with "נשלח איש מקצוע מטעמנו לבדוק ולטפל בזה": the list knew "נשלח מישהו / טכנאי" only.
  if (promiseV(SB9) >= 7) {
    console.log(NL + '--- Send: "a professional will be sent" is a promise too (10 Nov, the tester\'s C3.3) ---');
    const PIPE = [{ action: { tool: 'open_request' }, observation: ob9({ ok: true, reference: '255-1428-26', reference_spoken: 'אחת ארבע שתיים שמונה' }) }];
    const C33 = 'הבנתי. פתחתי עכשיו קריאה על הנזילה (המספר שלה הוא 255-1428-26), ורשמתי אותה על הדירה שלך. '
      + 'נשלח איש מקצוע מטעמנו לבדוק ולטפל בזה. כשהקריאה תיסגר נעדכן אותך בהודעה לכאן. יש עוד משהו שאוכל לעזור בו עכשיו?';
    expect('C3.3 exactly (170031): the professional and the update go, the ticket stays',
      () => content(E, { reply: C33, said: 'האינסטלטור שלי היה פה אתמול, והוא אמר שזה מהצנרת הראשית של הבניין', steps: PIPE }),
      'הבנתי. פתחתי עכשיו קריאה על הנזילה (המספר שלה הוא 255-1428-26), ורשמתי אותה על הדירה שלך. יש עוד משהו שאוכל לעזור בו עכשיו?');
    expect('"וישלחו אליך בעל מקצוע" goes with its clause',
      say({ reply: 'פתחתי קריאה על הגג, מספר 255-1339-26, וישלחו אליך בעל מקצוע לבדוק. משהו השתנה מאז?', said: 'roof' }),
      'פתחתי קריאה על הגג, מספר 255-1339-26. משהו השתנה מאז?');
    const LEAK = 'לא נעים בכלל. כשמדובר בנזילה בתוך הדירה, קודם כל צריך בעל מקצוע מטעמך שיבדוק מאיפה זה מגיע. יצא לך כבר לבדוק את זה עם בעל מקצוע?';
    expect("the leak rule's own professional, with no \"sent\": byte-identical", say({ reply: LEAK, said: 'יורדים מים מהתקרה' }), LEAK);
    const CLEAN = 'לכל בניין מוצמד מנקה קבוע, ואם הוא לא יכול להגיע, נשלח מחליף באותו יום. תרצה לדעת עוד משהו על הניקיון?';
    expect('the cleaning facts\' "נשלח מחליף": byte-identical', say({ reply: CLEAN, said: 'מה כולל הועד' }), CLEAN);
  }
  if (String((P.code || {}).inject || '').indexOf('מחוץ לשעות הפעילות של המשרד') !== -1) {
    console.log(NL + '--- the inject: the clock line says when the office is closed (9 Nov) ---');
    const at = (time, weekday) => String(E.inject({ greeted: true, text: 'x', tap_now: false }, clock9(time, weekday), who$()));
    expect('Sunday 12:20: open, nothing said', () => at('12:20', 7).includes('מחוץ לשעות'), false);
    expect('Thursday 16:59: open', () => at('16:59', 4).includes('מחוץ לשעות'), false);
    expect('Thursday 17:00: closed', () => at('17:00', 4).includes('מחוץ לשעות הפעילות של המשרד'), true);
    expect('Monday 08:59: closed', () => at('08:59', 1).includes('מחוץ לשעות'), true);
    expect('Monday 09:00: open', () => at('09:00', 1).includes('מחוץ לשעות'), false);
    expect('Friday noon: closed', () => at('12:00', 5).includes('מחוץ לשעות'), true);
    expect('Saturday noon: closed', () => at('12:00', 6).includes('מחוץ לשעות'), true);
    expect('the bracket still closes and the text follows', () => at('21:10', 5).includes(', מחוץ לשעות הפעילות של המשרד.]' + NL + 'x'), true);
  }
  console.log(NL + (fails ? fails + ' of ' + n + ' FAILED' : 'all ' + n + ' cases pass'));
  return fails;
}

// ---------------------------------------------------------------------------
// The replay: every real message, live code vs candidate. Prints every
// difference; returns how many results are broken (empty, a fragment).
// ---------------------------------------------------------------------------
function replay(L, C, corpus) {
  let broken = 0;
  const inbound = corpus.inbound || [];
  const outbound = corpus.outbound || [];

  console.log('--- every message residents ever sent (' + inbound.length + '), through Sort: which get the menu ---');
  const inDiff = inbound.filter((t) => L.isGreeting(t) !== C.isGreeting(t));
  console.log('changed: ' + inDiff.length);
  for (const t of inDiff) console.log('   ' + (C.isGreeting(t) ? 'now gets the menu : ' : 'NO LONGER the menu: ') + mask(t));

  console.log(NL + "--- the same messages, through Worth a word?'s note (both conversation states) ---");
  let noteDiff = 0;
  const seen = new Set();
  for (const t of inbound) {
    for (const greeted of [true, false]) {
      const a = String(L.worth({ greeted, text: t })).split(NL)[0];
      const b = String(C.worth({ greeted, text: t })).split(NL)[0];
      if (a !== b) {
        noteDiff++;
        const k = greeted + a + b;
        if (!seen.has(k)) { seen.add(k); console.log('   ' + (greeted ? 'mid' : 'first') + ': ' + a + NL + '     -> ' + b); }
      }
    }
  }
  console.log('changed: ' + noteDiff);

  // 1 Oct evening: A word first? reads the resident's words now. Live lets any
  // short note out; the candidate only on a message with a payment word.
  console.log(NL + '--- the same messages, through A word first? with a short note in hand ---');
  const NOTE = 'רגע, אני בודק את זה עכשיו.';
  const said$ = (t) => (n) => { if (n !== 'Still the last word?') throw new Error('no node ' + n); return { first: () => ({ json: { text: t } }) }; };
  const lets = (E, t) => { try { return E.word({ output: NOTE }, said$(t)) === true; } catch (e) { return 'THREW ' + e.message; } };
  let liveLets = 0; const candLets = [];
  for (const t of inbound) {
    if (lets(L, t) === true) liveLets++;
    const c = lets(C, t);
    if (typeof c === 'string') broken++;
    if (c === true) candLets.push(t);
  }
  console.log('live lets a note out on ' + liveLets + ' of ' + inbound.length + '; the candidate on ' + candLets.length + ':');
  for (const t of candLets) console.log('   ' + mask(t));

  console.log(NL + "--- every reply the bot ever sent (" + outbound.length + "), through Send, under each row of the owner's table ---");
  const REP_STATE = 'the representative tap, right after the menu';
  let restored = 0;
  const STATES = {
    'first contact, resident greeted': { S: { greeted: false }, said: 'hi, question' },
    'first contact, no hello': { S: { greeted: false }, said: 'question' },
    'mid-conversation, resident greeted': { said: 'hi, question' },
    'mid-conversation, no hello': { said: 'question' },
    'right after the menu': { S: { last_bot: MENU_TEXT }, said: 'question' },
    'after an ack that greeted': { said: 'hi, link please', acked: 'צהריים טובים, רגע אני בודק.', ackSent: true },
    'first contact, after an ack that greeted and named': { S: { greeted: false }, said: 'hi, link please', acked: "צהריים טובים, כאן מיכאל מהומי'ז, רגע אני בודק.", ackSent: true },
    // 1 Oct evening: the one state whose rule moved (manners v3). A change here is
    // expected when it only puts back the hello the menu rule used to cut.
    [REP_STATE]: { S: { last_bot: MENU_TEXT, tap: 'other', tap_now: true }, said: 'לדבר עם נציג' },
  };
  const changed = new Map();
  // 8 Nov, later (intro v1): after the menu a reply with no name opens with it. That change, and only
  // that change, is counted here instead of listed: "כאן מיכאל מהומי'ז. " + before, or after a greeting
  // the draft kept, "היי, כאן מיכאל מהומי'ז. " + the rest of before.
  const NAMED = "כאן מיכאל מהומי'ז.";
  const AFTER_MENU = new Set(['right after the menu', REP_STATE]);
  const introduced = (a, b) => {
    if (b === NAMED + ' ' + a) return true;
    const h = String(a).match(/^(שלום רב|שלום|היי|הי|אהלן|בוקר טוב|צהריים טובים|ערב טוב|לילה טוב)(?=[\s,.!:;]|$)[\s,.!:;]*/u);
    return !!h && b === h[1] + ', ' + NAMED + ' ' + String(a).slice(h[0].length);
  };
  let named = 0;
  for (const t of outbound) {
    for (const [st, o] of Object.entries(STATES)) {
      let a;
      let b;
      try { a = content(L, Object.assign({ reply: t }, o)); } catch (e) { a = 'THREW ' + e.message; }
      try { b = content(C, Object.assign({ reply: t }, o)); } catch (e) { b = 'THREW ' + e.message; broken++; }
      if (a !== b) {
        const words = String(b).trim().split(/\s+/).filter(Boolean).length;
        const bad = words < 2 || /^(גם|ו[א-ת])/.test(String(b).trim());
        if (bad) broken++;
        if (AFTER_MENU.has(st) && !bad && introduced(a, b)) {
          named++;
          continue;
        }
        if (st === REP_STATE && !bad && String(b).length > String(a).length && String(b).endsWith(String(a))) {
          restored++;
          continue;
        }
        if (!changed.has(t)) changed.set(t, []);
        changed.get(t).push({ st, a, b, bad });
      }
    }
  }
  console.log('[' + REP_STATE + '] ' + restored + ' replies keep the hello the menu rule used to cut '
    + '(after = that hello + before; any other change there is listed below)');
  if (named) console.log('[after the menu] ' + named + ' replies open with "' + NAMED + '" (after = that name + before; '
    + 'any other change there is listed below)');
  console.log('replies that change in at least one state: ' + changed.size);
  for (const [t, rows] of changed) {
    console.log('   reply : ' + mask(t));
    for (const x of rows) console.log('     ' + (x.bad ? 'BROKEN ' : '') + '[' + x.st + ']' + NL + '       before: ' + mask(x.a) + NL + '       after : ' + mask(x.b));
  }

  // 5 Oct (scripts/n8n_whatsapp_safetynet.py): the truth guards over every reply
  // the bot ever sent, first pass, no tool this turn, and the reply's own numbers
  // already in the chat -- so any change is the negation and question reading,
  // or a ticket quoted from earlier. A reply only one side lets through is listed.
  console.log(NL + "--- the same replies, through Reply usable?'s phantom and deeds (no tool this turn, its numbers already in the chat) ---");
  const ctx = (t) => (name) => {
    if (name === 'Anything newer?') return { all: () => [{ json: { direction: 'outbound', body: t } }] };
    throw new Error('no node ' + name);
  };
  let guardDiff = 0;
  for (const t of outbound) {
    for (const id of ['phantom', 'deeds']) {
      if (!L.reply[id] || !C.reply[id]) continue;
      let a; let b;
      try { a = L.reply[id]({ output: t, intermediateSteps: [] }, 0, ctx(t)); } catch (e) { a = 'THREW ' + e.message; }
      try { b = C.reply[id]({ output: t, intermediateSteps: [] }, 0, ctx(t)); } catch (e) { b = 'THREW ' + e.message; broken++; }
      if (a !== b) {
        guardDiff++;
        console.log('   ' + id + ': ' + (a === true ? 'passed' : 'blocked') + ' -> ' + (b === true ? 'passes' : 'blocked') + ' : ' + mask(t));
      }
    }
  }
  console.log('changed: ' + guardDiff);
  console.log(NL + (broken ? broken + ' BROKEN results' : 'nothing broken: no empty result, no fragment'));
  return broken;
}

let rc = 0;
if (P.mode === 'replay') {
  rc = replay(build(P.live), build(P.cand), P.corpus || {}) ? 1 : 0;
} else {
  rc = cases(build(P.code)) ? 1 : 0;
}
process.exit(rc);
