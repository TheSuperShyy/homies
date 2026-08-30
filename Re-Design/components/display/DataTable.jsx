import React from "react";
export function DataTable({ columns = [], rows = [], style }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--font-ui)", fontSize: 13, ...style }}>
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.key} style={{ textAlign: c.align || "left", padding: "10px 12px", fontSize: 12,
              fontWeight: 500, color: "var(--text-2)", borderBottom: "1px solid var(--border-1)" }}>{c.label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {columns.map((c) => (
              <td key={c.key} style={{ textAlign: c.align || "left", padding: "12px", color: "var(--text-1)",
                borderBottom: i < rows.length - 1 ? "1px solid var(--border-1)" : "none" }}>
                {c.render ? c.render(r) : r[c.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
