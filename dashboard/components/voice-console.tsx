'use client';

// Voice Agent call — the browser test console, living inside the dashboard.
//
// Two agents behind one Start button: the inbound intake agent (Michael, no
// setup — a caller is a caller) and the debt follow-up agent, which is a
// template and therefore needs a resident chosen first. The resident list and
// every composed Hebrew phrase come from the server page, read from
// v_debt_call_queue_person — the same view press_call() uses — so what the
// agent is told here is what it would be told on a real outbound call. Nothing
// is written: no handed_over flip, no attempt counted. This is a phone booth,
// not a dialer.
//
// The SDK loads inside the click handler: nobody pays its download for
// opening the page, and it touches browser-only globals. The call dies with
// the component — navigating away must not leave a microphone open.

import { useEffect, useRef, useState } from 'react';

export type DebtRow = {
  id: string;
  name: string;
  sub: string;            // "card 7355 · הרצל 14 · דירה 7", composed server-side
  amount: string;         // "₪450"
  variables: Record<string, string>;
};

type Labels = {
  tabIntake: string; tabDebt: string; who: string; source: string;
  idle: string; connecting: string; live: string;
  start: string; hangup: string; mute: string; unmute: string;
  agent: string; you: string; failed: string; micHint: string;
  transcriptHint: string; told: string; pickFirst: string;
  chatPlaceholder: string; chatIdle: string; send: string;
};

type Line = { role: 'agent' | 'you'; text: string; done: boolean };

