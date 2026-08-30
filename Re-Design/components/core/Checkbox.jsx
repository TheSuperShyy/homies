import React from "react";
export function Checkbox({ checked, onChange, label, disabled, style }) {
  return (
    <label style={{ display: "inline-flex", alignItems: "center", gap: 10, cursor: disabled ? "default" : "pointer",
      fontFamily: "var(--font-ui)", fontSize: 13, color: "var(--text-1)", opacity: disabled ? 0.45 : 1, ...style }}>
      <span onClick={() => !disabled && onChange && onChange(!checked)}
        style={{ width: 18, height: 18, borderRadius: 6, boxSizing: "border-box",
          background: checked ? "var(--accent)" : "var(--input-bg)",
          border: checked ? "1px solid var(--accent)" : "1px solid var(--border-2)",
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          transition: "background var(--transition-fast)" }}>
        {checked && <svg width="10" height="10" viewBox="0 0 10 10"><path d="M1.5 5.5l2.5 2.5 4.5-6" fill="none" stroke="var(--accent-fg)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>}
      </span>
      {label}
    </label>
  );
}
