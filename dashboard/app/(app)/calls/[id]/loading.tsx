

/* One call: the transcript pane and the facts beside it. The grid is the real
   `.callgrid`, so the two columns are already the width they will be. */
export default function Loading() {
  return (
    <>
      <div className="pagehead" aria-hidden="true">
        <span className="sk" style={{ height: 22, width: 120, borderRadius: 8 }} />
      </div>
      <div className="callgrid">
        <div className="panel" aria-hidden="true">
          <div className="thread">
            {[68, 52, 74, 44, 61, 38].map((w, i) => (
              <span key={i} className="sk"
                    style={{ height: 40, width: `${w}%`, borderRadius: 14,
                             alignSelf: i % 2 ? 'flex-end' : 'flex-start' }} />
            ))}
          </div>
        </div>
        <div className="side">
          <div className="panel" aria-hidden="true">
            <div className="rows">
              {[0, 1, 2, 3, 4].map((i) => (
                <div className="row" key={i}>
                  <span className="sk sk-line" style={{ width: 70 }} />
                  <span className="sk sk-line" style={{ width: 54 }} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
