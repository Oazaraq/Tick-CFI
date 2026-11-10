import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { api, ApiError } from '../api/client'
import type { Checklist, ChecklistCalcRow, ChecklistCustomItem, ChecklistData, ChecklistItem, ChecklistOwner, ChecklistSection, ChecklistStatus, Project, UserBrief } from '../api/types'
import { Button, Chip, ErrorState, inputClass, Spinner, useToast } from '../components/ui'
import { useCan } from '../hooks'
import { t } from '../i18n'
import { fmtDateTime, fullName } from '../lib/format'

const STATUSES: ChecklistStatus[] = ['ok', 'ko', 'tbc', 'na']
const SHORT: Record<string, string> = { ok: 'OK', ko: 'KO', tbc: '?', na: 'N/A' }
const ACTIVE: Record<string, string> = {
  ok: 'border-emerald-600 bg-emerald-600 text-white', ko: 'border-red-600 bg-red-600 text-white',
  tbc: 'border-amber-500 bg-amber-400 text-gray-900', na: 'border-gray-500 bg-gray-500 text-white',
}
const OWNER: Record<ChecklistOwner, string> = {
  'Avant-vente': 'bg-blue-50 text-blue-800', Client: 'bg-amber-50 text-amber-800', CFI: 'bg-emerald-50 text-emerald-800',
}
type Filter = 'all' | 'todo' | 'blocking'
const isOpen = (s: ChecklistStatus) => s !== 'ok' && s !== 'na'
const pick = (c: Checklist): ChecklistData => ({ revision: c.revision, meta: c.meta, states: c.states, custom: c.custom, calc: c.calc })
const newId = () => `X-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`

