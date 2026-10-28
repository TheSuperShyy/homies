// The one react-dom export the dashboard uses, typed here rather than by adding
// @types/react-dom for it. Next's App Router runs its own React canary, which
// exports useFormStatus (components/pending-button.tsx).
declare module 'react-dom' {
  export function useFormStatus(): { pending: boolean };
}
