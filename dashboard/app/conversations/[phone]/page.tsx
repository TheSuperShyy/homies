import { serverClient } from '@/lib/supabase-server';

export default async function Thread({ params }: { params: { phone: string } }) {
  const phone = decodeURIComponent(params.phone);
  const db = serverClient();

  const [{ data: messages, error }, { data: resident }, { data: tickets }] = await Promise.all([
    db.from('messages').select('*').eq('phone', phone).order('created_at', { ascending: true }),
    db.from('residents').select('full_name,building,unit').eq('phone', phone).maybeSingle(),
    // Tickets this person has, so the thread and its outcome are on one screen
    // rather than in two tabs.
    db.from('requests').select('reference,description,status,created_at')
      .order('created_at', { ascending: false }).limit(5),
  ]);

  return (
    <>
      <h1 dir="auto">
        {resident?.full_name ?? phone}
        {resident?.building && <span className="muted"> — {resident.building}{resident.unit ? ` · ${resident.unit}` : ''}</span>}
      </h1>
      <div className="muted mono" style={{ marginBottom: 14 }}>{phone}</div>

      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {messages?.length ? (
          <div className="thread">
            {messages.map((m: any) => (
              <div key={m.id} className={`msg ${m.sender === 'resident' ? 'resident' : 'bot'}`}>
                <div className="who">
                  {m.sender === 'resident' ? 'Resident' : m.sender === 'agent' ? 'Agent' : 'Michael'}
                  {' · '}{m.created_at.slice(11, 16)}
                  {m.message_type !== 'text' && ` · ${m.message_type}`}
                </div>
                {/* dir="auto" per bubble: Hebrew flows right-to-left while a
                    reference like HM-2026-1013 inside it stays left-to-right. */}
                <div dir="auto">{m.body ?? <span className="muted">({m.message_type}, no text)</span>}</div>
              </div>
            ))}
          </div>
        ) : !error && <div className="empty">No messages.</div>}
      </div>

      {tickets && tickets.length > 0 && (
        <>
          <h2>Recent tickets</h2>
          <div className="panel">
            <table>
              <tbody>
                {tickets.map((t: any) => (
                  <tr key={t.reference}>
                    <td className="mono">{t.reference}</td>
                    <td dir="auto">{t.description}</td>
                    <td><span className={`pill ${t.status}`}>{t.status}</span></td>
                    <td className="muted mono">{t.created_at.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