/** Check-list de lancement d'un projet : enregistrement automatique (clic immédiat, texte à la sortie du champ). */
export default function ChecklistPage() {
  const id = Number(useParams().id)
  const editable = useCan()('checklist_write')
  const toast = useToast()
  const project = useQuery({ queryKey: ['project', id], queryFn: () => api.get<Project>(`/projects/${id}`) })
  const remote = useQuery({ queryKey: ['checklist', id], queryFn: () => api.get<Checklist>(`/projects/${id}/checklist`),
    refetchOnWindowFocus: false, staleTime: Infinity })
  const [draft, setDraft] = useState<ChecklistData | null>(null)
  const [saved, setSaved] = useState<{ state: 'saved' | 'saving' | 'error'; by: UserBrief | null; at: string | null }>(
    { state: 'saved', by: null, at: null })
  const [filter, setFilter] = useState<Filter>('all')
  const latest = useRef<ChecklistData | null>(null)
  const queue = useRef<Promise<void>>(Promise.resolve())

  useEffect(() => {
    if (!remote.data) return
    latest.current = pick(remote.data)
    setDraft(latest.current)
    setSaved({ state: 'saved', by: remote.data.updated_by, at: remote.data.updated_at })
  }, [remote.data])

  function save() {
    setSaved((s) => ({ ...s, state: 'saving' }))
    queue.current = queue.current.then(async () => {
      try {
        const res = await api.put<Checklist>(`/projects/${id}/checklist`, latest.current)
        latest.current = { ...latest.current!, revision: res.revision }
        setSaved({ state: 'saved', by: res.updated_by, at: res.updated_at })
      } catch (e) {
        toast((e as Error).message, true)
        if (e instanceof ApiError && e.status === 409) await remote.refetch()
        else setSaved((s) => ({ ...s, state: 'error' }))
      }
    })
  }
  function change(mutate: (d: ChecklistData) => ChecklistData, persist = true) {
    if (!latest.current) return
    latest.current = mutate(latest.current)
    setDraft(latest.current)
    if (persist) save()
  }

  if (project.isPending || remote.isPending || !draft) return remote.isError ? <ErrorState error={remote.error} /> : <Spinner />
  if (project.isError) return <ErrorState error={project.error} />
  const sections = remote.data!.sections
  const itemsOf = (s: ChecklistSection): (ChecklistItem & { custom?: boolean })[] =>
    [...s.items, ...draft.custom.filter((c) => c.section === s.code).map((c) => ({ ...c, custom: true }))]
  const all = sections.flatMap(itemsOf)
  const status = (itemId: string): ChecklistStatus => draft.states[itemId]?.status ?? ''
  const count = (f: (i: ChecklistItem) => boolean) => all.filter(f).length
  const blockingOpen = count((i) => i.blocking && isOpen(status(i.id)))
  const visible = (i: ChecklistItem) =>
    filter === 'all' || (filter === 'todo' ? isOpen(status(i.id)) : i.blocking && isOpen(status(i.id)))
  const setState = (itemId: string, patch: Partial<{ status: ChecklistStatus; note: string }>, persist = true) =>
    change((d) => ({ ...d, states: { ...d.states, [itemId]: { ...(d.states[itemId] ?? { status: '', note: '' }), ...patch } } }), persist)
  const setMeta = (key: keyof ChecklistData['meta'], value: string, persist = false) =>
    change((d) => ({ ...d, meta: { ...d.meta, [key]: value || (key === 'kickoff_date' ? null : '') } }), persist)

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <Link to={`/projects/${id}`} className="text-sm text-blue-700 hover:underline print:hidden">← {project.data.title}</Link>
      <header className="flex flex-wrap items-start gap-3">
        <div>
          <h1 className="text-xl font-extrabold text-blue-900">{t('checklist.title')} — {project.data.title}</h1>
          <p className="text-sm text-gray-600">{t('checklist.subtitle')}</p>
        </div>
        <div className="ml-auto flex items-center gap-3 print:hidden">
          <span className={`text-sm ${saved.state === 'error' ? 'text-red-700' : 'text-gray-500'}`}>
            {saved.state === 'saving' ? t('checklist.saving') : saved.state === 'error' ? t('checklist.save_error')
              : saved.by && saved.at ? t('checklist.saved_by', { name: fullName(saved.by), date: fmtDateTime(saved.at) }) : ''}
          </span>
          <Button variant="secondary" onClick={() => window.print()}>{t('checklist.print')}</Button>
        </div>
      </header>

      <section className="grid gap-3 rounded-xl bg-white p-4 shadow-sm sm:grid-cols-2">
        {(['client', 'kickoff_date', 'participants', 'order_ref'] as const).map((key) => (
          <label key={key} className="text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t(`checklist.${key}`)}</span>
            <input className={inputClass} type={key === 'kickoff_date' ? 'date' : 'text'} disabled={!editable}
              value={draft.meta[key] ?? ''} maxLength={key === 'participants' ? 500 : 200}
              onChange={(e) => setMeta(key, e.target.value, key === 'kickoff_date')} onBlur={() => key !== 'kickoff_date' && save()} />
          </label>
        ))}
      </section>

      <div className={`rounded-xl p-3 text-sm font-semibold ${blockingOpen ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>
        {blockingOpen ? t('checklist.blocking_alert', { count: blockingOpen }) : t('checklist.all_clear')}
        <span className="ml-2 font-normal text-gray-700">
          {t('checklist.summary', { done: count((i) => !isOpen(status(i.id))), total: all.length,
            ko: count((i) => status(i.id) === 'ko'), tbc: count((i) => status(i.id) === 'tbc') })}
        </span>
      </div>
      <div className="flex gap-1 print:hidden">
        {(['all', 'todo', 'blocking'] as Filter[]).map((f) => (
          <Chip key={f} active={filter === f} onClick={() => setFilter(f)}>{t(`checklist.filter_${f}`)}</Chip>
        ))}
      </div>

      {sections.map((s) => (
        <section key={s.code} className="rounded-xl bg-white p-4 shadow-sm break-inside-avoid">
          <h2 className="font-bold text-blue-900">{s.title}</h2>
          {s.note && <p className="text-xs text-gray-500">{s.note}</p>}
          {itemsOf(s).filter(visible).map((it) => (
            <div key={it.id} className="grid gap-2 border-t border-gray-100 py-3 md:grid-cols-[1fr_auto] break-inside-avoid">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-gray-400">{it.id.startsWith('X-') ? '+' : it.id}</span>
                  <span className="font-bold text-gray-900">{it.point}</span>
                  <span className={`rounded px-1.5 text-xs font-semibold ${OWNER[it.owner]}`}>{it.owner}</span>
                  {it.blocking && <span className="rounded bg-red-50 px-1.5 text-xs font-semibold text-red-700">{t('checklist.blocking')}</span>}
                  {it.custom && editable && (
                    <button type="button" className="text-xs text-gray-400 hover:text-red-600 print:hidden" title={t('checklist.remove_point')}
                      onClick={() => window.confirm(t('checklist.confirm_remove', { point: it.point })) &&
                        change((d) => ({ ...d, custom: d.custom.filter((c) => c.id !== it.id) }))}>✕</button>
                  )}
                </div>
                {it.question && <p className="text-sm text-gray-600">{it.question}</p>}
                <input className={`${inputClass} mt-1 ${draft.states[it.id]?.note ? '' : 'print:hidden'}`} placeholder={t('checklist.note')} disabled={!editable} maxLength={2000}
                  value={draft.states[it.id]?.note ?? ''} onChange={(e) => setState(it.id, { note: e.target.value }, false)} onBlur={save} />
              </div>
              <div className="flex items-start gap-1">
                {STATUSES.map((st) => {
                  const on = status(it.id) === st
                  return (
                    <button key={st} type="button" disabled={!editable} title={t(`checklist.status.${st}`)} aria-pressed={on}
                      onClick={() => setState(it.id, { status: on ? '' : st })}
                      className={`min-w-11 rounded-lg border px-2 py-1 text-sm font-bold disabled:cursor-default ${on ? ACTIVE[st] : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-50 print:hidden'}`}>
                      {SHORT[st]}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
          {s.calc && <Calculator rows={draft.calc} editable={editable} onChange={(calc, persist) => change((d) => ({ ...d, calc }), persist)} />}
          {editable && <AddPoint section={s.code} onAdd={(item) => change((d) => ({ ...d, custom: [...d.custom, item] }))} />}
        </section>
      ))}
    </div>
  )
}

