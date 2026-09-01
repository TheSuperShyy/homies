import { cookies } from 'next/headers';

/**
 * Two languages, one dashboard.
 *
 * The staff who read this are Hebrew speakers and the data in it — building
 * names, descriptions, resident names — has always been Hebrew. Only the chrome
 * was English, so every page was already mixed script with the layout running
 * the wrong way. Hebrew is therefore the default; English stays because the
 * people building it read English, and a bug report is easier to write in the
 * language the code is in.
 *
 * WHY A COOKIE AND NOT A URL PARAM. Everything else on this dashboard puts its
 * state in the URL on purpose — a filtered view should be a link you can send a
 * colleague. Language is the exception: it belongs to the reader, not to the
 * view. Carrying `?lang=` on every link would double the size of every href
 * builder on every page, and sending somebody a filtered list of tickets would
 * also silently change their interface language.
 */
export type Locale = 'he' | 'en';

export const LOCALES: Locale[] = ['he', 'en'];
export const COOKIE = 'homies_lang';

export function getLocale(): Locale {
  const v = cookies().get(COOKIE)?.value;
  return v === 'en' ? 'en' : 'he';
}

export const dir = (l: Locale) => (l === 'he' ? 'rtl' : 'ltr');

/**
 * Theme, read the same way language is: a cookie, on the server, before a byte
 * of HTML is written.
 *
 * The design system's default is dark and this follows it, so `undefined` means
 * dark. Doing it server-side rather than with a script in the head is what
 * stops the flash — there is no moment where the page is one theme and then
 * becomes the other, because the `data-theme` attribute is already in the
 * markup that arrives. The cost is that the choice cannot follow the operating
 * system automatically; the system's own contract is an explicit dark default
 * plus a switch, so that is what this is.
 */
export type Theme = 'dark' | 'light';
export const THEME_COOKIE = 'homies_theme';

export function getTheme(): Theme {
  return cookies().get(THEME_COOKIE)?.value === 'light' ? 'light' : 'dark';
}

