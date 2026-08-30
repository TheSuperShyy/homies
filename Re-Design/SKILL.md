---
name: stovest-design
description: Use this skill to generate well-branded interfaces and assets for Stovest (dual-theme dashboard system — dark default, light via data-theme="light"), either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.
If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.
If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

Key facts: dark theme is the default (`:root`); light theme = `data-theme="light"` on any ancestor (near-black accent, warm gray canvas). Everything is pill-shaped; dark uses 1px borders instead of shadows. Tokens live in `tokens/`, entry point `styles.css`. Components: Button, IconButton, Input, Select, Checkbox, Switch, Badge, Delta, Avatar, Card, StatCard, DataTable, Tabs, SidebarItem, SidebarSection. Full-screen example: `ui_kits/dashboard/index.html`.
