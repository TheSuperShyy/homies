import { redirect } from 'next/navigation';
import { serverClient } from '@/lib/supabase-server';
import { month, shekels } from '@/lib/money';
import { Pager, pageFrom, pageSlice, perParam, sizeFrom } from '@/components/pager';
import { callButtonEnabled, callResident, phoneNumberConnected } from '@/lib/call';
import { getLocale, translator } from '@/lib/i18n';
import { IconInbox, IconCheck, IconAlert, IconPhoneOut } from '@/components/icons';
import Link from 'next/link';

// The Call button. A person chose this resident and pressed; the agent rings
// them, once, now. Everything that decides whether that may happen lives in
// lib/call.ts and migration 024 — this action only carries the form to it and
// comes back to the same page with the answer in the URL, so there is no
// client JS and a refresh cannot press the button again.
async function placeCall(formData: FormData) {
  'use server';
  const phone = String(formData.get('phone') ?? '');
  const pin = String(formData.get('pin') ?? '');
  const back = String(formData.get('back') ?? '/debts');
  const result = await callResident(phone, pin);
  const q = new URLSearchParams({ called: phone, result });
  redirect(`${back}${back.includes('?') ? '&' : '?'}${q}`);
}

// One row per apartment, not per charge and not per person. A resident owing
// three months is one decision, so months collapse; but an owner with two flats
// owes two separate debts against two separate apartments, and "how much does
// apartment 601 owe" is the question somebody rings up to ask. Before
// migration 012 the page could not answer it — the apartment lived on the
// resident, one per phone, so a second flat had nowhere to be.
//
// The grouping happens here rather than in a view because the whole table is
// small (hundreds of charges at pilot scale) and a migration for a page is
// more moving parts than the page. The month filter rides on the same query
// for the same reason — filtering in Postgres would buy nothing at this size
// and would need a second query just to know which months exist.
type Charge = {
  period: string; amount: number; status: string; unit: string;
  residents: { full_name: string; building: string; phone: string } | null;
};

const WELL_FORMED = /^\d{4}-\d{2}$/;
const REVIEW = { disputed: 'debts.disputed', pending: 'debts.pending' } as const;

