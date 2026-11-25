'use client';

/**
 * One box that ticks every open box in a form (the dialer's "the whole page").
 *
 * Boxes that are greyed out stay as they are: a tenant on do-not-call or already called today
 * cannot be ticked by hand, and must not be ticked by this either. Without JavaScript the box
 * does nothing and each row is still ticked on its own.
 */
export function SelectAll({ form, name, label }: { form: string; name: string; label: string }) {
  return (
    <input
      type="checkbox"
      className="dialcheck"
      aria-label={label}
      title={label}
      onChange={(e) => {
        const on = e.currentTarget.checked;
        document.getElementById(form)
          ?.querySelectorAll<HTMLInputElement>(`input[type="checkbox"][name="${name}"]`)
          .forEach((box) => { if (!box.disabled) box.checked = on; });
      }}
    />
  );
}
