import { serverClient } from '@/lib/supabase-server';
import { getLocale, label, translator, when } from '@/lib/i18n';
import { IconInbox } from '@/components/icons';

export default async function Thread({ params }: { params: { phone: string } }) {
  const phone = decodeURIComponent(params.phone);
  const db = serverClient();
  const locale = getLocale();
  const tr = translator(locale);

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
      <div className="pagehead">
        <h1 dir="auto">
          {resident?.full_name ?? phone}
          {resident?.building && (
            <span className="muted"> · {resident.building}{resident.unit ? ` · ${resident.unit}` : ''}</span>
          )}
        </h1>
        <p className="mono">{phone}</p>
      </div>

      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {messages?.length ? (
          <div className="thread">
            {messages.map((m: any) => (
              <div key={m.id} className={`msg ${m.sender === 'resident' ? 'resident' : 'bot'}`}>
                <div className="who">
                  {m.sender === 'resident' ? tr('thread.resident')
                    : m.sender === 'agent' ? tr('thread.agent') : tr('thread.bot')}
                  {' · '}{m.created_at.slice(11, 16)}
                  {m.message_type !== 'text' && ` · ${m.message_type}`}
                </div>
                {/* dir="auto" per bubble: Hebrew flows right-to-left while a
                    reference like 255-1013-26 inside it stays left-to-right. */}
                <div dir="auto">{m.body ?? <span className="muted">({m.message_type}, no text)</span>}</div>
              </div>
            ))}
          </div>
        ) : !error && (
          <div className="empty">
            <IconInbox />
            <div>{tr('thread.noMessages')}</div>
          </div>
        )}
      </div>

      {tickets && tickets.length > 0 && (
        <>
          <h2>{tr('thread.recent')}</h2>
          <div className="panel">
            <div className="scrollx">
            <table>
              <tbody>
                {tickets.map((t: any) => (
                  <tr key={t.reference}>
                    <td className="mono">{t.reference}</td>
                    <td dir="auto">{t.description}</td>
                    <td><span className={`pill ${t.status}`}>{label(tr, 'status', t.status)}</span></td>
                    <td className="muted mono">{when(t.created_at, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}
