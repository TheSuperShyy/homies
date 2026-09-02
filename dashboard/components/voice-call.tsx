'use client';

// Talk to Michael from the dashboard: a web call to the inbound intake
// assistant, microphone in the browser, no phone number involved. The same
// path web/index.html has used since the week-3 demo, wearing the dashboard's
// own clothes.
//
// The SDK is imported dynamically inside the click handler, not at module
// top. Two reasons: it touches browser-only globals, and nobody should pay
// its download for opening the Calls page — most visits here are to read the
// list, not to place a call.
//
// Everything the user reads arrives as props from the server page, already
// translated — the same pattern the icons use to stay out of the bundle.
// The public key is public by design (it starts web calls and can do nothing
// else); the private key never comes near this file.

import { useEffect, useRef, useState } from 'react';

type Labels = {
  start: string; connecting: string; hangup: string;
  mute: string; unmute: string; agent: string; you: string;
  failed: string; micHint: string;
};

type Line = { role: 'agent' | 'you'; text: string; done: boolean };

export function VoiceCall({ publicKey, assistantId, labels }: {
  publicKey: string; assistantId: string; labels: Labels;
}) {
  const [state, setState] = useState<'idle' | 'connecting' | 'live' | 'error'>('idle');
  const [muted, setMuted] = useState(false);
  const [lines, setLines] = useState<Line[]>([]);
  const vapiRef = useRef<any>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  // The call must not outlive the page. Without this, navigating away leaves
  // the mic open and Michael talking to a component that no longer exists.
  useEffect(() => () => { vapiRef.current?.stop?.(); }, []);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [lines]);

  function transcript(m: any) {
    if (m?.type !== 'transcript' || !m.transcript) return;
    const role: Line['role'] = m.role === 'assistant' ? 'agent' : 'you';
    const done = m.transcriptType !== 'partial';
    setLines(prev => {
      const last = prev[prev.length - 1];
      // A partial turn overwrites itself until it is final, so the thread
      // reads as speech settling rather than as a stutter of duplicates.
      if (last && last.role === role && !last.done) {
        return [...prev.slice(0, -1), { role, text: m.transcript, done }];
      }
      return [...prev, { role, text: m.transcript, done }];
    });
  }

  async function start() {
    setState('connecting');
    setLines([]);
    try {
      const Vapi = (await import('@vapi-ai/web')).default;
      const vapi = new Vapi(publicKey);
      vapiRef.current = vapi;
      vapi.on('call-start', () => setState('live'));
      vapi.on('call-end', () => { setState('idle'); setMuted(false); });
      vapi.on('error', () => setState('error'));
      vapi.on('message', transcript);
      await vapi.start(assistantId);
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

  if (state === 'idle' || state === 'error') {
    return (
      <div className="voicecall">
        <button type="button" className="btn-sm" onClick={start}>{labels.start}</button>
        {state === 'error' && <span className="notice bad">{labels.failed}</span>}
        {state === 'idle' && <span className="hint">{labels.micHint}</span>}
      </div>
    );
  }

  return (
    <div className="voicecall live">
      <div className="voicecall-controls">
        <span className="pill">{state === 'connecting' ? labels.connecting : labels.agent}</span>
        <button type="button" className="btn-sm" onClick={toggleMute}>
          {muted ? labels.unmute : labels.mute}
        </button>
        <button type="button" className="btn-sm" onClick={stop}>{labels.hangup}</button>
      </div>
      {lines.length > 0 && (
        <div className="thread voicecall-thread" ref={threadRef}>
          {lines.map((l, i) => (
            <div key={i} className={l.role === 'agent' ? 'msg bot' : 'msg resident'}>
              <span className="who">{l.role === 'agent' ? labels.agent : labels.you}</span>
              {l.text}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
