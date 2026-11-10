import { Fragment, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { DocLink, Project } from '../api/types'
import ActionsTab from '../components/ActionsTab'
import CommentsTab from '../components/CommentsTab'
import FilesSection from '../components/FilesSection'
import HistoryTab from '../components/HistoryTab'
import MeetingsTab from '../components/MeetingsTab'
import PlanningTab from '../components/PlanningTab'
import ProjectForm from '../components/ProjectForm'
import { useMoveProject } from '../components/ProjectMove'
import RisksTab from '../components/RisksTab'
import { Button, ErrorState, inputBase, inputClass, PriorityBadge, Spinner, useToast } from '../components/ui'
import { useCan, useStatuses } from '../hooks'
import { t } from '../i18n'
import { daysSince, fmtDate, fmtDays, fullName } from '../lib/format'

const TABS = ['general', 'actions', 'planning', 'risks', 'meetings', 'comments', 'history'] as const
type Tab = (typeof TABS)[number]

export default function ProjectPage() {
  const id = Number(useParams().id)
  const [params] = useSearchParams()
  const can = useCan()
  const qc = useQueryClient()
  const toast = useToast()
  const navigate = useNavigate()
  const statuses = useStatuses()
  const project = useQuery({ queryKey: ['project', id], queryFn: () => api.get<Project>(`/projects/${id}`) })
  const initial = params.get('tab') as Tab | null
  const [tab, setTab] = useState<Tab>(initial && TABS.includes(initial) ? initial : 'general')
  const [editing, setEditing] = useState(false)
  const { move, dialog } = useMoveProject()
  const remove = useMutation({
    mutationFn: () => api.del(`/projects/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['projects'] }); toast(t('project.deleted')); navigate('/projects') },
    onError: (e) => toast(e.message, true),
  })

  if (project.isPending) return <Spinner />
  if (project.isError) return <ErrorState error={project.error} />
  const p = project.data
  return (
    <div className="mx-auto max-w-6xl">
      <Link to="/projects" className="text-sm text-blue-700 hover:underline">← {t('nav.projects')}</Link>
      <header className="my-3 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-extrabold text-blue-900">{p.title}</h1>
        <select className={`${inputBase} w-auto`} value={p.status_code} disabled={!can('project_write')}
          onChange={(e) => move({ project: p, status_code: e.target.value })}>
          {statuses.data?.map((s) => <option key={s.code} value={s.code}>{s.label}</option>)}
        </select>
        <span className="text-sm text-gray-600">{fullName(p.owner)}</span>
        <PriorityBadge value={p.priority} />
        <div className="ml-auto flex gap-2">
          <Link to={`/projects/${p.id}/checklist`}
            className="rounded-lg border border-blue-200 bg-white px-3 py-1.5 text-sm font-medium text-blue-800 hover:bg-blue-50">☑ {t('checklist.button')}</Link>
          {can('project_write') && <Button variant="secondary" onClick={() => setEditing(true)}>{t('common.edit')}</Button>}
          {can('project_delete') && (
            <Button variant="danger" onClick={() => window.confirm(t('project.confirm_delete')) && remove.mutate()}>{t('common.delete')}</Button>
          )}
        </div>
      </header>
      <nav className="mb-4 flex gap-1 border-b border-gray-200">
        {TABS.map((k) => (
          <button key={k} type="button" onClick={() => setTab(k)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm whitespace-nowrap ${tab === k ? 'border-blue-600 font-medium text-blue-700' : 'border-transparent text-gray-600'}`}>
            {t(`tab.${k}`)}{k === 'actions' ? ` (${p.actions_open})` : ''}
          </button>
        ))}
      </nav>
      {tab === 'general' && <GeneralTab p={p} />}
      {tab === 'actions' && <ActionsTab project={p} />}
      {tab === 'planning' && <PlanningTab project={p} />}
      {tab === 'risks' && <RisksTab project={p} />}
      {tab === 'meetings' && <MeetingsTab project={p} />}
      {tab === 'comments' && <CommentsTab project={p} />}
      {tab === 'history' && <HistoryTab projectId={p.id} />}
      {editing && <ProjectForm project={p} onClose={() => setEditing(false)} />}
      {dialog}
    </div>
  )
}

