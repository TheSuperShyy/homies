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
const MENU_TEXT = 'צהריים טובים 👋 במה אפשר לעזור?';

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
    outage: map(X.outage_gate, ['$json', '$runIndex', '$']),
    worth: compile(['$json'], 'return (' + X.worth_text + ');', 'Worth a word?'),
    word: compile(['$json'], 'return (' + X.word_gate + ');', 'A word first?'),
    inject: compile(['$json', '$now'], 'return (' + X.inject + ');', 'the inject'),
    tryAgain: compile(['$json', '$'], 'return (' + X.try_again + ');', 'Try again'),
  };
}

// One mocked turn, the way n8n hands Send its world. `ackSent` false means
// `Say it now` did not run, and n8n throws on an unexecuted node.
function turn(o) {
  const S = Object.assign({ greeting: !!o.canned, greeted: true, last_bot: '', text: o.said || '', tap_now: false }, o.S || {});
  const nodes = {
    'Sort': { first: () => ({ json: S }) },
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
  expect('27 Sep 15:05: the two promise sentences go, the ticket stays',
    say({ reply: 'מבאס, אבל אל דאגה, אני מטפל בזה. פתחתי לכם קריאת שירות מספר 255-1339-26. הצוות שלנו יטפל בזה בהקדם. במה אוכל לעזור עוד?', said: 'Bar Kochba 23, apartment 4' }),
    'פתחתי לכם קריאת שירות מספר 255-1339-26. במה אוכל לעזור עוד?');
  expect('27 Sep 14:52, first contact: "אל דאגה," goes, the rest of its sentence stays',
    say({ reply: "היי! כאן מיכאל מהומי'ז. אני מבין, זה ממש לא נעים ללכת במדרגות ככה. אל דאגה, אני אפתח קריאת שירות כדי שיטפלו בתאורה. באיזה בניין אתם גרים ובאיזו דירה?", S: { greeted: false }, said: 'hi, lights' }),
    "היי! כאן מיכאל מהומי'ז. אני מבין, זה ממש לא נעים ללכת במדרגות ככה. אני אפתח קריאת שירות כדי שיטפלו בתאורה. באיזה בניין אתם גרים ובאיזו דירה?");
  expect('the only sentence: the promise clause goes, the sentence stays',
    say({ reply: 'אני מעביר את זה לצוות, נחזור בהקדם.', said: 'question' }), 'אני מעביר את זה לצוות.');
  expect('a comma clause goes',
    say({ reply: 'העברתי את הפנייה שלכם לצוות שלנו, שיחזור אליכם בהקדם.', said: 'question' }), 'העברתי את הפנייה שלכם לצוות שלנו.');
  expect('a ticket number in the sentence: cut from the ו, the number stays',
    say({ reply: 'פתחתי קריאה מספר 255-1-26 והצוות יטפל בזה בהקדם.', said: 'question' }), 'פתחתי קריאה מספר 255-1-26.');
  expect('a ticket number is never cut away: no clean cut, so the sentence stays whole',
    say({ reply: 'פתחתי לכם קריאה 255-1339-26 שהצוות יטפל בה בהקדם.', said: 'question' }), 'פתחתי לכם קריאה 255-1339-26 שהצוות יטפל בה בהקדם.');
  expect('an emergency pass-on stays true: its promise and "עזרה בדרך" go',
    say({ reply: 'בבקשה אל תנסו לפתוח את הדלת בכוח! זה מסוכן מאוד ויכול לגרום לפציעה. אני מעביר את הפנייה הזו מיד לצוות שלנו שיטפל בזה, והם יצרו איתכם קשר בהקדם. בינתיים, נסו להישאר רגועים. עזרה בדרך.', said: 'help' }),
    'בבקשה אל תנסו לפתוח את הדלת בכוח! זה מסוכן מאוד ויכול לגרום לפציעה. אני מעביר את הפנייה הזו מיד לצוות שלנו. בינתיים, נסו להישאר רגועים.');
  expect('an offer keeps its question',
    say({ reply: 'אני מצטער לשמוע שאתם לא מרוצים מהשירות. אני רוצה לוודא שאני מבין אתכם נכון, האם תרצו שאעביר את הפנייה שלכם לנציג מהצוות שלנו שיחזור אליכם?', said: 'question' }),
    'אני מצטער לשמוע שאתם לא מרוצים מהשירות. אני רוצה לוודא שאני מבין אתכם נכון, האם תרצו שאעביר את הפנייה שלכם לנציג מהצוות שלנו?');
  expect('a step back to an earlier boundary: never "וביקשתי."',
    say({ reply: 'העברתי את פנייתכם לצוות הרלוונטי וביקשתי שיחזרו אליכם בהקדם. במה עוד אפשר לעזור?', said: 'question' }),
    'העברתי את פנייתכם לצוות הרלוונטי. במה עוד אפשר לעזור?');
  expect('no clean cut: the sentence goes whole, never "ברגע שאפתח קריאה."',
    say({ reply: 'אני מבין שאתם רוצים שהתקלה תתוקן מיד. פתיחת קריאת שירות היא הדרך שלנו לטפל בתקלות כאלה ולהבטיח שהן יטופלו. ברגע שאפתח קריאה, הצוות שלנו יטפל בזה בהקדם. באיזה בניין מדובר?', said: 'question' }),
    'אני מבין שאתם רוצים שהתקלה תתוקן מיד. פתיחת קריאת שירות היא הדרך שלנו לטפל בתקלות כאלה ולהבטיח שהן יטופלו. באיזה בניין מדובר?');
  expect('never "כדי." at the end of a cut',
    say({ reply: 'אני לא יכול לראות אם בוצעה הדברה ספציפית בבניין. אם יש לכם מזיקים בדירה, אני יכול לפתוח קריאת שירות כדי שנטפל בזה. תרצו שאפתח קריאה?', said: 'question' }),
    'אני לא יכול לראות אם בוצעה הדברה ספציפית בבניין. תרצו שאפתח קריאה?');
  expect('a comma inside a number is not a boundary',
    say({ reply: 'היתרה שלכם 1,240 שקלים יטופלו בקרוב.', said: 'question' }), 'היתרה שלכם 1,240 שקלים יטופלו בקרוב.');
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
    say({ reply: 'אל דאגה, נחזור אליכם בהקדם.', said: 'question' }), 'אל דאגה, נחזור אליכם בהקדם.');
  expect('a newline is a sentence boundary',
    say({ reply: 'פתחתי לכם קריאה מספר 255-1339-26' + NL + 'הצוות יטפל בזה בהקדם' + NL + 'יש עוד משהו?', said: 'question' }),
    'פתחתי לכם קריאה מספר 255-1339-26' + NL + 'יש עוד משהו?');
  expect('an emoji stays with its sentence',
    say({ reply: 'פתחתי קריאה 255-1339-26. 🙂 הצוות יטפל בזה בהקדם. במה עוד?', said: 'question' }), 'פתחתי קריאה 255-1339-26. 🙂 במה עוד?');
  expect('a promise glued to an emoji goes with it',
    say({ reply: 'פתחתי קריאה 255-1339-26. הצוות יטפל בזה בהקדם🙂 במה עוד?', said: 'question' }), 'פתחתי קריאה 255-1339-26. במה עוד?');
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
  expect('a conditional whose main clause is the promise goes whole, never a dangling "אם…"',
    say({ reply: 'חשוב לי לציין שאם התקלה בתוך הדירה, הטיפול הוא באחריותכם. אם מדובר בתקלה ברכוש המשותף, כמו בחשמל הכללי של הבניין, נטפל בזה כמובן. במה עוד אוכל לעזור?', said: 'question' }),
    'חשוב לי לציין שאם התקלה בתוך הדירה, הטיפול הוא באחריותכם. במה עוד אוכל לעזור?');
  expect('a step back past "ולדאוג": the main clause stays',
    say({ reply: 'ברגע שאקבל את הפרטים, אוכל לפתוח קריאת שירות דחופה ולדאוג שיגיעו אליכם מהר ככל האפשר. באיזה בניין מדובר?', said: 'question' }),
    'ברגע שאקבל את הפרטים, אוכל לפתוח קריאת שירות דחופה. באיזה בניין מדובר?');
  expect('a technician time is an invented promise and goes',
    say({ reply: 'פתחתי לכם קריאה 255-1339-26. הטכנאי יגיע מחר בבוקר. יש עוד משהו?', said: 'question' }),
    'פתחתי לכם קריאה 255-1339-26. יש עוד משהו?');

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

  console.log(NL + '--- Second try usable?: deeds (the rescue) ---');
  const r = (output) => () => E.second.deeds({ output }, 0, turn({}).$);
  expect('a stub ticket with its number', r('פתחתי לכם קריאה מספר 255-1330-26 על התאורה בחדר המדרגות. במה עוד אפשר לעזור?'), true);
  expect('handled + opened, with a number', r('טיפלתי בזה ופתחתי קריאה 255-1330-26.'), true);
  expect('checked + opened, with a number', r('בדקתי ופתחתי קריאה 255-1330-26.'), false);
  expect('opened, NO number', r('פתחתי לכם קריאה על התאורה.'), false);
  expect('the invented repair', r(BULBS), false);
  expect('a plain honest line', r('ההודעה שלכם לא יצאה כמו שצריך, אפשר לכתוב לי שוב מה קרה?'), true);

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
  const w = (output) => () => E.word({ output });
  expect('NONE stays silent', w('NONE'), false);
  expect('"none" stays silent', w('none'), false);
  expect('empty stays silent', w(''), false);
  expect('a runaway stays silent', w('x'.repeat(330)), false);
  expect('a link never goes out early', w('רגע, בודק https://x.example'), false);
  expect('a short line goes out', w('רגע, אני בודק את זה עכשיו.'), true);

  console.log(NL + '--- Try again: the rewrite names what was wrong (27 Sep, execution 65856) ---');
  const still = { first: () => ({ json: { text: 'hi, the stair lights flicker', greeted: true } }) };
  const $t = (name) => { if (name === 'Still the last word?') return still; throw new Error('no node ' + name); };
  const why = (output) => JSON.parse(E.tryAgain({ output }, $t)).retry_note;
  const REJ = "צהריים טובים! אני מיכאל מהומי'ז. אני מבין שיש לכם בעיה עם התאורה בחדר המדרגות בבניין, וזה מקשה עליכם לעלות במדרגות. אני אטפל בזה. באיזה בניין מדובר ומה מספר הדירה שלכם?";
  expect('65856: the echo is named, not a list of eight', () => why(REJ).includes('נפתחה בזה שהבנת אותו') && !why(REJ).includes('או שנתנה קישור'), true);
  expect('the clerk is named', () => why('כדי שאוכל לפתוח קריאה, אצטרך את הבניין.').includes('הסבירה לו למה אתה צריך פרט'), true);
  expect('both are named', () => { const w = why('אני מבין שיש נזילה. כדי שאוכל לעזור אצטרך את הדירה.'); return w.includes('נפתחה בזה שהבנת') && w.includes('וגם היא הסבירה'); }, true);
  expect('any other reason keeps the full list', () => why('החלפתי את הנורה.').includes('או שנתנה קישור'), true);
  expect('the tools line is always there', () => why(REJ).includes('open_request') && why('x').includes('open_request'), true);
  expect('no output at all: the full list, never a throw', () => why(undefined).startsWith('[התשובה הקודמת'), true);
  expect("the resident's turn is carried through", () => JSON.parse(E.tryAgain({ output: REJ }, $t)).text, 'hi, the stair lights flicker');

  console.log(NL + '--- the inject: facts the answering model is handed ---');
  const now = { setZone: () => ({ toFormat: () => '12:20', weekday: 7 }) };
  const inj = (greeted, text) => () => String(E.inject({ greeted, text, tap_now: false }, now));
  expect('mid-conversation + "hi, …" gets the fact', () => inj(true, 'hi, so i want to let you know')().includes('הדייר פתח את ההודעה הזאת בברכה'), true);
  expect('mid-conversation + no hello: no fact', () => inj(true, 'the elevator is stuck')().includes('הדייר פתח'), false);
  expect('first message: no fact', () => inj(false, 'hi, lights')().includes('הדייר פתח'), false);
  expect('"מה קורה עם הקריאה" is not a greeting', () => inj(true, 'מה קורה עם הקריאה שלי?')().includes('הדייר פתח'), false);
  expect('the false "you introduced yourself" stays gone', () => inj(true, 'x')().includes('והצגת את עצמך'), false);

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

  console.log(NL + "--- every reply the bot ever sent (" + outbound.length + "), through Send, under each row of the owner's table ---");
  const STATES = {
    'first contact, resident greeted': { S: { greeted: false }, said: 'hi, question' },
    'first contact, no hello': { S: { greeted: false }, said: 'question' },
    'mid-conversation, resident greeted': { said: 'hi, question' },
    'mid-conversation, no hello': { said: 'question' },
    'right after the menu': { S: { last_bot: MENU_TEXT }, said: 'question' },
    'after an ack that greeted': { said: 'hi, link please', acked: 'צהריים טובים, רגע אני בודק.', ackSent: true },
    'first contact, after an ack that greeted and named': { S: { greeted: false }, said: 'hi, link please', acked: "צהריים טובים, כאן מיכאל מהומי'ז, רגע אני בודק.", ackSent: true },
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
        if (!changed.has(t)) changed.set(t, []);
        changed.get(t).push({ st, a, b, bad });
      }
    }
  }
  console.log('replies that change in at least one state: ' + changed.size);
  for (const [t, rows] of changed) {
    console.log('   reply : ' + mask(t));
    for (const x of rows) console.log('     ' + (x.bad ? 'BROKEN ' : '') + '[' + x.st + ']' + NL + '       before: ' + mask(x.a) + NL + '       after : ' + mask(x.b));
  }
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