export function VoiceConsole({ publicKey, intakeId, debtId, rows, labels }: {
  publicKey: string; intakeId: string; debtId: string | null;
  rows: DebtRow[]; labels: Labels;
}) {
  const [agent, setAgent] = useState<'intake' | 'debt'>('intake');
  const [picked, setPicked] = useState<string | null>(rows[0]?.id ?? null);
  const [state, setState] = useState<'idle' | 'connecting' | 'live' | 'error'>('idle');
  const [muted, setMuted] = useState(false);
  const [lines, setLines] = useState<Line[]>([]);
  const [draft, setDraft] = useState('');
  // WHY THE REASON IS KEPT. The error handler below used to be
  // `() => setState('error')`, which threw the only description of the failure
  // away: a call that would not connect looked identical whether the browser
  // had refused the microphone, the key was wrong, or Vapi was out of credit.
  // On 8 Sep that cost an afternoon on a console stuck at "connecting".
  const [detail, setDetail] = useState('');
  const vapiRef = useRef<any>(null);
  const watchdogRef = useRef<any>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => () => {
    clearTimeout(watchdogRef.current);
    vapiRef.current?.stop?.();
  }, []);
  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [lines]);

  const row = rows.find(r => r.id === picked) ?? null;
  const canStart = agent === 'intake' || (debtId && row);

  function reset() {
    setLines([]);
  }

  function transcript(m: any) {
    if (m?.type !== 'transcript' || !m.transcript) return;
    const role: Line['role'] = m.role === 'assistant' ? 'agent' : 'you';
    const done = m.transcriptType !== 'partial';
    setLines(prev => {
      const last = prev[prev.length - 1];
      // A partial turn overwrites itself until final, so the thread reads as
      // speech settling rather than a stutter of duplicates.
      if (last && last.role === role && !last.done) {
        return [...prev.slice(0, -1), { role, text: m.transcript, done }];
      }
      return [...prev, { role, text: m.transcript, done }];
    });
  }

  // Typed text goes INTO the live call, never anywhere else (22 Sep, owner:
  // "use this kind of engineering", after the no-call chat route turned out
  // to be the dashboard's only use of OpenRouter). Vapi's add-message injects
  // it as a user turn, exactly as if it had been said: no speech-to-text, the
  // agent reads it, answers out loud, and the reply arrives through the normal
  // transcript events. Only our own line is appended by hand. With no call
  // there is nowhere to send it, so the box is disabled until the call is live.
  function send() {
    const text = draft.trim();
    if (!text || state !== 'live') return;
    setDraft('');
    vapiRef.current?.send?.({ type: 'add-message', message: { role: 'user', content: text } });
    setLines(prev => [...prev, { role: 'you', text, done: true }]);
  }

  // Whatever the SDK hands back — an Error, a Vapi event, a bare string — said
  // in one line a person can act on.
  function reason(e: any): string {
    const raw = e?.errorMsg ?? e?.error?.message ?? e?.message ?? e?.msg ?? e;
    const text = typeof raw === 'string' ? raw : (() => {
      try { return JSON.stringify(raw); } catch { return String(raw); }
    })();
    return (text || 'unknown error').slice(0, 300);
  }

  function fail(e: any) {
    clearTimeout(watchdogRef.current);
    // The console is the second half of this: the badge has room for a
    // sentence, DevTools has room for the object.
    console.error('[voice] call failed:', e);
    setDetail(reason(e));
    setState('error');
  }

  async function start() {
    if (!canStart) return;
    setState('connecting');
    setDetail('');
    reset();
    try {
      const Vapi = (await import('@vapi-ai/web')).default;
      const vapi = new Vapi(publicKey);
      vapiRef.current = vapi;
      vapi.on('call-start', () => { clearTimeout(watchdogRef.current); setState('live'); });
      vapi.on('call-end', () => {
        clearTimeout(watchdogRef.current); setState('idle'); setMuted(false);
      });
      vapi.on('error', fail);
      vapi.on('message', transcript);
      // A refused microphone can leave getUserMedia pending with no error at
      // all, and the panel then says "connecting" until the tab is closed.
      // Twenty seconds is far longer than a healthy connect and far shorter
      // than for ever.
      clearTimeout(watchdogRef.current);
      watchdogRef.current = setTimeout(() => {
        setState((s) => {
          if (s !== 'connecting') return s;
          console.error('[voice] still connecting after 20s — check the '
            + 'microphone permission for this site, then the Vapi key and credit');
          setDetail('timeout: no answer after 20s — check the microphone '
            + 'permission for this site first');
          return 'error';
        });
      }, 20000);
      if (agent === 'debt' && row) {
        await vapi.start(debtId!, { variableValues: row.variables } as any);
      } else {
        await vapi.start(intakeId);
      }
    } catch (e) {
      fail(e);
    }
  }

  function stop() { clearTimeout(watchdogRef.current); vapiRef.current?.stop?.(); }
  function toggleMute() {
    const v = vapiRef.current;
    if (!v) return;
    v.setMuted(!v.isMuted());
    setMuted(v.isMuted());
  }

  const inCall = state === 'connecting' || state === 'live';
  const dot = state === 'live' ? 'live' : state === 'connecting' ? 'connecting' : 'idle';

  return (
    <div className="voice-console">
      <nav className="seg" aria-label={labels.tabIntake}>
        <button type="button" className={agent === 'intake' ? 'on' : ''}
          disabled={inCall} onClick={() => { setAgent('intake'); reset(); }}>{labels.tabIntake}</button>
        {debtId && (
          <button type="button" className={agent === 'debt' ? 'on' : ''}
            disabled={inCall} onClick={() => { setAgent('debt'); reset(); }}>{labels.tabDebt}</button>
        )}
      </nav>

      <div className="voice-cols">
        {agent === 'debt' && (
          <aside className="voice-list">
            <div className="voice-listhead">
              {labels.who} <span className="pill">{labels.source}</span>
            </div>
            {rows.map(r => (
              <button key={r.id} type="button" disabled={inCall}
                className={'voice-card' + (r.id === picked ? ' on' : '')}
                onClick={() => setPicked(r.id)}>
                <span className="voice-name">{r.name}</span>
                <span className="voice-amount">{r.amount}</span>
                <span className="voice-sub">{r.sub}</span>
              </button>
            ))}
            {rows.length === 0 && <div className="empty">{labels.pickFirst}</div>}
          </aside>
        )}

        <section className="panel voice-panel">
          <div className="voice-status">
            <span className={'voice-dot ' + dot} aria-hidden />
            {state === 'live' ? labels.live
              : state === 'connecting' ? labels.connecting : labels.idle}
          </div>

          {!inCall ? (
            <div className="voice-actions">
              <button type="button" className="btn-sm voice-start"
                disabled={!canStart} onClick={start}>{labels.start}</button>
              <span className="hint">{labels.micHint}</span>
              {state === 'error' && (
                <span className="notice bad">
                  {labels.failed}{detail ? ` — ${detail}` : ''}
                </span>
              )}
            </div>
          ) : (
            <div className="voice-actions">
              <button type="button" className="btn-sm" onClick={toggleMute}>
                {muted ? labels.unmute : labels.mute}
              </button>
              <button type="button" className="btn-sm" onClick={stop}>{labels.hangup}</button>
            </div>
          )}

          <hr className="voice-rule" />

          {lines.length === 0
            ? <p className="hint">{labels.transcriptHint}</p>
            : (
              <div className="thread voice-thread" ref={threadRef}>
                {lines.map((l, i) => (
                  <div key={i} className={l.role === 'agent' ? 'msg bot' : 'msg resident'}>
                    <span className="who">{l.role === 'agent' ? labels.agent : labels.you}</span>
                    {l.text}
                  </div>
                ))}
              </div>
            )}

          <form className="voice-composer"
            onSubmit={e => { e.preventDefault(); send(); }}>
            <input value={draft} onChange={e => setDraft(e.target.value)}
              placeholder={state === 'live' ? labels.chatPlaceholder : labels.chatIdle}
              disabled={state !== 'live'} dir="auto" />
            <button type="submit" className="btn-sm"
              disabled={state !== 'live' || !draft.trim()}>{labels.send}</button>
          </form>

          {agent === 'debt' && row && (
            <details className="voice-told">
              <summary>{labels.told}</summary>
              <dl>
                {Object.entries(row.variables).map(([k, v]) => (
                  <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
                ))}
              </dl>
            </details>
          )}
        </section>
      </div>
    </div>
  );
}
