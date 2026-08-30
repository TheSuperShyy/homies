import { TableSkeleton } from '@/components/skeleton';

/* One resident: the WhatsApp thread, then their recent tickets. */
export default function Loading() {
  return (
    <>
      <div className="pagehead" aria-hidden="true">
        <span className="sk" style={{ height: 22, width: 210, borderRadius: 8 }} />
      </div>
      <div className="panel" aria-hidden="true">
        <div className="thread">
          {[62, 48, 71, 40, 58].map((w, i) => (
            <span key={i} className="sk"
                  style={{ height: 40, width: `${w}%`, borderRadius: 14,
                           alignSelf: i % 2 ? 'flex-end' : 'flex-start' }} />
          ))}
        </div>
      </div>
      <h2><span className="sk" style={{ height: 11, width: 110, display: 'inline-block' }} /></h2>
      <TableSkeleton cols={4} rows={3} />
    </>
  );
}
