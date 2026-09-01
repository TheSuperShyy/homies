import Link from 'next/link';
import { serverClient } from '@/lib/supabase-server';
import { getLocale, label, translator, when, type Locale, type T } from '@/lib/i18n';
import { IconInbox, IconOpenLink, IconSearch } from '@/components/icons';
import { month, shekels } from '@/lib/money';

/**
 * One box for the whole dashboard.
 *
 * WHAT IT REPLACED. The header carried a search pill from the day the shell was
 * rebuilt, drawn to the design system's Input spec, disabled, and labelled
 * "Soon". It was honest about being empty and it stayed empty, which is the
 * same thing the notification bell was doing before it was removed.
 *
 * WHAT IT SEARCHES, AND WHY THESE FOUR. A ticket by its reference or its
 * description; a resident by name, phone, building or apartment; the words
 * inside a WhatsApp message; and what a call was about, including its
 * transcript. Those are the four things somebody at Homies knows when they pick
 * up the phone and do not know where to look — a name, a number, half a
 * sentence somebody said. Everything else on this dashboard is reachable by
 * filtering a list you already chose.
 *
 * NO CLIENT JAVASCRIPT. A GET form, the query in the URL, results rendered on
 * the server — so a search is a link you can send a colleague, which is the
 * convention every other filter here already follows.
 */

/** Newest first, capped. A search is a way in, not a report. */
const LIMIT = 8;

/**
 * Make a typed phrase safe to put inside PostgREST's `or=(…)`.
 *
 * That filter is a comma-separated list wrapped in parentheses, so a comma or a
 * bracket in the phrase does not fail — it silently reinterprets the rest of
 * the query as more filter clauses. `%` and `_` are `ilike`'s own wildcards and
 * would otherwise let a stray underscore match anything. All of it becomes
 * whitespace rather than being escaped: this is a search box, and a reader who
 * types a comma means "and also", not "close this filter clause".
 */
