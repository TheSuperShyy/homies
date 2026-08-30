import React from "react";
export function Input({ icon, size = "md", style, inputStyle, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  const h = { sm: "var(--control-sm)", md: "var(--control-md)", lg: "var(--control-lg)" }[size];
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 10, height: h, padding: "0 16px",
      borderRadius: "var(--radius-pill)", background: "var(--input-bg)",
      border: focus ? "1px solid var(--accent)" : "1px solid var(--pill-border)",
      boxShadow: focus ? "var(--focus-ring)" : "none", transition: "border-color var(--transition-fast)",
      minWidth: 220, boxSizing: "border-box", ...style }}>
      {icon && <span style={{ color: "var(--text-3)", display: "inline-flex" }}>{icon}</span>}
      <input {...rest} onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
        style={{ flex: 1, background: "transparent", border: "none", outline: "none",
          color: "var(--text-1)", fontFamily: "var(--font-ui)", fontSize: 13, ...inputStyle }} />
    </div>
  );
}
