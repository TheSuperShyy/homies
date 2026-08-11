  /**
  * Homies — resident lookup for the Vapi debt agent.
  *
  * Paste this into Extensions → Apps Script on the residents sheet, set the
  * HOMIES_SECRET script property (see getSecret below), then Deploy → New
  * deployment → Web app → Execute as *me*, Access *Anyone*.
  * The deployment URL is what the Vapi tool points at.
  *
  * Two entry points:
  *   doPost — Vapi's tool protocol. This is what the agent calls mid-conversation.
  *   doGet  — plain ?phone=+972501234567 for testing in a browser.
  *
  * PRIVACY, AND THIS IS NOT OPTIONAL
  * A web app deployed with Access=Anyone is reachable by anyone holding the URL.
  * The HOMIES_SECRET script property is the only thing in front of it, and Apps
  * Script web app cannot read custom request headers, so the secret must travel
  * in the query string — where it lands in logs. That is acceptable for the ten
  * fictional residents in residents.csv. It is NOT acceptable for real Homies
  * data: real names, phones and debts behind a guessable URL is a breach waiting
  * to happen. Move to Supabase before any real resident row goes in here.
  */

  // THE SECRET IS NOT IN THIS FILE ANY MORE, AND MUST NOT COME BACK.
  //
  // It used to be a literal here. That was sized for ten fictional residents and
  // it stopped being acceptable the moment real Homies data was proposed: the
  // literal is in this repository's git history, so anyone who ever gets a copy
  // of the repo has it, and deleting the line does not remove it from history.
  //
  // It now lives in Script Properties — Apps Script's own store, which is not in
  // the file, not in git, and not visible to anyone without edit access to the
  // script itself. Set it at:
  //
  //     Extensions > Apps Script > Project Settings (gear) > Script Properties
  //     Add property:  HOMIES_SECRET  =  <the new value>
  //
  // Read at call time rather than cached, so rotating the property takes effect
  // on the next request with no redeploy. Changing THIS FILE still needs a
  // redeploy; changing the secret does not.
  //
  // If the property is missing, getSecret() returns '' and checkSecret() then
  // refuses everything. That is deliberate — a missing secret must close the
  // door, never open it.
  function getSecret() {
    return PropertiesService.getScriptProperties().getProperty('HOMIES_SECRET') || '';
  }

  var SHEET_NAME = 'residents';

  // A resident is worth calling only if all four hold. This mirrors
  // v_debt_call_queue in supabase/004_debt_schema.sql — if the two ever disagree,
  // the SQL is the specification and this is the copy that is wrong.
  function isEligible(r) {
    return r.status === 'unpaid' &&
          r.handed_over === true &&
          r.do_not_call === false &&
          Number(r.attempts) < 4;
  }

  function normalisePhone(p) {
    // Vapi delivers E.164. Sheets loves to eat the leading + and reformat, so
    // compare on digits only and accept either shape from the caller.
    return String(p == null ? '' : p).replace(/[^0-9]/g, '');
  }

  function truthy(v) {
    // Sheets gives real booleans for TRUE/FALSE, strings if the column was ever
    // formatted as text. Accept both rather than silently reading "FALSE" as true.
    if (typeof v === 'boolean') return v;
    return String(v).trim().toUpperCase() === 'TRUE';
  }

  function readRows() {
    // A CSV imported into a new spreadsheet gets whatever tab name Google felt
    // like, so fall back to the first sheet rather than making the tab name a
    // setup step that fails silently.
    var ss = SpreadsheetApp.getActive();
    var sheet = ss.getSheetByName(SHEET_NAME) || ss.getSheets()[0];
    if (!sheet) throw new Error('Spreadsheet has no sheets');

    var values = sheet.getDataRange().getValues();
    var header = values[0].map(function (h) { return String(h).trim(); });

    return values.slice(1).map(function (row) {
      var r = {};
      header.forEach(function (h, i) { r[h] = row[i]; });
      r.handed_over = truthy(r.handed_over);
      r.do_not_call = truthy(r.do_not_call);
      // card_last4 must stay a string: a leading zero is real and Sheets will have
      // turned 0715 into the number 715.
      r.card_last4 = r.card_last4 === '' || r.card_last4 == null
        ? ''
        : String(r.card_last4).replace(/[^0-9]/g, '');
      if (r.card_last4 && r.card_last4.length < 4) {
        while (r.card_last4.length < 4) r.card_last4 = '0' + r.card_last4;
      }
      return r;
    }).filter(function (r) { return normalisePhone(r.phone); });
  }

  /**
  * What the agent gets back. Field names match the prompt's template variables so
  * the values can be handed straight to it.
  */
  function lookup(phone) {
    var wanted = normalisePhone(phone);
    if (!wanted) return { found: false, reason: 'no phone supplied' };

    var rows = readRows();
    var hit = null;
    for (var i = 0; i < rows.length; i++) {
      if (normalisePhone(rows[i].phone) === wanted) { hit = rows[i]; break; }
    }
    if (!hit) return { found: false, reason: 'no resident with that number' };

    var full = String(hit.full_name || '').trim();
    return {
      found: true,
      // Echoed back deliberately. The caller already knows the number it asked
      // for, but the *queue* form of this call asks for nobody in particular and
      // gets a list — and every row a tool writes is keyed on phone. Without it
      // here, a queue built from this endpoint produces calls that write rows
      // belonging to no resident, which is exactly what happened on 4 Aug.
      phone: String(hit.phone || ''),
      first_name: full.split(' ')[0],
      surname: full.split(' ').slice(1).join(' '),
      // Optional columns. An English voice handed "שרה" reads it as noise and the
      // call falls apart on the first sentence, so English needs a Latin form
      // from somewhere. If the sheet does not carry these the caller falls back
      // to its own table; adding the columns later needs no code change here.
      en_first_name: String(hit.en_first_name || ''),
      en_building: String(hit.en_building || ''),
      // How this resident can pay if the link does not suit them — a bank
      // transfer, standing order details, whatever the OXS export carries in
      // its "alternative payment details" column.
      //
      // The literal string 'none' when the column is empty, never ''. This is
      // the lesson from card_last4, applied on purpose: the agent does not see
      // a variable, it sees the prompt after substitution, and an empty one
      // leaves nothing to test. A resident asked for an alternative on 4 Aug
      // and was told "that's not how this works" three times, because there was
      // no way for the prompt to say whether an alternative existed.
      alt_payment: String(hit.alt_payment || '').trim() || 'none',
      building: String(hit.building || ''),
      unit: String(hit.unit || ''),
      gender: String(hit.gender || 'unknown'),
      // Empty string, never null — the prompt branches on this being empty to mean
      // "no card on file, do not ask for authorisation".
      card_last4: hit.card_last4,
      has_card: hit.card_last4 !== '',
      amount: String(hit.amount || ''),
      month: String(hit.month || ''),
      status: String(hit.status || ''),
      paid: String(hit.status || '') === 'paid',
      attempt: String(Number(hit.attempts || 0) + 1),
      eligible: isEligible(hit),
    };
  }

  // =========================================================================
  // THE EIGHT DEBT TOOLS
  // =========================================================================
  // A stopgap. The real implementation is supabase/functions/debt-tools/index.ts
  // and this is a second copy of the same contract, which is a thing to be
  // uncomfortable about: two implementations of eight tools will drift, and the
  // TypeScript one is the specification. This exists only because the Supabase
  // project does not yet, and it should be deleted the day it does.
  //
  // Known costs, accepted deliberately:
  //  - Apps Script cold-starts. Whichever turn fires a tool gets 1-3s of extra
  //    silence on top of the ~1,900ms the call already costs.
  //  - The secret travels in the query string, because Apps Script cannot read
  //    request headers. It lands in logs. Acceptable for ten fictional
  //    residents and for nothing else.
  //  - No constraints. The database version refuses a captured authorisation
  //    with no call attached, and refuses two open tickets for one charge. Here
  //    those are checks in code, which is weaker.

  var TABS = {
    call_outcomes:   ['at', 'call_id', 'phone', 'first_name', 'outcome', 'posture_reached',
                      'transfer_reason', 'standing_order_requested'],
    // What the office acts on now. No card column and no authorisation column:
    // from 4 Aug the agent does not take a spoken approval to charge anything,
    // it asks OXS to send the resident a link and OXS delivers it. The consent
    // happens when they tap it, which is where it belongs.
    payment_links:   ['at', 'call_id', 'phone', 'first_name', 'amount', 'month',
                      'status', 'note'],
    // Retired, kept so the historical rows still have a home and so a stale
    // deployment calling the old tool does not crash.
    payment_tickets: ['at', 'call_id', 'phone', 'first_name', 'amount', 'month',
                      'card_last4', 'authorization_captured', 'status', 'note'],
    promises:        ['at', 'call_id', 'phone', 'first_name', 'promised_date', 'said'],
    disputes:        ['at', 'call_id', 'phone', 'first_name', 'receipt_requested'],
    call_requests:   ['at', 'call_id', 'phone', 'reference', 'type', 'description',
                      'building', 'unit', 'urgency'],
    // Calls that ended without a usable request. Separate from call_requests
    // rather than a flag on it, because these are not a queue anyone works
    // through in order — they are a call-back list, and the thing a person needs
    // to see first is why it failed, not what was captured. No reference column:
    // nothing was read out to the caller, and minting one here would mean a
    // number exists that they were never given.
    partial_requests: ['at', 'call_id', 'phone', 'reason', 'description',
                       'building', 'unit'],
  };

  function tab(name) {
    // Created on first write rather than as a setup step, so there is no way to
    // deploy this and have a tool fail because a tab was never made by hand.
    var ss = SpreadsheetApp.getActive();
    var sheet = ss.getSheetByName(name);
    if (!sheet) {
      sheet = ss.insertSheet(name);
      sheet.appendRow(TABS[name]);
      sheet.setFrozenRows(1);
    }
    return sheet;
  }

  function write(name, values) {
    var sheet = tab(name);
    var row = TABS[name].map(function (h) {
      var v = values[h];
      return v === undefined || v === null ? '' : v;
    });
    sheet.appendRow(row);
    return true;
  }

  function stamp() {
    return Utilities.formatDate(new Date(), 'Asia/Jerusalem', 'yyyy-MM-dd HH:mm:ss');
  }

  /**
  * The facts about this call, taken from what the caller attached to it.
  *
  * THIS IS THE RULE THE FILE EXISTS TO KEEP. The agent never supplies the
  * amount, the month or who it is speaking to. Those come from variableValues,
  * which the model can read and cannot change, so a model that mishears a figure
  * still cannot write a wrong one into a payment ticket. Mirrors context() in
  * the Edge Function.
  */
  function callContext(body) {
    var msg  = body.message || {};
    var call = msg.call || {};
    var v = (call.assistantOverrides && call.assistantOverrides.variableValues)
         || (msg.assistant && msg.assistant.variableValues)
         || (call.assistant && call.assistant.variableValues)
         || {};
    return {
      call_id:    call.id || '',
      phone:      v.phone || '',
      first_name: v.first_name || '',
      amount:     v.amount || '',
      month:      v.month || '',
      card_last4: v.card_last4 || '',
      building:   v.building || '',
      unit:       v.unit || '',
    };
  }

  function alreadyOnCall(tabName, callId) {
    // The database version has a unique index. Here it is a scan, which is fine
    // at demo size and is why this is a stopgap.
    if (!callId) return false;
    var sheet = SpreadsheetApp.getActive().getSheetByName(tabName);
    if (!sheet || sheet.getLastRow() < 2) return false;
    var col = TABS[tabName].indexOf('call_id') + 1;
    var ids = sheet.getRange(2, col, sheet.getLastRow() - 1, 1).getValues();
    for (var i = 0; i < ids.length; i++) {
      if (String(ids[i][0]) === String(callId)) return true;
    }
    return false;
  }

  function setHandedOver(phone, value) {
    var ss = SpreadsheetApp.getActive();
    var sheet = ss.getSheetByName(SHEET_NAME) || ss.getSheets()[0];
    var values = sheet.getDataRange().getValues();
    var header = values[0].map(function (h) { return String(h).trim(); });
    var pCol = header.indexOf('phone'), hCol = header.indexOf('handed_over');
    if (pCol < 0 || hCol < 0) return false;
    var wanted = normalisePhone(phone);
    for (var i = 1; i < values.length; i++) {
      if (normalisePhone(values[i][pCol]) === wanted) {
        sheet.getRange(i + 1, hCol + 1).setValue(value);
        return true;
      }
    }
    return false;
  }

  var TOOLS = {
    /**
    * Ask OXS to send this resident a payment link. Nothing here sends it — the
    * row is the request, OXS is the sender, and until its API is documented a
    * person in the office is what closes the gap. That is why the agent says a
    * link is on its way rather than that one has arrived.
    */
    send_payment_link: function (args, ctx) {
      if (!ctx.amount || !ctx.month) {
        return { ok: false, error: 'no amount or month on this call' };
      }
      // One link per call. Two rows for one conversation means the office sends
      // the same resident the same link twice, which reads as a system that has
      // lost track of whether they have paid.
      if (alreadyOnCall('payment_links', ctx.call_id)) {
        return { ok: false, error: 'a link has already been requested on this call' };
      }
      write('payment_links', {
        at: stamp(), call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
        amount: ctx.amount, month: ctx.month, status: 'requested', note: args.note || '',
      });
      return { ok: true };
    },

    // Retired 4 Aug, kept live so a stale client calling it gets a written row
    // rather than 'unknown tool'. It is no longer offered to the agent.
    open_payment_ticket: function (args, ctx) {
      var captured = args.authorization_captured === true;
      if (!ctx.amount || !ctx.month) {
        return { ok: false, error: 'no amount or month on this call' };
      }
      // A captured authorisation says a named person approved a charge to a
      // specific card. With no card there is no charge to approve, so the claim
      // cannot be true whatever the agent believed. On 4 Aug משה, who has no
      // card, was told one was on file and this row was written with
      // authorization_captured TRUE — a staff member reading it would have gone
      // looking for a card that does not exist. The prompt is asked not to do
      // this; here it cannot.
      if (captured && !ctx.card_last4) {
        return { ok: false,
                 error: 'no card on file for this resident — authorisation cannot be captured' };
      }
      if (alreadyOnCall('payment_tickets', ctx.call_id)) {
        return { ok: false, error: 'a ticket already exists for this call' };
      }
      write('payment_tickets', {
        at: stamp(), call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
        amount: ctx.amount, month: ctx.month, card_last4: ctx.card_last4,
        authorization_captured: captured, status: 'pending', note: args.note || '',
      });
      return { ok: true, authorization_captured: captured };
    },

    log_promise_to_pay: function (args, ctx) {
      if (!args.said) return { ok: false, error: 'said is required' };
      write('promises', {
        at: stamp(), call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
        promised_date: args.promised_date || '', said: String(args.said),
      });
      return { ok: true };
    },

    request_standing_order: function (args, ctx) {
      write('call_outcomes', {
        at: stamp(), call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
        outcome: 'office_to_contact', standing_order_requested: true,
      });
      return { ok: true };
    },

    log_disputed_payment: function (args, ctx) {
      write('disputes', {
        at: stamp(), call_id: ctx.call_id, phone: ctx.phone,
        first_name: ctx.first_name, receipt_requested: true,
      });
      return { ok: true };
    },

    open_request: function (args, ctx) {
      if (!args.description) return { ok: false, error: 'description is required' };
      // A real reference, handed back for the agent to read out. It is forbidden
      // from inventing one, so it has to get a true value from somewhere.
      var ref = 'HM-' + new Date().getFullYear() + '-' +
                ('000' + Math.floor(Math.random() * 9000 + 1000)).slice(-4);
      write('call_requests', {
        at: stamp(), call_id: ctx.call_id, phone: ctx.phone, reference: ref,
        type: args.type || 'other', description: String(args.description),
        // The call's own values first, the model's arguments only when there are
        // none. Outbound the location is a fact the call carries and the model
        // cannot overwrite it; inbound there is no caller ID and no lookup, so
        // what the caller said is the only source. Same precedence as the n8n
        // Code node — if these two ever disagree, rows written through one path
        // stop matching rows written through the other.
        building: ctx.building || args.building || '',
        unit: ctx.unit || args.unit || '',
        urgency: args.urgency || 'normal',
      });
      return { ok: true, reference: ref };
    },

    // The inbound agent's admission that a call is not going to produce a
    // request: a line it cannot hear over, or the three-minute cap about to cut
    // it off. Deliberately incapable of refusing — it runs at the moment
    // everything else has already gone wrong, and an error here turns a salvaged
    // call into a lost one. An empty description is a valid row; it means the
    // audio was unusable, which is the whole point of recording the attempt.
    save_partial_request: function (args, ctx) {
      write('partial_requests', {
        at: stamp(), call_id: ctx.call_id, phone: ctx.phone,
        reason: args.reason || 'audio',
        description: args.description ? String(args.description) : '',
        building: ctx.building || args.building || '',
        unit: ctx.unit || args.unit || '',
      });
      // No recording URL. Vapi only publishes one in the end-of-call report,
      // which arrives after this tool has run, so the recording is found by
      // call_id later rather than stored here. A column holding a URL that is
      // always empty would read as "there is no recording", which is false.
      return { ok: true };
    },

    flag_not_handed_over: function (args, ctx) {
      var done = setHandedOver(ctx.phone, false);
      write('call_outcomes', {
        at: stamp(), call_id: ctx.call_id, phone: ctx.phone,
        first_name: ctx.first_name, outcome: 'not_handed_over',
      });
      return { ok: true, resident_updated: done };
    },

    transfer_to_human: function (args, ctx) {
      // Outbound reasons first, inbound after. Both agents post here, and an
      // unlisted reason is not rejected — it silently becomes 'caller_request',
      // so a missing string is a column that lies rather than an error anyone
      // notices. Kept in step with REASONS in scripts/n8n_deploy.py and
      // INTAKE_TRANSFER_REASONS in scripts/vapi_tools.py.
      var reasons = ['hardship', 'dispute', 'distress', 'language', 'not_understood',
                     'caller_request', 'ownership',
                     'out_of_scope', 'emergency', 'repeated_failure'];
      var reason = reasons.indexOf(args.reason) >= 0 ? args.reason : 'caller_request';
      write('call_outcomes', {
        at: stamp(), call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
        outcome: 'transferred', transfer_reason: reason,
        posture_reached: args.posture_reached || '',
      });
      return { ok: true, reason: reason };
    },

    log_call_outcome: function (args, ctx) {
      // 'link_sent' replaces 'authorized' as the good outcome. 'authorized' stays
      // accepted so rows written before 4 Aug still mean what they meant.
      var ok = ['link_sent', 'authorized', 'promised', 'disputed', 'refused',
                'transferred', 'voicemail', 'wrong_party', 'not_handed_over',
                'no_answer', 'office_to_contact'];
      if (ok.indexOf(args.outcome) < 0) {
        return { ok: false, error: 'outcome must be one of: ' + ok.join(', ') };
      }
      write('call_outcomes', {
        at: stamp(), call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
        outcome: args.outcome, posture_reached: args.posture_reached || '',
        transfer_reason: args.transfer_reason || '',
      });
      return { ok: true };
    },

    // The read that already existed. Kept on the same router so there is one
    // deployment and one URL.
    identify_resident: function (args, ctx) {
      return lookup(args.phone || ctx.phone);
    },
  };

  function checkSecret(e) {
    // No open-by-default branch. A ship-with-a-real-secret file does not need one,
    // and an "if unset, allow everything" escape hatch is how these end up public.
    var given = (e && e.parameter && e.parameter.key) || '';
    var secret = getSecret();
    return Boolean(secret) && given === secret;
  }

  function json(obj) {
    return ContentService
      .createTextOutput(JSON.stringify(obj))
      .setMimeType(ContentService.MimeType.JSON);
  }

  /**
  * Why a row is not worth calling, in words. Mirrors isEligible condition for
  * condition; returns '' when the resident is callable.
  *
  * The four reasons are not interchangeable. "already paid" is a data state that
  * will clear itself next month; "not handed over" stops calls for that
  * apartment permanently; "do not call" is a person's decision; "4 attempts
  * made" is the retry ceiling. Collapsing them into one "skipped" would hide the
  * only difference that matters when someone asks why a debtor was never rung.
  */
  function blockedReason(r) {
    if (r.status !== 'unpaid') return r.status === 'paid' ? 'already paid' : String(r.status || 'no status');
    if (r.handed_over !== true) return 'not handed over';
    if (r.do_not_call !== false) return 'do not call';
    if (!(Number(r.attempts) < 4)) return Number(r.attempts) + ' attempts made';
    return '';
  }

  /**
  * Empty the tabs the tools write to, keeping their headers. Used between test
  * runs — every rehearsal call leaves rows behind, and by the third one nobody
  * can tell a real result from a probe.
  *
  * It will not touch `residents`. That tab is the input, not the output: it is
  * hand-maintained, it is what decides who gets called, and there is no undo on
  * a spreadsheet reachable by URL. The name is refused explicitly rather than
  * merely being absent from TABS, so that adding it there later cannot quietly
  * make it wipeable.
  */
  function clearTabs(which) {
    var names = which === 'all' ? Object.keys(TABS) : [which];
    var out = [];
    for (var i = 0; i < names.length; i++) {
      var name = names[i];
      if (name === SHEET_NAME) return { ok: false, error: 'refusing to clear ' + name };
      if (!TABS[name]) return { ok: false, error: 'unknown tab ' + name };
      var sheet = SpreadsheetApp.getActive().getSheetByName(name);
      // A tab that was never written to is already clean; not an error.
      var removed = 0;
      if (sheet && sheet.getLastRow() > 1) {
        removed = sheet.getLastRow() - 1;
        sheet.deleteRows(2, removed);
      }
      out.push({ tab: name, removed: removed });
    }
    return { ok: true, cleared: out };
  }

  /**
  * Browser testing: <url>?key=SECRET&phone=+972501234567
  * The call queue:   <url>?key=SECRET
  * Everyone, with a reason on the ones being skipped: <url>?key=SECRET&all=1
  * Wipe the test rows: <url>?key=SECRET&clear=all  (or &clear=payment_tickets)
  */
  function doGet(e) {
    if (!checkSecret(e)) return json({ error: 'unauthorised' });

    if (e && e.parameter && e.parameter.clear) {
      return json(clearTabs(String(e.parameter.clear)));
    }

    // ?meta=1 — which spreadsheet is this actually writing to, and what is in it.
    // Worth a route of its own: the script is bound to a sheet rather than
    // naming one, so the only way to answer "where did my row go" from outside
    // is to already know. Answering it needs no access to the rows themselves.
    if (e && e.parameter && e.parameter.meta) {
      var book = SpreadsheetApp.getActive();
      return json({
        spreadsheet: book.getName(),
        url: book.getUrl(),
        tabs: book.getSheets().map(function (s) {
          return { name: s.getName(), rows: Math.max(0, s.getLastRow() - 1) };
        }),
      });
    }

    var phone = e && e.parameter ? e.parameter.phone : '';
    if (!phone) {
      // No phone means "show me the call queue", which is the useful default when
      // you are looking at this in a browser.
      var all = truthy((e && e.parameter && e.parameter.all) || '') ||
                String((e && e.parameter && e.parameter.all) || '') === '1';
      var rows = readRows();
      if (!all) rows = rows.filter(isEligible);
      return json({ queue: rows.map(function (r) {
        var out = lookup(r.phone);
        // A caller showing the whole list needs to say why a row is greyed out.
        // Only present in the all=1 form, so the plain queue stays exactly what
        // it was for anything already consuming it.
        if (all) out.blocked = blockedReason(r);
        return out;
      }) });
    }
    return json(lookup(phone));
  }

  /**
  * Vapi's tool protocol. It POSTs
  *   { message: { toolCalls: [ { id, function: { name, arguments } } ] } }
  * and expects
  *   { results: [ { toolCallId, result } ] }
  * `arguments` arrives as an object on some versions and a JSON string on others,
  * so both are handled.
  */
  function doPost(e) {
    if (!checkSecret(e)) return json({ error: 'unauthorised' });

    var body = {};
    try {
      body = JSON.parse(e.postData.contents);
    } catch (err) {
      return json({ error: 'bad json: ' + err });
    }

    var calls = (body.message && body.message.toolCalls) || [];
    if (!calls.length) {
      // Not a tool call — probably a manual poke. Behave like doGet.
      return json(lookup((body.phone) || ''));
    }

    var ctx = callContext(body);

    var results = calls.map(function (c) {
      var fn = c['function'] || {};
      var args = fn.arguments || {};
      if (typeof args === 'string') {
        try { args = JSON.parse(args); } catch (err) { args = {}; }
      }

      var handler = TOOLS[fn.name];
      if (!handler) {
        return { toolCallId: c.id,
                 result: JSON.stringify({ ok: false, error: 'unknown tool ' + fn.name }) };
      }
      try {
        return { toolCallId: c.id, result: JSON.stringify(handler(args, ctx)) };
      } catch (err) {
        // Never throw at Vapi. A failure mid-call is dead air; a failed result at
        // least lets the agent say it will check and come back to them.
        return { toolCallId: c.id,
                 result: JSON.stringify({ ok: false, error: String(err) }) };
      }
    });

    return json({ results: results });
  }

  /** Run this from the Apps Script editor to check the sheet parses. */
  function selfTest() {
    var rows = readRows();
    Logger.log('rows: ' + rows.length);
    // 5, not the 6 this used to say — דוד was marked paid in the sheet on 4 Aug.
    Logger.log('eligible: ' + rows.filter(isEligible).length + ' (expected 5)');
    Logger.log(JSON.stringify(lookup('+972501234567')));   // דוד, paid, card 4821
    Logger.log(JSON.stringify(lookup('+972531234569')));   // משה, no card
    Logger.log(JSON.stringify(lookup('+972581234572')));   // מיכל, already paid
    Logger.log(JSON.stringify(lookup('+972500000000')));   // not found
  }
