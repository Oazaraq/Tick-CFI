import type { EffortDatum } from './charts'
import { EffortBars } from './charts'
import { t } from '../i18n'
import { fmtDays, fmtHours, HOURLY_CATEGORY } from '../lib/format'

/** Taux de consommation (consommé / vendu), en %, ou null sans vendu. */
export const rate = (sold: number, consumed: number) => (sold ? Math.round((consumed / sold) * 100) : null)
/** Orange à partir de 80 %, rouge au-delà de 100 %. */
export const rateClass = (r: number | null) =>
  r == null ? 'text-gray-400' : r > 100 ? 'font-bold text-red-700' : r >= 80 ? 'font-semibold text-amber-700' : 'text-gray-800'

/** Ventilation du vendu et du consommé par catégorie : tableau (reste, taux) et barres.
 *  La gestion de projet, décomptée à l'heure, est aussi donnée en heures (1 j = 7,5 h). */
export default function EffortBreakdown({ lines, chart = true, onSelect }: {
  lines: EffortDatum[]; chart?: boolean; onSelect?: (d: EffortDatum) => void
}) {
  const total = lines.reduce((s, l) => ({ sold: s.sold + l.sold, consumed: s.consumed + l.consumed }), { sold: 0, consumed: 0 })
  const hours = (l: EffortDatum, n: number) => l.key === HOURLY_CATEGORY && <span className="text-gray-500"> ({fmtHours(n)})</span>
  const totalRate = rate(total.sold, total.consumed)
  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="py-1.5 font-medium">{t('reporting.category')}</th>
              {(['sold', 'consumed', 'remaining', 'rate'] as const).map((k) => <th key={k} className="py-1.5 text-right font-medium">{t(`reporting.${k}`)}</th>)}
            </tr>
          </thead>
          <tbody>
            {lines.map((l) => {
              const r = rate(l.sold, l.consumed)
              return (
                <tr key={l.key} className="border-b border-gray-100">
                  <td className="py-1.5">{l.label}</td>
                  <td className="py-1.5 text-right tabular-nums">{fmtDays(l.sold)}{hours(l, l.sold)}</td>
                  <td className="py-1.5 text-right tabular-nums">{fmtDays(l.consumed)}{hours(l, l.consumed)}</td>
                  <td className={`py-1.5 text-right tabular-nums ${l.consumed > l.sold ? 'text-red-700' : ''}`}>{fmtDays(l.sold - l.consumed)}</td>
                  <td className={`py-1.5 text-right tabular-nums ${rateClass(r)}`}>{r == null ? '—' : `${r} %`}</td>
                </tr>
              )
            })}
            <tr className="font-semibold">
              <td className="py-1.5">{t('reporting.total')}</td>
              <td className="py-1.5 text-right tabular-nums">{fmtDays(total.sold)}</td>
              <td className="py-1.5 text-right tabular-nums">{fmtDays(total.consumed)}</td>
              <td className={`py-1.5 text-right tabular-nums ${total.consumed > total.sold ? 'text-red-700' : ''}`}>{fmtDays(total.sold - total.consumed)}</td>
              <td className={`py-1.5 text-right tabular-nums ${rateClass(totalRate)}`}>{totalRate == null ? '—' : `${totalRate} %`}</td>
            </tr>
          </tbody>
        </table>
      </div>
      {chart && <EffortBars data={lines} format={fmtDays} onSelect={onSelect} />}
    </div>
  )
}
