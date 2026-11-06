import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Comment, Project } from '../api/types'
import { useCan, useMe } from '../hooks'
import { t } from '../i18n'
import { fmtDateTime, fullName } from '../lib/format'
import { Button, Empty, ErrorState, inputClass, Spinner, useToast } from './ui'

/** Fil chronologique ; chacun ne modifie ou ne supprime que ses propres commentaires (contrôlé par le serveur). */
export default function CommentsTab({ project }: { project: Project }) {
  const me = useMe().data
  const canWrite = useCan()('comment_write')
  const qc = useQueryClient()
  const toast = useToast()
  const [body, setBody] = useState('')
  const [editing, setEditing] = useState<{ id: number; body: string } | null>(null)
  const comments = useQuery({ queryKey: ['comments', project.id], queryFn: () => api.get<Comment[]>(`/projects/${project.id}/comments`) })
  const refresh = () => { for (const key of ['comments', 'history']) qc.invalidateQueries({ queryKey: [key] }) }
  const onError = (e: Error) => toast(e.message, true)
  const add = useMutation({
    mutationFn: () => api.post(`/projects/${project.id}/comments`, { body }),
    onSuccess: () => { refresh(); setBody(''); toast(t('comments.added')) }, onError,
  })
  const edit = useMutation({
    mutationFn: (c: { id: number; body: string }) => api.patch(`/comments/${c.id}`, { body: c.body }),
    onSuccess: () => { refresh(); setEditing(null); toast(t('comments.saved')) }, onError,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/comments/${id}`),
    onSuccess: () => { refresh(); toast(t('comments.deleted')) }, onError,
  })

  return (
    <div className="space-y-3">
      {comments.isPending ? <Spinner /> : comments.isError ? <ErrorState error={comments.error} /> : !comments.data.length ? <Empty text={t('comments.empty')} /> : (
        <ol className="space-y-2">
          {comments.data.map((c) => (
            <li key={c.id} className="rounded-xl bg-white p-3 text-sm shadow-sm">
              <p className="mb-1 text-xs text-gray-500">
                <span className="font-medium text-gray-700">{fullName(c.author)}</span> · {fmtDateTime(c.created_at)}
                {c.edited_at && <span className="italic"> · {t('comments.edited')}</span>}
              </p>
              {editing?.id === c.id ? (
                <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); edit.mutate(editing) }}>
                  <textarea className={inputClass} rows={3} required value={editing.body} onChange={(e) => setEditing({ id: c.id, body: e.target.value })} />
                  <div className="flex gap-2">
                    <Button type="submit" disabled={edit.isPending}>{t('common.save')}</Button>
                    <Button variant="secondary" onClick={() => setEditing(null)}>{t('common.cancel')}</Button>
                  </div>
                </form>
              ) : <p className="whitespace-pre-wrap">{c.body}</p>}
              {canWrite && me?.id === c.author.id && editing?.id !== c.id && (
                <div className="mt-1 flex gap-3 text-xs">
                  <button type="button" className="text-blue-700 hover:underline" onClick={() => setEditing({ id: c.id, body: c.body })}>{t('common.edit')}</button>
                  <button type="button" className="text-gray-500 hover:text-prio-critical" onClick={() => window.confirm(t('comments.confirm_delete')) && remove.mutate(c.id)}>{t('common.delete')}</button>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
      {canWrite && (
        <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); add.mutate() }}>
          <textarea className={inputClass} rows={3} required maxLength={5000} placeholder={t('comments.placeholder')} value={body} onChange={(e) => setBody(e.target.value)} />
          <Button type="submit" disabled={add.isPending || !body.trim()}>{t('comments.add')}</Button>
        </form>
      )}
    </div>
  )
}
