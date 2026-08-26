/**
 * One icon family, drawn here rather than pulled from a package.
 *
 * These are Lucide's shapes at Lucide's proportions — 24 unit box, 1.75 stroke,
 * round caps and joins — so they sit together as one set. Inlined instead of
 * installed because the dashboard needs eighteen of them and a dependency for
 * eighteen paths is a build step, a version to keep current, and a bundle for
 * something that never changes.
 *
 * Every one is presentational: `aria-hidden`, no title, no focusable. The
 * meaning is always in the text beside it, which is the rule this file exists
 * to make easy to follow — an icon on its own is a guess.
 */
type P = { className?: string };

const base = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
  focusable: false,
};

export const IconBuilding = (p: P) => (
  <svg {...base} {...p}>
    <path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18" />
    <path d="M2 22h20M9 6h.01M15 6h.01M9 10h.01M15 10h.01M9 14h.01M15 14h.01" />
    <path d="M10 22v-4h4v4" />
  </svg>
);

export const IconOverview = (p: P) => (
  <svg {...base} {...p}>
    <rect x="3" y="3" width="7" height="9" rx="1.5" />
    <rect x="14" y="3" width="7" height="5" rx="1.5" />
    <rect x="14" y="12" width="7" height="9" rx="1.5" />
    <rect x="3" y="16" width="7" height="5" rx="1.5" />
  </svg>
);

export const IconTicket = (p: P) => (
  <svg {...base} {...p}>
    <path d="M15 5v2M15 11v2M15 17v2" />
    <path d="M5 5h14a2 2 0 0 1 2 2v3a2 2 0 0 0 0 4v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3a2 2 0 0 0 0-4V7a2 2 0 0 1 2-2Z" />
  </svg>
);

export const IconMoney = (p: P) => (
  <svg {...base} {...p}>
    <rect x="2" y="6" width="20" height="12" rx="2" />
    <circle cx="12" cy="12" r="2.5" />
    <path d="M6 12h.01M18 12h.01" />
  </svg>
);

export const IconChat = (p: P) => (
  <svg {...base} {...p}>
    <path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 8.9 8.9 0 0 1-3.8-.9L3 21l1.9-5a8.4 8.4 0 0 1-.9-3.8 8.4 8.4 0 0 1 8.4-8.4h.5a8.4 8.4 0 0 1 8 8v.2Z" />
  </svg>
);

export const IconPhone = (p: P) => (
  <svg {...base} {...p}>
    <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.4 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.4 1.8.6 2.8.8a2 2 0 0 1 1.7 2Z" />
  </svg>
);

export const IconPhoneOut = (p: P) => (
  <svg {...base} {...p}>
    <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.4 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.4 1.8.6 2.8.8a2 2 0 0 1 1.7 2Z" />
    <path d="M15 6h6V0" transform="translate(0 3)" />
  </svg>
);

export const IconImport = (p: P) => (
  <svg {...base} {...p}>
    <path d="M21 12a9 9 0 1 1-3-6.7" />
    <path d="M21 3v6h-6" />
  </svg>
);

export const IconSignOut = (p: P) => (
  <svg {...base} {...p}>
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <path d="M16 17l5-5-5-5M21 12H9" />
  </svg>
);

export const IconLanguage = (p: P) => (
  <svg {...base} {...p}>
    <path d="M2 5h10M7 3v2c0 4.4-2.2 8-5 8" />
    <path d="M4 9c0 2.6 2.7 4.8 6 5" />
    <path d="M11 21l4.5-11L20 21M13 17h5" />
  </svg>
);

export const IconSearch = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </svg>
);

export const IconInbox = (p: P) => (
  <svg {...base} {...p}>
    <path d="M22 12h-6l-2 3h-4l-2-3H2" />
    <path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1Z" />
  </svg>
);

export const IconCheck = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="9.5" />
    <path d="m8 12.5 2.5 2.5L16 9.5" />
  </svg>
);

export const IconAlert = (p: P) => (
  <svg {...base} {...p}>
    <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
    <path d="M12 9v4M12 17h.01" />
  </svg>
);

export const IconInfo = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="9.5" />
    <path d="M12 16v-4.5M12 8h.01" />
  </svg>
);

export const IconOpenLink = (p: P) => (
  <svg {...base} {...p}>
    <path d="M15 3h6v6" />
    <path d="M10 14 21 3" />
    <path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" />
  </svg>
);

/** Named for the six views, so the rail reads as a list of destinations. */
export const NAV_ICON = {
  overview: IconOverview,
  tickets: IconTicket,
  debts: IconMoney,
  conversations: IconChat,
  calls: IconPhone,
  sync: IconImport,
} as const;
