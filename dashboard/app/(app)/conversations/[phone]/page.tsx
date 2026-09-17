import { serverClient } from '@/lib/supabase-server';
import { getLocale, label, translator, when } from '@/lib/i18n';
import { IconInbox } from '@/components/icons';

export default async function Thread({ params }: { params: { phone: string } }) {
  const phone = decodeURIComponent(params.phone);
  const db = serverClient();
  const locale = getLocale();
  const tr = translator(locale);

  // Two phone shapes: this page's `phone` is the bare 972… of messages.phone
  // and request_media.phone; requests.reported_by_phone carries the plus.
  const e164 = phone.startsWith('+') ? phone : '+' + phone;
  const [{ data: messages, error }, { data: resident }, { data: tickets }, { data: media }] = await Promise.all([
    db.from('messages').select('*').eq('phone', phone).order('created_at', { ascending: true }),
    db.from('residents').select('full_name,building,unit').eq('phone', e164).maybeSingle(),
    // Tickets this person has, so the thread and its outcome are on one screen
    // rather than in two tabs. Filtered to this phone since 17 Sep: it used to
    // list the five newest tickets in the whole table, whoever opened them.
    db.from('requests').select('reference,description,status,created_at')
      .eq('reported_by_phone', e164)
      .order('created_at', { ascending: false }).limit(5),
    // The photos this person sent, keyed by the Chatwoot message id so each
    // lands inside the bubble it came with.
    db.from('request_media').select('message_external_id,storage_path').eq('phone', phone),
  ]);

  // Private bucket, one-hour signed URLs, one round-trip for the thread.
  const photosByMessage = new Map<string, string[]>();
  if (media?.length) {
    const { data: signed } = await db.storage.from('ticket-media')
      .createSignedUrls(media.map((m: any) => m.storage_path), 3600);
    const urlOf = new Map((signed ?? []).filter((s) => s.path && s.signedUrl)
      .map((s) => [s.path as string, s.signedUrl]));
    for (const m of media) {
      const url = urlOf.get(m.storage_path);
      if (!url) continue;
      const key = String(m.message_external_id ?? '');
      photosByMessage.set(key, [...(photosByMessage.get(key) ?? []), url]);
    }
  }

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
                {(m.body || !photosByMessage.has(String(m.external_id))) && (
                  <div dir="auto">{m.body ?? <span className="muted">({m.message_type}, no text)</span>}</div>
                )}
                {photosByMessage.has(String(m.external_id)) && (
                  <span className="thumbs">
                    {photosByMessage.get(String(m.external_id))!.map((url) => (
                      <a key={url} href={url} target="_blank" rel="noreferrer" title={tr('tickets.photo')}>
                        <img src={url} alt="" loading="lazy" />
                      </a>
                    ))}
                  </span>
                )}
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
                    <td className="mono" data-label={tr('col.reference')}>{t.reference}</td>
                    <td dir="auto" data-label={tr('col.what')}>{t.description}</td>
                    <td data-label={tr('col.status')}><span className={`pill ${t.status}`}>{label(tr, 'status', t.status)}</span></td>
                    <td className="muted mono" data-label={tr('col.opened')}>{when(t.created_at, locale)}</td>
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
