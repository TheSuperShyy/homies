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
    send: compile(['$json', '$'], 'return (' + X.send_body + ');', 'Send'),
    reply: map(X.reply_usable, ['$json', '$runIndex', '$']),
    second: map(X.second_try, ['$json', '$runIndex', '$']),
    // 5 Oct: the last resort without a model (scripts/n8n_whatsapp_safetynet.py).
    claimed: map(X.claimed, ['$json', '$runIndex', '$']),
    mend: X.mend ? compile(['$json', '$'], 'return (' + X.mend + ');', 'Mend the reply') : null,
    outage: map(X.outage_gate, ['$json', '$runIndex', '$']),
    worth: compile(['$json'], 'return (' + X.worth_text + ');', 'Worth a word?'),
    word: compile(['$json', '$'], 'return (' + X.word_gate + ');', 'A word first?'),
    carry: compile(['$json', '$'], 'return (' + X.carry_on + ');', 'Carry on'),
    inject: compile(['$json', '$now'], 'return (' + X.inject + ');', 'the inject'),
    tryAgain: compile(['$json', '$'], 'return (' + X.try_again + ');', 'Try again'),
    teamNote: compile(['$json', '$'], 'return (' + X.team_note + ');', 'Team note this turn?'),
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
  return { $json: o.canned ? { text: o.reply } : { output: o.reply }, $ };
}
const sent = (E, o) => { const m = turn(o); return JSON.parse(E.send(m.$json, m.$)); };
const content = (E, o) => sent(E, o).content;

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
    'מבאס, אבל אל דאגה. פתחתי לכם קריאת שירות מספר 255-1339-26. הצוות שלנו יטפל בזה. במה אוכל לעזור עוד?');
  const DONT_WORRY = "היי! כאן מיכאל מהומי'ז. אני מבין, זה ממש לא נעים ללכת במדרגות ככה. אל דאגה, אני אפתח קריאת שירות כדי שיטפלו בתאורה. באיזה בניין אתם גרים ובאיזו דירה?";
  expect('27 Sep 14:52, first contact (v3): "אל דאגה," is reassurance and stays',
    say({ reply: DONT_WORRY, S: { greeted: false }, said: 'hi, lights' }), DONT_WORRY);
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
  same('v3: a note to the team, reported, stays ("רשמתי לצוות שלנו שיחזרו אליך")',
    'בטח, רשמתי לצוות שלנו שיחזרו אליך דחוף. יש עוד משהו?');
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
  // Not "never only anything else?": the filter can only remove, so that would
  // mean sending the promise, and an all-promise reply can be an invented one.
  expect('v3: a reply that is all promise still loses it, even down to "anything else?"',
    say({ reply: 'הם יחזרו אליך בהקדם. במה אוכל לעזור לך עוד?', said: 'when?' }), 'במה אוכל לעזור לך עוד?');
  // The 37 live replies (scripts/wa_promise_live_05oct.json): raw draft in, v3 out.
  for (const k of P.promise_live || []) {
    expect('5 Oct live #' + k.n + ' (' + k.case + ')', say({ reply: k.raw, said: k.said }), k.want);
  }

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
    expect('the first word of an emergency: "right away" goes, the question for the address stays',
      say({ reply: 'אוי ואבוי! זה נשמע מסוכן מאוד! אני מעביר את זה לצוות החירום שלנו באופן מיידי. באיזה בניין מדובר?',
        said: 'יש מים שנוזלים מהתקרה בחדר מדרגות ישר על המנורה!!! מה עושים??', steps: ALERT }),
      'אוי ואבוי! זה נשמע מסוכן מאוד! באיזה בניין מדובר?');
    expect('the ticket opened: "on the way" and every instruction go, the ticket and its number stay',
      say({ reply: 'הבנתי, תודה! פתחתי קריאת חירום עבורך, מספר הקריאה הוא 255-1349-26. הצוות שלנו כבר בדרך לטפל בזה. לגבי כיבוי חשמל - '
        + 'אל תנסה לגעת בשום דבר שקשור לחשמל או למים בעצמך. בבקשה תתרחק מהאזור הרטוב. הבטיחות שלך היא הכי חשובה עכשיו. אני כאן לכל עדכון.',
        said: 'בר כוכבא 23. מה אני עושה בינתיים, לכבות חשמל??', steps: URGENT }), OPENED_LINE);
    expect('pushed for a number to call: only the ticket line',
      say({ reply: 'אין לי מספר לתת לך להתקשר אליו ישירות, אבל הצוות עודכן ומטפל בזה. בבקשה תמשיך להישאר רחוק מהאזור המסוכן.',
        said: 'יש מספר של מישהו שאני יכול להתקשר אליו עכשיו?', S: { last_bot: OPENED_LINE } }), PUSHED);
    expect('pushed about an electrician: the promise goes, the ticket line comes',
      say({ reply: 'אני מבין את התסכול שלך, אסף. הצוות שלנו בדרך. אין צורך להזמין חשמלאי בעצמך, הומי\'ז מטפלת בזה.',
        said: 'אז מה, להזמין חשמלאי לבד או שאתם שולחים מישהו?', S: { last_bot: PUSHED } }),
      'אני מבין את התסכול שלך, אסף. ' + PUSHED);
    expect('a goodbye in an emergency: the wish that they come soon goes, the ticket is named',
      say({ reply: 'בכיף, אסף. תודה רבה על הסבלנות. אני מקווה שהצוות יגיע במהרה.', said: 'טוב, תודה. אני מחכה להם למטה',
        S: { last_bot: PUSHED } }), 'בכיף, אסף. תודה רבה על הסבלנות. הקריאה הדחופה שלך פתוחה, מספר 255-1349-26.');
    const HONEST = 'אין לי תאריך מדויק מתי יגיעו, אבל הקריאה הדחופה שלך פתוחה, מספר 255-1349-26.';
    expect('"I don\'t know when they will come" stays whole', say({ reply: HONEST, said: 'מתי הם מגיעים?', S: { last_bot: PUSHED } }), HONEST);
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
  const inj = (greeted, text) => () => String(E.inject({ greeted, text, tap_now: false }, now));
  expect('mid-conversation + "hi, …" gets the fact', () => inj(true, 'hi, so i want to let you know')().includes('הדייר פתח את ההודעה הזאת בברכה'), true);
  expect('mid-conversation + no hello: no fact', () => inj(true, 'the elevator is stuck')().includes('הדייר פתח'), false);
  expect('first message: no fact', () => inj(false, 'hi, lights')().includes('הדייר פתח'), false);
  expect('"מה קורה עם הקריאה" is not a greeting', () => inj(true, 'מה קורה עם הקריאה שלי?')().includes('הדייר פתח'), false);
  expect('the false "you introduced yourself" stays gone', () => inj(true, 'x')().includes('והצגת את עצמך'), false);

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
  expect('menu rule: the bare singular opener with the name, first contact, gets the buttons',
    () => sent(E, { reply: "היי, כאן מיכאל מהומי'ז. במה אוכל לעזור לך היום?", S: { greeted: false }, said: 'hi' }).content_type, 'input_select');


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
