import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { t } from '../i18n'
import { Button, Field, inputClass, Modal, useToast } from './ui'

export type MoveRequest = { project: { id: number; status_code: string }; status_code: string; position?: number | null }
type MoveBody = MoveRequest & { blocked_reason?: string; confirm?: boolean }

/**
 * Changement de statut d'un projet (glisser-déposer ou liste de la fiche) :
 * demande le motif vers « Bloqué » (RG03) et la confirmation vers « Terminé » si le serveur répond 409 (RG14).
 * `onReset` remet l'affichage d'origine si le déplacement est annulé ou refusé.
 */
export function useMoveProject(onReset?: () => void) {
  const qc = useQueryClient()
  const toast = useToast()
  const [pending, setPending] = useState<{ move: MoveBody; need: 'reason' | 'confirm'; count: number } | null>(null)
  const mutation = useMutation({
    mutationFn: (b: MoveBody) => api.post(`/projects/${b.project.id}/move`, {
      status_code: b.status_code, position: b.position ?? null, blocked_reason: b.blocked_reason ?? null, confirm: b.confirm ?? false,
    }),
    onSuccess: () => { setPending(null); toast(t('projects.moved')) },
    onError: (e, b) => {
      if (e instanceof ApiError && e.status === 409) return setPending({ move: b, need: 'confirm', count: Number(e.body?.count ?? 0) })
      toast(e.message, true)
      if (b.blocked_reason === undefined) onReset?.()
    },
    onSettled: () => { for (const key of ['projects', 'project', 'history']) qc.invalidateQueries({ queryKey: [key] }) },
  })

  const cancel = () => { setPending(null); onReset?.() }
  const move = (m: MoveRequest) => {
    if (m.status_code === 'blocked' && m.project.status_code !== 'blocked') setPending({ move: m, need: 'reason', count: 0 })
    else mutation.mutate(m)
  }

  let dialog = null
  if (pending?.need === 'reason') {
    dialog = <ReasonDialog busy={mutation.isPending} onCancel={cancel} onSubmit={(reason) => mutation.mutate({ ...pending.move, blocked_reason: reason })} />
  } else if (pending?.need === 'confirm') {
    dialog = (
      <Modal title={t('move.confirm_title')} onClose={cancel}>
        <p className="mb-4 text-sm">{t('move.confirm_text', { n: pending.count })}</p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={cancel}>{t('common.cancel')}</Button>
          <Button disabled={mutation.isPending} onClick={() => mutation.mutate({ ...pending.move, confirm: true })}>{t('move.confirm_ok')}</Button>
        </div>
      </Modal>
    )
  }
  return { move, dialog }
}

function ReasonDialog({ busy, onCancel, onSubmit }: { busy: boolean; onCancel: () => void; onSubmit: (reason: string) => void }) {
  const [reason, setReason] = useState('')
  return (
    <Modal title={t('move.reason_title')} onClose={onCancel}>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); onSubmit(reason) }}>
        <Field label={t('move.reason_label')}>
          <textarea className={inputClass} rows={3} required autoFocus value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={busy || !reason.trim()}>{t('common.save')}</Button>
        </div>
      </form>
    </Modal>
  )
}
