import type { RefObject } from 'react'
import type { PlanningItem } from '../api/types'
import { t } from '../i18n'
import { fmtDate, fmtDays, todayParis } from '../lib/format'

const DAY = 86_400_000
const LABEL_W = 220
const ROW_H = 30
const TITLE_H = 36
const AXIS_H = 44
const PAD = 12
// Couleurs neutres provisoires (charte au lot 5) ; l'orange signale une alerte (dépassement, ordre non respecté)
const PLANNED = '#c7d2fe'
const PHASE = '#6366f1'
const INK = '#111827'
const LINK = '#6b7280'
const ALERT = '#f59e0b'
const DIAMOND = 7

const ms = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10))
const isoOf = (time: number) => new Date(time).toISOString().slice(0, 10)
const monthYear = new Intl.DateTimeFormat('fr-FR', { month: 'long', year: 'numeric', timeZone: 'UTC' })
const monthShort = new Intl.DateTimeFormat('fr-FR', { month: 'short', timeZone: 'UTC' })
const clip = (text: string, max: number) => (text.length > max ? `${text.slice(0, max - 1)}…` : text)
const diamond = (cx: number, cy: number, r: number) => `${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r} ${cx - r},${cy}`

type Unit = 'day' | 'week' | 'month'

/** Échelle automatique selon la durée couverte : jours (≤ 1 mois), semaines (≤ 6 mois), mois au-delà. */
function frame(items: PlanningItem[]) {
  let start = Math.min(...items.map((i) => ms(i.start_date)))
  let end = Math.max(...items.map((i) => ms(i.end_date))) + DAY
  const span = (end - start) / DAY
  const unit: Unit = span <= 31 ? 'day' : span <= 183 ? 'week' : 'month'
  if (unit === 'week') {
    start -= ((new Date(start).getUTCDay() + 6) % 7) * DAY // lundi précédent
    end += ((8 - new Date(end).getUTCDay()) % 7) * DAY // lundi suivant
  } else if (unit === 'month') {
    const s = new Date(start)
    const e = new Date(end - DAY)
    start = Date.UTC(s.getUTCFullYear(), s.getUTCMonth(), 1)
    end = Date.UTC(e.getUTCFullYear(), e.getUTCMonth() + 1, 1)
  }
  const px = Math.max({ day: 22, week: 4, month: 1.5 }[unit], 900 / ((end - start) / DAY))
  return { start, end, unit, px }
}

function axis(start: number, end: number, unit: Unit) {
  const ticks: { time: number; label: string }[] = []
  for (let time = start; time < end;) {
    const d = new Date(time)
    if (unit === 'day') {
      ticks.push({ time, label: String(d.getUTCDate()) })
      time += DAY
    } else if (unit === 'week') {
      ticks.push({ time, label: fmtDate(isoOf(time)).slice(0, 5) })
      time += 7 * DAY
    } else {
      ticks.push({ time, label: monthShort.format(d) })
      time = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1)
    }
  }
  const groups: { time: number; until: number; label: string }[] = []
  for (let time = start; time < end;) {
    const d = new Date(time)
    const next = unit === 'month' ? Date.UTC(d.getUTCFullYear() + 1, 0, 1) : Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1)
    groups.push({ time, until: Math.min(next, end), label: unit === 'month' ? String(d.getUTCFullYear()) : monthYear.format(d) })
    time = next
  }
  return { ticks, groups }
}

/**
 * Gantt en SVG pur (avenants 1 et 3), exportable tel quel en .png :
 * barre claire = durée prévue, remplissage = j/h consommés sur vendus, flèche = dépendance.
 */
