import { serverClient } from '@/lib/supabase-server';
import { Pager, pageFrom, pageRange, sizeFrom } from '@/components/pager';
import { getLocale, translator, when } from '@/lib/i18n';
import { IconInbox } from '@/components/icons';
import Link from 'next/link';

export default async function Conversations({
  searchParams,
}: { searchParams?: { page?: string; per?: string } }) {
  const locale = getLocale();
  const t = translator(locale);
  const page = pageFrom(searchParams);
  const size = sizeFrom(searchParams);
  const [from, to] = pageRange(page, size);
  const { data, error, count } = await serverClient()
    .from('v_conversations').select('*', { count: 'exact' })
    .order('last_message_at', { ascending: false }).range(from, to);

  return (
    <>
      <div className="pagehead"><h1>{t('convos.title')}</h1></div>
      <Pager page={page} size={size} total={count ?? 0} basePath="/conversations"
             unit={t('convos.unit')} t={t} />
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {data?.length ? (
          <div className="scrollx">
          <table>
            <thead><tr>
              <th>{t('convos.who')}</th><th>{t('convos.last')}</th><th>{t('convos.count')}</th>
              <th>{t('convos.lang')}</th><th>{t('convos.human')}</th><th>{t('convos.activity')}</th>
            </tr></thead>
            <tbody>
              {data.map((c: any) => (
                <tr key={c.phone}>
                  <td data-label={t('convos.who')}>
                    <Link href={`/conversations/${encodeURIComponent(c.phone)}`}>
                      {/* A name when the phone matches a resident, the number
                          when it does not. An unmatched number is a signal, not
                          a blank: it means somebody outside the imported list
                          is writing in. */}
                      {c.full_name ?? <span className="mono">{c.phone}</span>}
                      {c.building && <span className="sub" dir="auto">{c.building}{c.unit ? ` · ${c.unit}` : ''}</span>}
                    </Link>
                  </td>
                  <td dir="auto" data-label={t('convos.last')}>{c.last_message}</td>
                  <td className="mono" data-label={t('convos.count')}>{c.message_count}<span className="muted"> / {c.from_resident} in</span></td>
                  <td className="muted" data-label={t('convos.lang')}>{c.lang ?? '—'}</td>
                  <td data-label={t('convos.human')}>{c.touched_by_human
                    ? <span className="pill in_progress">{t('convos.yes')}</span>
                    : <span className="muted">{t('convos.botOnly')}</span>}</td>
                  <td className="muted mono" data-label={t('convos.activity')}>{when(c.last_message_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : !error && (
          <div className="empty">
            <IconInbox />
            <div>{t('convos.empty')}</div>
          </div>
        )}
      </div>
    </>
  );
}
