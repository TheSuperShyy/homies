import { CardsSkeleton, HeadSkeleton, SegSkeleton, TableSkeleton } from '@/components/skeleton';

/* Sized off `app/(app)/dialer/page.tsx`: the two tabs, the four counts, then
   the list of who owes, 5 columns, so nothing shifts when the rows arrive. */
export default function Loading() {
  return (
    <>
      <HeadSkeleton />
      <SegSkeleton n={2} />
      <CardsSkeleton n={4} />
      <SegSkeleton />
      <TableSkeleton cols={5} rows={8} />
    </>
  );
}
