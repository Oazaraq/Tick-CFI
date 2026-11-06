import { useState, type FocusEvent, type PointerEvent, type ReactNode } from 'react'
import { t } from '../i18n'

/** Graphiques du dashboard, en HTML et SVG simples. Couleurs : rôles --viz-* (index.css), à reprendre avec la DA. */
export interface Datum { key: string; label: string; value: number }
export interface EffortDatum { key: string; label: string; sold: number; consumed: number }

const SERIES = ['var(--viz-1)', 'var(--viz-2)', 'var(--viz-3)', 'var(--viz-4)']
const INK = ['#ffffff', '#ffffff', '#0b0b0b', '#0b0b0b']  // texte posé dans un segment, selon la luminance du fond

/** Info-bulle d'un graphique : valeur en premier, libellé ensuite ; suit le pointeur ou le focus clavier. */
function useTip() {
  const [tip, setTip] = useState<{ x: number; y: number; value: string; label: string } | null>(null)
  const place = (el: Element, x: number, y: number, value: string, label: string) => {
    const box = el.closest('[data-chart]')?.getBoundingClientRect()
    if (box) setTip({ x: x - box.left, y: y - box.top, value, label })
  }
  const bind = (label: string, value: string) => ({
    onPointerMove: (e: PointerEvent<Element>) => place(e.currentTarget, e.clientX, e.clientY, value, label),
    onPointerLeave: () => setTip(null),
    onFocus: (e: FocusEvent<Element>) => {
      const r = e.currentTarget.getBoundingClientRect()
      place(e.currentTarget, r.left + r.width / 2, r.top, value, label)
    },
    onBlur: () => setTip(null),
  })
  const node = tip && (
    <div className="pointer-events-none absolute z-10 max-w-60 rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs shadow"
      style={{ left: tip.x + 12, top: tip.y + 12 }}>
      <div className="font-semibold text-gray-900">{tip.value}</div>
      <div className="text-gray-600">{tip.label}</div>
    </div>
  )
  return { bind, node }
}

const Empty = () => <p className="py-6 text-center text-sm text-gray-400">{t('charts.empty')}</p>

/** Barres horizontales, une seule série : valeur à l'extrémité, clic facultatif (ex. ouvrir le projet). */
export function HBars({ data, format = String, onSelect }: { data: Datum[]; format?: (n: number) => string; onSelect?: (d: Datum) => void }) {
  const tip = useTip()
  if (!data.length) return <Empty />
  const max = Math.max(1, ...data.map((d) => d.value))
  return (
    <div data-chart className="relative space-y-2">
      {data.map((d) => (
        <div key={d.key} className="grid grid-cols-[minmax(5rem,10rem)_1fr] items-center gap-3 text-sm">
          <span className="truncate font-semibold text-gray-700" title={d.label}>{d.label}</span>
          <div className="flex items-center gap-2">
            <button type="button" aria-label={`${d.label} : ${format(d.value)}`} onClick={() => onSelect?.(d)} {...tip.bind(d.label, format(d.value))}
              className={`h-4 rounded-r-[4px] bg-[var(--viz-1)] hover:brightness-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${onSelect ? 'cursor-pointer' : 'cursor-default'}`}
              style={{ flex: `0 0 calc((100% - 4rem) * ${d.value / max})`, minWidth: d.value ? 3 : 0 }} />
            <span className="font-bold tabular-nums text-blue-900">{format(d.value)}</span>
          </div>
        </div>
      ))}
      {tip.node}
    </div>
  )
}

