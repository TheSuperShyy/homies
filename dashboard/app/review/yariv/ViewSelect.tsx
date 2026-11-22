'use client';

import { useRouter } from 'next/navigation';
import styles from './yariv.module.css';
import type { View } from './replies';

// The dropdown above Yariv's comments (owner, 22 Nov: "create a dropdown so i can see whats the new feedback and
// old one"). The choice lives in the address as `show`, beside the key, so the page stays a server page and a
// filtered view can be linked to; "all" leaves `show` out.
export default function ViewSelect({
  reviewKey,
  view,
  label,
  options,
}: {
  reviewKey: string;
  view: View;
  label: string;
  options: { value: View; text: string }[];
}) {
  const router = useRouter();
  return (
    <label className={styles.view}>
      <span>{label}</span>
      <select
        value={view}
        onChange={(e) => {
          const v = e.target.value;
          const q = `?k=${encodeURIComponent(reviewKey)}${v === 'all' ? '' : `&show=${encodeURIComponent(v)}`}`;
          router.replace(`/review/yariv${q}`, { scroll: false });
        }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.text}
          </option>
        ))}
      </select>
    </label>
  );
}
