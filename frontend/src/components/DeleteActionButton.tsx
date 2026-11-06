import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Action } from '../api/types'
import { useCan } from '../hooks'
import { t } from '../i18n'
import { useToast } from './ui'

/** Suppression d'une action depuis une liste (Administrateur et Chef de projet), après confirmation.
 *  Suppression logique côté serveur : l'action disparaît des listes, l'historique la conserve. */
export default function DeleteActionButton({ action }: { action: Pick<Action, 'id' | 'title'> }) {
  const can = useCan()
  const qc = useQueryClient()
  const toast = useToast()
  const remove = useMutation({
    mutationFn: () => api.del(`/actions/${action.id}`),
    onSuccess: () => {
      for (const key of ['actions', 'dashboard', 'projects', 'project', 'history']) qc.invalidateQueries({ queryKey: [key] })
      toast(t('action.deleted'))
    },
    onError: (e) => toast(e.message, true),
  })
  if (!can('action_delete')) return null
  return (
    <button type="button" title={t('common.delete')} aria-label={`${t('common.delete')} : ${action.title}`}
      className="rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
      disabled={remove.isPending}
      onClick={() => window.confirm(t('action.confirm_delete_named', { title: action.title })) && remove.mutate()}>
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
        strokeLinejoin="round" aria-hidden="true">
        <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v6M14 11v6" />
      </svg>
    </button>
  )
}
