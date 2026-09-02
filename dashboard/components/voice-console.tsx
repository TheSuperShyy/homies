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
  chatPlaceholder: string; send: string; chatFailed: string;
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
  const [sending, setSending] = useState(false);
  const [chatErr, setChatErr] = useState(false);
  const vapiRef = useRef<any>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  // One id per conversation, minted at the first typed message — it is the
  // call id the Edge Function sees, so a whole chat groups under one "call".
  const chatIdRef = useRef<string | null>(null);

  useEffect(() => () => { vapiRef.current?.stop?.(); }, []);
  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [lines]);

  const row = rows.find(r => r.id === picked) ?? null;
  const canStart = agent === 'intake' || (debtId && row);
  const canChat = agent === 'intake' || !!row;

  function reset() {
    setLines([]);
    setChatErr(false);
    chatIdRef.current = null;
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

  // Typed chat — the same agent brain over /api/voice-chat, no microphone.
  // The thread is the context: a voice transcript already on screen is sent
  // along, so hanging up and typing "מה מספר הפנייה?" continues the same
  // conversation as far as the model is concerned.
  async function send() {
    const text = draft.trim();
    if (!text || sending || !canChat) return;
    setDraft('');
    setChatErr(false);
    // Mid-call, the text goes INTO the call: Vapi injects it as a user turn,
    // the agent hears it and answers out loud. The reply arrives through the
    // normal transcript events; only our own line needs appending by hand.
    if (inCall) {
      vapiRef.current?.send?.({ type: 'add-message', message: { role: 'user', content: text } });
      setLines(prev => [...prev, { role: 'you', text, done: true }]);
      return;
    }
    if (!chatIdRef.current) chatIdRef.current = 'chat-' + crypto.randomUUID();
    const history = [
      ...lines.map(l => ({ role: l.role === 'agent' ? 'assistant' : 'user', content: l.text })),
      { role: 'user', content: text },
    ];
    setLines(prev => [...prev, { role: 'you', text, done: true }]);
    setSending(true);
    try {
      const res = await fetch('/api/voice-chat', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          agent, chatId: chatIdRef.current, messages: history,
          ...(agent === 'debt' && row ? { variables: row.variables } : {}),
        }),
      });
      const out = await res.json().catch(() => ({}));
      if (!res.ok || !out.reply) throw new Error();
      setLines(prev => {
        // The greeting belongs at the top of a typed conversation too — the
        // server already gave it to the model; show the reader the same thing.
        const opened = out.first && !prev.some(l => l.role === 'agent')
          ? [{ role: 'agent' as const, text: out.first, done: true }, ...prev]
          : prev;
        return [...opened, { role: 'agent', text: out.reply, done: true }];
      });
    } catch {
      setChatErr(true);
    } finally {
      setSending(false);
    }
  }

  async function start() {
    if (!canStart) return;
    setState('connecting');
    reset();
    try {
      const Vapi = (await import('@vapi-ai/web')).default;
      const vapi = new Vapi(publicKey);
      vapiRef.current = vapi;
      vapi.on('call-start', () => setState('live'));
      vapi.on('call-end', () => { setState('idle'); setMuted(false); });
      vapi.on('error', () => setState('error'));
      vapi.on('message', transcript);
      if (agent === 'debt' && row) {
        await vapi.start(debtId!, { variableValues: row.variables } as any);
      } else {
        await vapi.start(intakeId);
      }
    } catch {
      setState('error');
    }
  }

  function stop() { vapiRef.current?.stop?.(); }
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
              {state === 'error' && <span className="notice bad">{labels.failed}</span>}
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
                {sending && (
                  <div className="msg bot voice-typing">
                    <span className="who">{labels.agent}</span>…
                  </div>
                )}
              </div>
            )}

          <form className="voice-composer"
            onSubmit={e => { e.preventDefault(); send(); }}>
            <input value={draft} onChange={e => setDraft(e.target.value)}
              placeholder={labels.chatPlaceholder} disabled={sending || !canChat}
              dir="auto" />
            <button type="submit" className="btn-sm"
              disabled={sending || !canChat || !draft.trim()}>{labels.send}</button>
          </form>
          {chatErr && <p className="notice bad">{labels.chatFailed}</p>}

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
