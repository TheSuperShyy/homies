import { serverClient } from '@/lib/supabase-server';
import { Pager, pageFrom, pageSlice } from '@/components/pager';

// One row per resident, not per charge: the person reading this is deciding
// who to chase, and a resident owing three months is one decision, not three.
// The grouping happens here rather than in a view because the whole table is
// small (hundreds of charges at pilot scale) and a migration for a page is
// more moving parts than the page. The month filter rides on the same query
// for the same reason — filtering in Postgres would buy nothing at this size
// and would need a second query just to know which months exist.
type Charge = {
  period: string; amount: number; status: string;
  residents: { full_name: string; building: string; unit: string; phone: string } | null;
};

const month = (p: string) => p.slice(0, 7);
const shekels = (n: number) => '₪' + n.toLocaleString('en-US');
const WELL_FORMED = /^\d{4}-\d{2}$/;

export default async function Debts({
  searchParams,
}: { searchParams?: { page?: string; month?: string } }) {
  const page = pageFrom(searchParams);
  const { data, error } = await serverClient()
    .from('charges')
    .select('period,amount,status,residents(full_name,building,unit,phone)')
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
  // nothing paid against them — and today the newest month carrying a charge
  // is the legacy 2022 debt stamped with the current month by a sync that had
  // no month to use. Landing there would show one phantom debtor instead of
  // the hundred who owe for the month just gone. That tab still exists; the
  // page just does not open on it.
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

  const byResident = new Map<string, {
    name: string; building: string; unit: string; phone: string;
    owed: number; months: string[]; inReview: string[];
  }>();
  for (const c of scoped) {
    if (!c.residents) continue;
    const key = c.residents.phone;
    const row = byResident.get(key) ?? {
      name: c.residents.full_name, building: c.residents.building,
      unit: c.residents.unit, phone: c.residents.phone,
      owed: 0, months: [], inReview: [],
    };
    if (c.status === 'unpaid') {
      row.owed += Number(c.amount);
      row.months.push(month(c.period));
    } else {
      row.inReview.push(`${month(c.period)} (${c.status === 'disputed' ? 'disputed' : 'pending'})`);
    }
    byResident.set(key, row);
  }
  // Totals are over everybody who owes in the selected month, never over the
  // visible page — a figure that changed when you turned the page would be
  // worse than none.
  const rows = [...byResident.values()].sort((a, b) => b.owed - a.owed);
  const total = rows.reduce((s, r) => s + r.owed, 0);
  const visible = pageSlice(rows, page);

  const cards = [
    [selected === 'all' ? 'Total open' : `Open in ${selected}`, shekels(total)],
    ['Residents owing', rows.filter((r) => r.owed > 0).length],
    ['In review', rows.reduce((s, r) => s + r.inReview.length, 0)],
  ] as const;

  const tabs = ['all', ...months];

  return (
    <>
      <h1>Open balances</h1>
      <nav style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        {tabs.map((t) => (
          <a key={t} href={`/debts?month=${t}`} className="pill"
             style={{ opacity: selected === t ? 1 : 0.55 }}>
            {t}
          </a>
        ))}
      </nav>

      <div className="cards">
        {cards.map(([k, n]) => (
          <div className="card" key={k}>
            <div className="n">{n}</div>
            <div className="k">{k}</div>
          </div>
        ))}
      </div>

      <h2>By resident, largest first</h2>
      <div className="panel">
        {error && <div className="empty">{error.message}</div>}
        {rows.length ? (
          <table>
            <thead><tr>
              <th>Resident</th><th>Building</th><th>Phone</th>
              {selected === 'all' && <th>Months owed</th>}
              <th>In review</th>
              <th>{selected === 'all' ? 'Owed' : `Owed (${selected})`}</th>
            </tr></thead>
            <tbody>
              {visible.map((r) => (
                <tr key={r.phone}>
                  <td dir="auto">{r.name}</td>
                  <td dir="auto">{r.building}{r.unit ? ` · ${r.unit}` : ''}</td>
                  <td className="mono">{r.phone}</td>
                  {/* Dropped under a month filter: it would be the selected
                      month repeated on every row. */}
                  {selected === 'all' &&
                    <td className="muted mono">{r.months.join(', ') || '—'}</td>}
                  <td className="muted">{r.inReview.join(', ') || '—'}</td>
                  <td className="mono">{r.owed ? shekels(r.owed) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : !error && (
          <div className="empty">
            {selected === 'all' ? 'Nobody owes anything.' : `Nobody owes for ${selected}.`}
          </div>
        )}
      </div>
      <Pager page={page} total={rows.length} basePath="/debts"
             params={{ month: selected }} unit="residents" />
    </>
  );
}
