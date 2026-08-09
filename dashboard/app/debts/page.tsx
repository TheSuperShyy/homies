import { serverClient } from '@/lib/supabase-server';

// One row per resident, not per charge: the person reading this is deciding
// who to chase, and a resident owing three months is one decision, not three.
// The grouping happens here rather than in a view because the whole table is
// small (hundreds of charges at pilot scale) and a migration for a page is
// more moving parts than the page.
type Charge = {
  period: string; amount: number; status: string;
  residents: { full_name: string; building: string; unit: string; phone: string } | null;
};

const month = (p: string) => p.slice(0, 7);
const shekels = (n: number) => '₪' + n.toLocaleString('en-US');

export default async function Debts() {
  const { data, error } = await serverClient()
    .from('charges')
    .select('period,amount,status,residents(full_name,building,unit,phone)')
    .in('status', ['unpaid', 'disputed', 'pending_charge'])
    .order('period', { ascending: true });

  const byResident = new Map<string, {
    name: string; building: string; unit: string; phone: string;
    owed: number; months: string[]; inReview: string[];
  }>();
  for (const c of (data ?? []) as unknown as Charge[]) {
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
  const rows = [...byResident.values()].sort((a, b) => b.owed - a.owed);
  const total = rows.reduce((s, r) => s + r.owed, 0);

  const cards = [
    ['Total open', shekels(total)],
    ['Residents owing', rows.filter((r) => r.owed > 0).length],
    ['In review', rows.reduce((s, r) => s + r.inReview.length, 0)],
  ] as const;

  return (
    <>
      <h1>Open balances</h1>
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
              <th>Months owed</th><th>In review</th><th>Owed</th>
            </tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.phone}>
                  <td dir="auto">{r.name}</td>
                  <td dir="auto">{r.building}{r.unit ? ` · ${r.unit}` : ''}</td>
                  <td className="mono">{r.phone}</td>
                  <td className="muted mono">{r.months.join(', ') || '—'}</td>
                  <td className="muted">{r.inReview.join(', ') || '—'}</td>
                  <td className="mono">{r.owed ? shekels(r.owed) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : !error && <div className="empty">Nobody owes anything.</div>}
      </div>
    </>
  );
}
