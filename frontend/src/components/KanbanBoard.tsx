import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { DndContext, DragOverlay, PointerSensor, closestCorners, useDroppable, useSensor, useSensors } from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import type { ProjectCard, Status } from '../api/types'
import { useCan, useMe, useStatuses } from '../hooks'
import { t } from '../i18n'
import { dueClass, fmtDate, fmtDays, fullName, initials } from '../lib/format'
import { useMoveProject } from './ProjectMove'
import { PriorityBadge, Spinner } from './ui'

type Columns = Record<string, ProjectCard[]>

function group(projects: ProjectCard[]): Columns {
  const cols: Columns = {}
  for (const p of projects) (cols[p.status_code] ??= []).push(p)
  return cols
}

export default function KanbanBoard({ projects, showAllDone, onToggleDone }: {
  projects: ProjectCard[]; showAllDone: boolean; onToggleDone: () => void
}) {
  const statuses = useStatuses()
  const canDrag = useCan()('project_write') // Lecteur : Kanban visible, cartes non déplaçables
  const [cols, setCols] = useState(() => group(projects))
  const [draggedId, setDraggedId] = useState<number | null>(null)
  useEffect(() => setCols(group(projects)), [projects])
  const { move, dialog } = useMoveProject(() => setCols(group(projects)))
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))

  if (!statuses.data) return <Spinner />
  const all = Object.values(cols).flat()
  const find = (id: unknown) => all.find((p) => p.id === Number(id))
  const dragged = draggedId === null ? undefined : find(draggedId)

  function onDragEnd({ active, over }: DragEndEvent) {
    setDraggedId(null)
    const card = find(active.id)
    if (!card || !over) return
    const overId = String(over.id)
    const onColumn = overId.startsWith('col:')
    const target = onColumn ? overId.slice(4) : find(over.id)?.status_code
    if (!target) return
    const source = cols[card.status_code] ?? []
    const dest = (cols[target] ?? []).filter((p) => p.id !== card.id)
    const sameColumn = target === card.status_code
    let index = onColumn ? dest.length : (sameColumn ? source : dest).findIndex((p) => p.id === Number(over.id))
    if (sameColumn && (onColumn || index === source.indexOf(card))) return
    if (index < 0) index = dest.length
    dest.splice(index, 0, { ...card, status_code: target })
    setCols({ ...cols, [card.status_code]: source.filter((p) => p.id !== card.id), [target]: dest })
    move({ project: card, status_code: target, position: index })
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={onDragEnd}
      onDragStart={(e) => setDraggedId(Number(e.active.id))} onDragCancel={() => setDraggedId(null)}>
      <div className="flex gap-3 overflow-x-auto pb-4">
        {statuses.data.map((s) => (
          <Column key={s.code} status={s} cards={cols[s.code] ?? []} canDrag={canDrag}>
            {s.code === 'done' && (
              <button type="button" className="px-3 pb-2 text-left text-xs text-blue-700 hover:underline" onClick={onToggleDone}>
                {t(showAllDone ? 'kanban.hide_old' : 'kanban.show_all')}
              </button>
            )}
          </Column>
        ))}
      </div>
      <DragOverlay>{dragged ? <Card card={dragged} /> : null}</DragOverlay>
      {dialog}
    </DndContext>
  )
}

function Column({ status, cards, canDrag, children }: { status: Status; cards: ProjectCard[]; canDrag: boolean; children?: ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id: `col:${status.code}`, disabled: !canDrag })
  return (
    <section className={`flex min-w-44 flex-1 flex-col rounded-lg ${isOver ? 'bg-blue-100' : 'bg-tide'}`}>
      <h3 className="px-3 py-2 text-sm font-bold text-blue-900">{status.label} ({cards.length})</h3>
      <SortableContext id={status.code} items={cards.map((c) => c.id)} strategy={verticalListSortingStrategy}>
        <div ref={setNodeRef} className="flex min-h-24 flex-1 flex-col gap-2 px-2 pb-2">
          {cards.map((c) => <SortableCard key={c.id} card={c} disabled={!canDrag} />)}
        </div>
      </SortableContext>
      {children}
    </section>
  )
}

function SortableCard({ card, disabled }: { card: ProjectCard; disabled: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: card.id, disabled })
  const style = { transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined, transition, opacity: isDragging ? 0.4 : 1 }
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card card={card} />
    </div>
  )
}

function Card({ card }: { card: ProjectCard }) {
  const navigate = useNavigate()
  const soonDays = useMe().data?.due_soon_days ?? 7
  return (
    <article onClick={() => navigate(`/projects/${card.id}`)}
      className="cursor-pointer rounded-lg border border-gray-200 bg-white p-2.5 text-sm shadow-sm hover:border-blue-400">
      <p className="mb-2 font-medium">{card.title}</p>
      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
        <span title={fullName(card.owner)} className="rounded-full bg-gray-200 px-1.5 py-0.5 font-semibold">{initials(card.owner)}</span>
        <PriorityBadge value={card.priority} />
        {card.due_date && <span className={dueClass(card.due_date, card.status_code === 'done', soonDays)}>📅 {fmtDate(card.due_date).slice(0, 5)}</span>}
      </div>
      <div className="mt-2 flex justify-between text-xs text-gray-600">
        <span>{t('card.progress', { done: card.actions_done, total: card.actions_total })}</span>
        {card.actions_overdue > 0 && <span className="font-medium text-prio-critical">⚠ {t('card.overdue', { n: card.actions_overdue })}</span>}
      </div>
      {card.days_sold > 0 && (
        <p className={`mt-1 text-xs ${card.days_consumed > card.days_sold ? 'font-medium text-prio-high' : 'text-gray-600'}`}>
          ⏱ {t('card.effort', { consumed: fmtDays(card.days_consumed), sold: fmtDays(card.days_sold) })}
        </p>
      )}
    </article>
  )
}