/** Répartition d'un tout (≤ 4 parts) : barre segmentée, espaces de 2 px, légende avec valeurs et parts. */
export function Shares({ data }: { data: Datum[] }) {
  const tip = useTip()
  const total = data.reduce((sum, d) => sum + d.value, 0)
  if (!total) return <Empty />
  const pct = (v: number) => Math.round((v / total) * 100)
  return (
    <div data-chart className="relative">
      <div className="flex h-8 w-full gap-[2px]">
        {data.map((d, i) => d.value > 0 && (
          <button key={d.key} type="button" aria-label={`${d.label} : ${d.value} (${pct(d.value)} %)`} {...tip.bind(d.label, `${d.value} · ${pct(d.value)} %`)}
            className="min-w-[3px] text-xs font-semibold first:rounded-l-[4px] last:rounded-r-[4px] hover:brightness-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            style={{ flexGrow: d.value, flexBasis: 0, background: SERIES[i], color: INK[i] }}>
            {d.value / total >= 0.12 ? d.value : ''}
          </button>
        ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {data.map((d, i) => (
          <li key={d.key} className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: SERIES[i] }} aria-hidden />
            <span className="font-semibold text-gray-700">{d.label}</span>
            <span className="font-bold tabular-nums text-blue-900">{d.value}</span>
            <span className="text-gray-500">({pct(d.value)} %)</span>
          </li>
        ))}
      </ul>
      {tip.node}
    </div>
  )
}

const Legend = ({ items }: { items: [string, string][] }) => (
  <ul className="mb-3 flex flex-wrap gap-x-4 text-sm">
    {items.map(([label, color]) => (
      <li key={label} className="flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} aria-hidden />
        <span className="text-gray-700">{label}</span>
      </li>
    ))}
  </ul>
)

/** J/h vendus et consommés par projet : deux barres par projet, légende obligatoire (deux séries). */
export function EffortBars({ data, format, onSelect }: { data: EffortDatum[]; format: (n: number) => string; onSelect?: (d: EffortDatum) => void }) {
  const tip = useTip()
  if (!data.length) return <Empty />
  const max = Math.max(1, ...data.flatMap((d) => [d.sold, d.consumed]))
  const series: ['sold' | 'consumed', string, string][] = [['sold', t('charts.sold'), SERIES[0]], ['consumed', t('charts.consumed'), SERIES[1]]]
  return (
    <div data-chart className="relative">
      <Legend items={series.map(([, label, color]) => [label, color])} />
      <div className="space-y-3">
        {data.map((d) => (
          <div key={d.key} className="grid grid-cols-[minmax(5rem,10rem)_1fr] items-center gap-3 text-sm">
            <button type="button" className="truncate text-left text-gray-700 hover:underline" title={d.label} onClick={() => onSelect?.(d)}>{d.label}</button>
            <div className="space-y-[2px]">
              {series.map(([key, label, color]) => (
                <div key={key} className="flex items-center gap-2">
                  <span className="h-3 rounded-r-[4px] hover:brightness-110" {...tip.bind(`${d.label} · ${label}`, format(d[key]))}
                    style={{ flex: `0 0 calc((100% - 4rem) * ${d[key] / max})`, minWidth: d[key] ? 3 : 0, background: color }} />
                  <span className="text-xs font-bold tabular-nums text-blue-900">{format(d[key])}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {tip.node}
    </div>
  )
}

function niceMax(value: number): number {
  const step = 10 ** Math.floor(Math.log10(value))
  return [1, 2, 2.5, 5, 10].map((k) => k * step).find((v) => v >= value * 1.05) ?? 10 * step
}

/** Nuage de points : vendus (x) et consommés (y) ; au-dessus de la diagonale, le projet consomme plus que vendu. */
export function EffortScatter({ data, format, onSelect }: { data: EffortDatum[]; format: (n: number) => string; onSelect?: (d: EffortDatum) => void }) {
  const tip = useTip()
  if (!data.length) return <Empty />
  const W = 520, H = 280, m = { l: 40, r: 16, t: 12, b: 40 }
  const max = niceMax(Math.max(1, ...data.flatMap((d) => [d.sold, d.consumed])))
  const x = (v: number) => m.l + (v / max) * (W - m.l - m.r)
  const y = (v: number) => H - m.b - (v / max) * (H - m.t - m.b)
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((k) => k * max)
  const tick = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1).replace('.', ','))
  return (
    <div data-chart className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={t('charts.effort_title')}>
        {ticks.map((v) => (
          <g key={v} className="text-[11px]" fill="var(--viz-text-muted)">
            <line x1={m.l} x2={W - m.r} y1={y(v)} y2={y(v)} stroke="var(--viz-grid)" strokeWidth={1} />
            <line x1={x(v)} x2={x(v)} y1={m.t} y2={H - m.b} stroke="var(--viz-grid)" strokeWidth={1} />
            <text x={m.l - 6} y={y(v) + 4} textAnchor="end">{tick(v)}</text>
            <text x={x(v)} y={H - m.b + 16} textAnchor="middle">{tick(v)}</text>
          </g>
        ))}
        <line x1={x(0)} y1={y(0)} x2={x(max)} y2={y(max)} stroke="var(--viz-axis)" strokeWidth={1} />
        <text x={x(max) - 2} y={y(max) + 68} textAnchor="end" className="text-[11px]" fill="var(--viz-text-muted)">{t('charts.diagonal')}</text>
        <text x={(m.l + W - m.r) / 2} y={H - 6} textAnchor="middle" className="text-[11px]" fill="var(--viz-text-muted)">{t('charts.sold')}</text>
        <text x={12} y={(m.t + H - m.b) / 2} textAnchor="middle" transform={`rotate(-90 12 ${(m.t + H - m.b) / 2})`} className="text-[11px]" fill="var(--viz-text-muted)">{t('charts.consumed')}</text>
        {data.map((d) => {
          const over = d.consumed > d.sold
          const ratio = d.sold ? ` · ${Math.round((d.consumed / d.sold) * 100)} %` : ''
          return (
            <g key={d.key} tabIndex={0} role="button" aria-label={`${d.label} : ${format(d.sold)} / ${format(d.consumed)}`}
              className="cursor-pointer outline-none [&:focus-visible>circle:last-of-type]:stroke-blue-600"
              onClick={() => onSelect?.(d)} onKeyDown={(e) => e.key === 'Enter' && onSelect?.(d)}
              {...tip.bind(d.label, `${format(d.sold)} → ${format(d.consumed)}${ratio}`)}>
              <circle cx={x(d.sold)} cy={y(d.consumed)} r={12} fill="transparent" />
              <circle cx={x(d.sold)} cy={y(d.consumed)} r={5} fill="var(--viz-1)" stroke="var(--viz-surface)" strokeWidth={2} />
              {over && (
                <text x={x(d.sold) + 9} y={y(d.consumed) - 8} className="text-[11px]" fill="var(--viz-text)">
                  {d.label.length > 22 ? `${d.label.slice(0, 21)}…` : d.label}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      <p className="text-xs text-gray-500">{t('charts.scatter_hint')}</p>
      {tip.node}
    </div>
  )
}

/** Carte de graphique : titre, choix de la vue, données en tableau (accessibilité, valeurs sans survol). */
export function ChartCard<V extends string>({ title, views, view, onView, table, children }: {
  title: string
  views?: [V, string][]
  view?: V
  onView?: (v: V) => void
  table: { head: string[]; rows: (string | number)[][] }
  children: ReactNode
}) {
  return (
    <section className="rounded-xl bg-white p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="font-extrabold text-blue-900">{title}</h2>
        {views && (
          <div role="group" aria-label={t('charts.view')} className="ml-auto flex rounded-lg border border-gray-200 p-0.5 text-xs">
            {views.map(([key, label]) => (
              <button key={key} type="button" aria-pressed={view === key} onClick={() => onView?.(key)}
                className={`rounded-lg px-2 py-1 ${view === key ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}>{label}</button>
            ))}
          </div>
        )}
      </div>
      {children}
      {table.rows.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-xs text-gray-500">{t('charts.table')}</summary>
          <table className="mt-2 w-full text-left">
            <thead><tr className="border-b border-gray-200 text-gray-500">{table.head.map((h) => <th key={h} className="py-1 pr-3 font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {table.rows.map((row, i) => (
                <tr key={i} className="border-b border-gray-100">{row.map((cell, j) => <td key={j} className={`py-1 pr-3 ${j ? 'tabular-nums' : ''}`}>{cell}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </section>
  )
}
