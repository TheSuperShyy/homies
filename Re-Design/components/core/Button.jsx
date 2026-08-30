import React from "react";
const H = { sm: "var(--control-sm)", md: "var(--control-md)", lg: "var(--control-lg)" };
const F = { sm: 12, md: 13, lg: 14 };
export function Button({ variant = "primary", size = "md", icon, children, disabled, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  const base = {
    height: H[size], padding: size === "sm" ? "0 14px" : "0 20px", borderRadius: "var(--radius-pill)",
    fontFamily: "var(--font-ui)", fontSize: F[size], fontWeight: 500, display: "inline-flex",
    alignItems: "center", justifyContent: "center", gap: 8, whiteSpace: "nowrap",
    cursor: disabled ? "default" : "pointer", border: "1px solid transparent",
    opacity: disabled ? 0.45 : 1, transition: "background var(--transition-fast), border-color var(--transition-fast)",
  };
  const v = {
    primary: { background: hover && !disabled ? "var(--accent-hover)" : "var(--accent)", color: "var(--accent-fg)" },
    secondary: { background: hover && !disabled ? "var(--surface-3)" : "var(--pill-bg)", color: "var(--text-1)", borderColor: "var(--pill-border)" },
    ghost: { background: hover && !disabled ? "var(--surface-2)" : "transparent", color: "var(--text-2)" },
  }[variant];
  return (
    <button {...rest} disabled={disabled} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ ...base, ...v, ...style }}>{icon}{children}</button>
  );
}
