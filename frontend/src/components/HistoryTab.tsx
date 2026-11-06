import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, qs } from '../api/client'
import type { HistoryEvent } from '../api/types'
import { useUsers } from '../hooks'
import { t } from '../i18n'
import { fmtDateTime, fullName } from '../lib/format'
import { Empty, ErrorState, inputBase, inputClass, Spinner } from './ui'

const TYPES = [
  'project_created', 'project_updated', 'project_status_changed', 'project_deleted',
  'action_created', 'action_updated', 'action_status_changed', 'action_deleted',
  'planning_item_created', 'planning_item_updated', 'planning_item_deleted',
  'risk_created', 'risk_updated', 'document_added', 'document_removed',
  'comment_added', 'comment_edited', 'comment_deleted', 'meeting_imported', 'actions_created_by_ai',
  'action_overdue', 'meeting_deleted', 'file_added', 'file_deleted', 'files_purged',
]

/** Une ligne lisible : les valeurs sont figées par le serveur, la formulation vient de fr.json. */
function describe(h: HistoryEvent): string {
  const d = h.detail
  const text = t(`history.${h.event_type}`, {
    label: d.label ?? '', count: d.count ?? '', field: d.field ? t(`field.${d.field}`) : '', old: d.old || '—', new: d.new || '—',
  })
  return d.reason ? `${text} (${t('history.reason')} : ${d.reason})` : text
}

/** Journal en lecture seule (RG08) : aucun bouton de modification ni de suppression. */
export default function HistoryTab({ projectId }: { projectId: number }) {
  const users = useUsers()
  const [f, setF] = useState({ event_type: '', author_id: '', from: '', to: '' })
  const history = useQuery({
    queryKey: ['history', projectId, f],
    queryFn: () => api.get<HistoryEvent[]>(`/projects/${projectId}/history${qs(f)}`),
  })
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <select className={`${inputBase} w-56`} value={f.event_type} onChange={(e) => setF({ ...f, event_type: e.target.value })}>
          <option value="">{t('history.all_types')}</option>
          {TYPES.map((x) => <option key={x} value={x}>{t(`event.${x}`)}</option>)}
        </select>
        <select className={`${inputBase} w-48`} value={f.author_id} onChange={(e) => setF({ ...f, author_id: e.target.value })}>
          <option value="">{t('history.all_authors')}</option>
          {users.data?.map((u) => <option key={u.id} value={u.id}>{fullName(u)}</option>)}
        </select>
        <input type="date" className={`${inputBase} w-40`} title={t('history.from')} value={f.from} onChange={(e) => setF({ ...f, from: e.target.value })} />
        <input type="date" className={`${inputBase} w-40`} title={t('history.to')} value={f.to} onChange={(e) => setF({ ...f, to: e.target.value })} />
      </div>
      {history.isPending ? <Spinner /> : history.isError ? <ErrorState error={history.error} /> : !history.data.length ? <Empty text={t('history.empty')} /> : (
        <ol className="space-y-2">
          {history.data.map((h) => (
            <li key={h.id} className="rounded-xl bg-white p-3 text-sm shadow-sm">
              <p className="text-xs text-gray-500">{fmtDateTime(h.created_at)}</p>
              <p>{describe(h)}</p>
              <p className="text-xs text-gray-500">{t('history.by', { name: h.author ? fullName(h.author) : t('history.system') })}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
