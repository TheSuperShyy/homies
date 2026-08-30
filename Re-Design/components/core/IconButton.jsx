import React from "react";
export function IconButton({ variant = "outline", size = 38, label, children, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  const v = {
    solid: { background: hover ? "var(--accent-hover)" : "var(--accent)", color: "var(--accent-fg)", border: "1px solid transparent" },
    outline: { background: hover ? "var(--surface-3)" : "var(--pill-bg)", color: "var(--text-1)", border: "1px solid var(--pill-border)" },
    ghost: { background: hover ? "var(--surface-2)" : "transparent", color: "var(--text-2)", border: "1px solid transparent" },
  }[variant];
  return (
    <button {...rest} aria-label={label} title={label} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ width: size, height: size, borderRadius: "50%", display: "inline-flex", alignItems: "center",
        justifyContent: "center", cursor: "pointer", transition: "background var(--transition-fast)", ...v, ...style }}>
      {children}
    </button>
  );
}
