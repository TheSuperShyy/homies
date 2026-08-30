/* Demo loader: loads component .jsx sources directly (no bundler). Used by cards + UI kit. */
window.loadDS = async function (base, paths) {
  const ns = (window.__DS_NS__ = window.__DS_NS__ || {});
  for (const p of paths) {
    if (ns["__" + p]) continue;
    const src = await (await fetch(base + p)).text();
    const names = [...src.matchAll(/export\s+function\s+(\w+)/g)].map((m) => m[1]);
    let cleaned = src
      .replace(/^import\s+React[^\n]*$/gm, "")
      .replace(/^import\s+\{([^}]+)\}[^\n]*$/gm, (m, n) => `const {${n.trim()}} = window.__DS_NS__;`)
      .replace(/export\s+function/g, "function");
    cleaned += `\n;Object.assign(window.__DS_NS__, {${names.join(",")}});`;
    const code = Babel.transform(cleaned, { presets: [["react", { runtime: "classic" }]] }).code;
    new Function("React", code)(window.React);
    ns["__" + p] = true;
  }
  return ns;
};
window.DS_ALL = [
  "core/Badge.jsx", "core/Button.jsx", "core/IconButton.jsx", "core/Input.jsx", "core/Select.jsx",
  "core/Checkbox.jsx", "core/Switch.jsx", "core/Avatar.jsx",
  "display/Card.jsx", "display/StatCard.jsx", "display/DataTable.jsx",
  "navigation/Tabs.jsx", "navigation/SidebarItem.jsx",
];

function runDemoScripts(){
  document.querySelectorAll('script[type="text/babel-demo"]').forEach((s) => {
    try {
      (0, eval)(Babel.transform(s.textContent, { presets: [[Babel.availablePresets["react"], { runtime: "classic" }]], filename: "demo.jsx" }).code);
    } catch (e) { console.error("demo script failed:", e); }
  });
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", runDemoScripts);
else runDemoScripts();
