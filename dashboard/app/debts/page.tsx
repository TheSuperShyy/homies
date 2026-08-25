import { redirect } from 'next/navigation';
import { serverClient } from '@/lib/supabase-server';
import { Pager, pageFrom, pageSlice, perParam, sizeFrom } from '@/components/pager';
import { callButtonEnabled, callResident, phoneNumberConnected } from '@/lib/call';

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

const month = (p: string) => p.slice(0, 7);
// Whole shekels. Monthly rates from OXS carry agorot (683.4), and a total of
// ₪105,760.7 on a card reads as a typo, not as precision anybody wanted.
const shekels = (n: number) => '₪' + Math.round(n).toLocaleString('en-US');
const WELL_FORMED = /^\d{4}-\d{2}$/;

export default async function Debts({
  searchParams,
}: { searchParams?: { page?: string; month?: string; by?: string; per?: string;
                      called?: string; result?: string } }) {
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
      row.inReview.push(`${month(c.period)} (${c.status === 'disputed' ? 'disputed' : 'pending'})`);
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
    [selected === 'all' ? 'Total open' : `Open in ${selected}`, shekels(total)],
    ['Apartments owing', owing.length],
    ['Residents owing', new Set(owing.map((r) => r.phone)).size],
    ['In review', apartments.reduce((s, r) => s + r.inReview.length, 0)],
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
      <h1>Open balances</h1>
      <nav style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap',
                    alignItems: 'center' }}>
        {tabs.map((t) => (
          <a key={t} href={link(t, byOwnerView)}
             className="pill" style={{ opacity: selected === t ? 1 : 0.55 }}>
            {t}
          </a>
        ))}
        <span style={{ flex: 1 }} />
        {/* The month survives the toggle and the toggle survives the month —
            either one resetting the other would make the pair unusable. */}
        {[['apartment', 'by apartment'], ['owner', 'by owner']].map(([v, label]) => (
          <a key={v} href={link(selected, v === 'owner')}
             className="pill"
             style={{ opacity: byOwnerView === (v === 'owner') ? 1 : 0.55 }}>
            {label}
          </a>
        ))}
      </nav>

      {/* What happened to the last press, from the URL the action came back
          with. ok: the call id Vapi returned; err: a sentence a person can act
          on. Shown once — it is part of the URL, so a bookmark carries it,
          which is preferable to a toast nobody was looking at. */}
      {outcome && (
        <div className="panel" style={{ padding: '10px 14px', marginBottom: 14,
                                        borderColor: outcome.startsWith('ok:') ? 'var(--ok, #2a7)' : 'var(--review)' }}>
          {outcome.startsWith('ok:')
            ? <>Calling <span className="mono">{searchParams?.called}</span> now — call <span className="mono">{outcome.slice(3) || '(no id)'}</span>. It will appear under Calls when it ends.</>
            : <>Did not call <span className="mono">{searchParams?.called}</span>: {outcome.replace(/^err:/, '')}</>}
        </div>
      )}

      <div className="cards">
        {cards.map(([k, n]) => (
          <div className="card" key={k}>
            <div className="n">{n}</div>
            <div className="k">{k}</div>
          </div>
        ))}
      </div>

      <h2>{byOwnerView ? 'By resident, largest first' : 'By apartment, largest first'}</h2>
      <Pager page={page} size={size} total={rows.length} basePath="/debts"
             params={{ month: selected, by: byOwnerView ? 'owner' : undefined }}
             unit={byOwnerView ? 'residents' : 'apartments'} />
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {rows.length ? (
          <table>
            <thead><tr>
              <th>Resident</th><th>Building</th>
              <th>{byOwnerView ? 'Apartments' : 'Apartment'}</th><th>Phone</th>
              {selected === 'all' && <th>Months owed</th>}
              <th>In review</th>
              <th>{selected === 'all' ? 'Owed' : `Owed (${selected})`}</th>
              {canCall && <th>Call</th>}
            </tr></thead>
            <tbody>
              {visible.map((r) => {
                const owner = owners.get(r.phone);
                const others = (owner?.units ?? []).filter((u) => u !== r.unit);
                return (
                <tr key={byOwnerView ? r.phone : `${r.phone} ${r.unit}`}>
                  <td dir="auto">{r.name}</td>
                  <td dir="auto">{r.building}</td>
                  {/* From the charge, not the resident. In apartment view an
                      owner of two flats has two rows, and the marker is what
                      stops them reading as two unrelated people a page apart. */}
                  <td dir="auto" className="mono">
                    {byOwnerView
                      ? ((r as any).units.join(', ') || '—')
                      : (r.unit || '—')}
                    {!byOwnerView && others.length > 0 && (
                      <span className="muted" style={{ fontSize: 12, marginInlineStart: 6 }}>
                        · also apt {others.join(', ')} · {shekels(owner!.total)} total
                      </span>
                    )}
                  </td>
                  <td className="mono">{r.phone}</td>
                  {/* Dropped under a month filter: it would be the selected
                      month repeated on every row. */}
                  {/* Sorted here rather than relied on: in owner view the
                      months arrive merged from flats ordered by amount, so
                      the query's period ordering no longer holds. */}
                  {selected === 'all' &&
                    <td className="muted mono">{[...r.months].sort().join(', ') || '—'}</td>}
                  <td className="muted">{r.inReview.join(', ') || '—'}</td>
                  <td className="mono">{r.owed ? shekels(r.owed) : '—'}</td>
                  {/* One press, one call, this resident. The PIN is typed
                      every time on purpose: this page has no login, and the
                      cost of a mistaken press is a resident's phone ringing
                      about money. In owner view the row already is the whole
                      call; in apartment view it is too — the agent gets every
                      flat the owner owes on, so pressing on either row of a
                      two-flat owner places the same call. */}
                  {canCall && (
                    <td>
                      {hasNumber && r.owed > 0 ? (
                        <form action={placeCall} className="status-edit">
                          <input type="hidden" name="phone" value={r.phone} />
                          <input type="hidden" name="back" value={link(selected, byOwnerView)} />
                          <input type="password" name="pin" placeholder="PIN" required
                                 inputMode="numeric" autoComplete="off"
                                 style={{ width: 56 }} />
                          <button type="submit" className="pill">call</button>
                        </form>
                      ) : (
                        <span className="muted" style={{ fontSize: 12 }}>
                          {r.owed > 0 ? 'no number yet' : '—'}
                        </span>
                      )}
                    </td>
                  )}
                </tr>
                );
              })}
            </tbody>
          </table>
        ) : !error && (
          <div className="empty">
            {selected === 'all' ? 'Nobody owes anything.' : `Nobody owes for ${selected}.`}
          </div>
        )}
      </div>
    </>
  );
}
