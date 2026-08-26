import type { T } from '@/lib/i18n';

// The pager, and the page size, for every list on the dashboard.
//
// A list nobody can see the end of reads as "there is more" and hides its own
// size; a pager states the total and lets somebody link a colleague to page
// four. The size picker is part of that link: reviewing a hundred debtors and
// checking one ticket are different jobs, and ten rows is only right for one of
// them.
//
// Offset-based over a stable sort. Rows arriving between clicks shift the
// window slightly, which is the right trade for a review dashboard.
export const PAGE_SIZES = [10, 25, 50] as const;
export const PAGE_SIZE = PAGE_SIZES[0];

export type PagerParams = Record<string, string | undefined>;

export function pageFrom(searchParams?: { page?: string }) {
  return Math.max(1, parseInt(searchParams?.page ?? '1', 10) || 1);
}

/** The rows-per-page from the URL. Anything not on the list falls back to 10,
 *  so `?per=1000` cannot be used to pull the whole table down in one request. */
export function sizeFrom(searchParams?: { per?: string }): number {
  const n = parseInt(searchParams?.per ?? '', 10);
  return (PAGE_SIZES as readonly number[]).includes(n) ? n : PAGE_SIZE;
}

/** What `per` should carry in a link — omitted at the default so the common
 *  URL stays clean and a shared link means what it looks like. */
export function perParam(size: number): string | undefined {
  return size === PAGE_SIZE ? undefined : String(size);
}

/** [from, to] for Supabase `.range()`. */
export function pageRange(page: number, size: number = PAGE_SIZE): [number, number] {
  const from = (page - 1) * size;
  return [from, from + size - 1];
}

/** The slice of an in-memory array for this page. */
export function pageSlice<T>(rows: T[], page: number, size: number = PAGE_SIZE): T[] {
  const [from] = pageRange(page, size);
  return rows.slice(from, from + size);
}

export function Pager({
  page, total, basePath, params = {}, unit = 'rows', t,
  size = PAGE_SIZE, prev, next,
}: {
  page: number;
  total: number;
  basePath: string;
  params?: PagerParams;
  unit?: string;
  size?: number;
  /** The page's translator. Passed in rather than read from the cookie here so
   *  this stays a plain component with no server-only import, which is what
   *  lets it be dropped into any of the six lists unchanged. */
  t: T;
  prev?: string;
  next?: string;
}) {
  const pages = Math.max(1, Math.ceil(total / size));
  const prevLabel = prev ?? t('pager.prev');
  const nextLabel = next ?? t('pager.next');

  // Hidden only when no size on offer would change what is on screen. With
  // more rows than the smallest size the picker still earns its place even on
  // a single page — that is how somebody at 50 gets back to 10.
  if (total <= PAGE_SIZE) return null;

  const href = (p: number, s: number) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v) q.set(k, v);
    const per = perParam(s);
    if (per) q.set('per', per);
    if (p > 1) q.set('page', String(p));
    const str = q.toString();
    return str ? `${basePath}?${str}` : basePath;
  };

  return (
    <div className="pager">
      {/* Changing the size always lands on page one. Page nine of ninety at
          ten rows is page two at fifty, and there is no honest way to guess
          which of those somebody meant — the first page is the one that is
          never empty. */}
      <span className="per">
        <span className="muted">{t('pager.rows')}</span>
        {PAGE_SIZES.map((n) => (
          <a key={n} href={href(1, n)} className={n === size ? 'on' : ''}
             aria-current={n === size ? 'true' : undefined}>{n}</a>
        ))}
      </span>
      <span className="muted mono">
        {t('pager.of', { page, pages, total, unit })}
      </span>
      {/* Buttons, not bare words. At the first or last page they stay in
          place and go visibly dead rather than disappearing — a control that
          vanishes moves everything beside it and leaves you unsure whether you
          reached the end or misclicked. `aria-disabled` on a span says the same
          thing to a screen reader that the grey says to everyone else. */}
      <span className="nav">
        {/* The arrow is a span so RTL can mirror it without mirroring the
            words beside it — see .btn-nav .arr. */}
        {page > 1
          ? <a className="btn-nav" href={href(page - 1, size)}><span className="arr">&larr;</span> {prevLabel}</a>
          : <span className="btn-nav off" aria-disabled="true"><span className="arr">&larr;</span> {prevLabel}</span>}
        {page < pages
          ? <a className="btn-nav" href={href(page + 1, size)}>{nextLabel} <span className="arr">&rarr;</span></a>
          : <span className="btn-nav off" aria-disabled="true">{nextLabel} <span className="arr">&rarr;</span></span>}
      </span>
    </div>
  );
}