function AddPoint({ section, onAdd }: { section: string; onAdd: (item: ChecklistCustomItem) => void }) {
  const empty = { point: '', question: '', owner: 'CFI' as ChecklistOwner, blocking: false }
  const [open, setOpen] = useState(false)
  const [v, setV] = useState(empty)
  if (!open) return <button type="button" className="mt-2 text-sm text-blue-700 hover:underline print:hidden" onClick={() => setOpen(true)}>+ {t('checklist.add_point')}</button>
  return (
    <form className="mt-2 grid gap-2 rounded-lg bg-gray-50 p-3 sm:grid-cols-[1fr_2fr_auto_auto_auto] print:hidden"
      onSubmit={(e) => { e.preventDefault(); onAdd({ ...v, id: newId(), section }); setV(empty); setOpen(false) }}>
      <input className={inputClass} required maxLength={120} placeholder={t('checklist.point')} value={v.point} onChange={(e) => setV({ ...v, point: e.target.value })} />
      <input className={inputClass} maxLength={500} placeholder={t('checklist.question')} value={v.question} onChange={(e) => setV({ ...v, question: e.target.value })} />
      <select className={inputClass} value={v.owner} onChange={(e) => setV({ ...v, owner: e.target.value as ChecklistOwner })}>
        {Object.keys(OWNER).map((o) => <option key={o}>{o}</option>)}
      </select>
      <label className="flex items-center gap-1 text-sm"><input type="checkbox" checked={v.blocking} onChange={(e) => setV({ ...v, blocking: e.target.checked })} />{t('checklist.blocking')}</label>
      <div className="flex gap-1"><Button type="submit">{t('checklist.add')}</Button><Button variant="ghost" onClick={() => setOpen(false)}>✕</Button></div>
    </form>
  )
}

function Calculator({ rows, editable, onChange }: { rows: ChecklistCalcRow[]; editable: boolean; onChange: (rows: ChecklistCalcRow[], persist: boolean) => void }) {
  const total = (k: 'watts' | 'units') => rows.reduce((sum, r) => sum + (r.qty || 0) * (r[k] || 0), 0)
  const set = (i: number, patch: Partial<ChecklistCalcRow>, persist = false) => onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)), persist)
  const num = (s: string) => (s === '' ? null : Number(s))
  const cell = (node: ReactNode) => <td className="px-1 py-1">{node}</td>
  return (
    <div className="mt-3 rounded-lg border border-gray-200 p-3">
      <h3 className="mb-2 text-sm font-semibold text-gray-700">{t('checklist.calc_title')}</h3>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-gray-500">{['calc_name', 'calc_qty', 'calc_watts', 'calc_units'].map((k) => <th key={k} className="px-1 font-medium">{t(`checklist.${k}`)}</th>)}<th /></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {cell(<input className={inputClass} disabled={!editable} maxLength={120} value={r.name} onChange={(e) => set(i, { name: e.target.value })} onBlur={() => onChange(rows, true)} />)}
              {cell(<input className={`${inputClass} w-20`} type="number" min={0} disabled={!editable} value={r.qty} onChange={(e) => set(i, { qty: Number(e.target.value) || 0 })} onBlur={() => onChange(rows, true)} />)}
              {cell(<input className={`${inputClass} w-28`} type="number" min={0} disabled={!editable} value={r.watts ?? ''} onChange={(e) => set(i, { watts: num(e.target.value) })} onBlur={() => onChange(rows, true)} />)}
              {cell(<input className={`${inputClass} w-24`} type="number" min={0} step="0.5" disabled={!editable} value={r.units ?? ''} onChange={(e) => set(i, { units: num(e.target.value) })} onBlur={() => onChange(rows, true)} />)}
              <td className="w-8 print:hidden">{editable && rows.length > 1 && <button type="button" className="text-gray-400 hover:text-red-600" onClick={() => onChange(rows.filter((_, j) => j !== i), true)}>✕</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
        <strong className="text-blue-900">{t('checklist.calc_total', { watts: total('watts'), btu: Math.round(total('watts') * 3.412), units: total('units') })}</strong>
        {editable && rows.length < 50 && <button type="button" className="text-blue-700 hover:underline print:hidden" onClick={() => onChange([...rows, { name: '', qty: 1, watts: null, units: null }], true)}>+ {t('checklist.calc_add')}</button>}
      </div>
    </div>
  )
}
