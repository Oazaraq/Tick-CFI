import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, qs } from '../api/client'
import type { Action, Dashboard, DashboardCharts, TileKey, Zone } from '../api/types'
import { ChartCard, EffortBars, HBars, Shares } from '../components/charts'
import { Chip, ErrorState, inputBase, inputClass, Spinner, UserSelect, useToast } from '../components/ui'
import { useMe, useUsers } from '../hooks'
import { t } from '../i18n'
import { daysSince, dueClass, fmtDate, fmtDays, fullName } from '../lib/format'

export default function DashboardPage() {
  const [mine, setMine] = useState(false)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const toast = useToast()
  const users = useUsers()
  const me = useMe().data
  const soonDays = me?.due_soon_days ?? 7
  const dash = useQuery({ queryKey: ['dashboard', mine], queryFn: () => api.get<Dashboard>(`/dashboard${qs({ mine })}`) })
  const assign = useMutation({
    mutationFn: ({ id, assignee_id }: { id: number; assignee_id: number }) => api.patch(`/actions/${id}`, { assignee_id }),
    onSuccess: () => {
      for (const key of ['dashboard', 'actions', 'projects', 'project', 'history']) qc.invalidateQueries({ queryKey: [key] })
      toast(t('action.saved'))
    },
    onError: (e) => toast(e.message, true),
  })

  if (dash.isPending) return <Spinner />
  if (dash.isError) return <ErrorState error={dash.error} />
  const d = dash.data
  const projectScope = mine ? '&mine=1' : ''
  const actionScope = mine ? '&my_projects=1' : ''
  const tiles: [TileKey, string][] = [
    ['active_projects', `/projects?view=list&active=1${projectScope}`],
    ['open_actions', `/actions?preset=open${actionScope}`],
    ['overdue_actions', `/actions?preset=overdue${actionScope}`],
    ['blocked_projects', `/projects?view=list&blocked=1${projectScope}`],
    ['my_actions', '/actions'],
  ]
  const reassign = (a: Action) => (
    <UserSelect className={`${inputBase} w-40`} users={users.data ?? []} value={null} allowEmpty
      onChange={(id) => id && assign.mutate({ id: a.id, assignee_id: id })} />
  )

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-extrabold text-blue-900">{t('nav.dashboard')}</h1>
        {me?.role === 'admin' && (  // les autres ne voient déjà que leurs projets (compartimentage)
          <div className="ml-auto flex gap-1">
            <Chip active={!mine} onClick={() => setMine(false)}>{t('dashboard.all')}</Chip>
            <Chip active={mine} onClick={() => setMine(true)}>{t('projects.mine')}</Chip>
          </div>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {tiles.map(([key, to]) => (
          <button key={key} type="button" onClick={() => navigate(to)} className="rounded-xl bg-white p-4 text-left shadow-sm hover:ring-2 hover:ring-blue-200">
            <p className="text-sm font-bold text-gray-600">{t(`dashboard.${key}`)}</p>
            <p className={`mt-1 text-4xl font-extrabold tabular-nums ${key === 'overdue_actions' && d.tiles[key] ? 'text-prio-critical' : 'text-blue-800'}`}>{d.tiles[key]}</p>
          </button>
        ))}
      </div>
      <Charts c={d.charts} />
      <div className="grid gap-4 md:grid-cols-2">
        <ZoneCard title={t('dashboard.due_soon', { n: soonDays })} zone={d.due_soon} to={`/actions?preset=due_soon${actionScope}`}
          render={(a) => <ActionLine a={a}><span className="text-gray-500">{fullName(a.assignee)}</span><span className={dueClass(a.due_date, false, soonDays)}>{fmtDate(a.due_date)}</span></ActionLine>} />
        <ZoneCard title={t('dashboard.blocked_projects')} zone={d.blocked_projects} to={`/projects?view=list&blocked=1${projectScope}`}
          render={(p) => (
            <>
              <Link to={`/projects/${p.id}`} className="font-medium hover:underline">{p.title}</Link>
              <span className="min-w-0 flex-1 truncate text-gray-500" title={p.blocked_reason ?? ''}>{p.blocked_reason}</span>
              {p.blocked_since && <span className="text-prio-critical">{t('dashboard.days', { n: daysSince(p.blocked_since) })}</span>}
            </>
          )} />
        <ZoneCard title={t('dashboard.unassigned')} zone={d.unassigned} to={`/actions?preset=unassigned${actionScope}`}
          render={(a) => <ActionLine a={a}>{reassign(a)}</ActionLine>} />
        <ZoneCard title={t('dashboard.inactive')} zone={d.inactive_assignee} to={`/actions?preset=inactive${actionScope}`}
          render={(a) => <ActionLine a={a}><span className="text-gray-400 line-through">{fullName(a.assignee)}</span>{reassign(a)}</ActionLine>} />
      </div>
      {d.no_due_date > 0 && (
        <p className="text-sm text-gray-600">
          ⚠ {t('dashboard.no_due', { n: d.no_due_date })} — <Link to={`/actions?preset=no_due${actionScope}`} className="text-blue-700 hover:underline">{t('dashboard.see_all')}</Link>
        </p>
      )}
    </div>
  )
}

const days = (n: number) => `${fmtDays(n)} j`

/** Graphiques de l'état du jour (avenant 3) : chaque carte propose ses vues et ses données en tableau. */
function Charts({ c }: { c: DashboardCharts }) {
  const navigate = useNavigate()
  const [statusView, setStatusView] = useState<'bars' | 'shares'>('bars')
  const statuses = c.projects_by_status.map((s) => ({ key: s.code, label: s.label ?? s.code, value: s.count }))
  const priorities = c.actions_by_priority.map((p) => ({ key: p.code, label: t(`priority.${p.code}`), value: p.count }))
  const overdue = c.overdue_by_project.map((p) => ({ key: String(p.project_id), label: p.title, value: p.count }))
  const effort = c.effort_by_project.map((p) => ({ key: String(p.project_id), label: p.title, sold: p.sold, consumed: p.consumed }))
  const open = (d: { key: string }) => navigate(`/projects/${d.key}`)
  const counts = (head: string, data: { label: string; value: number }[]) => ({ head: [head, t('charts.actions')], rows: data.map((d) => [d.label, d.value]) })
  return (
    <div className="grid items-start gap-4 md:grid-cols-2">
      <ChartCard title={t('charts.status_title')} views={[['bars', t('charts.view_bars')], ['shares', t('charts.view_shares')]]}
        view={statusView} onView={setStatusView}
        table={{ head: [t('field.status'), t('charts.projects')], rows: statuses.map((d) => [d.label, d.value]) }}>
        {statusView === 'bars' ? <HBars data={statuses} /> : <Shares data={statuses} />}
      </ChartCard>
      <ChartCard title={t('charts.priority_title')} table={counts(t('field.priority'), priorities)}>
        <HBars data={priorities} />
      </ChartCard>
      <ChartCard title={t('charts.overdue_title')} table={counts(t('charts.project'), overdue)}>
        <HBars data={overdue} onSelect={open} />
      </ChartCard>
      <ChartCard title={t('charts.effort_title')}
        table={{ head: [t('charts.project'), t('charts.sold'), t('charts.consumed')], rows: effort.map((d) => [d.label, days(d.sold), days(d.consumed)]) }}>
        <EffortBars data={effort} format={days} onSelect={open} />
      </ChartCard>
    </div>
  )
}

function ZoneCard<T extends { id: number }>({ title, zone, to, render }: { title: string; zone: Zone<T>; to: string; render: (item: T) => ReactNode }) {
  return (
    <section className="rounded-xl bg-white p-4 shadow-sm">
      <h2 className="mb-2 font-bold text-blue-900">⚠ {title} ({zone.total})</h2>
      {zone.items.length ? (
        <ul className="divide-y divide-gray-100 text-sm">
          {zone.items.map((item) => <li key={item.id} className="flex items-center gap-2 py-1.5">{render(item)}</li>)}
        </ul>
      ) : <p className="text-sm text-gray-400">{t('dashboard.none')}</p>}
      {zone.total > 0 && <Link to={to} className="mt-2 inline-block text-xs text-blue-700 hover:underline">{t('dashboard.see_all')}</Link>}
    </section>
  )
}

function ActionLine({ a, children }: { a: Action; children?: ReactNode }) {
  return (
    <>
      <Link to={`/projects/${a.project_id}?tab=actions`} className="min-w-0 flex-1 truncate hover:underline">
        <span className="font-medium">{a.title}</span> <span className="text-gray-500">· {a.project_title}</span>
      </Link>
      {children}
    </>
  )
}
