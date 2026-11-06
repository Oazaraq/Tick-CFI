import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { api } from '../api/client'
import type { Me } from '../api/types'
import { Button, Field, inputClass } from '../components/ui'
import { Logo } from '../components/Logo'
import { t } from '../i18n'

/** Lien d'activation ou de réinitialisation : le jeton est dans le fragment (#token=…), jamais envoyé au serveur
 *  autrement que dans la requête de validation. Succès : session ouverte, retour au dashboard. */
export default function ResetPasswordPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const token = new URLSearchParams(window.location.hash.slice(1)).get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const mismatch = confirm.length > 0 && confirm !== password
  const reset = useMutation({
    mutationFn: () => api.post<Me>('/auth/password/reset', { token, password }),
    onSuccess: (me) => {
      window.history.replaceState(null, '', '/dashboard')  // le jeton disparaît de la barre d'adresse
      qc.setQueryData(['me'], me)
      navigate('/dashboard', { replace: true })
    },
  })
  return (
    <main className="bg-ocean flex min-h-screen flex-col items-center justify-center gap-6 p-4">
      <h1 className="text-white"><Logo size="lg" /></h1>
      <form className="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow-sm"
        onSubmit={(e) => { e.preventDefault(); if (!mismatch) reset.mutate() }}>
        <h2 className="font-bold text-blue-900">{t('reset.title')}</h2>
        {!token ? <p className="text-sm text-prio-critical">{t('reset.no_token')}</p> : (
          <>
            <Field label={t('password.new')}>
              <input className={inputClass} type="password" autoComplete="new-password" required minLength={8} autoFocus
                value={password} onChange={(e) => setPassword(e.target.value)} />
            </Field>
            <Field label={t('reset.confirm')}>
              <input className={inputClass} type="password" autoComplete="new-password" required minLength={8}
                value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            </Field>
            {mismatch && <p className="text-sm text-prio-critical">{t('reset.mismatch')}</p>}
            {reset.isError && <p className="text-sm text-prio-critical">{reset.error.message}</p>}
            <Button type="submit" className="w-full" disabled={reset.isPending || mismatch}>{t('reset.submit')}</Button>
          </>
        )}
        <a href="/" className="block text-center text-sm font-semibold text-blue-700 hover:underline">{t('login.back')}</a>
      </form>
    </main>
  )
}
