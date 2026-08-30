import { HeadSkeleton, TableSkeleton } from '@/components/skeleton';

/* Sized off `app/sync/page.tsx`: 4 columns, so nothing shifts when the
   rows arrive. */
export default function Loading() {
  return (
    <>
      <HeadSkeleton />

      <TableSkeleton cols={4} rows={5} />
    </>
  );
}
