import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { PRIORITIES } from '../api/types'
import type { Priority, Project } from '../api/types'
import { useMe, useStatuses, useUsers } from '../hooks'
import { t } from '../i18n'
import { fullName } from '../lib/format'
import { Button, Field, inputClass, Modal, UserSelect, useToast } from './ui'

/** Création ou modification d'un projet (le statut d'un projet existant change via le Kanban ou la fiche). */
export default function ProjectForm({ project, onClose }: { project?: Project; onClose: () => void }) {
  const qc = useQueryClient()
  const toast = useToast()
  const users = useUsers()
  const statuses = useStatuses()
  const me = useMe().data
  const [v, setV] = useState({
    title: project?.title ?? '',
    description: project?.description ?? '',
    owner_id: project?.owner.id ?? me?.id ?? null,
    member_ids: project?.members.map((m) => m.id) ?? [],
    priority: project?.priority ?? ('medium' as Priority),
    start_date: project?.start_date ?? '',
    due_date: project?.due_date ?? '',
    status_code: 'presale',
    blocked_reason: '',
  })
  const set = <K extends keyof typeof v>(key: K, value: (typeof v)[K]) => setV({ ...v, [key]: value })
  const toggleMember = (id: number) =>
    set('member_ids', v.member_ids.includes(id) ? v.member_ids.filter((x) => x !== id) : [...v.member_ids, id])

  const save = useMutation({
    mutationFn: () => {
      const body = {
        title: v.title, description: v.description || null, owner_id: v.owner_id, member_ids: v.member_ids,
        priority: v.priority, start_date: v.start_date || null, due_date: v.due_date || null,
      }
      return project
        ? api.patch<Project>(`/projects/${project.id}`, body)
        : api.post<Project>('/projects', { ...body, status_code: v.status_code, blocked_reason: v.blocked_reason || null })
    },
    onSuccess: () => {
      for (const key of ['projects', 'project', 'history']) qc.invalidateQueries({ queryKey: [key] })
      toast(t(project ? 'project.saved' : 'project.created'))
      onClose()
    },
  })

  return (
    <Modal title={t(project ? 'project.edit' : 'project.new')} onClose={onClose} wide>
      <form className="grid grid-cols-2 gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
        <div className="col-span-2">
          <Field label={`${t('field.title')} *`}>
            <input className={inputClass} required autoFocus maxLength={200} value={v.title} onChange={(e) => set('title', e.target.value)} />
          </Field>
        </div>
        <div className="col-span-2">
          <Field label={t('field.description')}>
            <textarea className={inputClass} rows={3} value={v.description} onChange={(e) => set('description', e.target.value)} />
          </Field>
        </div>
        <Field label={`${t('field.owner')} *`}>
          <UserSelect users={users.data ?? []} current={project?.owner} value={v.owner_id} onChange={(id) => set('owner_id', id)} />
        </Field>
        <Field label={`${t('field.priority')} *`}>
          <select className={inputClass} value={v.priority} onChange={(e) => set('priority', e.target.value as Priority)}>
            {PRIORITIES.map((p) => <option key={p} value={p}>{t(`priority.${p}`)}</option>)}
          </select>
        </Field>
        <Field label={t('field.start_date')}>
          <input type="date" className={inputClass} value={v.start_date} onChange={(e) => set('start_date', e.target.value)} />
        </Field>
        <Field label={t('project.due_date')}>
          <input type="date" className={inputClass} min={v.start_date || undefined} value={v.due_date} onChange={(e) => set('due_date', e.target.value)} />
        </Field>
        {!project && (
          <Field label={`${t('field.status')} *`}>
            <select className={inputClass} value={v.status_code} onChange={(e) => set('status_code', e.target.value)}>
              {statuses.data?.map((s) => <option key={s.code} value={s.code}>{s.label}</option>)}
            </select>
          </Field>
        )}
        {!project && v.status_code === 'blocked' && (
          <Field label={`${t('project.blocked_reason')} *`}>
            <input className={inputClass} required value={v.blocked_reason} onChange={(e) => set('blocked_reason', e.target.value)} />
          </Field>
        )}
        <div className="col-span-2 text-sm">
          <span className="mb-1 block font-medium text-gray-700">{t('field.members')}</span>
          <span className="mb-1 block text-xs text-gray-500">{t('project.team_hint')}</span>
          <div className="flex max-h-32 flex-wrap gap-x-4 gap-y-1 overflow-y-auto rounded-lg border border-gray-300 p-2">
            {(users.data ?? []).map((u) => (
              <label key={u.id} className="flex items-center gap-1">
                <input type="checkbox" checked={v.member_ids.includes(u.id)} onChange={() => toggleMember(u.id)} />
                {fullName(u)}
              </label>
            ))}
          </div>
        </div>
        {save.error && <p className="col-span-2 text-sm text-prio-critical">{save.error.message}</p>}
        <div className="col-span-2 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={save.isPending}>{t('common.save')}</Button>
        </div>
      </form>
    </Modal>
  )
}
