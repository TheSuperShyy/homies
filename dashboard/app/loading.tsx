import { CardsSkeleton, HeadSkeleton, TableSkeleton } from '@/components/skeleton';

/* The overview: five stat tiles, then the last seven days as a nine-column
   table. Same counts as `app/page.tsx`, which is the whole point — when the
   real numbers land they land in these boxes. */
export default function Loading() {
  return (
    <>
      <HeadSkeleton />
      <CardsSkeleton n={5} />
      <h2><span className="sk" style={{ height: 11, width: 120, display: 'inline-block' }} /></h2>
      <TableSkeleton cols={7} rows={6} />
    </>
  );
}
