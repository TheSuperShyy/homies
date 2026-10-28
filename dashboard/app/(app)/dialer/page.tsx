import { redirect } from 'next/navigation';
import { getLocale, translator, type Key, type T } from '@/lib/i18n';
import { shekels } from '@/lib/money';
import { dial, dialerConnected, testers } from '@/lib/dialer';
import { inCallingHours, type Answerer } from '@/lib/dialer-rules';
import { PendingButton } from '@/components/pending-button';
import { IconAlert, IconCheck, IconInfo, IconPhoneOut } from '@/components/icons';

// Feature 20, the dialer test. A number typed here, or one press on a tester,
// goes into Tokomni's List 2 and Omni's dialer rings it at once; before this,
// every test call meant building an Excel sheet and uploading it in Tokomni.
//
// Everything that decides whether a press may go out is in lib/dialer.ts. This
// action only carries the form there and comes back to the page with the
// outcome in the URL, the Debts page's shape, so a refresh cannot press again.
async function ring(formData: FormData) {
  'use server';
  const outcome = await dial(String(formData.get('number') ?? ''));
  redirect(`/dialer?${new URLSearchParams(outcome)}`);
}

type Q = Partial<Record<'r' | 'n' | 's' | 'b' | 'x' | 'a' | 'f' | 'm' | 't' | 'y' | 'w', string>>;

/**
 * A value set inside a sentence in its own direction. Tokomni's answer, the
 * lead id and a number are left-to-right inside a Hebrew sentence, and without
 * the isolate the browser reorders them with the words around them.
 */
const iso = (s: string) => `⁨${s}⁩`;

const WHY: Record<string, Key> = {
  notListed: 'dialer.whyNotListed',
  twoRows: 'dialer.whyTwoRows',
  nothingOwed: 'dialer.whyNothingOwed',
};

/** Who picks up, in the words the tester rows use. */
function whoLine(t: T, a: Answerer) {
  return a.agent === 'debt'
    ? t('dialer.rowDebt', { amount: iso(shekels(a.amount)), attempt: a.attempt })
    : t('dialer.rowIntake', { why: t(WHY[a.why]) });
}

/** The outcome of the last press, from the URL the action came back with. */
function Outcome({ t, q }: { t: T; q: Q }) {
  const bad = (text: string) => (
    <div className="notice bad" role="alert"><IconAlert /><span>{text}</span></div>
  );
  const number = iso(q.n ?? '');
  const answer = iso(q.b || '—');
  switch (q.r) {
    case 'ok': {
      const who = q.a === 'debt'
        ? t('dialer.whoDebt', { name: iso(q.f ?? ''), amount: iso(shekels(Number(q.m ?? 0))) })
        : t('dialer.whoIntake');
      return (
        <div className="notice ok" role="status">
          <IconCheck />
          <span>
            {t('dialer.sent', { number, status: iso(q.s ?? ''), answer, who })}
            <span className="sub">{t('dialer.noRing', { id: iso(q.x ?? '') })}</span>
          </span>
        </div>
      );
    }
    case 'http': return bad(t('dialer.errHttp', { number, status: iso(q.s ?? ''), answer }));
    case 'net': return bad(t('dialer.errNet', { number, answer }));
    case 'db': return bad(t('dialer.errDb', { number, answer }));
    case 'tenant': return bad(t('dialer.errTenant', { number, building: iso(q.w ?? '') }));
    case 'number': return bad(t('dialer.errNumber', { typed: iso(q.n ?? '') }));
    // 'off' and 'hours' are the standing notices below; showing them twice
    // would say the same thing in two boxes.
    default: return null;
  }
}

export default async function Dialer({ searchParams }: { searchParams?: Q }) {
  const locale = getLocale();
  const t = translator(locale);
  const q = searchParams ?? {};

  // Both are facts read once per render. The action checks them again on the
  // press, because a page left open past 20:00 still shows live buttons.
  const connected = dialerConnected();
  const now = new Date();
  const open = inCallingHours(now);
  const can = connected && open;
  const nowText = new Intl.DateTimeFormat(locale === 'he' ? 'he-IL' : 'en-GB', {
    timeZone: 'Asia/Jerusalem', weekday: 'long', hour: '2-digit', minute: '2-digit',
  }).format(now);

  const people = await testers();

  return (
    <div className="setpage">
      <div className="pagehead">
        <h1>{t('dialer.title')}</h1>
        <p>{t('dialer.blurb')}</p>
      </div>

      <Outcome t={t} q={q} />
      {!connected && (
        <div className="notice bad" role="alert"><IconAlert /><span>{t('dialer.off')}</span></div>
      )}
      {connected && !open && (
        <div className="notice info" role="status">
          <IconInfo /><span>{t('dialer.closed', { now: nowText })}</span>
        </div>
      )}

      <div className="setcol">
        <section>
          <h2>{t('dialer.numberHead')}</h2>
          <div className="panel">
            <form className="setinline" action={ring}>
              <label htmlFor="number">{t('dialer.number')}</label>
              <div className="row">
                {/* ltr whatever the interface: a phone number reads left to
                    right in Hebrew too, and RTL puts the "+" at the wrong end. */}
                <input id="number" name="number" type="tel" dir="ltr" inputMode="tel"
                       autoComplete="off" required placeholder="054-1234567"
                       aria-describedby="numberhint" />
                <PendingButton className="btn-sm" disabled={!can} busy={t('dialer.sending')}>
                  <IconPhoneOut />{t('dialer.ring')}
                </PendingButton>
              </div>
              <p className="hint" id="numberhint">{t('dialer.numberHint')}</p>
            </form>
            <p className="setnote">{t('dialer.listRules')}</p>
          </div>
        </section>

        <section>
          <h2>{t('dialer.testersHead')}</h2>
          <div className="panel">
            {people.length ? people.map((p) => (
              <div className="setrow" key={p.local}>
                <span className="lbl">
                  <b dir="auto">{p.name}</b>
                  {' · '}{t('dialer.flat', { unit: p.unit })}
                  {' · '}<span className="mono" dir="ltr">{p.local}</span>
                  <span className="sub">{whoLine(t, p.answerer)}</span>
                </span>
                <form action={ring}>
                  <input type="hidden" name="number" value={p.local} />
                  <PendingButton className="btn-sm" disabled={!can} busy={t('dialer.sending')}>
                    <IconPhoneOut />{t('dialer.ringName', { name: p.name.split(' ')[0] })}
                  </PendingButton>
                </form>
              </div>
            )) : (
              <div className="empty">{t('dialer.noTesters')}</div>
            )}
            <p className="setnote">{t('dialer.attemptsNote')}</p>
          </div>
        </section>
      </div>
    </div>
  );
}
