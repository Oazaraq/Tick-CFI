import { createContext, useCallback, useContext, useState } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import type { Priority, UserBrief } from '../api/types'
import { t } from '../i18n'
import { fullName } from '../lib/format'

/** Champ sans largeur imposée (barres de filtres) ; `inputClass` occupe toute la largeur (formulaires). */
export const inputBase =
  'rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none disabled:bg-gray-100'
export const inputClass = `${inputBase} w-full`

const VARIANTS = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'border border-gray-300 bg-white hover:bg-gray-50',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  ghost: 'text-gray-700 hover:bg-gray-100',
}

export function Button({ variant = 'primary', className = '', ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof VARIANTS }) {
  return <button type="button" className={`rounded-lg px-3 py-1.5 text-sm font-medium disabled:opacity-50 ${VARIANTS[variant]} ${className}`} {...props} />
}

export function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick}
      className={`rounded-full border px-3 py-1 text-sm ${active ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-300 bg-white text-gray-700'}`}>
      {children}
    </button>
  )
}

export function Modal({ title, onClose, children, wide }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4" onMouseDown={onClose}>
      <div role="dialog" aria-label={title} onMouseDown={(e) => e.stopPropagation()}
        className={`max-h-full w-full overflow-y-auto rounded-xl bg-white p-5 shadow-xl ${wide ? 'max-w-2xl' : 'max-w-md'}`}>
        <h2 className="mb-4 text-lg font-bold text-blue-900">{title}</h2>
        {children}
      </div>
    </div>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-gray-700">{label}</span>
      {children}
    </label>
  )
}

const PRIO_BG: Record<Priority, string> = {
  low: 'bg-prio-low', medium: 'bg-prio-medium', high: 'bg-prio-high', critical: 'bg-prio-critical',
}

export const PriorityBadge = ({ value }: { value: Priority }) => (
  <span className={`rounded-lg px-1.5 py-0.5 text-xs font-medium text-white ${PRIO_BG[value]}`}>{t(`priority.${value}`)}</span>
)

export function UserSelect({ users, value, onChange, current, allowEmpty, className = inputClass }: {
  users: UserBrief[]; value: number | null; onChange: (id: number | null) => void
  current?: UserBrief | null; allowEmpty?: boolean; className?: string
}) {
  // Un responsable devenu inactif reste affiché, sans pouvoir être choisi à nouveau (RG17)
  const list = current && !users.some((u) => u.id === current.id) ? [current, ...users] : users
  return (
    <select className={className} value={value ?? ''} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
      {(allowEmpty || value === null) && <option value="">{t('common.none')}</option>}
      {list.map((u) => (
        <option key={u.id} value={u.id} disabled={!u.is_active}>
          {fullName(u)}{u.is_active ? '' : ` (${t('users.inactive')})`}
        </option>
      ))}
    </select>
  )
}

export const Spinner = () => <div className="p-6 text-center text-sm text-gray-500">{t('common.loading')}</div>
export const Empty = ({ text }: { text: string }) => <div className="p-6 text-center text-sm text-gray-500">{text}</div>
export const ErrorState = ({ error }: { error: unknown }) => (
  <div className="p-6 text-center text-sm text-prio-critical">{error instanceof Error ? error.message : t('error.generic')}</div>
)

type Toast = { id: number; text: string; error: boolean }
const ToastContext = createContext<(text: string, error?: boolean) => void>(() => {})
export const useToast = () => useContext(ToastContext)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const push = useCallback((text: string, error = false) => {
    const id = Date.now() + Math.random()
    setToasts((list) => [...list, { id, text, error }])
    setTimeout(() => setToasts((list) => list.filter((x) => x.id !== id)), 3500)
  }, [])
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="fixed right-4 bottom-4 z-50 space-y-2">
        {toasts.map((x) => (
          <div key={x.id} role="status" className={`rounded-lg px-4 py-2 text-sm text-white shadow ${x.error ? 'bg-red-600' : 'bg-gray-800'}`}>{x.text}</div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
