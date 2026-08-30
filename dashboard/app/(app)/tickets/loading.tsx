import { HeadSkeleton, SegSkeleton, TableSkeleton } from '@/components/skeleton';

/* Sized off `app/tickets/page.tsx`: 9 columns, so nothing shifts when the
   rows arrive. */
export default function Loading() {
  return (
    <>
      <HeadSkeleton />
      <SegSkeleton />
      <TableSkeleton cols={9} rows={8} />
    </>
  );
}
