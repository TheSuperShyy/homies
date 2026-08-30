import React from "react";
export function Tabs({ items = [], value, onChange, size = "sm", style }) {
  const h = { sm: "var(--control-sm)", md: "var(--control-md)" }[size];
  return (
    <div style={{ display: "inline-flex", gap: 8, ...style }}>
      {items.map((it) => {
        const active = it === value;
        return (
          <button key={it} onClick={() => onChange && onChange(it)}
            style={{ height: h, padding: "0 16px", borderRadius: "var(--radius-pill)", cursor: "pointer",
              fontFamily: "var(--font-ui)", fontSize: 12, fontWeight: 500,
              background: active ? "var(--accent)" : "var(--pill-bg)",
              color: active ? "var(--accent-fg)" : "var(--text-2)",
              border: "1px solid " + (active ? "var(--accent)" : "var(--pill-border)"),
              transition: "background var(--transition-fast), color var(--transition-fast)" }}>
            {it}
          </button>
        );
      })}
    </div>
  );
}
