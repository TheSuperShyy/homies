import { HeadSkeleton, SegSkeleton, TableSkeleton } from '@/components/skeleton';

/* Sized off `app/calls/page.tsx`: 8 columns, so nothing shifts when the
   rows arrive. */
export default function Loading() {
  return (
    <>
      <HeadSkeleton />
      <SegSkeleton />
      <TableSkeleton cols={8} rows={8} />
    </>
  );
}
