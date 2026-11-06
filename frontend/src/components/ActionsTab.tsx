import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { ACTION_STATUSES, isClosed, PRIORITIES } from '../api/types'
import type { Action, ActionStatus, Priority, Project, Sourcing } from '../api/types'
import { useCan, useMe, useTeam } from '../hooks'
import { t } from '../i18n'
import { dueClass, fmtDate, fullName } from '../lib/format'
import DeleteActionButton from './DeleteActionButton'
import { Button, Empty, ErrorState, Field, inputBase, inputClass, PriorityBadge, Spinner, UserSelect, useToast } from './ui'

export default function ActionsTab({ project }: { project: Project }) {
  const can = useCan()
  const canWrite = can('action_write')
  const canDelete = can('action_delete')
  const soonDays = useMe().data?.due_soon_days ?? 7
  const qc = useQueryClient()
  const toast = useToast()
  const actions = useQuery({ queryKey: ['actions', project.id], queryFn: () => api.get<Action[]>(`/projects/${project.id}/actions`) })
  const [selected, setSelected] = useState<Action | null>(null)
  const refresh = () => { for (const key of ['actions', 'project', 'projects', 'history']) qc.invalidateQueries({ queryKey: [key] }) }
  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ActionStatus }) => api.patch(`/actions/${id}`, { status }),
    onSuccess: () => { refresh(); toast(t('action.saved')) },
    onError: (e) => toast(e.message, true),
  })

  const list = actions.data ?? []
  const counts = {
    open: list.filter((a) => !isClosed(a.status)).length,
    done: list.filter((a) => a.status === 'done').length,
    overdue: list.filter((a) => a.is_overdue).length,
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">{t('actions.counters', counts)}</p>
      {canWrite && <QuickCreate projectId={project.id} onCreated={refresh} />}
      {actions.isPending ? <Spinner /> : actions.isError ? <ErrorState error={actions.error} /> : !list.length ? <Empty text={t('actions.empty')} /> : (
        <table className="w-full rounded-xl bg-white text-sm shadow-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              {['title', 'assignee', 'sourcing', 'due_date', 'priority', 'status'].map((k) => <th key={k} className="px-3 py-2 font-medium">{t(`field.${k}`)}</th>)}
              {canDelete && <th className="w-10" aria-label={t('common.delete')} />}
            </tr>
          </thead>
          <tbody>
            {list.map((a) => (
              <tr key={a.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="cursor-pointer px-3 py-2 font-medium text-blue-800 hover:underline" onClick={() => setSelected(a)}>{a.title}</td>
                <td className="px-3 py-2">{a.assignee ? fullName(a.assignee) : <span className="text-gray-400">{t('actions.unassigned')}</span>}</td>
                <td className="px-3 py-2">{t(`sourcing.${a.sourcing}`)}{a.subcontractor && <span className="text-gray-500"> · {a.subcontractor}</span>}</td>
                <td className={`px-3 py-2 ${dueClass(a.due_date, isClosed(a.status), soonDays)}`}>{fmtDate(a.due_date)}</td>
                <td className="px-3 py-2"><PriorityBadge value={a.priority} /></td>
                <td className="px-3 py-2">
                  <select className={`${inputBase} w-36`} value={a.status} disabled={!canWrite}
                    onChange={(e) => setStatus.mutate({ id: a.id, status: e.target.value as ActionStatus })}>
                    {ACTION_STATUSES.map((s) => <option key={s} value={s}>{t(`action_status.${s}`)}</option>)}
                  </select>
                </td>
                {canDelete && <td className="px-2 py-2 text-right"><DeleteActionButton action={a} /></td>}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {selected && <ActionPanel action={selected} onClose={() => setSelected(null)} onSaved={() => { refresh(); setSelected(null) }} />}
    </div>
  )
}

const EMPTY = { title: '', assignee_id: null as number | null, due_date: '', priority: 'medium' as Priority, sourcing: 'internal' as Sourcing }

const SourcingSelect = ({ value, onChange }: { value: Sourcing; onChange: (v: Sourcing) => void }) => (
  <select className={inputClass} value={value} onChange={(e) => onChange(e.target.value as Sourcing)}>
    <option value="internal">{t('sourcing.internal')}</option>
    <option value="external">{t('sourcing.external')}</option>
  </select>
)

function QuickCreate({ projectId, onCreated }: { projectId: number; onCreated: () => void }) {
  const team = useTeam(projectId)
  const toast = useToast()
  const titleRef = useRef<HTMLInputElement>(null)
  const [v, setV] = useState(EMPTY)
  const create = useMutation({
    mutationFn: () => api.post(`/projects/${projectId}/actions`, { ...v, due_date: v.due_date || null }),
    onError: (e) => toast(e.message, true),
  })
  const submit = (again: boolean) => create.mutate(undefined, {
    onSuccess: () => {
      onCreated()
      toast(t('action.created'))
      setV(EMPTY)
      if (again) titleRef.current?.focus()
    },
  })
  return (
    <form className="flex flex-wrap items-end gap-2 rounded-xl bg-white p-3 shadow-sm" onSubmit={(e) => { e.preventDefault(); submit(false) }}>
      <div className="min-w-56 flex-1">
        <Field label={`${t('field.title')} *`}>
          <input ref={titleRef} className={inputClass} required maxLength={200} placeholder={t('actions.title_placeholder')} value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} />
        </Field>
      </div>
      <div className="w-48">
        <Field label={t('field.assignee')}>
          <UserSelect users={team} value={v.assignee_id} allowEmpty onChange={(id) => setV({ ...v, assignee_id: id })} />
        </Field>
      </div>
      <div className="w-40">
        <Field label={t('field.due_date')}>
          <input type="date" className={inputClass} value={v.due_date} onChange={(e) => setV({ ...v, due_date: e.target.value })} />
        </Field>
      </div>
      <div className="w-32">
        <Field label={t('field.priority')}>
          <select className={inputClass} value={v.priority} onChange={(e) => setV({ ...v, priority: e.target.value as Priority })}>
            {PRIORITIES.map((p) => <option key={p} value={p}>{t(`priority.${p}`)}</option>)}
          </select>
        </Field>
      </div>
      <div className="w-32">
        <Field label={t('field.sourcing')}>
          <SourcingSelect value={v.sourcing} onChange={(sourcing) => setV({ ...v, sourcing })} />
        </Field>
      </div>
      <Button type="submit" disabled={create.isPending}>{t('common.create')}</Button>
      <Button variant="secondary" disabled={create.isPending || !v.title.trim()} onClick={() => submit(true)}>{t('actions.create_again')}</Button>
    </form>
  )
}

function ActionPanel({ action, onClose, onSaved }: { action: Action; onClose: () => void; onSaved: () => void }) {
  const can = useCan()
  const team = useTeam(action.project_id)
  const toast = useToast()
  const readOnly = !can('action_write')
  const [v, setV] = useState({
    title: action.title, description: action.description ?? '', assignee_id: action.assignee?.id ?? null,
    due_date: action.due_date ?? '', priority: action.priority, status: action.status,
    sourcing: action.sourcing, subcontractor: action.subcontractor ?? '',
  })
  const save = useMutation({
    mutationFn: () => api.patch(`/actions/${action.id}`, { ...v, description: v.description || null, due_date: v.due_date || null }),
    onSuccess: () => { toast(t('action.saved')); onSaved() },
    onError: (e) => toast(e.message, true),
  })
  const remove = useMutation({
    mutationFn: () => api.del(`/actions/${action.id}`),
    onSuccess: () => { toast(t('action.deleted')); onSaved() },
    onError: (e) => toast(e.message, true),
  })
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/20" onMouseDown={onClose}>
      <aside className="h-full w-full max-w-md overflow-y-auto bg-white p-5 shadow-xl" onMouseDown={(e) => e.stopPropagation()}>
        <h2 className="mb-4 text-lg font-bold text-blue-900">{t('action.edit')}</h2>
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
          <fieldset disabled={readOnly} className="space-y-3">
            <Field label={`${t('field.title')} *`}>
              <input className={inputClass} required maxLength={200} value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} />
            </Field>
            <Field label={t('field.description')}>
              <textarea className={inputClass} rows={4} value={v.description} onChange={(e) => setV({ ...v, description: e.target.value })} />
            </Field>
            <Field label={t('field.assignee')}>
              <UserSelect users={team} current={action.assignee} value={v.assignee_id} allowEmpty onChange={(id) => setV({ ...v, assignee_id: id })} />
            </Field>
            <Field label={t('field.due_date')}>
              <input type="date" className={inputClass} value={v.due_date} onChange={(e) => setV({ ...v, due_date: e.target.value })} />
            </Field>
            <Field label={t('field.priority')}>
              <select className={inputClass} value={v.priority} onChange={(e) => setV({ ...v, priority: e.target.value as Priority })}>
                {PRIORITIES.map((p) => <option key={p} value={p}>{t(`priority.${p}`)}</option>)}
              </select>
            </Field>
            <Field label={t('field.status')}>
              <select className={inputClass} value={v.status} onChange={(e) => setV({ ...v, status: e.target.value as ActionStatus })}>
                {ACTION_STATUSES.map((s) => <option key={s} value={s}>{t(`action_status.${s}`)}</option>)}
              </select>
            </Field>
            <Field label={t('field.sourcing')}>
              <SourcingSelect value={v.sourcing} onChange={(sourcing) => setV({ ...v, sourcing })} />
            </Field>
            {v.sourcing === 'external' && (
              <Field label={t('field.subcontractor')}>
                <input className={inputClass} maxLength={200} value={v.subcontractor} onChange={(e) => setV({ ...v, subcontractor: e.target.value })} />
              </Field>
            )}
          </fieldset>
          <div className="flex justify-between pt-2">
            {can('action_delete')
              ? <Button variant="danger" onClick={() => window.confirm(t('action.confirm_delete')) && remove.mutate()}>{t('common.delete')}</Button>
              : <span />}
            <div className="flex gap-2">
              <Button variant="secondary" onClick={onClose}>{t('common.close')}</Button>
              {!readOnly && <Button type="submit" disabled={save.isPending}>{t('common.save')}</Button>}
            </div>
          </div>
        </form>
      </aside>
    </div>
  )
}
