import React from "react";
export function SidebarItem({ icon, label, active = false, onClick, style }) {
  const [hover, setHover] = React.useState(false);
  return (
    <div onClick={onClick} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ display: "flex", alignItems: "center", gap: 12, height: 40, padding: "0 14px",
        borderRadius: 10, cursor: "pointer", fontFamily: "var(--font-ui)", fontSize: 13, fontWeight: active ? 500 : 400,
        background: active ? "var(--accent)" : hover ? "var(--surface-2)" : "transparent",
        color: active ? "var(--accent-fg)" : hover ? "var(--text-1)" : "var(--text-2)",
        transition: "background var(--transition-fast), color var(--transition-fast)", ...style }}>
      <span style={{ display: "inline-flex", width: 18, justifyContent: "center" }}>{icon}</span>
      {label}
    </div>
  );
}
export function SidebarSection({ label, style }) {
  return (
    <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "var(--tracking-wide)",
      color: "var(--text-3)", padding: "18px 14px 8px", fontFamily: "var(--font-ui)", ...style }}>{label}</div>
  );
}
