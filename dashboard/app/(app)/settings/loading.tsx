import { getLocale, translator } from '@/lib/i18n';
import { HeadSkeleton, RowsSkeleton } from '@/components/skeleton';

/* Sized off `app/(app)/settings/page.tsx`: an account panel with the identity
   block and three rows, then the password form, then the two appearance rows,
   then sign-out.

   The section labels are real text rather than grey bars. Nothing is being
   waited on to know that the second section is called Password — it is a
   constant, and greying out a word the server already knows is the kind of fake
   loading state that makes a fast page feel slow. */
export default function Loading() {
  const t = translator(getLocale());
  return (
    <div className="setpage">
      <HeadSkeleton />
      <div className="setcol">
        <section>
          <h2>{t('settings.account')}</h2>
          <RowsSkeleton head rows={3} />
        </section>
        <section>
          <h2>{t('settings.password')}</h2>
          <RowsSkeleton rows={4} />
        </section>
        <section>
          <h2>{t('settings.appearance')}</h2>
          <RowsSkeleton rows={2} />
        </section>
        <section>
          <h2>{t('settings.session')}</h2>
          <RowsSkeleton rows={1} />
        </section>
      </div>
    </div>
  );
}
