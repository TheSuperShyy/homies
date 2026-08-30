import React from "react";
export function Select({ options = [], size = "md", style, ...rest }) {
  const h = { sm: "var(--control-sm)", md: "var(--control-md)", lg: "var(--control-lg)" }[size];
  return (
    <div style={{ position: "relative", display: "inline-flex", ...style }}>
      <select {...rest} style={{ appearance: "none", WebkitAppearance: "none", height: h,
        padding: "0 36px 0 16px", borderRadius: "var(--radius-pill)", background: "var(--pill-bg)",
        border: "1px solid var(--pill-border)", color: "var(--text-1)", fontFamily: "var(--font-ui)",
        fontSize: 13, cursor: "pointer", outline: "none" }}>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
      <svg width="12" height="12" viewBox="0 0 12 12" style={{ position: "absolute", right: 14, top: "50%",
        transform: "translateY(-50%)", pointerEvents: "none", color: "var(--text-2)" }}>
        <path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}
