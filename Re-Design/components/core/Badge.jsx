import React from "react";
export function Badge({ tone = "neutral", children, style }) {
  const t = {
    positive: { color: "var(--positive)", background: "var(--positive-soft)" },
    negative: { color: "var(--negative)", background: "var(--negative-soft)" },
    accent: { color: "var(--accent-fg)", background: "var(--accent)" },
    neutral: { color: "var(--text-2)", background: "var(--surface-2)", border: "1px solid var(--border-1)" },
  }[tone];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "3px 10px",
      borderRadius: "var(--radius-pill)", fontFamily: "var(--font-ui)", fontSize: 11, fontWeight: 500, ...t, ...style }}>
      {children}
    </span>
  );
}
export function Delta({ value, showArrow = true, style }) {
  const up = !String(value).trim().startsWith("-");
  return (
    <span style={{ color: up ? "var(--positive)" : "var(--negative)", fontFamily: "var(--font-ui)",
      fontSize: 12, fontWeight: 500, display: "inline-flex", alignItems: "center", gap: 3, ...style }}>
      {showArrow && (
        <svg width="10" height="10" viewBox="0 0 10 10" style={{ transform: up ? "none" : "scaleY(-1)" }}>
          <path d="M1 7l3.2-3.2L6 5.6 9 2.4M9 2.4V5M9 2.4H6.6" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
      {value}
    </span>
  );
}
