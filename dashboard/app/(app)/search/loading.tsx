import { HeadSkeleton, TableSkeleton } from '@/components/skeleton';

/* Sized off `app/(app)/search/page.tsx`. The real page shows up to four panels
   and cannot know how many until the queries land, so this stands in for the
   two most likely to have something in them rather than guessing at four and
   collapsing to one. */
export default function Loading() {
  return (
    <>
      <HeadSkeleton />
      <TableSkeleton cols={5} rows={4} />
      <div style={{ height: 18 }} />
      <TableSkeleton cols={5} rows={3} />
    </>
  );
}
