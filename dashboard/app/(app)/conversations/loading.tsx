import { HeadSkeleton, TableSkeleton } from '@/components/skeleton';

/* Sized off `app/conversations/page.tsx`: 6 columns, so nothing shifts when the
   rows arrive. */
export default function Loading() {
  return (
    <>
      <HeadSkeleton />

      <TableSkeleton cols={6} rows={8} />
    </>
  );
}