function term(raw: string) {
  return raw.replace(/[,()"'\\%_*]/g, ' ').replace(/\s+/g, ' ').trim();
}

/** Enough of a long message to recognise it, and no more. */
function clip(s: string | null | undefined, n = 160) {
  if (!s) return '—';
  const one = s.replace(/\s+/g, ' ').trim();
  return one.length > n ? one.slice(0, n - 1) + '…' : one;
}

/**
 * The line under a panel that admits it is showing only the first few.
 *
 * A results list that quietly stops at eight is a results list that tells you
 * there are eight. Only the calls page can take the query onward — it has its
 * own full-text filter — so only that line is a link; the others say the number
 * and leave it, which is honest about what exists.
 */
function More({ shown, total, href, t }: {
  shown: number; total: number; href?: string; t: T;
}) {
  if (total <= shown) return null;
  const text = t('search.showing', { shown: String(shown), total: String(total) });
  return (
    <p className="setnote">
      {href ? <Link href={href} style={{ color: 'var(--accent)' }}>{text}</Link> : text}
    </p>
  );
}

function Section({ title, count, children }: {
  title: string; count: number; children: React.ReactNode;
}) {
  if (!count) return null;
  return (
    <section>
      <h2>{title} · {count}</h2>
      <div className="panel">{children}</div>
    </section>
  );
}

export default async function Search({ searchParams }: {
  searchParams?: { q?: string };
}) {
  const locale: Locale = getLocale();
  const t = translator(locale);

  const raw = (searchParams?.q ?? '').trim();
  const cleaned = term(raw);
  // Two characters, because one matches most of the database and the reader
  // learns nothing from a page of everything.
  const ready = cleaned.length >= 2;
  const like = `%${cleaned}%`;

  const db = serverClient();

  // Four independent queries, so they go together rather than one after
  // another — the slowest one sets the wait, not the sum of them.
  const [tickets, residents, msgs, calls, charges] = ready
    ? await Promise.all([
        db.from('requests')
          .select('reference,description,building,unit,status,urgency,created_at',
                  { count: 'exact' })
          .or([
            `reference.ilike.${like}`, `description.ilike.${like}`,
            `building.ilike.${like}`, `unit.ilike.${like}`,
            `reported_by_name.ilike.${like}`, `reported_by_phone.ilike.${like}`,
            `category_he.ilike.${like}`, `oxs_ref.ilike.${like}`,
          ].join(','))
          .order('created_at', { ascending: false }).limit(LIMIT),

        db.from('residents')
          .select('id,full_name,phone,building,unit', { count: 'exact' })
          .or([
            `full_name.ilike.${like}`, `phone.ilike.${like}`,
            `building.ilike.${like}`, `unit.ilike.${like}`,
          ].join(','))
          .order('full_name').limit(LIMIT),

        db.from('messages')
          .select('id,phone,body,sender,created_at', { count: 'exact' })
          .ilike('body', like)
          .order('created_at', { ascending: false }).limit(LIMIT),

        db.from('interactions')
          .select('id,caller_phone,summary,disposition,started_at', { count: 'exact' })
          .eq('channel', 'voice')
          .or([
            `summary.ilike.${like}`, `transcript.ilike.${like}`,
            `caller_phone.ilike.${like}`, `external_call_id.ilike.${like}`,
          ].join(','))
          .order('started_at', { ascending: false }).limit(LIMIT),
        // WHAT A NAME OWES, BY MONTH.
        //
        // Joined from `charges` through the resident rather than filtered by
        // the ids of the residents panel above. That was the first attempt and
        // it was quietly wrong: the panel is capped at LIMIT and ordered by
        // name, so a search for `גולן` listed eight Golans, none of whom
        // happened to owe anything, and reported no debt — while דניאלה גולן,
        // ninth alphabetically, owed ₪14,976. A section that answers "does this
        // person owe" must not depend on where their surname sorts.
        //
        // Unpaid only. `status` also carries paid, disputed, waived and
        // pending_charge, and only one of those is a debt — a total quietly
        // including a waived month gets somebody chased for money they do not
        // owe.
        db.from('charges')
          .select('period,amount,unit,residents!inner(id,full_name,building,unit)')
          .eq('status', 'unpaid')
          .or([
            `full_name.ilike.${like}`, `phone.ilike.${like}`,
            `building.ilike.${like}`, `unit.ilike.${like}`,
          ].join(','), { referencedTable: 'residents' })
          .order('period', { ascending: true })
          .limit(500),
      ])
    : [null, null, null, null, null];

  // One entry per resident who owes, biggest first — the reason somebody
  // searched a surname is almost always the largest number under it.
  //
  // `charges.unit` before `residents.unit`: migration 012 put the apartment on
  // the charge because an owner can hold several, and the resident row names
  // only one of them.
  type Owed = {
    id: string; name: string | null; building: string | null;
    months: { period: string; amount: number; unit: string | null }[];
    total: number;
  };
  const byResident = new Map<string, Owed>();
  for (const c of (charges?.data ?? []) as any[]) {
    const p = c.residents;
    if (!p) continue;
    let g = byResident.get(p.id);
    if (!g) {
      g = { id: p.id, name: p.full_name, building: p.building, months: [], total: 0 };
      byResident.set(p.id, g);
    }
    g.months.push({ period: c.period, amount: Number(c.amount), unit: c.unit || p.unit || null });
    g.total += Number(c.amount);
  }
  const owingAll = [...byResident.values()].sort((a, b) => b.total - a.total);
  const owing = owingAll.slice(0, LIMIT);

  const counts = [tickets, residents, msgs, calls]
    .reduce((n, r) => n + (r?.count ?? 0), 0) + owingAll.length;
  const failed = [tickets, residents, msgs, calls, charges].find((r) => r?.error)?.error;

  return (
    <>
      <div className="pagehead">
        <h1>{t('search.title')}</h1>
        <p>{t('search.blurb')}</p>
      </div>

      <form method="get" action="/search" className="search">
        <input name="q" defaultValue={raw} dir="auto" autoFocus
               aria-label={t('search.title')} placeholder={t('chrome.search')} />
        <button type="submit"><IconSearch />{t('search.go')}</button>
      </form>

      {failed && <div className="notice bad"><span>{failed.message}</span></div>}

      {!ready ? (
        <div className="panel">
          <div className="empty">
            <IconSearch />
            <div>{raw ? t('search.short') : t('search.prompt')}</div>
            <div style={{ fontSize: 13, marginBlockStart: 4 }}>{t('search.promptHint')}</div>
          </div>
        </div>
      ) : counts === 0 ? (
        <div className="panel">
          <div className="empty">
            <IconInbox />
            <div>{t('search.none', { q: raw })}</div>
            <div style={{ fontSize: 13, marginBlockStart: 4 }}>{t('search.noneHint')}</div>
          </div>
        </div>
      ) : (
        <div className="setcol">
          <Section title={t('search.tickets')} count={tickets?.count ?? 0}>
            <div className="scrollx">
              <table>
                <thead><tr>
                  <th>{t('col.reference')}</th><th>{t('col.what')}</th>
                  <th>{t('col.where')}</th><th>{t('col.status')}</th>
                  <th>{t('col.opened')}</th>
                </tr></thead>
                <tbody>
                  {(tickets?.data ?? []).map((r: any) => (
                    <tr key={r.reference}>
                      <td className="mono" data-label={t('col.reference')}>{r.reference}</td>
                      <td dir="auto" data-label={t('col.what')}>{clip(r.description)}</td>
                      <td dir="auto" data-label={t('col.where')}>
                        {r.building}{r.unit ? ` · ${r.unit}` : ''}
                      </td>
                      <td data-label={t('col.status')}>
                        <span className={`pill ${r.status}`}>{label(t, 'status', r.status)}</span>
                      </td>
                      <td className="muted mono" data-label={t('col.opened')}>
                        {when(r.created_at, locale)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <More shown={tickets?.data?.length ?? 0} total={tickets?.count ?? 0} t={t} />
          </Section>

          {/* Above Residents on purpose: somebody who typed a name and is
              owed money wants the number, and the resident's contact details
              are the thing they look at second. */}
          <Section title={t('search.debt')} count={owingAll.length}>
            <div className="scrollx">
              <table>
                <thead><tr>
                  <th>{t('col.resident')}</th><th>{t('col.where')}</th>
                  <th>{t('debts.monthsOwed')}</th><th>{t('debts.owed')}</th>
                </tr></thead>
                <tbody>
                  {owing.map((r) => (
                    <tr key={r.id}>
                      <td dir="auto" data-label={t('col.resident')}>{r.name ?? '—'}</td>
                      <td dir="auto" data-label={t('col.where')}>{r.building ?? '—'}</td>
                      {/* Every month listed with its own amount, not just a
                          count. The rates are not equal month to month — a flat
                          that joined mid-year, or a rate that changed, shows up
                          here and nowhere else on the dashboard. */}
                      <td data-label={t('debts.monthsOwed')}>
                        <div className="months">
                          {r.months.map((m) => (
                            <span key={m.period + m.unit} className="mono">
                              {month(m.period)}
                              <span className="muted">{' '}{shekels(m.amount)}</span>
                              {/* Only when an owner's charges span more than
                                  one flat, which is the case migration 012
                                  exists for. Printing it always would put the
                                  same apartment on every line. */}
                              {new Set(r.months.map((x) => x.unit)).size > 1 && m.unit && (
                                <span className="muted" dir="auto">{' · '}{m.unit}</span>
                              )}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="mono num" data-label={t('debts.owed')}>{shekels(r.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <More shown={owing.length} total={owingAll.length} t={t} />
          </Section>

          <Section title={t('search.residents')} count={residents?.count ?? 0}>
            <div className="scrollx">
              <table>
                <thead><tr>
                  <th>{t('col.resident')}</th><th>{t('col.phone')}</th>
                  <th>{t('col.building')}</th><th>{t('col.unit')}</th><th></th>
                </tr></thead>
                <tbody>
                  {(residents?.data ?? []).map((r: any) => (
                    <tr key={r.id}>
                      <td dir="auto" data-label={t('col.resident')}>{r.full_name ?? '—'}</td>
                      <td className="mono" data-label={t('col.phone')}>{r.phone ?? '—'}</td>
                      <td dir="auto" data-label={t('col.building')}>{r.building ?? '—'}</td>
                      <td className="mono" data-label={t('col.unit')}>{r.unit ?? '—'}</td>
                      {/* There is no resident page, and this is the nearest
                          thing to one: it carries their details in a side panel
                          and their recent tickets under the thread, and it
                          handles having no messages. */}
                      <td data-label="">
                        {r.phone && (
                          <Link className="btn-sm"
                                href={`/conversations/${encodeURIComponent(r.phone)}`}>
                            <IconOpenLink />{t('search.openResident')}
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <More shown={residents?.data?.length ?? 0} total={residents?.count ?? 0} t={t} />
          </Section>

          <Section title={t('search.messages')} count={msgs?.count ?? 0}>
            <div className="scrollx">
              <table>
                <thead><tr>
                  <th>{t('col.when')}</th><th>{t('search.said')}</th>
                  <th>{t('col.phone')}</th><th></th>
                </tr></thead>
                <tbody>
                  {(msgs?.data ?? []).map((m: any) => (
                    <tr key={m.id}>
                      <td className="muted mono" data-label={t('col.when')}>
                        {when(m.created_at, locale)}
                      </td>
                      <td dir="auto" data-label={t('search.said')}>
                        {clip(m.body)}
                        <span className="sub">
                          {m.sender === 'resident' ? t('thread.resident') : t('thread.bot')}
                        </span>
                      </td>
                      <td className="mono" data-label={t('col.phone')}>{m.phone ?? '—'}</td>
                      <td data-label="">
                        {m.phone && (
                          <Link className="btn-sm"
                                href={`/conversations/${encodeURIComponent(m.phone)}`}>
                            <IconOpenLink />{t('search.openThread')}
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <More shown={msgs?.data?.length ?? 0} total={msgs?.count ?? 0} t={t} />
          </Section>

          <Section title={t('search.calls')} count={calls?.count ?? 0}>
            <div className="scrollx">
              <table>
                <thead><tr>
                  <th>{t('col.when')}</th><th>{t('col.number')}</th>
                  <th>{t('col.summary')}</th><th>{t('col.outcome')}</th><th></th>
                </tr></thead>
                <tbody>
                  {(calls?.data ?? []).map((c: any) => (
                    <tr key={c.id}>
                      <td className="muted mono" data-label={t('col.when')}>
                        {when(c.started_at, locale)}
                      </td>
                      <td className="mono" data-label={t('col.number')}>{c.caller_phone ?? '—'}</td>
                      <td dir="auto" data-label={t('col.summary')}>
                        {c.summary ? clip(c.summary) : <span className="muted">{t('calls.noSummary')}</span>}
                      </td>
                      <td className="muted" data-label={t('col.outcome')}>{c.disposition ?? '—'}</td>
                      <td data-label="">
                        <Link className="btn-sm" href={`/calls/${c.id}`}>
                          <IconOpenLink />{t('calls.view')}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* The one section whose list page can take the query onward. */}
            <More shown={calls?.data?.length ?? 0} total={calls?.count ?? 0} t={t}
                  href={`/calls?q=${encodeURIComponent(raw)}`} />
          </Section>
        </div>
      )}
    </>
  );
}
