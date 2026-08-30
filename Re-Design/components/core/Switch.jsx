import React from "react";
export function Switch({ checked, onChange, disabled, style }) {
  return (
    <span onClick={() => !disabled && onChange && onChange(!checked)}
      style={{ width: 40, height: 22, borderRadius: 999, boxSizing: "border-box", padding: 2,
        background: checked ? "var(--accent)" : "var(--surface-3)",
        border: "1px solid " + (checked ? "var(--accent)" : "var(--border-2)"),
        display: "inline-flex", cursor: disabled ? "default" : "pointer", opacity: disabled ? 0.45 : 1,
        transition: "background var(--transition-med)", ...style }}>
      <span style={{ width: 16, height: 16, borderRadius: "50%", background: "#fff",
        transform: checked ? "translateX(18px)" : "translateX(0)", transition: "transform var(--transition-med)" }} />
    </span>
  );
}
