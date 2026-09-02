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

// Three invented residents for when the queue is empty — TODAY it is empty,
// because nobody in the demo data currently owes and is still callable, and a
// debt tab with nothing to pick makes the agent untestable. The moment the
// view returns real people these never render; the pill over the list says
// which world is showing. Shapes mirror v_debt_call_queue_person exactly
// (amount is money_say() words, charges is the whitelist), because these rows
// go through the same composer as real ones.
const SAMPLE_PEOPLE: Record<string, any>[] = [
  {
    resident_id: 'demo-1', first_name: 'שחר', gender: 'm', card_last4: '7355',
    building: 'הרצל 14', unit: '12', amount: 'ארבע מאות וחמישים שקלים',
    apartments_phrase: 'דירה 12', months_phrase: 'יולי',
    breakdown_phrase: 'יולי, ארבע מאות וחמישים שקלים', attempt: '1',
    charges: [{ charge_id: 'demo-1a', unit: '12', period: '2026-07', amount: 450 }],
  },
  {
    resident_id: 'demo-2', first_name: 'מיכל', gender: 'f', card_last4: '',
    building: 'ויצמן 3', unit: '6', amount: 'אלף ומאתיים שקלים',
    apartments_phrase: 'דירה 6', months_phrase: 'יוני ויולי',
    breakdown_phrase: 'יוני, שש מאות שקלים. יולי, שש מאות שקלים', attempt: '2',
    charges: [
      { charge_id: 'demo-2a', unit: '6', period: '2026-06', amount: 600 },
      { charge_id: 'demo-2b', unit: '6', period: '2026-07', amount: 600 },
    ],
  },
  {
    // gender null on purpose: the third example exercises the neutral-forms
    // branch of gender_forms, the one that never gets tested by accident.
    resident_id: 'demo-3', first_name: 'נועם', gender: null, card_last4: '',
    building: 'בן גוריון 8', unit: '4', amount: 'שלוש מאות ועשרים שקלים',
    apartments_phrase: 'דירה 4', months_phrase: 'אוגוסט',
    breakdown_phrase: 'אוגוסט, שלוש מאות ועשרים שקלים', attempt: '1',
    charges: [{ charge_id: 'demo-3a', unit: '4', period: '2026-08', amount: 320 }],
  },
];

export default async function Voice() {
  const locale = getLocale();
  const t = translator(locale);

  const publicKey = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY;
  const intakeId = process.env.NEXT_PUBLIC_VAPI_INTAKE_ASSISTANT_ID;

  let rows: DebtRow[] = [];
  let sample = false;
  if (publicKey && intakeId) {
    const { data } = await serverClient()
      .from('v_debt_call_queue_person')
      .select('*')
      .order('first_name');
    sample = !data?.length;
    rows = (sample ? SAMPLE_PEOPLE : data!).map((p: Record<string, any>) => ({
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
            who: t('voice.who'), source: sample ? t('voice.sample') : t('voice.source'),
            chatPlaceholder: t('voice.chatPlaceholder'), send: t('voice.send'),
            chatFailed: t('voice.chatFailed'),
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
