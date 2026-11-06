import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { RISK_LEVELS, RISK_STATUSES } from '../api/types'
import type { Project, Risk, RiskLevel, RiskStatus } from '../api/types'
import { useCan, useTeam } from '../hooks'
import { t } from '../i18n'
import { fullName } from '../lib/format'
import { Button, Empty, ErrorState, Field, inputClass, Modal, Spinner, UserSelect, useToast } from './ui'

const LEVEL_STYLE: Record<RiskLevel, string> = {
  low: 'bg-gray-200 text-gray-800', medium: 'bg-prio-high text-white', high: 'bg-prio-critical text-white',
}

/** Criticité calculée par le serveur (RG11) : l'interface ne fait que l'afficher. */
const CriticityBadge = ({ risk }: { risk: Risk }) => (
  <span className={`rounded-lg px-1.5 py-0.5 text-xs font-medium ${LEVEL_STYLE[risk.criticity]}`}>{t(`criticity.${risk.criticity}`)} ({risk.score})</span>
)

export default function RisksTab({ project }: { project: Project }) {
  const canWrite = useCan()('risk_write')
  const risks = useQuery({ queryKey: ['risks', project.id], queryFn: () => api.get<Risk[]>(`/projects/${project.id}/risks`) })
  const [editing, setEditing] = useState<Risk | 'new' | null>(null)
  return (
    <div className="space-y-4">
      {canWrite && <Button onClick={() => setEditing('new')}>{t('risks.new')}</Button>}
      {risks.isPending ? <Spinner /> : risks.isError ? <ErrorState error={risks.error} /> : !risks.data.length ? <Empty text={t('risks.empty')} /> : (
        <table className="w-full rounded-xl bg-white text-sm shadow-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              {['title', 'probability', 'impact', 'criticity', 'owner', 'status'].map((k) => <th key={k} className="px-3 py-2 font-medium">{t(`field.${k}`)}</th>)}
            </tr>
          </thead>
          <tbody>
            {risks.data.map((r) => (
              <tr key={r.id} className={`border-b border-gray-100 ${canWrite ? 'cursor-pointer hover:bg-gray-50' : ''}`} onClick={() => canWrite && setEditing(r)}>
                <td className="px-3 py-2 font-medium">{r.title}</td>
                <td className="px-3 py-2">{t(`probability.${r.probability}`)}</td>
                <td className="px-3 py-2">{t(`impact.${r.impact}`)}</td>
                <td className="px-3 py-2"><CriticityBadge risk={r} /></td>
                <td className="px-3 py-2">{fullName(r.owner) || '—'}</td>
                <td className="px-3 py-2">{t(`risk_status.${r.status}`)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {editing && <RiskForm projectId={project.id} risk={editing === 'new' ? undefined : editing} onClose={() => setEditing(null)} />}
    </div>
  )
}

function RiskForm({ projectId, risk, onClose }: { projectId: number; risk?: Risk; onClose: () => void }) {
  const qc = useQueryClient()
  const toast = useToast()
  const team = useTeam(projectId)
  const [v, setV] = useState({
    title: risk?.title ?? '', description: risk?.description ?? '', mitigation: risk?.mitigation ?? '',
    probability: risk?.probability ?? ('medium' as RiskLevel), impact: risk?.impact ?? ('medium' as RiskLevel),
    owner_id: risk?.owner?.id ?? null, status: risk?.status ?? ('open' as RiskStatus),
  })
  const save = useMutation({
    mutationFn: () => {
      const body = { ...v, description: v.description || null, mitigation: v.mitigation || null }
      return risk ? api.patch(`/risks/${risk.id}`, body) : api.post(`/projects/${projectId}/risks`, body)
    },
    onSuccess: () => {
      for (const key of ['risks', 'history']) qc.invalidateQueries({ queryKey: [key] })
      toast(t(risk ? 'risks.saved' : 'risks.created'))
      onClose()
    },
  })
  const levelSelect = (key: 'probability' | 'impact') => (
    <select className={inputClass} value={v[key]} onChange={(e) => setV({ ...v, [key]: e.target.value as RiskLevel })}>
      {RISK_LEVELS.map((l) => <option key={l} value={l}>{t(`${key}.${l}`)}</option>)}
    </select>
  )
  return (
    <Modal title={t(risk ? 'risks.edit' : 'risks.new')} onClose={onClose} wide>
      <form className="grid grid-cols-2 gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
        <div className="col-span-2">
          <Field label={`${t('field.title')} *`}>
            <input className={inputClass} required autoFocus maxLength={200} value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} />
          </Field>
        </div>
        <Field label={`${t('field.probability')} *`}>{levelSelect('probability')}</Field>
        <Field label={`${t('field.impact')} *`}>{levelSelect('impact')}</Field>
        <Field label={t('field.owner')}>
          <UserSelect users={team} current={risk?.owner} value={v.owner_id} allowEmpty onChange={(id) => setV({ ...v, owner_id: id })} />
        </Field>
        <Field label={t('field.status')}>
          <select className={inputClass} value={v.status} onChange={(e) => setV({ ...v, status: e.target.value as RiskStatus })}>
            {RISK_STATUSES.map((s) => <option key={s} value={s}>{t(`risk_status.${s}`)}</option>)}
          </select>
        </Field>
        <div className="col-span-2">
          <Field label={t('field.description')}>
            <textarea className={inputClass} rows={2} value={v.description} onChange={(e) => setV({ ...v, description: e.target.value })} />
          </Field>
        </div>
        <div className="col-span-2">
          <Field label={t('field.mitigation')}>
            <textarea className={inputClass} rows={2} value={v.mitigation} onChange={(e) => setV({ ...v, mitigation: e.target.value })} />
          </Field>
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