/** Locale-aware dates. Hebrew staff read day-first; the ISO slice did not. */
export function when(iso: string | null | undefined, l: Locale) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return new Intl.DateTimeFormat(l === 'he' ? 'he-IL' : 'en-GB', {
    timeZone: 'Asia/Jerusalem',
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(d);
}

type Entry = { he: string; en: string };

/**
 * Flat keys, not nested. A nested tree reads better in the file and worse at
 * the call site, where `t('debts.cards.inReview')` and a typo in the middle
 * segment fail the same silent way. Flat keys are one lookup and TypeScript
 * catches an unknown one.
 */
const S = {
  // --- chrome -------------------------------------------------------------
  'app.name':          { he: 'הומיז',            en: 'Homies' },
  'app.subtitle':      { he: 'ניהול בניינים',    en: 'Building management' },
  'nav.overview':      { he: 'סקירה',            en: 'Overview' },
  'nav.tickets':       { he: 'קריאות',           en: 'Tickets' },
  'nav.debts':         { he: 'חובות',            en: 'Debts' },
  'nav.conversations': { he: 'שיחות ווטסאפ',     en: 'Conversations' },
  'nav.calls':         { he: 'שיחות טלפון',      en: 'Calls' },
  'nav.sync':          { he: 'ייבוא',            en: 'Import' },
  'nav.settings':      { he: 'הגדרות',           en: 'Settings' },
  'nav.signOut':       { he: 'יציאה',            en: 'Sign out' },
  'nav.menu':          { he: 'תפריט',            en: 'Menu' },
  'nav.tabs':          { he: 'ניווט ראשי',       en: 'Main navigation' },
  // The sidebar has 200px for a label and the tab bar has 78. "Conversations"
  // and "שיחות ווטסאפ" both run off the end of a tab, and a truncated label is
  // worse than a short one — it looks like a broken layout rather than a name.
  // These are the names the same destinations go by when there is no room.
  'tab.overview':      { he: 'סקירה',            en: 'Overview' },
  'tab.tickets':       { he: 'קריאות',           en: 'Tickets' },
  'tab.debts':         { he: 'חובות',            en: 'Debts' },
  'tab.conversations': { he: 'ווטסאפ',           en: 'Chats' },
  'tab.calls':         { he: 'טלפון',            en: 'Calls' },
  'lang.switch':       { he: 'English',          en: 'עברית' },
  'lang.switchLabel':  { he: 'Switch to English', en: 'החלף לעברית' },

  // --- topbar and rail chrome ---------------------------------------------
  // The design system groups its sidebar under uppercase micro-labels. Hebrew
  // has no case, so "MAIN MENU" cannot be shouted the way English can — the
  // uppercase transform simply does nothing to Hebrew letters. The label still
  // earns its place as a grouping line at the same size and tracking; it just
  // reads as small muted text rather than as small muted capitals, which is
  // what Hebrew typography does in that position anyway.
  'nav.group.main':    { he: 'תפריט ראשי',      en: 'Main menu' },
  'nav.group.support': { he: 'מערכת',           en: 'System' },
  'chrome.greeting':   { he: 'שלום',            en: 'Welcome' },
  'chrome.greetingSub':{ he: 'זה מה שקורה היום בבניינים', en: "Here's what is happening across the buildings" },
  'chrome.search':     { he: 'חיפוש בכל המערכת', en: 'Search everything' },
  'chrome.settings':   { he: 'הגדרות',          en: 'Settings' },
  'chrome.staff':      { he: 'צוות',            en: 'Staff' },
  'theme.dark':        { he: 'כהה',             en: 'Dark' },
  'theme.light':       { he: 'בהיר',            en: 'Light' },
  'theme.switchLabel': { he: 'מעבר לתצוגה בהירה או כהה', en: 'Switch between light and dark' },
  'load.loading':      { he: 'טוען…',           en: 'Loading…' },
  'overview.seeAll':   { he: 'לכל הקריאות',     en: 'See all' },

  // --- overview charts ----------------------------------------------------
  'chart.activity':    { he: 'פעילות השבוע',      en: 'This week' },
  'chart.tickets':     { he: 'קריאות שנפתחו',     en: 'Tickets opened' },
  'chart.calls':       { he: 'שיחות של הסוכן',    en: 'Agent calls' },
  'chart.links':       { he: 'לינקים לתשלום',     en: 'Payment links' },
  'chart.events':      { he: 'פעולות',            en: 'events' },
  'chart.perDay':      { he: 'קריאות שנפתחו, לפי יום', en: 'Tickets opened, by day' },
  'chart.vsPrev':      { he: 'מול התקופה הקודמת', en: 'vs the period before' },
  'chart.noneInRange': { he: 'אין נתונים בטווח הזה.', en: 'Nothing in this range.' },
  'range.d7':          { he: '7 ימים',           en: '7 days' },
  'range.d30':         { he: '30 יום',           en: '30 days' },
  'range.d90':         { he: '90 יום',           en: '90 days' },
  'range.from':        { he: 'מתאריך',           en: 'From' },
  'range.to':          { he: 'עד תאריך',         en: 'To' },
  'range.apply':       { he: 'הצג',              en: 'Apply' },
  'range.custom':      { he: 'טווח תאריכים',     en: 'Date range' },
  'chart.nothingYet':  { he: 'טרם נשלח',          en: 'none yet' },
  'chart.noActivity':  { he: 'לא נרשמה פעילות בשבוע האחרון.', en: 'No activity in the last seven days.' },
  // Said once, under the chart, because a zero segment with no explanation
  // reads as a broken chart rather than as a feature that is not wired up.
  'chart.linksNote':   { he: 'הסוכן יודע ליצור לינק לתשלום, אבל עדיין אין מי שישלח אותו — לכן המספר אפס.',
                         en: 'The agent can raise a payment link, but nothing delivers it yet — which is why that number is zero.' },

  // --- shared column headings --------------------------------------------
  'col.reference':  { he: 'מספר קריאה', en: 'Reference' },
  'col.what':       { he: 'מה',          en: 'What' },
  'col.where':      { he: 'איפה',        en: 'Where' },
  'col.caller':     { he: 'טלפון הפונה', en: 'Caller' },
  'col.type':       { he: 'סוג',         en: 'Type' },
  'col.urgency':    { he: 'דחיפות',      en: 'Urgency' },
  'col.status':     { he: 'סטטוס',       en: 'Status' },
  'col.via':        { he: 'הגיע דרך',    en: 'Via' },
  'col.opened':     { he: 'נפתחה',       en: 'Opened' },
  'col.when':       { he: 'מתי',         en: 'When' },
  'col.resident':   { he: 'דייר',        en: 'Resident' },
  'col.phone':      { he: 'טלפון',       en: 'Phone' },
  'col.building':   { he: 'בניין',       en: 'Building' },
  'col.unit':       { he: 'דירה',        en: 'Unit' },
  'col.amount':     { he: 'סכום',        en: 'Amount' },
  'col.period':     { he: 'תקופה',       en: 'Period' },
  'col.summary':    { he: 'תקציר',       en: 'Summary' },
  'col.outcome':    { he: 'תוצאה',       en: 'Outcome' },
  'col.length':     { he: 'אורך',        en: 'Length' },
  'col.latency':    { he: 'זמן תגובה',   en: 'Latency' },
  'col.direction':  { he: 'כיוון',       en: 'Direction' },
  'col.number':     { he: 'מספר',        en: 'Number' },
  'col.attempt':    { he: 'ניסיון',      en: 'Attempt' },

  // --- statuses, shown as words not codes ---------------------------------
  'status.open':        { he: 'פתוחה',    en: 'Open' },
  'status.in_progress': { he: 'בטיפול',   en: 'In progress' },
  'status.resolved':    { he: 'נסגרה',    en: 'Resolved' },
  'status.cancelled':   { he: 'בוטלה',    en: 'Cancelled' },
  'status.needs_review':{ he: 'לבדיקה',   en: 'Needs review' },
  'status.all':         { he: 'הכול',     en: 'All' },

  'urgency.low':       { he: 'נמוכה',   en: 'Low' },
  'urgency.normal':    { he: 'רגילה',   en: 'Normal' },
  'urgency.high':      { he: 'גבוהה',   en: 'High' },
  'urgency.emergency': { he: 'חירום',   en: 'Emergency' },

  // --- overview -----------------------------------------------------------
  'overview.title':      { he: 'סקירה',                en: 'Overview' },
  'overview.openTickets':{ he: 'קריאות פתוחות',        en: 'Open tickets' },
  'overview.urgent':     { he: 'דחופות ופתוחות',       en: 'Urgent, open' },
  'overview.allTickets': { he: 'קריאות, מאז ומתמיד',   en: 'Tickets, all time' },
  'overview.convos':     { he: 'שיחות ווטסאפ',         en: 'Conversations' },
  'overview.calls':      { he: 'שיחות טלפון שתועדו',   en: 'Calls recorded' },
  'overview.last7':      { he: 'שבעת הימים האחרונים',  en: 'Last 7 days' },
  'overview.empty':      { he: 'שום דבר בשבעת הימים האחרונים.', en: 'Nothing in the last 7 days.' },

  // --- tickets ------------------------------------------------------------
  'tickets.title':      { he: 'קריאות',   en: 'Tickets' },
  'tickets.save':       { he: 'שמירה',    en: 'Save' },
  'tickets.empty':      { he: 'אין קריאות.', en: 'No tickets.' },
  'tickets.emptyStatus':{ he: 'אין קריאות בסטטוס {status}.', en: 'No tickets with status {status}.' },
  'tickets.unit':       { he: 'קריאות',   en: 'tickets' },
  // Not "gone" any more — a departure is a closure and the sync writes it as
  // one. This fires only on a ticket still open our side that OXS is not
  // serving, which means the importer could not reconcile that row.
  // Fires only when the LAST IMPORT looked and did not find it — not on a
  // clock. No {ago}: the age belongs to the importer, not to the ticket,
  // and /sync is where importer lag is reported.
  'tickets.notInOxs':   { he: 'לא נמצאה ב-OXS בייבוא האחרון', en: 'not found in OXS at the last import' },
  'tickets.lastSeen':   { he: 'נראתה לאחרונה ב-OXS ב-{when}', en: 'Last seen in OXS {when}' },
  'tickets.earlier':    { he: '+{n} קודמות', en: '+{n} earlier' },

  // --- debts --------------------------------------------------------------
  'debts.title':        { he: 'יתרות פתוחות',   en: 'Open balances' },
  'debts.byApartment':  { he: 'לפי דירה',       en: 'By apartment' },
  'debts.byOwner':      { he: 'לפי בעלים',      en: 'By owner' },
  'debts.headApartment':{ he: 'לפי דירה, מהגבוה לנמוך',  en: 'By apartment, largest first' },
  'debts.headOwner':    { he: 'לפי דייר, מהגבוה לנמוך',  en: 'By resident, largest first' },
  'debts.totalOpen':    { he: 'סך הפתוח',       en: 'Total open' },
  'debts.openIn':       { he: 'פתוח ב-{month}', en: 'Open in {month}' },
  'debts.apartments':   { he: 'דירות שחייבות',  en: 'Apartments owing' },
  'debts.residents':    { he: 'דיירים שחייבים', en: 'Residents owing' },
  'debts.inReview':     { he: 'בבדיקה',         en: 'In review' },
  'debts.monthsOwed':   { he: 'חודשים שחייבים', en: 'Months owed' },
  'debts.owed':         { he: 'חוב',            en: 'Owed' },
  'debts.owedIn':       { he: 'חוב ({month})',  en: 'Owed ({month})' },
  'debts.colApartment': { he: 'דירה',           en: 'Apartment' },
  'debts.colApartments':{ he: 'דירות',          en: 'Apartments' },
  'debts.call':         { he: 'חיוג',           en: 'Call' },
  'debts.callBtn':      { he: 'חייג',           en: 'Call' },
  'debts.pin':          { he: 'קוד',            en: 'PIN' },
  'debts.noNumber':     { he: 'אין עדיין מספר', en: 'no number yet' },
  'debts.alsoApt':      { he: 'וגם דירה {units} · {total} בסך הכול', en: 'also apt {units} · {total} total' },
  'debts.emptyAll':     { he: 'אף אחד לא חייב כלום.', en: 'Nobody owes anything.' },
  'debts.emptyMonth':   { he: 'אף אחד לא חייב עבור {month}.', en: 'Nobody owes for {month}.' },
  'debts.calling':      { he: 'מחייג ל-{phone} עכשיו, שיחה {id}. היא תופיע תחת שיחות טלפון כשתסתיים.',
                          en: 'Calling {phone} now — call {id}. It will appear under Calls when it ends.' },
  'debts.notCalled':    { he: 'לא חייג ל-{phone}: {why}', en: 'Did not call {phone}: {why}' },
  'debts.unitAp':       { he: 'דירות',  en: 'apartments' },
  'debts.unitRes':      { he: 'דיירים', en: 'residents' },
  'debts.disputed':     { he: 'במחלוקת', en: 'disputed' },
  'debts.pending':      { he: 'ממתין',   en: 'pending' },

  // --- conversations ------------------------------------------------------
  'convos.title':   { he: 'שיחות ווטסאפ',    en: 'Conversations' },
  'convos.who':     { he: 'מי',              en: 'Who' },
  'convos.last':    { he: 'הודעה אחרונה',    en: 'Last message' },
  'convos.count':   { he: 'הודעות',          en: 'Messages' },
  'convos.lang':    { he: 'שפה',             en: 'Lang' },
  'convos.human':   { he: 'נציג נכנס',       en: 'Human' },
  'convos.activity':{ he: 'פעילות אחרונה',   en: 'Last activity' },
  'convos.yes':     { he: 'כן',              en: 'yes' },
  'convos.botOnly': { he: 'בוט בלבד',        en: 'bot only' },
  'convos.empty':   { he: 'אין עדיין שיחות.', en: 'No conversations yet.' },
  'convos.unit':    { he: 'שיחות',           en: 'conversations' },

  // --- calls --------------------------------------------------------------
  'calls.title':     { he: 'שיחות טלפון',   en: 'Calls' },
  'calls.all':       { he: 'כל השיחות',     en: 'All calls' },
  'calls.noAnswer':  { he: 'ללא מענה',      en: 'No answer' },
  'calls.links':     { he: 'לינקים שנשלחו', en: 'Links sent' },
  'calls.search':    { he: 'חיפוש במה שנאמר, עברית או אנגלית', en: 'Search what was said - Hebrew or English' },
  'calls.searchBtn': { he: 'חיפוש',         en: 'Search' },
  'calls.clear':     { he: 'ניקוי',         en: 'clear' },
  'calls.view':      { he: 'צפייה בשיחה',   en: 'View call' },
  'calls.unknown':   { he: 'לא ידוע',       en: 'unknown' },
  'calls.noSummary': { he: 'אין תקציר',     en: 'no summary' },
  'calls.emptyNoAnswer': { he: 'אף אחד עוד לא נשאר ללא מענה.', en: 'Nobody has gone unanswered yet.' },
  'calls.emptyLinks':    { he: 'עוד לא נשלחו לינקים לתשלום.',  en: 'No payment links sent yet.' },
  'calls.newer':     { he: 'חדשות יותר',    en: 'Newer' },
  'calls.older':     { he: 'ישנות יותר',    en: 'Older' },
  'calls.unit':      { he: 'שורות',         en: 'rows' },
  'calls.inbound':   { he: 'נכנסות',        en: 'Inbound' },
  'calls.outbound':  { he: 'יוצאות',        en: 'Outbound' },
  'calls.emptySearch':     { he: 'שום דבר שנאמר בשיחה לא תואם ל"{q}".',
                             en: 'Nothing said in a call matches “{q}”.' },
  'calls.emptySearchHint': { he: 'רק שיחות עם תמלול יכולות להתאים, ולישנות ביותר אין.',
                             en: 'Only calls with a transcript can match, and the oldest calls have none.' },
  'calls.emptyNone':       { he: 'לא תועדו עדיין שיחות.', en: 'No calls recorded yet.' },
  'calls.emptyDirection':  { he: 'לא תועדו עדיין שיחות {direction}.',
                             en: 'No {direction} calls recorded yet.' },
  'calls.emptyHint':       { he: 'דוחות סוף שיחה חוברו ב-8 באוגוסט; שורות מופיעות כאן מהשיחה הבאה שתתבצע.',
                             en: 'End-of-call reports were wired on 8 Aug; rows appear here from the next call placed.' },
  'calls.linksNote':       { he: '"נשלח" אומר ש-OXS אישרה שהלינק יצא. אם הוא שולם נראה רק ב-OXS, אז שום דבר כאן לא נחשב כסף שהתקבל.',
                             en: '“sent” means OXS confirmed the link went out — whether it was paid is only visible in OXS, so nothing here counts as money received.' },

  // --- sync ---------------------------------------------------------------
  'sync.title':      { he: 'ייבוא מ-OXS',        en: 'Import from OXS' },
  'sync.lastReal':   { he: 'הייבוא האמיתי האחרון', en: 'Last real import' },
  'sync.residents':  { he: 'דיירים מ-OXS',       en: 'Residents from OXS' },
  'sync.arrears':    { he: 'חובות מ-OXS',        en: 'Arrears from OXS' },
  'sync.requests':   { he: 'קריאות מ-OXS',       en: 'Requests from OXS' },
  'sync.runNow':     { he: 'הרצה עכשיו',         en: 'Run it now' },
  'sync.runBtn':     { he: 'הרץ ייבוא עכשיו',    en: 'Run import now' },
  'sync.running':    { he: 'ריצה כבר מתבצעת',    en: 'A run is already going' },
  'sync.recent':     { he: 'ריצות אחרונות',      en: 'Recent runs' },
  'sync.startedBy':  { he: 'הופעל על ידי',       en: 'Started by' },
  'sync.result':     { he: 'תוצאה',              en: 'Result' },
  'sync.took':       { he: 'משך',                en: 'Took' },
  'sync.openLog':    { he: 'פתח יומן',           en: 'Open log' },
  'sync.seeWhy':     { he: 'ראה למה',            en: 'see why' },
  'sync.never':      { he: 'מעולם',              en: 'never' },
  'sync.empty':      { he: 'לא תועדו ריצות.',    en: 'No runs recorded yet.' },
  'sync.blurb':      { he: 'דיירים, חובות וקריאות שירות, פעמיים ביום בחצות וב-15:00 שעון ישראל. OXS היא לקריאה בלבד: שום דבר כאן לא כותב אליה בחזרה.',
                       en: 'Residents, arrears and maintenance requests, twice a day at midnight and 3pm Israel time. OXS is read-only: nothing here ever writes back to it.' },
  'sync.runningNow': { he: 'רצה עכשיו',        en: 'running now' },
  'sync.tookLabel':  { he: 'לקח {d}',          en: 'took {d}' },
  'sync.newestAdded':{ he: 'החדש ביותר נוסף {ago}', en: 'newest added {ago}' },
  'sync.refreshed':  { he: 'רועננה לאחרונה {ago}',  en: 'last refreshed {ago}' },
  'sync.noneImported': { he: 'אף ריצה בהיסטוריה הזאת לא ייבאה כלום.',
                         en: 'No run in this history imported anything.' },
  'sync.noneWhy':    { he: 'כל ריצה למטה או דולגה כחצי הלא נכון של זוג שעון קיץ, או התחילה ולא סיימה. השורות למעלה הגיעו מריצות קודמות. בדוק את שורות "החדש ביותר" כדי לראות לפני כמה זמן.',
                       en: 'Every run listed below either skipped as the wrong half of a daylight-saving pair, or started and did not finish. The rows above arrived from earlier runs — check the newest-row lines to see how long ago.' },
  'sync.openLast':   { he: 'פתח את היומן האחרון', en: 'open the last log' },
  'sync.lastEnded':  { he: 'הריצה האחרונה הסתיימה ב-{how}.', en: 'The last run ended {how}.' },
  'sync.nothingSince': { he: 'שום דבר לא נכנס מאז {ago}.', en: 'Nothing has come in since {ago}.' },
  'sync.nothingFrom':  { he: 'שום דבר לא נכנס ממנה.',     en: 'Nothing has come in from it.' },
  'sync.dryRun':     { he: 'ריצה יבשה, מושכת ומדווחת, לא כותבת כלום',
                       en: 'Dry run — fetch and report, write nothing' },
  'sync.notWiredT':  { he: 'הכפתור עוד לא חובר.', en: 'Button not wired yet.' },
  'sync.notWired':   { he: 'הפעלת ריצה דורשת טוקן של גיטהאב עם הרשאה להתחיל תהליכים, שמוחזק על ידי האפליקציה ולא על ידי אדם. הוסיפו טוקן מצומצם למאגר הזה עם Actions: read and write, בשם GITHUB_DISPATCH_TOKEN בפרויקט בוורסל. כל מה שלמעלה עובד בלעדיו.',
                       en: 'Triggering a run needs a GitHub token with permission to start workflows, held by this app rather than by a person. Add a fine-grained token scoped to this repository with Actions: read and write, as GITHUB_DISPATCH_TOKEN in the Vercel project. Everything above works without it.' },
  'sync.bySchedule': { he: 'לפי לוח זמנים',   en: 'schedule' },
  'sync.byHand':     { he: 'ידנית',            en: 'by hand' },
  'sync.footnote':   { he: 'הייבוא רץ פעמיים ביום. הקרון של גיטהאב עובד לפי UTC ואין בו שעון קיץ, אז כל ריצה מתוזמנת פעמיים — לשני ההיסטים האפשריים של ישראל — וזו שלא בשעה הנכונה נעצרת תוך שניות. הריצות האלו לא מופיעות כאן, והן גם לא כישלון.',
                       en: 'The import runs twice a day. GitHub schedules on UTC and has no daylight saving, so each run is scheduled twice — once for each possible Israel offset — and the wrong-hour twin quits in seconds. Those are not listed here, and they are not failures.' },
  'sync.stateRunning':{ he: 'רצה',               en: 'running' },
  'sync.hidden':     { he: '{n} ריצות כאלו הוסתרו מהרשימה.', en: '{n} such exits hidden from this list.' },
  'sync.stateDone':  { he: 'יובא',               en: 'imported' },

  'thread.noMessages': { he: 'אין הודעות.',      en: 'No messages.' },
  'thread.recent':     { he: 'קריאות אחרונות',  en: 'Recent tickets' },
  'thread.resident':   { he: 'דייר',            en: 'Resident' },
  'thread.agent':      { he: 'נציג',            en: 'Agent' },
  'thread.bot':        { he: 'מיכאל',           en: 'Michael' },
  'call.title':        { he: 'שיחה',            en: 'Call' },
  'call.back':         { he: 'כל השיחות',       en: 'All calls' },
  'call.conversation': { he: 'השיחה',           en: 'Conversation' },
  'call.noTranscript': { he: 'אין תמלול לשיחה הזאת.', en: 'No transcript on this call.' },
  'call.summary':      { he: 'תקציר',           en: 'Summary' },
  'call.recording':    { he: 'הקלטה',           en: 'Recording' },
  'call.details':      { he: 'פרטים',           en: 'Details' },
  'call.tools':        { he: 'כלים שהופעלו',    en: 'Tools called' },
  'call.turns':        { he: 'תורות',           en: 'Turns' },

  // --- pager --------------------------------------------------------------
  'pager.rows':  { he: 'שורות',                 en: 'rows' },
  'pager.of':    { he: 'עמוד {page} מתוך {pages} · {total} {unit}',
                   en: 'page {page} of {pages} · {total} {unit}' },
  'pager.prev':  { he: 'הקודם',                 en: 'Previous' },
  'pager.next':  { he: 'הבא',                   en: 'Next' },

  // --- login --------------------------------------------------------------
  'login.title':    { he: 'כניסה',       en: 'Sign in' },
  'login.email':    { he: 'אימייל',      en: 'Email' },
  'login.password': { he: 'סיסמה',       en: 'Password' },
  'login.submit':   { he: 'כניסה',       en: 'Sign in' },
  'login.working':  { he: 'רגע…',        en: 'Signing in…' },

  // --- search -------------------------------------------------------------
  'search.title':    { he: 'חיפוש',              en: 'Search' },
  'search.blurb':    { he: 'קריאות, דיירים, הודעות ושיחות — בחיפוש אחד.',
                       en: 'Tickets, residents, messages and calls, in one search.' },
  'search.go':       { he: 'חפש',                en: 'Search' },
  'search.prompt':   { he: 'מה מחפשים?',          en: 'What are you looking for?' },
  'search.promptHint':{ he: 'שם של דייר, מספר טלפון, מספר קריאה, או משפט שנאמר בוואטסאפ או בשיחה.',
                       en: 'A resident, a phone number, a ticket reference, or something that was said in a message or a call.' },
  'search.short':    { he: 'עוד תו אחד לפחות — אות בודדת מחזירה כמעט הכל.',
                       en: 'One more character — a single letter matches almost everything.' },
  'search.none':     { he: 'לא נמצא כלום עבור “{q}”.', en: 'Nothing found for “{q}”.' },
  'search.noneHint': { he: 'שווה לנסות רק את שם המשפחה, או את ארבע הספרות האחרונות של הטלפון.',
                       en: 'Try just the surname, or the last four digits of the phone number.' },
  'search.tickets':  { he: 'קריאות',             en: 'Tickets' },
  'search.debt':       { he: 'חוב לפי חודש', en: 'Debt by month' },
  'search.residents':{ he: 'דיירים',             en: 'Residents' },
  'search.messages': { he: 'הודעות ווטסאפ',      en: 'WhatsApp messages' },
  'search.calls':    { he: 'שיחות טלפון',        en: 'Calls' },
  'search.said':     { he: 'מה נכתב',            en: 'Message' },
  'search.openResident': { he: 'לדייר',          en: 'Open' },
  'search.openThread':   { he: 'לשיחה',          en: 'Thread' },
  // Said rather than left implied: a list that stops at eight looks like a list
  // of eight, and somebody acts on "there are only two of these" being wrong.
  'search.showing':  { he: 'מוצגות {shown} מתוך {total} — הישנות יותר לא כאן.',
                       en: 'Showing {shown} of {total} — the older ones are not here.' },

  // --- settings -----------------------------------------------------------
  'settings.title':     { he: 'הגדרות',            en: 'Settings' },
  'settings.blurb':     { he: 'הפרטים שלך, והדרך שבה המערכת נראית לך.',
                          en: 'Your account, and how this dashboard looks to you.' },

  'settings.profile':   { he: 'הפרופיל שלי',       en: 'Profile' },
  'settings.photo':     { he: 'תמונה',              en: 'Photo' },
  'settings.photoChoose':{ he: 'בחירת תמונה',       en: 'Choose a photo' },
  'settings.photoChange':{ he: 'החלפת תמונה',       en: 'Change photo' },
  'settings.photoRemove':{ he: 'הסרת התמונה',       en: 'Remove photo' },
  'settings.photoSave': { he: 'שמירת התמונה',       en: 'Save photo' },
  'settings.photoSaving':{ he: 'מעלה…',             en: 'Uploading…' },
  'settings.photoHint': { he: 'התמונה נחתכת לריבוע ומוקטנת ל־256 פיקסלים בדפדפן, לפני שהיא נשלחת.',
                          en: 'Cropped square and shrunk to 256px in your browser, before it is sent.' },
  'settings.photoSaved':{ he: 'התמונה עודכנה.',     en: 'Photo updated.' },
  'settings.name':      { he: 'שם לתצוגה',          en: 'Display name' },
  'settings.nameHint':  { he: 'מה שיופיע בסרגל הצד ובפינה. אם משאירים ריק, נשתמש בכתובת המייל.',
                          en: 'What shows in the sidebar and the corner. Leave it empty and we use your email address.' },
  'settings.nameSave':  { he: 'שמירה',              en: 'Save' },
  'settings.nameSaved': { he: 'השם עודכן.',         en: 'Name updated.' },
  'settings.errImage':  { he: 'זה לא קובץ תמונה.',  en: 'That is not an image file.' },
  'settings.errBig':    { he: 'הקובץ גדול מדי.',    en: 'That file is too large.' },
  'settings.errRead':   { he: 'לא הצלחנו לפתוח את התמונה הזאת.',
                          en: 'That image could not be opened.' },
  'settings.errUpload': { he: 'ההעלאה נכשלה. נסו שוב בעוד רגע.',
                          en: 'The upload did not go through. Try again in a moment.' },
  'settings.account':   { he: 'החשבון שלי',        en: 'Account' },
  'settings.email':     { he: 'אימייל',            en: 'Email address' },
  // Said plainly because it is true and because the alternative is a "Role:
  // Admin" line that means nothing. There is one policy, `staff_read`, and it
  // grants every signed-in account the same read of every table.
  'settings.accessAll': { he: 'לכל מי שמחובר יש בדיוק אותה גישה — צפייה בכל הבניינים. אין עדיין הפרדה לפי תפקיד.',
                          en: 'Everyone signed in has the same access: read everything, across every building. There are no roles yet.' },
  'settings.lastSignIn':{ he: 'כניסה אחרונה',      en: 'Last signed in' },
  'settings.created':   { he: 'החשבון נפתח',       en: 'Account opened' },
  'settings.whoAdds':   { he: 'חשבונות נפתחים ידנית על ידי מנהל המערכת. אין הרשמה עצמית לדשבורד.',
                          en: 'Accounts are opened by hand by an administrator. Nobody can sign themselves up.' },

  'settings.password':  { he: 'שינוי סיסמה',       en: 'Password' },
  'settings.currentPw': { he: 'הסיסמה הנוכחית',    en: 'Current password' },
  'settings.newPw':     { he: 'סיסמה חדשה',        en: 'New password' },
  'settings.againPw':   { he: 'הסיסמה החדשה שוב',  en: 'New password again' },
  'settings.pwRule':    { he: 'לפחות 8 תווים.',    en: 'At least 8 characters.' },
  'settings.pwSave':    { he: 'עדכון הסיסמה',      en: 'Update password' },
  'settings.pwSaved':   { he: 'הסיסמה עודכנה.',    en: 'Password updated.' },
  'settings.errWrong':  { he: 'הסיסמה הנוכחית לא נכונה.',
                          en: 'That is not the current password.' },
  'settings.errMismatch':{ he: 'שתי הסיסמאות החדשות לא זהות.',
                          en: 'The two new passwords are not the same.' },
  'settings.errShort':  { he: 'הסיסמה החדשה קצרה מ־8 תווים.',
                          en: 'The new password is shorter than 8 characters.' },
  'settings.errSame':   { he: 'הסיסמה החדשה זהה לנוכחית.',
                          en: 'The new password is the same as the current one.' },
  'settings.errFailed': { he: 'העדכון לא עבר. נסו שוב בעוד רגע.',
                          en: 'The update did not go through. Try again in a moment.' },

  'settings.appearance':{ he: 'תצוגה',             en: 'Appearance' },
  'settings.theme':     { he: 'ערכת צבעים',        en: 'Theme' },
  'settings.language':  { he: 'שפה',               en: 'Language' },
  'settings.remembered':{ he: 'הבחירה נשמרת בדפדפן הזה בלבד.',
                          en: 'Remembered in this browser only.' },

  'settings.session':   { he: 'החיבור',            en: 'Session' },
  'settings.signOutNote':{ he: 'יציאה מהחשבון בדפדפן הזה. לא משפיע על מכשירים אחרים.',
                          en: 'Signs you out in this browser. Other devices stay signed in.' },

  // --- generic ------------------------------------------------------------
  'generic.none':   { he: '—', en: '—' },
} satisfies Record<string, Entry>;

export type Key = keyof typeof S;

/**
 * `t('debts.openIn', { month: '2026-07' })`.
 *
 * Placeholders are `{name}`. A missing one is left in the string rather than
 * blanked: a visible `{month}` in the interface is a bug somebody reports, and
 * an empty gap is a bug nobody notices.
 */
export function translator(locale: Locale) {
  return function t(key: Key, vars?: Record<string, string | number>) {
    let out: string = S[key][locale];
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        out = out.split('{' + k + '}').join(String(v));
      }
    }
    return out;
  };
}

export type T = ReturnType<typeof translator>;

/** A database status/urgency code rendered as a word. Unknown codes pass through. */
export function label(t: T, prefix: 'status' | 'urgency', code?: string | null) {
  if (!code) return '—';
  const key = `${prefix}.${code}` as Key;
  return key in S ? t(key) : code;
}
