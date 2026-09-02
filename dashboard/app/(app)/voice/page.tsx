import { serverClient } from '@/lib/supabase-server';
import { getLocale, translator } from '@/lib/i18n';
import { debtVariableValues, debtAssistantId } from '@/lib/call';
import { VoiceConsole, type DebtRow } from '@/components/voice-console';

// Voice Agent call — the browser test console, inside the dashboard.
//
// The left column is not the demo's built-in list: it is
// v_debt_call_queue_person, the same view press_call() composes a real
// outbound call from, read here WITHOUT press_call — nothing flips
// handed_over, nothing counts an attempt. A web call from this page is a
// rehearsal with live data, which is exactly what the browser console was
// for, minus the copy of the resident list that had to be kept in step by
// hand.

export default async function Voice() {
  const locale = getLocale();
  const t = translator(locale);

  const publicKey = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY;
  const intakeId = process.env.NEXT_PUBLIC_VAPI_INTAKE_ASSISTANT_ID;

  let rows: DebtRow[] = [];
  if (publicKey && intakeId) {
    const { data } = await serverClient()
      .from('v_debt_call_queue_person')
      .select('*')
      .order('first_name');
    rows = (data ?? []).map((p: Record<string, any>) => ({
      id: String(p.resident_id),
      name: String(p.first_name ?? ''),
      // `amount` in the view is money_say() output - Hebrew words for the
      // TTS - so the card's figure is summed from the charges whitelist.
      amount: '₪' + (Array.isArray(p.charges)
        ? p.charges.reduce((n: number, c: any) => n + Number(c?.amount ?? 0), 0)
        : 0),
      sub: [
        String(p.card_last4 ?? '').trim()
          ? t('voice.card', { n: p.card_last4 })
          : t('voice.noCard'),
        String(p.building ?? ''),
        String(p.apartments_phrase ?? ''),
      ].filter(Boolean).join(' · '),
      // The composed Hebrew the template substitutes — visible on the page
      // under "what the agent is told", because a call you cannot inspect is
      // a call you cannot debug.
      variables: debtVariableValues(p, ''),
    }));
  }

  return (
    <>
      <div className="pagehead"><h1>{t('voice.title')}</h1></div>
      {!publicKey || !intakeId ? (
        <div className="empty">{t('voice.notConfigured')}</div>
      ) : (
        <VoiceConsole
          publicKey={publicKey}
          intakeId={intakeId}
          debtId={debtAssistantId()}
          rows={rows}
          labels={{
            tabIntake: t('voice.tabIntake'), tabDebt: t('voice.tabDebt'),
            who: t('voice.who'), source: t('voice.source'),
            idle: t('voice.idle'), connecting: t('voice.connecting'),
            live: t('voice.live'), start: t('voice.start'),
            hangup: t('voice.hangup'), mute: t('voice.mute'),
            unmute: t('voice.unmute'), agent: t('voice.agent'),
            you: t('voice.you'), failed: t('voice.failed'),
            micHint: t('voice.micHint'), transcriptHint: t('voice.transcriptHint'),
            told: t('voice.told'), pickFirst: t('voice.empty'),
          }}
        />
      )}
    </>
  );
}
