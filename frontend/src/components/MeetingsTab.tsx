import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { PRIORITIES } from '../api/types'
import type { Meeting, MeetingItem, MeetingStatus, MeetingSummary, Priority, Project, Sourcing } from '../api/types'
import { useCan, useTeam } from '../hooks'
import { t } from '../i18n'
import { fmtDate, fullName, todayParis } from '../lib/format'
import { Button, Empty, ErrorState, Field, inputBase, inputClass, Modal, Spinner, UserSelect, useToast } from './ui'

const STATUS_STYLE: Record<MeetingStatus, string> = {
  processing: 'bg-blue-100 text-blue-800', to_validate: 'bg-amber-100 text-amber-800',
  validated: 'bg-green-100 text-green-800', failed: 'bg-red-100 text-red-800', rejected: 'bg-gray-200 text-gray-700',
}
const StatusBadge = ({ status }: { status: MeetingStatus }) => (
  <span className={`rounded-lg px-1.5 py-0.5 text-xs font-medium ${STATUS_STYLE[status]}`}>{t(`meeting_status.${status}`)}</span>
)
const useProvider = () =>
  useQuery({ queryKey: ['ai-provider'], queryFn: () => api.get<{ provider: string }>('/ai/provider'), staleTime: Infinity })

/** Onglet Réunions : comptes-rendus, import d'une transcription et validation humaine des actions (DFB §4.6). */
export default function MeetingsTab({ project }: { project: Project }) {
  const canManage = useCan()('meeting_manage')
  const [openId, setOpenId] = useState<number | null>(null)
  const [importing, setImporting] = useState(false)
  const list = useQuery({ queryKey: ['meetings', project.id], queryFn: () => api.get<MeetingItem[]>(`/projects/${project.id}/meetings`) })
  if (openId) return <MeetingView id={openId} onBack={() => setOpenId(null)} />
  return (
    <div className="space-y-4">
      {canManage && <Button onClick={() => setImporting(true)}>{t('meetings.new')}</Button>}
      {list.isPending ? <Spinner /> : list.isError ? <ErrorState error={list.error} /> : !list.data.length ? <Empty text={t('meetings.empty')} /> : (
        <table className="w-full rounded-xl bg-white text-sm shadow-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              {['title', 'date', 'status', 'actions'].map((k) => <th key={k} className="px-3 py-2 font-medium">{t(`meetings.col.${k}`)}</th>)}
            </tr>
          </thead>
          <tbody>
            {list.data.map((m) => (
              <tr key={m.id} className="cursor-pointer border-b border-gray-100 hover:bg-gray-50" onClick={() => setOpenId(m.id)}>
                <td className="px-3 py-2 font-medium">{m.title}</td>
                <td className="px-3 py-2">{fmtDate(m.meeting_date)}</td>
                <td className="px-3 py-2"><StatusBadge status={m.status} /></td>
                <td className="px-3 py-2">{m.status === 'validated' ? m.actions_count : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {importing && <ImportForm project={project} onClose={() => setImporting(false)}
        onCreated={(id) => { setImporting(false); setOpenId(id) }} />}
    </div>
  )
}

function ImportForm({ project, onClose, onCreated }: { project: Project; onClose: () => void; onCreated: (id: number) => void }) {
  const qc = useQueryClient()
  const toast = useToast()
  const provider = useProvider()
  const fileInput = useRef<HTMLInputElement>(null)
  const team = [project.owner, ...project.members.filter((m) => m.id !== project.owner.id)].filter((u) => u.is_active)
  const [v, setV] = useState({
    title: '', meeting_date: todayParis(), participants: team.map(fullName).join(', '), transcript: '', filename: null as string | null,
  })
  const loadFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => setV((s) => ({ ...s, transcript: String(reader.result), filename: file.name, title: s.title || file.name.replace(/\.[^.]+$/, '') }))
    reader.readAsText(file)
  }
  const demo = useMutation({
    mutationFn: () => api.get<{ title: string; filename: string; content: string }>('/ai/demo-transcript'),
    onSuccess: (d) => setV((s) => ({ ...s, title: d.title, transcript: d.content, filename: d.filename })),
  })
  const send = useMutation({
    mutationFn: () => api.post<Meeting>(`/projects/${project.id}/meetings`, {
      ...v, participants: v.participants.split(',').map((p) => p.trim()).filter(Boolean),
    }),
    onSuccess: (m) => {
      qc.invalidateQueries({ queryKey: ['meetings', project.id] })
      toast(t('meetings.created'))
      onCreated(m.id)
    },
  })
  return (
    <Modal title={t('meetings.new')} onClose={onClose} wide>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); send.mutate() }}>
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2"><Field label={t('meetings.field.title')}>
            <input className={inputClass} required maxLength={200} value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} />
          </Field></div>
          <Field label={t('meetings.field.date')}>
            <input type="date" className={inputClass} required value={v.meeting_date} onChange={(e) => setV({ ...v, meeting_date: e.target.value })} />
          </Field>
        </div>
        <Field label={t('meetings.field.participants')}>
          <input className={inputClass} value={v.participants} onChange={(e) => setV({ ...v, participants: e.target.value })} />
        </Field>
        <Field label={t('meetings.field.transcript')}>
          <textarea className={`${inputClass} font-mono text-xs`} rows={10} required value={v.transcript}
            onChange={(e) => setV({ ...v, transcript: e.target.value, filename: null })} />
        </Field>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <input ref={fileInput} type="file" accept=".txt,.vtt,text/plain,text/vtt" className="hidden"
            onChange={(e) => e.target.files?.[0] && loadFile(e.target.files[0])} />
          <Button variant="secondary" onClick={() => fileInput.current?.click()}>{t('meetings.file')}</Button>
          {v.filename && <span className="text-gray-600">{v.filename}</span>}
          <button type="button" className="text-blue-700 hover:underline" onClick={() => demo.mutate()}>{t('meetings.load_demo')}</button>
        </div>
        <p className="rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-900">
          {t('meetings.provider_notice', { provider: provider.data ? t(`ai.provider.${provider.data.provider}`) : '…' })}
        </p>
        {send.isError && <ErrorState error={send.error} />}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={send.isPending}>{t('meetings.analyze')}</Button>
        </div>
      </form>
    </Modal>
  )
}

function MeetingView({ id, onBack }: { id: number; onBack: () => void }) {
  const canManage = useCan()('meeting_manage')
  const qc = useQueryClient()
  const meeting = useQuery({
    queryKey: ['meeting', id],
    queryFn: () => api.get<Meeting>(`/meetings/${id}`),
    refetchInterval: (q) => (q.state.data?.status === 'processing' ? 2000 : false),  // analyse en tâche de fond
  })
  const remove = useMutation({
    mutationFn: () => api.del(`/meetings/${id}`),
    onSuccess: () => { qc.invalidateQueries(); onBack() },
  })
  const retry = useMutation({
    mutationFn: () => api.post(`/meetings/${id}/retry`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['meeting', id] }),
  })
  if (meeting.isPending) return <Spinner />
  if (meeting.isError) return <ErrorState error={meeting.error} />
  const m = meeting.data
  return (
    <div className="space-y-4">
      <button type="button" className="text-sm text-blue-700 hover:underline" onClick={onBack}>{t('meetings.back')}</button>
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-bold text-blue-900">{m.title}</h2>
        <span className="text-sm text-gray-600">{fmtDate(m.meeting_date)}</span>
        <StatusBadge status={m.status} />
        {m.provider && <span className="text-xs text-gray-500">{t('meetings.by_provider', { provider: t(`ai.provider.${m.provider}`) })}</span>}
      </div>
      {m.status === 'processing' && <div className="rounded-xl bg-white p-6 text-center text-sm text-gray-600 shadow-sm">{t('meetings.processing')}</div>}
      {canManage && (m.status === 'rejected' || m.status === 'failed') && (
        <Button variant="secondary" disabled={remove.isPending}
          onClick={() => window.confirm(t('meetings.confirm_delete')) && remove.mutate()}>{t('meetings.delete')}</Button>
      )}
      {m.status === 'failed' && (
        <div className="space-y-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <p><strong>{t('meetings.failed')}</strong> : {m.error_message}</p>
          {canManage && <Button onClick={() => retry.mutate()} disabled={retry.isPending}>{t('meetings.retry')}</Button>}
        </div>
      )}
      {m.status === 'to_validate' && (canManage
        ? <ValidationForm meeting={m} />
        : <><p className="text-sm text-gray-600">{t('meetings.waiting_validation')}</p>{m.summary && <SummaryView summary={m.summary} />}</>)}
      {m.status === 'validated' && (
        <>
          <p className="text-sm text-gray-700">{t('meetings.actions_created', { count: m.actions_count })}</p>
          {m.summary && <SummaryView summary={m.summary} />}
        </>
      )}
      <details className="rounded-xl bg-white p-3 text-sm shadow-sm">
        <summary className="cursor-pointer font-medium">{t('meetings.transcript')}</summary>
        <pre className="mt-2 whitespace-pre-wrap font-sans text-gray-700">{m.transcript}</pre>
      </details>
    </div>
  )
}