export default function Gantt({ title, items, svgRef }: { title: string; items: PlanningItem[]; svgRef: RefObject<SVGSVGElement | null> }) {
  const { start, end, unit, px } = frame(items)
  const { ticks, groups } = axis(start, end, unit)
  const x = (time: number) => LABEL_W + ((time - start) / DAY) * px
  const width = Math.ceil(x(end)) + PAD
  const top = TITLE_H + AXIS_H
  const height = top + items.length * ROW_H + PAD
  const today = ms(todayParis())
  const row = new Map(items.map((item, i) => [item.id, i]))
  const centerY = (i: number) => top + i * ROW_H + ROW_H / 2
  // Bords gauche et droit de chaque élément, là où partent et arrivent les flèches
  const center = (item: PlanningItem) => x(ms(item.start_date)) + px / 2
  const left = (item: PlanningItem) => (item.kind === 'milestone' ? center(item) - DIAMOND : x(ms(item.start_date)))
  const right = (item: PlanningItem) => (item.kind === 'milestone' ? center(item) + DIAMOND : x(ms(item.end_date) + DAY))

  const arrows = items.flatMap((item) => item.predecessor_ids.flatMap((pid) => {
    const pi = row.get(pid)
    if (pi === undefined) return []
    const pred = items[pi]
    const [x1, y1, x2, y2] = [right(pred), centerY(pi), left(item), centerY(row.get(item.id)!)]
    const down = y2 > y1 ? 1 : -1
    let d: string
    if (x2 - x1 >= 12) {
      d = `M${x1},${y1} H${x1 + 6} V${y2} H${x2 - 1}` // écart suffisant : coude classique
    } else if (x2 - x1 >= -6) {
      // éléments qui s'enchaînent : la flèche descend depuis la fin du prédécesseur
      const xd = pred.kind === 'milestone' ? center(pred) : Math.min(x1 - 6, x2 - 4)
      const yd = y1 + down * (pred.kind === 'milestone' ? DIAMOND : 8)
      d = `M${xd},${yd} V${y2} H${x2 - 1}`
    } else {
      d = `M${x1},${y1} H${x1 + 6} V${y2 - (down * ROW_H) / 2} H${x2 - 8} V${y2} H${x2 - 1}` // chevauchement : boucle d'alerte
    }
    return [{ key: `${pid}-${item.id}`, d, alert: item.dependency_issues.includes(pid) }]
  }))

  return (
    <svg ref={svgRef} xmlns="http://www.w3.org/2000/svg" width={width} height={height} viewBox={`0 0 ${width} ${height}`}
      fontFamily="system-ui, -apple-system, 'Segoe UI', sans-serif" fontSize="12">
      <defs>
        {[['ok', LINK], ['ko', ALERT]].map(([id, color]) => (
          <marker key={id} id={`arrow-${id}`} viewBox="0 0 6 6" refX="5" refY="3" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L6,3 L0,6 z" fill={color} />
          </marker>
        ))}
      </defs>
      <rect width={width} height={height} fill="#ffffff" />
      <text x={PAD} y={23} fontSize="15" fontWeight="600" fill={INK}>{title}</text>
      <text x={width - PAD} y={23} textAnchor="end" fill="#6b7280">{t('planning.as_of', { date: fmtDate(todayParis()) })}</text>
      {groups.map((g, i) => (
        <g key={g.time}>
          <rect x={x(g.time)} y={TITLE_H} width={x(g.until) - x(g.time)} height={22} fill={i % 2 ? '#f3f4f6' : '#e5e7eb'} />
          <text x={x(g.time) + 4} y={TITLE_H + 15} fill="#374151">{g.label}</text>
        </g>
      ))}
      {ticks.map((tk) => (
        <g key={tk.time}>
          <line x1={x(tk.time)} x2={x(tk.time)} y1={TITLE_H + 22} y2={height - PAD} stroke="#e5e7eb" />
          <text x={x(tk.time) + 3} y={TITLE_H + 37} fontSize="10" fill="#6b7280">{tk.label}</text>
        </g>
      ))}
      {items.map((item, i) => {
        const y = top + i * ROW_H
        const s = ms(item.start_date)
        const w = Math.max(3, x(ms(item.end_date) + DAY) - x(s))
        const sold = item.days_sold ?? 0
        const consumed = item.days_consumed ?? 0
        const ratio = sold > 0 ? Math.min(consumed / sold, 1) : 1
        return (
          <g key={item.id}>
            <line x1={0} x2={width} y1={y + ROW_H} y2={y + ROW_H} stroke="#f3f4f6" />
            <text x={PAD} y={y + 19} fill={INK}>{clip(item.label, sold > 0 ? 22 : 30)}</text>
            {sold > 0 && (
              <text x={LABEL_W - 8} y={y + 19} textAnchor="end" fontSize="10" fill={consumed > sold ? ALERT : '#6b7280'}>
                {fmtDays(consumed)}/{fmtDays(sold)} j
              </text>
            )}
            {item.kind === 'milestone'
              ? <polygon points={diamond(x(s) + px / 2, y + ROW_H / 2, DIAMOND)} fill={INK} />
              : (
                <>
                  <rect x={x(s)} y={y + 7} width={w} height={16} rx={3} fill={sold > 0 ? PLANNED : PHASE} />
                  {sold > 0 && consumed > 0 && <rect x={x(s)} y={y + 7} width={w * ratio} height={16} rx={3} fill={consumed > sold ? ALERT : PHASE} />}
                </>
              )}
          </g>
        )
      })}
      {arrows.map((a) => (
        <path key={a.key} d={a.d} fill="none" stroke={a.alert ? ALERT : LINK} strokeWidth={1.2} markerEnd={`url(#arrow-${a.alert ? 'ko' : 'ok'})`} />
      ))}
      {today >= start && today < end && (
        <line x1={x(today) + px / 2} x2={x(today) + px / 2} y1={TITLE_H} y2={height - PAD} stroke={INK} strokeWidth={1.5} strokeDasharray="4 3" />
      )}
    </svg>
  )
}
