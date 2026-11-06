import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, qs } from '../api/client'
import { ACTION_STATUSES, isClosed, PRIORITIES } from '../api/types'
import type { Action, ActionStatus, ProjectCard } from '../api/types'
import { Button, Empty, ErrorState, inputBase, inputClass, PriorityBadge, Spinner, useToast } from '../components/ui'
import DeleteActionButton from '../components/DeleteActionButton'
import { useCan, useMe } from '../hooks'
import { t } from '../i18n'
import { dueClass, fmtDate, fullName } from '../lib/format'

const PRESETS = ['me', 'open', 'overdue', 'due_soon', 'unassigned', 'inactive', 'no_due'] as const
type Preset = (typeof PRESETS)[number]

/** « Mes actions » (DFB §4.7) et listes filtrées ouvertes depuis le dashboard (?preset=…). */
export default function ActionsPage() {
  const [params] = useSearchParams()
  const raw = params.get('preset') ?? 'me'
  const preset: Preset = (PRESETS as readonly string[]).includes(raw) ? (raw as Preset) : 'me'
  const soonDays = useMe().data?.due_soon_days ?? 7
  const canWrite = useCan()('action_write')
  const qc = useQueryClient()
  const toast = useToast()
  const [f, setF] = useState({ status: '', priority: '', project_id: '', hide_closed: true })
  const projects = useQuery({ queryKey: ['projects', 'all'], queryFn: () => api.get<ProjectCard[]>('/projects?include_old_done=true') })
  const presetFilters: Record<Preset, Record<string, string | number | boolean>> = {
    me: {}, open: {}, overdue: { overdue: true }, due_soon: { due_within_days: soonDays },
    unassigned: { unassigned: true }, inactive: { inactive_assignee: true }, no_due: { no_due_date: true },
  }
  const query = { ...f, ...presetFilters[preset], my_projects: params.get('my_projects') === '1' }
  const path = preset === 'me' ? '/actions/me' : '/actions'
  const actions = useQuery({ queryKey: ['actions', 'list', preset, query], queryFn: () => api.get<Action[]>(`${path}${qs(query)}`) })
  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ActionStatus }) => api.patch(`/actions/${id}`, { status }),
    onSuccess: () => {
      for (const key of ['actions', 'dashboard', 'projects', 'project', 'history']) qc.invalidateQueries({ queryKey: [key] })
      toast(t('action.saved'))
    },
    onError: (e) => toast(e.message, true),
  })

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <h1 className="text-xl font-extrabold text-blue-900">{t(`actions_page.${preset}`)}</h1>
      <div className="flex flex-wrap items-center gap-2">
        <select className={`${inputBase} w-40`} value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}>
          <option value="">{t('actions.all_statuses')}</option>
          {ACTION_STATUSES.map((s) => <option key={s} value={s}>{t(`action_status.${s}`)}</option>)}
        </select>
        <select className={`${inputBase} w-40`} value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })}>
          <option value="">{t('projects.all_priorities')}</option>
          {PRIORITIES.map((p) => <option key={p} value={p}>{t(`priority.${p}`)}</option>)}
        </select>
        <select className={`${inputBase} w-56`} value={f.project_id} onChange={(e) => setF({ ...f, project_id: e.target.value })}>
          <option value="">{t('actions.all_projects')}</option>
          {projects.data?.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
        </select>
        <label className="flex items-center gap-1 text-sm">
          <input type="checkbox" checked={f.hide_closed} onChange={(e) => setF({ ...f, hide_closed: e.target.checked })} />
          {t('actions.hide_closed')}
        </label>
      </div>
      {actions.isPending ? <Spinner /> : actions.isError ? <ErrorState error={actions.error} /> : !actions.data.length ? <Empty text={t('actions.empty')} /> : (
        <table className="w-full rounded-xl bg-white text-sm shadow-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="px-3 py-2 font-medium">{t('field.due_date')}</th>
              <th className="px-3 py-2 font-medium">{t('projects.col.title')}</th>
              <th className="px-3 py-2 font-medium">{t('actions.col.action')}</th>
              {preset !== 'me' && <th className="px-3 py-2 font-medium">{t('field.assignee')}</th>}
              <th className="px-3 py-2 font-medium">{t('field.priority')}</th>
              <th className="px-3 py-2 font-medium">{t('field.status')}</th>
            </tr>
          </thead>
          <tbody>
            {actions.data.map((a) => (
              <tr key={a.id} className="border-b border-gray-100">
                <td className={`px-3 py-2 ${dueClass(a.due_date, isClosed(a.status), soonDays)}`}>{fmtDate(a.due_date)}</td>
                <td className="px-3 py-2"><Link to={`/projects/${a.project_id}`} className="hover:underline">{a.project_title}</Link></td>
                <td className="px-3 py-2"><Link to={`/projects/${a.project_id}?tab=actions`} className="font-medium text-blue-800 hover:underline">{a.title}</Link></td>
                {preset !== 'me' && <td className="px-3 py-2">{fullName(a.assignee) || <span className="text-gray-400">{t('actions.unassigned')}</span>}</td>}
                <td className="px-3 py-2"><PriorityBadge value={a.priority} /></td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <select className={`${inputBase} w-36`} value={a.status} disabled={!canWrite}
                      onChange={(e) => setStatus.mutate({ id: a.id, status: e.target.value as ActionStatus })}>
                      {ACTION_STATUSES.map((s) => <option key={s} value={s}>{t(`action_status.${s}`)}</option>)}
                    </select>
                    {canWrite && !isClosed(a.status) && (
                      <Button variant="ghost" title={t('actions.mark_done')} onClick={() => setStatus.mutate({ id: a.id, status: 'done' })}>✓</Button>
                    )}
                    <DeleteActionButton action={a} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