const SECTIONS = ['topics', 'decisions', 'open_points'] as const

function SummaryView({ summary }: { summary: MeetingSummary }) {
  return (
    <div className="space-y-3 rounded-xl bg-white p-4 text-sm shadow-sm">
      <h3 className="font-bold text-blue-900">{t('meetings.summary')}</h3>
      {summary.context && <p className="whitespace-pre-wrap">{summary.context}</p>}
      {SECTIONS.filter((k) => summary[k].length).map((k) => (
        <div key={k}>
          <h4 className="font-medium text-gray-700">{t(`meetings.${k}`)}</h4>
          <ul className="list-disc pl-5">{summary[k].map((item, i) => <li key={i}>{item}</li>)}</ul>
        </div>
      ))}
    </div>
  )
}

interface Row {
  key: number; checked: boolean; title: string; assignee_id: number | null; assignee_name: string | null
  due_date: string; priority: Priority; sourcing: Sourcing; source_quote: string
}

function ValidationForm({ meeting }: { meeting: Meeting }) {
  const qc = useQueryClient()
  const toast = useToast()
  const team = useTeam(meeting.project_id)
  const s = meeting.summary ?? { context: '', topics: [], decisions: [], open_points: [] }
  const [summary, setSummary] = useState({ context: s.context, topics: s.topics.join('\n'), decisions: s.decisions.join('\n'), open_points: s.open_points.join('\n') })
  const [rows, setRows] = useState<Row[]>((meeting.candidates ?? []).map((c, i) => ({
    key: i, checked: true, title: c.title, assignee_id: c.assignee_id, assignee_name: c.assignee_name,
    due_date: c.due_date ?? '', priority: c.priority, sourcing: 'internal', source_quote: c.source_quote,
  })))
  const patch = (key: number, change: Partial<Row>) => setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...change } : r)))
  const selected = rows.filter((r) => r.checked)
  const done = (message: string) => {
    qc.invalidateQueries()  // réunion, liste, actions, compteurs du projet, historique
    toast(message)
  }
  const validate = useMutation({
    mutationFn: () => api.post(`/meetings/${meeting.id}/validate`, {
      summary: {
        context: summary.context,
        ...Object.fromEntries(SECTIONS.map((k) => [k, summary[k].split('\n').map((l) => l.trim()).filter(Boolean)])),
      },
      actions: selected.map((r) => ({
        title: r.title, assignee_id: r.assignee_id, due_date: r.due_date || null, priority: r.priority, sourcing: r.sourcing,
        description: r.source_quote ? t('meetings.source', { quote: r.source_quote }) : null,
      })),
    }),
    onSuccess: () => done(t('meetings.validated', { count: selected.length })),
  })
  const reject = useMutation({ mutationFn: () => api.post(`/meetings/${meeting.id}/reject`), onSuccess: () => done(t('meetings.rejected')) })
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); validate.mutate() }}>
      <div className="space-y-3 rounded-xl bg-white p-4 shadow-sm">
        <h3 className="font-bold text-blue-900">{t('meetings.summary')}</h3>
        <Field label={t('meetings.context')}>
          <textarea className={inputClass} rows={3} value={summary.context} onChange={(e) => setSummary({ ...summary, context: e.target.value })} />
        </Field>
        <div className="grid gap-3 md:grid-cols-3">
          {SECTIONS.map((k) => (
            <Field key={k} label={`${t(`meetings.${k}`)} (${t('meetings.one_per_line')})`}>
              <textarea className={inputClass} rows={4} value={summary[k]} onChange={(e) => setSummary({ ...summary, [k]: e.target.value })} />
            </Field>
          ))}
        </div>
      </div>
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <h3 className="font-bold text-blue-900">{t('meetings.candidates')}</h3>
        <p className="mb-2 text-xs text-gray-500">{t('meetings.candidates_hint')}</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500">
                <th className="w-8 px-2 py-2" />
                {['title', 'assignee', 'due_date', 'priority', 'sourcing'].map((k) => <th key={k} className="px-2 py-2 font-medium">{t(`field.${k}`)}</th>)}
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className={`border-b border-gray-100 align-top ${!r.assignee_id || !r.due_date ? 'bg-amber-50' : ''} ${r.checked ? '' : 'opacity-50'}`}>
                  <td className="px-2 py-2"><input type="checkbox" checked={r.checked} aria-label={r.title} onChange={(e) => patch(r.key, { checked: e.target.checked })} /></td>
                  <td className="px-2 py-2">
                    <input className={inputClass} required={r.checked} maxLength={200} value={r.title} onChange={(e) => patch(r.key, { title: e.target.value })} />
                    {r.source_quote && <p className="mt-1 truncate text-xs text-gray-500" title={r.source_quote}>« {r.source_quote} »</p>}
                  </td>
                  <td className="px-2 py-2">
                    <UserSelect users={team} value={r.assignee_id} allowEmpty className={`${inputBase} w-44`}
                      onChange={(id) => patch(r.key, { assignee_id: id })} />
                    {!r.assignee_id && r.assignee_name && <p className="mt-1 text-xs text-amber-800">{t('meetings.unidentified', { name: r.assignee_name })}</p>}
                  </td>
                  <td className="px-2 py-2">
                    <input type="date" className={`${inputBase} w-36`} value={r.due_date} onChange={(e) => patch(r.key, { due_date: e.target.value })} />
                  </td>
                  <td className="px-2 py-2">
                    <select className={inputBase} value={r.priority} onChange={(e) => patch(r.key, { priority: e.target.value as Priority })}>
                      {PRIORITIES.map((p) => <option key={p} value={p}>{t(`priority.${p}`)}</option>)}
                    </select>
                  </td>
                  <td className="px-2 py-2">
                    <select className={inputBase} value={r.sourcing} onChange={(e) => patch(r.key, { sourcing: e.target.value as Sourcing })}>
                      <option value="internal">{t('sourcing.internal')}</option>
                      <option value="external">{t('sourcing.external')}</option>
                    </select>
                  </td>
                  <td className="px-2 py-2">
                    <button type="button" className="text-gray-500 hover:text-prio-critical" title={t('meetings.remove_row')} aria-label={t('meetings.remove_row')}
                      onClick={() => setRows((rs) => rs.filter((x) => x.key !== r.key))}>×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button type="button" className="mt-2 text-sm text-blue-700 hover:underline" onClick={() => setRows((rs) => [...rs, {
          key: Math.max(0, ...rs.map((x) => x.key)) + 1, checked: true, title: '', assignee_id: null, assignee_name: null,
          due_date: '', priority: 'medium', sourcing: 'internal', source_quote: '',
        }])}>{t('meetings.add_row')}</button>
      </div>
      {(validate.isError || reject.isError) && <ErrorState error={validate.error ?? reject.error} />}
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="secondary" disabled={reject.isPending} onClick={() => window.confirm(t('meetings.confirm_reject')) && reject.mutate()}>{t('meetings.reject_all')}</Button>
        <Button type="submit" disabled={validate.isPending}>{t('meetings.create_selected', { count: selected.length })}</Button>
      </div>
    </form>
  )
}
