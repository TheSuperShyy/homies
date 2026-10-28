'use client';

import { useFormStatus } from 'react-dom';

/**
 * A submit button that greys out while its form is on its way.
 *
 * Made for the dialer test page, where a second click is a second lead and the
 * phone rings twice. The page itself stays server-rendered; only this button
 * runs in the browser, and without JavaScript it is a plain submit button.
 */
export function PendingButton({ children, busy, className, disabled }: {
  children: React.ReactNode; busy: string; className?: string; disabled?: boolean;
}) {
  const { pending } = useFormStatus();
  return (
    <button type="submit" className={className} disabled={disabled || pending}
            aria-busy={pending || undefined}>
      {pending ? busy : children}
    </button>
  );
}
