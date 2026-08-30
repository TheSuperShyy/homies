import React from "react";
import { Delta } from "../core/Badge.jsx";
export function StatCard({ label, value, delta, sub, icon, hero = false, style }) {
  return (
    <div style={{ background: hero ? "var(--accent-soft)" : "var(--surface-2)",
      border: "1px solid " + (hero ? "transparent" : "var(--border-1)"),
      borderRadius: hero ? "var(--radius-lg)" : "var(--radius-md)",
      padding: hero ? 24 : 14, boxSizing: "border-box", fontFamily: "var(--font-ui)",
      position: "relative", overflow: "hidden", ...style }}>
      {hero && (
        <svg aria-hidden="true" viewBox="0 0 320 190" preserveAspectRatio="xMidYMid slice"
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
          {[0,1,2,3,4,5,6,7].map((i) => (
            <circle key={i} cx="265" cy="30" r={18 + i * 24} fill="none" stroke="var(--text-1)"
              strokeOpacity={0.05 - i * 0.004} strokeWidth="13" />
          ))}
        </svg>
      )}
      <div style={{ fontSize: hero ? 13 : 12, color: "var(--text-2)", display: "flex", alignItems: "center", gap: 8 }}>
        {icon}{label}
      </div>
      <div style={{ fontSize: hero ? "var(--text-3xl)" : 15, fontWeight: 600, color: "var(--text-1)",
        margin: hero ? "10px 0 8px" : "8px 0 6px", letterSpacing: "-0.01em" }}>{value}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {delta && <Delta value={delta} />}
        {sub && <span style={{ fontSize: 11, color: "var(--text-3)" }}>{sub}</span>}
      </div>
    </div>
  );
}
