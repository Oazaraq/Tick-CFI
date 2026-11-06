import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api, qs } from '../api/client'
import { PRIORITIES } from '../api/types'
import type { ProjectCard } from '../api/types'
import KanbanBoard from '../components/KanbanBoard'
import ProjectForm from '../components/ProjectForm'
import { Button, Chip, Empty, ErrorState, inputBase, inputClass, PriorityBadge, Spinner } from '../components/ui'
import { useCan, useMe, useStatuses, useUsers } from '../hooks'
import { t } from '../i18n'
import { dueClass, fmtDate, fullName } from '../lib/format'

type Filters = {
  q: string; owner_id: number | null; priority: string
  mine: boolean; blocked: boolean; has_overdue: boolean; include_old_done: boolean; active: boolean
}

export default function ProjectsPage() {
  const can = useCan()
  const isAdmin = useMe().data?.role === 'admin' // seul l'administrateur voit au-delà de ses projets
  const users = useUsers()
  const [params] = useSearchParams() // filtres posés par les tuiles du dashboard
  const flag = (name: string) => params.get(name) === '1'
  const [f, setF] = useState<Filters>({
    q: '', owner_id: null, priority: '', mine: flag('mine'), blocked: flag('blocked'),
    has_overdue: false, include_old_done: false, active: flag('active'),
  })
  const [view, setView] = useState<'kanban' | 'list'>(params.get('view') === 'list' ? 'list' : 'kanban')
  const [creating, setCreating] = useState(false)
  const projects = useQuery({ queryKey: ['projects', f], queryFn: () => api.get<ProjectCard[]>(`/projects${qs(f)}`) })
  const toggle = (key: 'mine' | 'blocked' | 'has_overdue' | 'include_old_done' | 'active') => setF({ ...f, [key]: !f[key] })

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input className={`${inputBase} w-56`} placeholder={t('projects.search')} value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
        <select className={`${inputBase} w-48`} value={f.owner_id ?? ''} onChange={(e) => setF({ ...f, owner_id: e.target.value ? Number(e.target.value) : null })}>
          <option value="">{t('projects.all_owners')}</option>
          {users.data?.map((u) => <option key={u.id} value={u.id}>{fullName(u)}</option>)}
        </select>
        <select className={`${inputBase} w-40`} value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })}>
          <option value="">{t('projects.all_priorities')}</option>
          {PRIORITIES.map((p) => <option key={p} value={p}>{t(`priority.${p}`)}</option>)}
        </select>
        {isAdmin && <Chip active={f.mine} onClick={() => toggle('mine')}>{t('projects.mine')}</Chip>}
        <Chip active={f.active} onClick={() => toggle('active')}>{t('dashboard.active_projects')}</Chip>
        <Chip active={f.blocked} onClick={() => toggle('blocked')}>{t('projects.blocked')}</Chip>
        <Chip active={f.has_overdue} onClick={() => toggle('has_overdue')}>{t('projects.overdue')}</Chip>
        <div className="ml-auto flex gap-2">
          <Button variant="secondary" onClick={() => setView(view === 'kanban' ? 'list' : 'kanban')}>
            {t(view === 'kanban' ? 'projects.view_list' : 'projects.view_kanban')}
          </Button>
          {can('project_write') && <Button onClick={() => setCreating(true)}>{t('projects.new')}</Button>}
        </div>
      </div>
      {projects.isPending ? <Spinner />
        : projects.isError ? <ErrorState error={projects.error} />
          : view === 'kanban'
            ? <KanbanBoard projects={projects.data} showAllDone={f.include_old_done} onToggleDone={() => toggle('include_old_done')} />
            : <ProjectList projects={projects.data} />}
      {creating && <ProjectForm onClose={() => setCreating(false)} />}
    </div>
  )
}

function ProjectList({ projects }: { projects: ProjectCard[] }) {
  const navigate = useNavigate()
  const statuses = useStatuses()
  const soonDays = useMe().data?.due_soon_days ?? 7
  const label = (code: string) => statuses.data?.find((s) => s.code === code)?.label ?? code
  if (!projects.length) return <Empty text={t('projects.empty')} />
  return (
    <table className="w-full rounded-xl bg-white text-sm shadow-sm">
      <thead>
        <tr className="border-b border-gray-200 text-left text-gray-500">
          {['title', 'status', 'owner', 'priority', 'due', 'progress'].map((k) => <th key={k} className="px-3 py-2 font-medium">{t(`projects.col.${k}`)}</th>)}
        </tr>
      </thead>
      <tbody>
        {projects.map((p) => (
          <tr key={p.id} className="cursor-pointer border-b border-gray-100 hover:bg-gray-50" onClick={() => navigate(`/projects/${p.id}`)}>
            <td className="px-3 py-2 font-medium">{p.title}</td>
            <td className="px-3 py-2">{label(p.status_code)}</td>
            <td className="px-3 py-2">{fullName(p.owner)}</td>
            <td className="px-3 py-2"><PriorityBadge value={p.priority} /></td>
            <td className={`px-3 py-2 ${dueClass(p.due_date, p.status_code === 'done', soonDays)}`}>{fmtDate(p.due_date)}</td>
            <td className="px-3 py-2">
              {t('card.progress', { done: p.actions_done, total: p.actions_total })}
              {p.actions_overdue > 0 && <span className="ml-2 font-medium text-prio-critical">⚠ {t('card.overdue', { n: p.actions_overdue })}</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
