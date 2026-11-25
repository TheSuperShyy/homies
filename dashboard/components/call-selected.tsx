'use client';

import { useEffect, useState } from 'react';
import { useFormStatus } from 'react-dom';

/**
 * The dialer's "Call selected", with how many are ticked on it.
 *
 * It counts the form's ticked boxes after every change and every refresh of the page, and stays
 * off while none is ticked, so a press always means the people the reader can see counted. Greys
 * out while its press is on its way, like PendingButton: a second press would be a second queue.
 */
export function CallSelected({ form, name, label, busy, disabled, icon }: {
  form: string; name: string; label: string; busy: string; disabled?: boolean; icon?: React.ReactNode;
}) {
  const { pending } = useFormStatus();
  const [ticked, setTicked] = useState(0);

  // After every render, so a refresh of the page that greys a row out is counted too.
  useEffect(() => {
    const f = document.getElementById(form);
    setTicked(f ? f.querySelectorAll(`input[type="checkbox"][name="${name}"]:checked`).length : 0);
  });
  useEffect(() => {
    const f = document.getElementById(form);
    if (!f) return;
    const count = () => setTicked(f.querySelectorAll(`input[type="checkbox"][name="${name}"]:checked`).length);
    f.addEventListener('change', count);
    return () => f.removeEventListener('change', count);
  }, [form, name]);

  return (
    <button type="submit" className="btn-sm" disabled={disabled || pending || ticked === 0}
            aria-busy={pending || undefined}>
      {pending ? busy : (
        <>
          {icon}
          {label}
          {ticked > 0 && <span className="dialcount" aria-hidden="true">{ticked}</span>}
        </>
      )}
    </button>
  );
}
