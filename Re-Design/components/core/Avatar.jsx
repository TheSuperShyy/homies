import React from "react";
export function Avatar({ src, name = "", size = 36, style }) {
  const initials = name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  return src ? (
    <img src={src} alt={name} style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover", ...style }} />
  ) : (
    <span style={{ width: size, height: size, borderRadius: "50%", background: "var(--surface-3)",
      color: "var(--text-2)", display: "inline-flex", alignItems: "center", justifyContent: "center",
      fontFamily: "var(--font-ui)", fontSize: size * 0.36, fontWeight: 600, ...style }}>{initials}</span>
  );
}
