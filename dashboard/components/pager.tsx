// Ten rows a page, everywhere. A list nobody can see the end of reads as
// "there is more" and hides its own size; a pager states the total and lets
// somebody link a colleague to page four.
//
// Offset-based over a stable sort. Rows arriving between clicks shift the
// window slightly, which is the right trade for a review dashboard.
export const PAGE_SIZE = 10;

export function pageFrom(searchParams?: { page?: string }) {
  return Math.max(1, parseInt(searchParams?.page ?? '1', 10) || 1);
}

/** [from, to] for Supabase `.range()`. */
export function pageRange(page: number): [number, number] {
  const from = (page - 1) * PAGE_SIZE;
  return [from, from + PAGE_SIZE - 1];
}

/** The slice of an in-memory array for this page. */
export function pageSlice<T>(rows: T[], page: number): T[] {
  const [from] = pageRange(page);
  return rows.slice(from, from + PAGE_SIZE);
}

export function Pager({
  page, total, basePath, params = {}, unit = 'rows',
}: {
  page: number;
  total: number;
  basePath: string;
  params?: Record<string, string | undefined>;
  unit?: string;
}) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages <= 1) return null;

  const href = (p: number) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v) q.set(k, v);
    if (p > 1) q.set('page', String(p));
    const s = q.toString();
    return s ? `${basePath}?${s}` : basePath;
  };

  return (
    <div className="pager">
      {page > 1 ? <a href={href(page - 1)}>&larr; Previous</a>
                : <span className="muted">&larr; Previous</span>}
      <span className="muted mono">page {page} of {pages} · {total} {unit}</span>
      {page < pages ? <a href={href(page + 1)}>Next &rarr;</a>
                    : <span className="muted">Next &rarr;</span>}
    </div>
  );
}