function GeneralTab({ p }: { p: Project }) {
  const rows: [string, ReactNode][] = [
    ['field.description', p.description ? <p className="whitespace-pre-wrap">{p.description}</p> : '—'],
    ['field.owner', fullName(p.owner)],
    ['field.members', p.members.map(fullName).join(', ') || '—'],
    ['field.start_date', fmtDate(p.start_date) || '—'],
    ['project.due_date', fmtDate(p.due_date) || '—'],
    ['project.end_date', fmtDate(p.end_date) || '—'],
    ['field.priority', <PriorityBadge value={p.priority} />],
    ['project.effort', p.days_sold || p.days_consumed
      ? t('project.effort_value', { consumed: fmtDays(p.days_consumed), sold: fmtDays(p.days_sold) }) : '—'],
    ['field.status', p.status_label],
  ]
  return (
    <div className="space-y-4">
      {p.status_code === 'blocked' && p.blocked_since && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm">
          ⚠ {t('project.blocked_since', { n: daysSince(p.blocked_since) })} — {p.blocked_reason}
        </div>
      )}
      <dl className="grid grid-cols-[12rem_1fr] gap-x-4 gap-y-2 rounded-xl bg-white p-4 text-sm shadow-sm">
        {rows.map(([key, value]) => (
          <Fragment key={key}>
            <dt className="text-gray-500">{t(key)}</dt>
            <dd>{value}</dd>
          </Fragment>
        ))}
      </dl>
      <Links projectId={p.id} />
      <FilesSection projectId={p.id} />
    </div>
  )
}

/** Documents = liens (Q16) ; le serveur n'accepte que http(s). */
function Links({ projectId }: { projectId: number }) {
  const canWrite = useCan()('link_write')
  const qc = useQueryClient()
  const toast = useToast()
  const [v, setV] = useState({ label: '', url: '' })
  const links = useQuery({ queryKey: ['links', projectId], queryFn: () => api.get<DocLink[]>(`/projects/${projectId}/links`) })
  const refresh = () => { for (const key of ['links', 'history']) qc.invalidateQueries({ queryKey: [key] }) }
  const add = useMutation({
    mutationFn: () => api.post(`/projects/${projectId}/links`, v),
    onSuccess: () => { refresh(); setV({ label: '', url: '' }); toast(t('links.added')) },
    onError: (e) => toast(e.message, true),
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/links/${id}`),
    onSuccess: () => { refresh(); toast(t('links.removed')) },
    onError: (e) => toast(e.message, true),
  })
  return (
    <section className="rounded-xl bg-white p-4 text-sm shadow-sm">
      <h2 className="mb-2 font-bold text-blue-900">{t('links.title')}</h2>
      {links.data?.length ? (
        <ul className="mb-3 space-y-1">
          {links.data.map((l) => (
            <li key={l.id} className="flex items-center gap-2">
              <a href={/^https?:\/\//.test(l.url) ? l.url : undefined} target="_blank" rel="noopener noreferrer" className="text-blue-700 hover:underline">{l.label}</a>
              {canWrite && <button type="button" className="text-xs text-gray-400 hover:text-prio-critical" onClick={() => window.confirm(t('links.confirm_delete')) && remove.mutate(l.id)}>✕</button>}
            </li>
          ))}
        </ul>
      ) : <p className="mb-3 text-gray-400">{t('links.empty')}</p>}
      {canWrite && (
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); add.mutate() }}>
          <input className={`${inputBase} w-48`} required maxLength={200} placeholder={t('links.label')} value={v.label} onChange={(e) => setV({ ...v, label: e.target.value })} />
          <input className={`${inputBase} min-w-64 flex-1`} required type="url" maxLength={1000} placeholder={t('links.url')} value={v.url} onChange={(e) => setV({ ...v, url: e.target.value })} />
          <Button type="submit" disabled={add.isPending}>{t('links.add')}</Button>
        </form>
      )}
    </section>
  )
}
