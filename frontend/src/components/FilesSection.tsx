import { useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { FilesList, ProjectFile } from '../api/types'
import { useCan } from '../hooks'
import { t } from '../i18n'
import { fmtDate, fmtDateTime, fullName } from '../lib/format'
import { Button, useToast } from './ui'

const ACCEPT = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp,.png,.jpg,.jpeg,.txt,.csv'

const size = (bytes: number) =>
  bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} Ko` : `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} Mo`

/** Fichiers « en dur » (avenant 3) : supprimés définitivement N jours après la livraison du projet. */
export default function FilesSection({ projectId }: { projectId: number }) {
  const canWrite = useCan()('file_write')
  const qc = useQueryClient()
  const toast = useToast()
  const input = useRef<HTMLInputElement>(null)
  const list = useQuery({ queryKey: ['files', projectId], queryFn: () => api.get<FilesList>(`/projects/${projectId}/files`) })
  const refresh = () => { for (const key of ['files', 'history']) qc.invalidateQueries({ queryKey: [key] }) }
  const upload = useMutation({
    mutationFn: (file: File) => api.upload<ProjectFile>(`/projects/${projectId}/files`, file),
    onSuccess: (f) => { refresh(); toast(t('files.added', { name: f.filename })) },
    onError: (e) => toast(e.message, true),
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/files/${id}`),
    onSuccess: () => { refresh(); toast(t('files.removed')) },
    onError: (e) => toast(e.message, true),
  })
  return (
    <section className="rounded-xl bg-white p-4 text-sm shadow-sm">
      <h2 className="mb-2 font-bold text-blue-900">{t('files.title')}</h2>
      {list.data?.purge_on && (
        <p className="mb-2 rounded-lg bg-amber-50 px-3 py-2 text-amber-900">{t('files.purge_notice', { date: fmtDate(list.data.purge_on) })}</p>
      )}
      {list.data?.files.length ? (
        <ul className="mb-3 divide-y divide-gray-100">
          {list.data.files.map((f) => (
            <li key={f.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5">
              <a href={`/api/files/${f.id}/download`} className="font-medium text-blue-700 hover:underline">{f.filename}</a>
              <span className="text-xs text-gray-500">
                {size(f.size)} · {f.uploader ? fullName(f.uploader) : '—'} · {fmtDateTime(f.created_at)}
              </span>
              {canWrite && (
                <button type="button" className="text-xs text-gray-400 hover:text-prio-critical" aria-label={t('files.delete')} title={t('files.delete')}
                  onClick={() => window.confirm(t('files.confirm_delete', { name: f.filename })) && remove.mutate(f.id)}>✕</button>
              )}
            </li>
          ))}
        </ul>
      ) : <p className="mb-3 text-gray-400">{t('files.empty')}</p>}
      {canWrite && (
        <div className="flex flex-wrap items-center gap-3">
          <input ref={input} type="file" accept={ACCEPT} className="hidden"
            onChange={(e) => { const file = e.target.files?.[0]; e.target.value = ''; if (file) upload.mutate(file) }} />
          <Button variant="secondary" disabled={upload.isPending} onClick={() => input.current?.click()}>
            {upload.isPending ? t('files.uploading') : t('files.add')}
          </Button>
          <span className="text-xs text-gray-500">{t('files.hint')}</span>
        </div>
      )}
    </section>
  )
}
