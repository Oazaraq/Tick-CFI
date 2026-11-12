import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router'
import { api } from '../api/client'
import type { EffortReportRow } from '../api/types'
import { ChartCard, EffortBars } from '../components/charts'
import { Button, ErrorState, inputClass, Spinner } from '../components/ui'
import { t } from '../i18n'
import { download } from '../lib/exportImage'
import { fmtDays, fmtHours, fullName, HOURLY_CATEGORY, toHours, todayParis } from '../lib/format'

type Total = { key: string; label: string; sold: number; consumed: number; extra?: EffortReportRow }
const NOT_DONE = '!done'

function sum(rows: EffortReportRow[], key: (r: EffortReportRow) => string, label: (r: EffortReportRow) => string): Total[] {
  const totals = new Map<string, Total>()
  for (const r of rows) {
    const k = key(r)
    const tot = totals.get(k) ?? { key: k, label: label(r), sold: 0, consumed: 0, extra: r }
    tot.sold += r.sold
    tot.consumed += r.consumed
    totals.set(k, tot)
  }
  return [...totals.values()]
}

const rate = (sold: number, consumed: number) => (sold ? Math.round((consumed / sold) * 100) : null)
const rateClass = (r: number | null) => (r == null ? 'text-gray-400' : r > 100 ? 'font-bold text-red-700' : r >= 80 ? 'font-semibold text-amber-700' : 'text-gray-800')
const num = (n: number) => n.toLocaleString('fr-FR', { maximumFractionDigits: 2, useGrouping: false })
const cell = (v: string) => (/[;"\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v)

/** Reporting de charge : jours vendus et consommés par projet et par catégorie, export CSV pour Excel. */
export default function ReportingPage() {
  const navigate = useNavigate()
  const report = useQuery({ queryKey: ['reporting', 'effort'], queryFn: () => api.get<EffortReportRow[]>('/reporting/effort') })
  const [status, setStatus] = useState('')
  const [owner, setOwner] = useState('')
  if (report.isPending) return <Spinner />
  if (report.isError) return <ErrorState error={report.error} />
  const all = report.data
  const statuses = sum(all, (r) => r.status_code, (r) => r.status_label)
  const owners = sum(all, (r) => String(r.owner.id), (r) => fullName(r.owner))
  const rows = all.filter((r) => (!status || (status === NOT_DONE ? r.status_code !== 'done' : r.status_code === status))
    && (!owner || String(r.owner.id) === owner))
  const byProject = sum(rows, (r) => String(r.project_id), (r) => r.title)
  const byCategory = sum(rows, (r) => r.category ?? '', (r) => r.category_label).sort((a, b) => a.label.localeCompare(b.label, 'fr'))
  const total = { sold: rows.reduce((s, r) => s + r.sold, 0), consumed: rows.reduce((s, r) => s + r.consumed, 0) }

  const exportCsv = () => {
    const head = ['Projet', 'Statut', 'Responsable', 'Catégorie', 'Vendu (j)', 'Consommé (j)', 'Reste (j)', 'Consommé (%)', 'Vendu (h)', 'Consommé (h)']
    const lines = rows.map((r) => {
      const hourly = r.category === HOURLY_CATEGORY
      const pct = rate(r.sold, r.consumed)
      return [r.title, r.status_label, fullName(r.owner), r.category_label, num(r.sold), num(r.consumed), num(r.sold - r.consumed),
        pct == null ? '' : String(pct), hourly ? num(toHours(r.sold)) : '', hourly ? num(toHours(r.consumed)) : ''].map(cell).join(';')
    })
    download(new Blob(['﻿' + [head.join(';'), ...lines].join('\r\n')], { type: 'text/csv;charset=utf-8' }), `reporting-charge-${todayParis()}.csv`)
  }

  const table = (title: string, first: string, data: Total[], link: boolean) => (
    <section className="overflow-x-auto rounded-xl bg-white p-4 shadow-sm">
      <h2 className="mb-2 font-bold text-blue-900">{title}</h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-500">
            <th className="py-1.5 font-medium">{first}</th>
            {link && <><th className="py-1.5 font-medium">{t('reporting.status')}</th><th className="py-1.5 font-medium">{t('reporting.owner')}</th></>}
            {(['sold', 'consumed', 'remaining', 'rate'] as const).map((k) => <th key={k} className="py-1.5 text-right font-medium">{t(`reporting.${k}`)}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map((d) => {
            const pct = rate(d.sold, d.consumed)
            const hours = !link && d.key === HOURLY_CATEGORY
            return (
              <tr key={d.key} className="border-b border-gray-100">
                <td className="py-1.5">{link ? <Link to={`/projects/${d.key}?tab=planning`} className="font-medium text-blue-700 hover:underline">{d.label}</Link> : d.label}</td>
                {link && <><td className="py-1.5">{d.extra?.status_label}</td><td className="py-1.5">{fullName(d.extra?.owner)}</td></>}
                <td className="py-1.5 text-right tabular-nums">{fmtDays(d.sold)}{hours && <span className="text-gray-500"> ({fmtHours(d.sold)})</span>}</td>
                <td className="py-1.5 text-right tabular-nums">{fmtDays(d.consumed)}{hours && <span className="text-gray-500"> ({fmtHours(d.consumed)})</span>}</td>
                <td className={`py-1.5 text-right tabular-nums ${d.consumed > d.sold ? 'text-red-700' : ''}`}>{fmtDays(d.sold - d.consumed)}</td>
                <td className={`py-1.5 text-right tabular-nums ${rateClass(pct)}`}>{pct == null ? '—' : `${pct} %`}</td>
              </tr>
            )
          })}
          <tr className="font-semibold">
            <td className="py-1.5" colSpan={link ? 3 : 1}>{t('reporting.total')}</td>
            <td className="py-1.5 text-right tabular-nums">{fmtDays(total.sold)}</td>
            <td className="py-1.5 text-right tabular-nums">{fmtDays(total.consumed)}</td>
            <td className="py-1.5 text-right tabular-nums">{fmtDays(total.sold - total.consumed)}</td>
            <td className={`py-1.5 text-right tabular-nums ${rateClass(rate(total.sold, total.consumed))}`}>{rate(total.sold, total.consumed) ?? '—'}{total.sold ? ' %' : ''}</td>
          </tr>
        </tbody>
      </table>
    </section>
  )

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <header className="flex flex-wrap items-end gap-3">
        <div>
          <h1 className="text-xl font-extrabold text-blue-900">{t('reporting.title')}</h1>
          <p className="text-sm text-gray-600">{t('reporting.subtitle')}</p>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <select className={`${inputClass} w-auto`} value={status} onChange={(e) => setStatus(e.target.value)} aria-label={t('reporting.status')}>
            <option value="">{t('reporting.all_statuses')}</option>
            <option value={NOT_DONE}>{t('reporting.not_delivered')}</option>
            {statuses.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
          <select className={`${inputClass} w-auto`} value={owner} onChange={(e) => setOwner(e.target.value)} aria-label={t('reporting.owner')}>
            <option value="">{t('reporting.all_owners')}</option>
            {owners.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
          </select>
          <Button variant="secondary" disabled={!rows.length} onClick={exportCsv}>{t('reporting.export')}</Button>
        </div>
      </header>
      {!rows.length ? <p className="rounded-xl bg-white p-6 text-center text-sm text-gray-500 shadow-sm">{t('reporting.empty')}</p> : (
        <>
          {table(t('reporting.by_project'), t('reporting.project'), byProject, true)}
          {table(t('reporting.by_category'), t('reporting.category'), byCategory, false)}
          <ChartCard title={t('reporting.chart')}
            table={{ head: [t('reporting.project'), t('reporting.sold'), t('reporting.consumed')], rows: byProject.map((d) => [d.label, fmtDays(d.sold), fmtDays(d.consumed)]) }}>
            <EffortBars data={byProject} format={fmtDays} onSelect={(d) => navigate(`/projects/${d.key}?tab=planning`)} />
          </ChartCard>
        </>
      )}
    </div>
  )
}