export default async function Debts({
  searchParams,
}: { searchParams?: { page?: string; month?: string; by?: string; per?: string;
                      called?: string; result?: string } }) {
  const locale = getLocale();
  const t = translator(locale);
  const page = pageFrom(searchParams);
  const size = sizeFrom(searchParams);
  // Calling exists only when a PIN is configured (lib/call.ts explains why),
  // and a number only when the Israeli line is connected. Both are facts about
  // Vercel's env, read once per render.
  const canCall = callButtonEnabled();
  const hasNumber = phoneNumberConnected();
  const outcome = searchParams?.result ?? '';
  const { data, error } = await serverClient()
    .from('charges')
    .select('period,amount,status,unit,residents(full_name,building,phone)')
    .in('status', ['unpaid', 'disputed', 'pending_charge'])
    .order('period', { ascending: true });

  const charges = (data ?? []) as unknown as Charge[];

  // The tabs are whatever months the data actually contains — nothing is
  // hardcoded, so a month appears the moment the sync writes a charge into it
  // and disappears when the last one is paid. Newest first, so the round being
  // called sits next to "all" rather than at the far end of a growing row.
  const months = [...new Set(charges.filter((c) => c.status === 'unpaid').map((c) => month(c.period)))]
    .sort().reverse();

  // No month in the URL means the newest *completed* month anybody owes for:
  // that is the round being worked. Not simply the newest month, because the
  // current month is never chased — arrears are months that have ended with
  // nothing paid against them. That tab still exists; the page just does not
  // open on it.
  //
  // This rule also used to dodge a phantom: the legacy 2022 debt, stamped with
  // the current month by a sync that had no month to use, so the newest tab
  // held one departed owner rather than the hundred who owe for last month.
  // That row was deleted on 17 Aug and `--skip-charges` stops it returning, so
  // the workaround is gone — but the rule stays, because "the current month is
  // not late yet" was always the better half of the reasoning.
  const now = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Jerusalem', year: 'numeric', month: '2-digit',
  }).formatToParts(new Date());
  const part = (t: string) => now.find((p) => p.type === t)?.value ?? '';
  const thisMonth = `${part('year')}-${part('month')}`;

  // A malformed value falls back to the default. A well-formed month that
  // nobody owes for is kept and shown empty — somebody following a bookmarked
  // link deserves "nobody owes for that month", not a silent redirect onto a
  // different month's numbers.
  const asked = searchParams?.month;
  const fallback = months.find((m) => m < thisMonth) ?? months[0] ?? 'all';
  const selected =
    asked === 'all' || (asked && WELL_FORMED.test(asked)) ? asked : fallback;
  const scoped = selected === 'all' ? charges : charges.filter((c) => month(c.period) === selected);

  // Keyed on phone *and* apartment. The separator is a character that cannot
  // occur in either, so two flats belonging to one owner can never collide and
  // an odd apartment label can never merge two people.
  const byApartment = new Map<string, {
    name: string; building: string; unit: string; phone: string;
    owed: number; months: string[]; inReview: string[];
  }>();
  for (const c of scoped) {
    if (!c.residents) continue;
    const key = `${c.residents.phone}\u0000${c.unit}`;
    const row = byApartment.get(key) ?? {
      name: c.residents.full_name, building: c.residents.building,
      unit: c.unit, phone: c.residents.phone,
      owed: 0, months: [], inReview: [],
    };
    if (c.status === 'unpaid') {
      row.owed += Number(c.amount);
      row.months.push(month(c.period));
    } else {
      row.inReview.push(
        `${month(c.period)} (${t(REVIEW[c.status === 'disputed' ? 'disputed' : 'pending'])})`);
    }
    byApartment.set(key, row);
  }
  const apartments = [...byApartment.values()].sort((a, b) => b.owed - a.owed);

  // What every apartment row needs to know about its owner. Sorting by amount
  // scatters one owner's flats across pages — the ₪5,572 one lands third and
  // the ₪1,838 one lands on page two — so without this a reader has no way to
  // tell that two rows are one phone call, or what that call is really worth.
  const owners = new Map<string, { units: string[]; total: number }>();
  for (const r of apartments) {
    const o = owners.get(r.phone) ?? { units: [], total: 0 };
    o.units.push(r.unit);
    o.total += r.owed;
    owners.set(r.phone, o);
  }

  // One row per owner: their flats merged, months deduped across them. This is
  // the view for deciding what to say when you ring somebody; the apartment
  // view is for answering what a given flat owes. Both are real questions, so
  // both are a URL rather than one being the truth.
  const byOwner = new Map<string, typeof apartments[number] & { units: string[] }>();
  for (const r of apartments) {
    const o = byOwner.get(r.phone);
    if (!o) {
      byOwner.set(r.phone, { ...r, units: [r.unit], months: [...r.months],
                             inReview: [...r.inReview] });
      continue;
    }
    o.units.push(r.unit);
    o.owed += r.owed;
    for (const m of r.months) if (!o.months.includes(m)) o.months.push(m);
    o.inReview.push(...r.inReview);
    if (!o.building.includes(r.building)) o.building += `, ${r.building}`;
  }

  const byOwnerView = searchParams?.by === 'owner';
  const rows = byOwnerView
    ? [...byOwner.values()].sort((a, b) => b.owed - a.owed)
    : apartments;

  // Totals are over every apartment that owes in the selected month, never over
  // the visible page — a figure that changed when you turned the page would be
  // worse than none. Taken from `apartments` in both views so the cards do not
  // move when the toggle does: the money owed is the same either way.
  const total = apartments.reduce((s, r) => s + r.owed, 0);
  const visible = pageSlice(rows, page, size);

  // Apartments and people are both counted, because they stopped being the
  // same number: 108 flats owe for July, held by 106 owners.
  const owing = apartments.filter((r) => r.owed > 0);
  const cards = [
    ['is-money', selected === 'all' ? t('debts.totalOpen') : t('debts.openIn', { month: selected }), shekels(total)],
    ['is-open',  t('debts.apartments'), owing.length],
    ['is-open',  t('debts.residents'),  new Set(owing.map((r) => r.phone)).size],
    ['',         t('debts.inReview'),   apartments.reduce((acc, r) => acc + r.inReview.length, 0)],
  ] as const;

  const tabs = ['all', ...months];

  // Month, view and size are three independent choices, and every link here
  // has to carry the two it is not changing — the month already survived the
  // toggle before the size existed, and the size has to survive both.
  const per = perParam(size);
  const link = (month: string, owner: boolean) => {
    const q = new URLSearchParams({ month });
    if (owner) q.set('by', 'owner');
    if (per) q.set('per', per);
    return `/debts?${q}`;
  };

  return (
    <>
      <div className="pagehead"><h1>{t('debts.title')}</h1></div>
      <div className="filters">
        <nav className="seg" aria-label={t('col.period')}>
          {tabs.map((m) => (
            <Link key={m} href={link(m, byOwnerView)}
               aria-current={selected === m ? 'true' : undefined}>
              {m === 'all' ? t('status.all') : m}
            </Link>
          ))}
        </nav>
        {/* The month survives the toggle and the toggle survives the month:
            either one resetting the other would make the pair unusable. */}
        <nav className="seg" aria-label={t('debts.byApartment')}>
          {([['apartment', t('debts.byApartment')], ['owner', t('debts.byOwner')]] as const)
            .map(([v, lab]) => (
              <Link key={v} href={link(selected, v === 'owner')}
                 aria-current={byOwnerView === (v === 'owner') ? 'true' : undefined}>
                {lab}
              </Link>
            ))}
        </nav>
      </div>

      {/* What happened to the last press, from the URL the action came back
          with. ok: the call id Vapi returned; err: a sentence a person can act
          on. Shown once — it is part of the URL, so a bookmark carries it,
          which is preferable to a toast nobody was looking at. */}
      {outcome && (
        <div className={`notice ${outcome.startsWith('ok:') ? 'ok' : 'bad'}`} role="status">
          {outcome.startsWith('ok:') ? <IconCheck /> : <IconAlert />}
          <span>
            {outcome.startsWith('ok:')
              ? t('debts.calling', { phone: searchParams?.called ?? '', id: outcome.slice(3) || '—' })
              : t('debts.notCalled', { phone: searchParams?.called ?? '', why: outcome.replace(/^err:/, '') })}
          </span>
        </div>
      )}

      <div className="cards">
        {cards.map(([tone, k, v]) => (
          <div className={`card ${tone}`} key={k}>
            <div className="n">{v}</div>
            <div className="k">{k}</div>
          </div>
        ))}
      </div>

      <h2>{byOwnerView ? t('debts.headOwner') : t('debts.headApartment')}</h2>
      <Pager page={page} size={size} total={rows.length} basePath="/debts"
             params={{ month: selected, by: byOwnerView ? 'owner' : undefined }}
             unit={byOwnerView ? t('debts.unitRes') : t('debts.unitAp')} t={t} />
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {rows.length ? (
          <div className="scrollx">
          <table>
            <thead><tr>
              <th>{t('col.resident')}</th><th>{t('col.building')}</th>
              <th>{byOwnerView ? t('debts.colApartments') : t('debts.colApartment')}</th>
              <th>{t('col.phone')}</th>
              {selected === 'all' && <th>{t('debts.monthsOwed')}</th>}
              <th>{t('debts.inReview')}</th>
              <th>{selected === 'all' ? t('debts.owed') : t('debts.owedIn', { month: selected })}</th>
              {canCall && <th>{t('debts.call')}</th>}
            </tr></thead>
            <tbody>
              {visible.map((r) => {
                const owner = owners.get(r.phone);
                const others = (owner?.units ?? []).filter((u) => u !== r.unit);
                return (
                <tr key={byOwnerView ? r.phone : `${r.phone} ${r.unit}`}>
                  <td dir="auto" data-label={t('col.resident')}>{r.name}</td>
                  <td dir="auto" data-label={t('col.building')}>{r.building}</td>
                  {/* From the charge, not the resident. In apartment view an
                      owner of two flats has two rows, and the marker is what
                      stops them reading as two unrelated people a page apart. */}
                  <td dir="auto" className="mono"
                      data-label={byOwnerView ? t('debts.colApartments') : t('debts.colApartment')}>
                    {byOwnerView
                      ? ((r as any).units.join(', ') || '—')
                      : (r.unit || '—')}
                    {!byOwnerView && others.length > 0 && (
                      <span className="sub">
                        {t('debts.alsoApt', { units: others.join(', '), total: shekels(owner!.total) })}
                      </span>
                    )}
                  </td>
                  <td className="mono" data-label={t('col.phone')}>{r.phone}</td>
                  {/* Dropped under a month filter: it would be the selected
                      month repeated on every row. */}
                  {/* Sorted here rather than relied on: in owner view the
                      months arrive merged from flats ordered by amount, so
                      the query's period ordering no longer holds. */}
                  {selected === 'all' &&
                    <td className="muted mono" data-label={t('debts.monthsOwed')}>{[...r.months].sort().join(', ') || '—'}</td>}
                  <td className="muted" data-label={t('debts.inReview')}>{r.inReview.join(', ') || '—'}</td>
                  <td className="mono num"
                      data-label={selected === 'all' ? t('debts.owed') : t('debts.owedIn', { month: selected })}>{r.owed ? shekels(r.owed) : '—'}</td>
                  {/* One press, one call, this resident. The PIN is typed
                      every time on purpose: this page has no login, and the
                      cost of a mistaken press is a resident's phone ringing
                      about money. In owner view the row already is the whole
                      call; in apartment view it is too — the agent gets every
                      flat the owner owes on, so pressing on either row of a
                      two-flat owner places the same call. */}
                  {canCall && (
                    <td data-label={t('debts.call')}>
                      {hasNumber && r.owed > 0 ? (
                        <form action={placeCall} className="status-edit">
                          <input type="hidden" name="phone" value={r.phone} />
                          <input type="hidden" name="back" value={link(selected, byOwnerView)} />
                          <input type="password" name="pin" placeholder={t('debts.pin')} required
                                 inputMode="numeric" autoComplete="off"
                                 aria-label={t('debts.pin')} />
                          <button type="submit" className="btn-sm">
                            <IconPhoneOut />{t('debts.callBtn')}
                          </button>
                        </form>
                      ) : (
                        <span className="muted" style={{ fontSize: 12 }}>
                          {r.owed > 0 ? t('debts.noNumber') : '—'}
                        </span>
                      )}
                    </td>
                  )}
                </tr>
                );
              })}
            </tbody>
          </table>
          </div>
        ) : !error && (
          <div className="empty">
            <IconInbox />
            <div>{selected === 'all'
              ? t('debts.emptyAll')
              : t('debts.emptyMonth', { month: selected })}</div>
          </div>
        )}
      </div>
    </>
  );
}
