import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Effort, PlanningItem, Project } from '../api/types'
import { useCan, useCategories } from '../hooks'
import { t } from '../i18n'
import { exportPng, slug } from '../lib/exportPng'
import { fmtDate, fmtDays, todayParis } from '../lib/format'
import Gantt from './Gantt'
import { Button, Empty, ErrorState, Field, inputClass, Spinner, useToast } from './ui'

type Form = {
  id?: number; label: string; kind: 'phase' | 'milestone'; start_date: string; end_date: string
  category: string; days_sold: string; days_consumed: string; predecessor_ids: number[]
}
const EMPTY: Form = { label: '', kind: 'phase', start_date: '', end_date: '', category: '', days_sold: '', days_consumed: '', predecessor_ids: [] }
const num = (v: string) => (v === '' ? null : Number(v))

/** Avenants 1 et 3 : saisie en tableau, Gantt redessiné à chaque changement, charge par catégorie, export .png. */
export default function PlanningTab({ project }: { project: Project }) {
  const canWrite = useCan()('project_write')
  const categories = useCategories()
  const qc = useQueryClient()
  const toast = useToast()
  const svgRef = useRef<SVGSVGElement>(null)
  const [form, setForm] = useState<Form>(EMPTY)
  const items = useQuery({ queryKey: ['planning', project.id], queryFn: () => api.get<PlanningItem[]>(`/projects/${project.id}/planning`) })
  const effort = useQuery({ queryKey: ['planning', project.id, 'effort'], queryFn: () => api.get<Effort>(`/projects/${project.id}/effort`) })
  const refresh = () => { for (const key of ['planning', 'history', 'project', 'projects']) qc.invalidateQueries({ queryKey: [key] }) }
  const save = useMutation({
    mutationFn: () => {
      const phase = form.kind === 'phase'
      const body = {
        label: form.label, kind: form.kind, start_date: form.start_date, end_date: phase ? form.end_date || null : form.start_date,
        category: phase ? form.category || null : null, days_sold: phase ? num(form.days_sold) : null,
        days_consumed: phase ? num(form.days_consumed) : null, predecessor_ids: form.predecessor_ids,
      }
      return form.id ? api.patch(`/planning/${form.id}`, body) : api.post(`/projects/${project.id}/planning`, body)
    },
    onSuccess: () => { refresh(); setForm(EMPTY); toast(t('planning.saved')) },
    onError: (e) => toast(e.message, true),
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/planning/${id}`),
    onSuccess: () => { refresh(); setForm(EMPTY); toast(t('planning.deleted')) },
    onError: (e) => toast(e.message, true),
  })
  const download = () => {
    if (!svgRef.current) return
    exportPng(svgRef.current, `planning-${slug(project.title)}-${todayParis()}.png`).catch(() => toast(t('error.generic'), true))
  }
  const edit = (item: PlanningItem) => setForm({
    id: item.id, label: item.label, kind: item.kind, start_date: item.start_date, end_date: item.end_date,
    category: item.category ?? '', days_sold: item.days_sold?.toString() ?? '', days_consumed: item.days_consumed?.toString() ?? '',
    predecessor_ids: item.predecessor_ids,
  })
  const togglePredecessor = (id: number) => setForm({
    ...form,
    predecessor_ids: form.predecessor_ids.includes(id) ? form.predecessor_ids.filter((x) => x !== id) : [...form.predecessor_ids, id],
  })
  const categoryLabel = (code: string | null) => categories.data?.find((c) => c.code === code)?.label ?? ''

  if (items.isPending) return <Spinner />
  if (items.isError) return <ErrorState error={items.error} />
  const list = items.data
  const byId = new Map(list.map((i) => [i.id, i]))
  return (
    <div className="space-y-4">
      <div className="flex items-center">
        <p className="text-sm text-gray-600">{t('planning.hint')}</p>
        <Button className="ml-auto" variant="secondary" disabled={!list.length} onClick={download}>{t('planning.export')}</Button>
      </div>
      {list.length
        ? <div className="overflow-x-auto rounded-xl bg-white p-2 shadow-sm"><Gantt title={project.title} items={list} svgRef={svgRef} /></div>
        : <Empty text={t('planning.empty')} />}
      {list.length > 0 && (
        <table className="w-full rounded-xl bg-white text-sm shadow-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              {['label', 'kind', 'start_date', 'end_date', 'category', 'days', 'predecessors'].map((k) => <th key={k} className="px-3 py-2 font-medium">{t(`planning.col.${k}`)}</th>)}
              <th />
            </tr>
          </thead>
          <tbody>
            {list.map((item) => (
              <tr key={item.id} className={`border-b border-gray-100 ${form.id === item.id ? 'bg-blue-50' : ''}`}>
                <td className="px-3 py-2 font-medium">{item.label}</td>
                <td className="px-3 py-2">{t(`kind.${item.kind}`)}</td>
                <td className="px-3 py-2">{fmtDate(item.start_date)}</td>
                <td className="px-3 py-2">{item.kind === 'milestone' ? '—' : fmtDate(item.end_date)}</td>
                <td className="px-3 py-2">{categoryLabel(item.category) || '—'}</td>
                <td className={`px-3 py-2 ${(item.days_consumed ?? 0) > (item.days_sold ?? 0) ? 'font-medium text-prio-high' : ''}`}>
                  {item.days_sold != null || item.days_consumed != null ? `${fmtDays(item.days_consumed)}/${fmtDays(item.days_sold)}` : '—'}
                </td>
                <td className="px-3 py-2">
                  {item.predecessor_ids.map((pid) => (
                    <span key={pid} className={`mr-2 ${item.dependency_issues.includes(pid) ? 'font-medium text-prio-high' : ''}`}
                      title={item.dependency_issues.includes(pid) ? t('planning.issue') : undefined}>
                      {byId.get(pid)?.label}{item.dependency_issues.includes(pid) ? ' ⚠' : ''}
                    </span>
                  ))}
                </td>
                <td className="px-3 py-2 text-right">
                  {canWrite && (
                    <span className="flex justify-end gap-3 text-xs">
                      <button type="button" className="text-blue-700 hover:underline" onClick={() => edit(item)}>{t('common.edit')}</button>
                      <button type="button" className="text-gray-500 hover:text-prio-critical" onClick={() => window.confirm(t('planning.confirm_delete')) && remove.mutate(item.id)}>{t('common.delete')}</button>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {effort.data && effort.data.categories.length > 0 && (
        <section className="rounded-xl bg-white p-4 text-sm shadow-sm">
          <h2 className="mb-2 font-bold text-blue-900">{t('planning.effort_title')}</h2>
          <table className="w-full max-w-xl">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="py-1 font-medium">{t('planning.col.category')}</th>
                <th className="py-1 text-right font-medium">{t('field.days_sold')}</th>
                <th className="py-1 text-right font-medium">{t('field.days_consumed')}</th>
              </tr>
            </thead>
            <tbody>
              {effort.data.categories.map((c) => (
                <tr key={c.code} className={c.consumed > c.sold ? 'text-prio-high' : ''}>
                  <td className="py-1">{c.label}</td>
                  <td className="py-1 text-right">{fmtDays(c.sold)}</td>
                  <td className="py-1 text-right">{fmtDays(c.consumed)}</td>
                </tr>
              ))}
              <tr className="border-t border-gray-200 font-semibold">
                <td className="py-1">{t('planning.total')}</td>
                <td className="py-1 text-right">{fmtDays(effort.data.sold)}</td>
                <td className="py-1 text-right">{fmtDays(effort.data.consumed)}</td>
              </tr>
            </tbody>
          </table>
        </section>
      )}
      {canWrite && (
        <form className="space-y-3 rounded-xl bg-white p-3 shadow-sm" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-56 flex-1">
              <Field label={`${t('field.label')} *`}>
                <input className={inputClass} required maxLength={200} value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
              </Field>
            </div>
            <div className="w-28">
              <Field label={t('field.kind')}>
                <select className={inputClass} value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as Form['kind'] })}>
                  <option value="phase">{t('kind.phase')}</option>
                  <option value="milestone">{t('kind.milestone')}</option>
                </select>
              </Field>
            </div>
            <div className="w-40">
              <Field label={`${t(form.kind === 'milestone' ? 'planning.date' : 'field.start_date')} *`}>
                <input type="date" className={inputClass} required value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
              </Field>
            </div>
            {form.kind === 'phase' && (
              <>
                <div className="w-40">
                  <Field label={`${t('field.end_date')} *`}>
                    <input type="date" className={inputClass} required min={form.start_date || undefined} value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
                  </Field>
                </div>
                <div className="w-56">
                  <Field label={t('field.category')}>
                    <select className={inputClass} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                      <option value="">{t('planning.no_category')}</option>
                      {categories.data?.map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
                    </select>
                  </Field>
                </div>
                <div className="w-28">
                  <Field label={t('field.days_sold')}>
                    <input type="number" min={0} step={0.5} className={inputClass} value={form.days_sold} onChange={(e) => setForm({ ...form, days_sold: e.target.value })} />
                  </Field>
                </div>
                <div className="w-28">
                  <Field label={t('field.days_consumed')}>
                    <input type="number" min={0} step={0.5} className={inputClass} value={form.days_consumed} onChange={(e) => setForm({ ...form, days_consumed: e.target.value })} />
                  </Field>
                </div>
              </>
            )}
            <Button type="submit" disabled={save.isPending}>{t(form.id ? 'common.save' : 'planning.add')}</Button>
            {form.id && <Button variant="secondary" onClick={() => setForm(EMPTY)}>{t('common.cancel')}</Button>}
          </div>
          {list.some((i) => i.id !== form.id) && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <span className="font-medium text-gray-700">
                {t('planning.predecessors_of', { label: form.label.trim() || t('planning.this_item') })}
              </span>
              {list.filter((i) => i.id !== form.id).map((i) => (
                <label key={i.id} className="flex items-center gap-1">
                  <input type="checkbox" checked={form.predecessor_ids.includes(i.id)} onChange={() => togglePredecessor(i.id)} />
                  {i.label}
                </label>
              ))}
            </div>
          )}
        </form>
      )}
    </div>
  )
}
