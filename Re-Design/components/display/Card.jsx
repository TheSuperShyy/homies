import React from "react";
export function Card({ title, action, padding = 20, nested = false, children, style }) {
  return (
    <div style={{ background: nested ? "var(--surface-2)" : "var(--surface-1)",
      border: "1px solid var(--border-1)", borderRadius: nested ? "var(--radius-md)" : "var(--radius-lg)",
      boxShadow: "var(--shadow-card)", padding, boxSizing: "border-box", fontFamily: "var(--font-ui)", ...style }}>
      {(title || action) && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-1)" }}>{title}</span>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
