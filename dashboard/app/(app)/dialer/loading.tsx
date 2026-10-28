import { getLocale, translator } from '@/lib/i18n';
import { HeadSkeleton, RowsSkeleton } from '@/components/skeleton';

/* Sized off `app/(app)/dialer/page.tsx`: the number form, then one row per
   tester. The section labels are constants, so they are real text. */
export default function Loading() {
  const t = translator(getLocale());
  return (
    <div className="setpage">
      <HeadSkeleton />
      <div className="setcol">
        <section>
          <h2>{t('dialer.numberHead')}</h2>
          <RowsSkeleton rows={2} />
        </section>
        <section>
          <h2>{t('dialer.testersHead')}</h2>
          <RowsSkeleton rows={1} />
        </section>
      </div>
    </div>
  );
}
