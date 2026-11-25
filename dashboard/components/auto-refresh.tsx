'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Asks the server for the page again every few seconds, while the tab is in front.
 *
 * The dialer page renders it only while a call is waiting, ringing or under way, so the line's
 * state moves on the screen by itself and stops asking once the queue is empty. A refresh keeps
 * what the reader has ticked or typed: those are the browser's, not the server's.
 */
export function AutoRefresh({ seconds }: { seconds: number }) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => {
      if (document.visibilityState === 'visible') router.refresh();
    }, seconds * 1000);
    return () => clearInterval(id);
  }, [router, seconds]);
  return null;
}
