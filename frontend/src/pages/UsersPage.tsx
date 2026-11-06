import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { ROLES } from '../api/types'
import type { Role, User } from '../api/types'
import { Button, ErrorState, Field, inputBase, inputClass, Modal, Spinner, useToast } from '../components/ui'
import { useUsers } from '../hooks'
import { t } from '../i18n'
import { fullName } from '../lib/format'

export default function UsersPage() {
  const users = useUsers(true)
  const qc = useQueryClient()
  const toast = useToast()
  const [creating, setCreating] = useState(false)
  const [link, setLink] = useState<LinkInfo | null>(null)
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) => api.patch(`/users/${id}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); toast(t('users.saved')) },
    onError: (e) => toast(e.message, true),
  })
  const resetLink = useMutation({
    mutationFn: (u: User) => api.post<{ url: string; valid_hours: number; emailed: boolean }>(`/users/${u.id}/password-link`),
    onSuccess: (r, u) => setLink({ ...r, email: u.email }),
    onError: (e) => toast(e.message, true),
  })
  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex items-center">
        <h1 className="text-xl font-extrabold text-blue-900">{t('nav.users')}</h1>
        <Button className="ml-auto" onClick={() => setCreating(true)}>{t('users.new')}</Button>
      </div>
      {users.isPending ? <Spinner /> : users.isError ? <ErrorState error={users.error} /> : (
        <table className="w-full rounded-xl bg-white text-sm shadow-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              {['name', 'email', 'role', 'active'].map((k) => <th key={k} className="px-3 py-2 font-medium">{t(`users.col.${k}`)}</th>)}
              <th />
            </tr>
          </thead>
          <tbody>
            {users.data.map((u) => (
              <tr key={u.id} className={`border-b border-gray-100 ${u.is_active ? '' : 'text-gray-400'}`}>
                <td className="px-3 py-2">{fullName(u)}</td>
                <td className="px-3 py-2">{u.email}</td>
                <td className="px-3 py-2">
                  <select className={`${inputBase} w-44`} value={u.role} onChange={(e) => update.mutate({ id: u.id, body: { role: e.target.value } })}>
                    {ROLES.map((r) => <option key={r} value={r}>{t(`role.${r}`)}</option>)}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <input type="checkbox" checked={u.is_active} aria-label={t('users.col.active')} onChange={(e) => update.mutate({ id: u.id, body: { is_active: e.target.checked } })} />
                </td>
                <td className="px-3 py-2 text-right"><Button variant="ghost" disabled={resetLink.isPending} onClick={() => resetLink.mutate(u)}>{t('users.reset_password')}</Button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {creating && <UserForm onClose={() => setCreating(false)} onLink={setLink} />}
      {link && <LinkModal link={link} onClose={() => setLink(null)} />}
    </div>
  )
}

interface LinkInfo { url: string; valid_hours: number; emailed: boolean; email: string }

/** Lien d'activation ou de réinitialisation : envoyé par email, et à transmettre autrement si l'email n'arrive pas. */
function LinkModal({ link, onClose }: { link: LinkInfo; onClose: () => void }) {
  const toast = useToast()
  const copy = () => navigator.clipboard.writeText(link.url).then(() => toast(t('users.copied')), () => toast(t('users.copy_failed'), true))
  return (
    <Modal title={t('users.link_title')} onClose={onClose}>
      <div className="space-y-3 text-sm">
        <p>{link.emailed ? t('users.link_emailed', { email: link.email }) : t('users.link_not_emailed')}</p>
        <input className={`${inputClass} font-mono text-xs`} readOnly value={link.url} onFocus={(e) => e.target.select()} aria-label={t('users.link_title')} />
        <p className="text-gray-600">{link.valid_hours ? t('users.link_help', { hours: link.valid_hours }) : t('users.link_help_short')}</p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>{t('common.close')}</Button>
          <Button onClick={copy}>{t('users.copy')}</Button>
        </div>
      </div>
    </Modal>
  )
}

function UserForm({ onClose, onLink }: { onClose: () => void; onLink: (link: LinkInfo) => void }) {
  const qc = useQueryClient()
  const toast = useToast()
  const [v, setV] = useState({ first_name: '', last_name: '', email: '', role: 'contributor' as Role, password: '' })
  const create = useMutation({
    mutationFn: () => api.post<User & { activation_url: string | null }>('/users', { ...v, password: v.password || null }),
    onSuccess: (u) => {
      qc.invalidateQueries({ queryKey: ['users'] })
      toast(t('users.created'))
      onClose()
      if (u.activation_url) onLink({ url: u.activation_url, valid_hours: 0, emailed: true, email: u.email })
    },
  })
  const input = (key: 'first_name' | 'last_name' | 'email' | 'password', type = 'text', min?: number, required = true) => (
    <input className={inputClass} type={type} required={required} minLength={min} value={v[key]} onChange={(e) => setV({ ...v, [key]: e.target.value })} />
  )
  return (
    <Modal title={t('users.new')} onClose={onClose}>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); create.mutate() }}>
        <Field label={t('users.first_name')}>{input('first_name')}</Field>
        <Field label={t('users.last_name')}>{input('last_name')}</Field>
        <Field label={t('users.col.email')}>{input('email', 'email')}</Field>
        <Field label={t('users.col.role')}>
          <select className={inputClass} value={v.role} onChange={(e) => setV({ ...v, role: e.target.value as Role })}>
            {ROLES.map((r) => <option key={r} value={r}>{t(`role.${r}`)}</option>)}
          </select>
        </Field>
        <Field label={t('users.initial_password')}>{input('password', 'password', 8, false)}</Field>
        <p className="text-xs text-gray-500">{t('users.initial_password_hint')}</p>
        {create.error && <p className="text-sm text-prio-critical">{create.error.message}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={create.isPending}>{t('common.create')}</Button>
        </div>
      </form>
    </Modal>
  )
}
