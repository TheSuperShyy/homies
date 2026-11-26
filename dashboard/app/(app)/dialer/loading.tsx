import { CardsSkeleton, HeadSkeleton, SegSkeleton, TableSkeleton } from '@/components/skeleton';

/* Sized off `app/(app)/dialer/page.tsx`: the four counts, then
   the list of who owes, 5 columns, so nothing shifts when the rows arrive. */
export default function Loading() {
  return (
    <>
      <HeadSkeleton />
      <CardsSkeleton n={4} />
      <SegSkeleton />
      <TableSkeleton cols={5} rows={8} />
    </>
  );
}
