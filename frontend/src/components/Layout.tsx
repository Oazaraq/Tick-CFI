import { useState } from 'react'
import { NavLink, Outlet } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useMe } from '../hooks'
import { t } from '../i18n'
import { fullName } from '../lib/format'
import { Logo } from './Logo'
import { Button, Field, inputClass, Modal, useToast } from './ui'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 text-sm ${isActive ? 'bg-white/20 font-bold text-white' : 'font-semibold text-white/85 hover:bg-white/10 hover:text-white'}`

export default function Layout() {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const toast = useToast()
  const [menu, setMenu] = useState(false)
  const [password, setPassword] = useState(false)
  const logout = useMutation({
    mutationFn: () => api.post('/auth/logout'),
    onSettled: () => { qc.clear(); qc.setQueryData(['me'], null) },
  })
  const emails = useMutation({  // interrupteur personnel des alertes (DFB A.1)
    mutationFn: (enabled: boolean) => api.patch('/auth/me', { notifications_enabled: enabled }),
    onSuccess: (_d, enabled) => { qc.invalidateQueries({ queryKey: ['me'] }); toast(t(enabled ? 'menu.emails_on_done' : 'menu.emails_off_done')) },
    onError: (e) => toast(e.message, true),
  })
  // Nouvelle version publiée pendant que la page est ouverte : proposer de recharger (vérifié au retour sur l'onglet)
  const version = useQuery({
    queryKey: ['version'],
    queryFn: async () => (await (await fetch('/version.json', { cache: 'no-store' })).json()) as { build: string },
    refetchOnWindowFocus: true, refetchInterval: 10 * 60_000, staleTime: 60_000, retry: false,
  })
  const outdated = version.data !== undefined && version.data.build !== __BUILD_ID__
  if (!me) return null
  return (
    <div className="min-h-screen">
      <header className="bg-ocean flex flex-wrap items-center gap-2 px-4 py-2.5 text-white shadow-md print:hidden">
        <Logo className="mr-4" />
        <NavLink to="/dashboard" className={navClass}>{t('nav.dashboard')}</NavLink>
        <NavLink to="/projects" className={navClass}>{t('nav.projects')}</NavLink>
        <NavLink to="/actions" className={navClass}>{t('nav.my_actions')}</NavLink>
        <NavLink to="/reporting" className={navClass}>{t('nav.reporting')}</NavLink>
        {me.permissions.includes('user_manage') && <NavLink to="/users" className={navClass}>{t('nav.users')}</NavLink>}
        {me.permissions.includes('email_log_view') && <NavLink to="/emails" className={navClass}>{t('nav.emails')}</NavLink>}
        <div className="relative ml-auto" onMouseLeave={() => setMenu(false)}>
          <Button variant="ghost" className="text-white hover:bg-white/10" onClick={() => setMenu(!menu)}>{fullName(me)} ▾</Button>
          {menu && (
            <div className="absolute right-0 z-30 w-56 rounded-lg border border-gray-200 bg-white py-1 text-gray-800 shadow">
              <label className="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left text-sm hover:bg-gray-50">
                <input type="checkbox" checked={me.notifications_enabled} disabled={emails.isPending} onChange={(e) => emails.mutate(e.target.checked)} />
                {t('menu.emails')}
              </label>
              <button type="button" className="block w-full px-3 py-2 text-left text-sm hover:bg-gray-50" onClick={() => { setPassword(true); setMenu(false) }}>{t('menu.password')}</button>
              <button type="button" className="block w-full px-3 py-2 text-left text-sm hover:bg-gray-50" onClick={() => logout.mutate()}>{t('menu.logout')}</button>
            </div>
          )}
        </div>
      </header>
      {outdated && (
        <div role="status" className="flex flex-wrap items-center justify-center gap-3 bg-blue-50 px-4 py-2 text-sm text-blue-900">
          {t('app.new_version')}
          <Button variant="secondary" onClick={() => window.location.reload()}>{t('app.reload')}</Button>
        </div>
      )}
      <main className="p-4">
        <Outlet />
      </main>
      {password && <PasswordModal onClose={() => setPassword(false)} onDone={() => { setPassword(false); toast(t('menu.password_done')) }} />}
    </div>
  )
}

function PasswordModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const save = useMutation({
    mutationFn: () => api.patch('/auth/me', { current_password: current, new_password: next }),
    onSuccess: onDone,
  })
  return (
    <Modal title={t('menu.password')} onClose={onClose}>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
        <Field label={t('password.current')}>
          <input type="password" className={inputClass} required autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </Field>
        <Field label={t('password.new')}>
          <input type="password" className={inputClass} required minLength={8} autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        </Field>
        {save.error && <p className="text-sm text-prio-critical">{save.error.message}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={save.isPending}>{t('common.save')}</Button>
        </div>
      </form>
    </Modal>
  )
}
