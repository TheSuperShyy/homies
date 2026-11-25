import Link from 'next/link';
import type { T } from '@/lib/i18n';

/**
 * The dialer's two halves (25 Nov): calling tenants who owe, which is the dialer itself, and
 * the test calls page that came before it (feature 20), which rings only testers.
 */
export function DialerTabs({ t, here }: { t: T; here: 'tenants' | 'test' }) {
  return (
    <nav className="seg dialtabs" aria-label={t('dial.title')}>
      <Link href="/dialer" aria-current={here === 'tenants' ? 'page' : undefined}>{t('dial.tabTenants')}</Link>
      <Link href="/dialer/test" aria-current={here === 'test' ? 'page' : undefined}>{t('dial.tabTest')}</Link>
    </nav>
  );
}
