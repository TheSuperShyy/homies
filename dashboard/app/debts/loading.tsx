import { CardsSkeleton, HeadSkeleton, SegSkeleton, TableSkeleton } from '@/components/skeleton';

/* Sized off `app/debts/page.tsx`: 7 columns, so nothing shifts when the
   rows arrive. */
export default function Loading() {
  return (
    <>
      <HeadSkeleton />
      <SegSkeleton />
      <SegSkeleton n={2} />
      <CardsSkeleton n={4} />
      <TableSkeleton cols={7} rows={8} />
    </>
  );
}
