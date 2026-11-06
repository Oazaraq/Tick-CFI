import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Me } from '../api/types'
import { Button, Field, inputClass } from '../components/ui'
import { Logo } from '../components/Logo'
import { t } from '../i18n'

/** Connexion (email ou identifiant) et demande de lien « mot de passe oublié », sur le dégradé de la charte. */
export default function LoginPage() {
  const [forgot, setForgot] = useState(false)
  return (
    <main className="bg-ocean flex min-h-screen flex-col items-center justify-center gap-6 p-4">
      <h1 className="text-white"><Logo size="lg" /></h1>
      {forgot ? <ForgotForm onBack={() => setForgot(false)} /> : <LoginForm onForgot={() => setForgot(true)} />}
    </main>
  )
}

const card = 'w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow-sm'

function LoginForm({ onForgot }: { onForgot: () => void }) {
  const qc = useQueryClient()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = useMutation({
    mutationFn: () => api.post<Me>('/auth/login', { email, password }),
    onSuccess: (me) => qc.setQueryData(['me'], me),
  })
  return (
    <form className={card} onSubmit={(e) => { e.preventDefault(); login.mutate() }}>
      <Field label={t('login.email')}>
        <input className={inputClass} type="text" autoComplete="username" autoCapitalize="none" spellCheck={false} required autoFocus
          value={email} onChange={(e) => setEmail(e.target.value)} />
      </Field>
      <Field label={t('login.password')}>
        <input className={inputClass} type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </Field>
      {login.isError && <p className="text-sm text-prio-critical">{login.error.message}</p>}
      <Button type="submit" className="w-full" disabled={login.isPending}>{t('login.submit')}</Button>
      <button type="button" className="block w-full text-center text-sm font-semibold text-blue-700 hover:underline" onClick={onForgot}>
        {t('login.forgot')}
      </button>
    </form>
  )
}

function ForgotForm({ onBack }: { onBack: () => void }) {
  const [email, setEmail] = useState('')
  const send = useMutation({ mutationFn: () => api.post<{ detail: string }>('/auth/password/forgot', { email }) })
  return (
    <form className={card} onSubmit={(e) => { e.preventDefault(); send.mutate() }}>
      <h2 className="font-bold text-blue-900">{t('login.forgot_title')}</h2>
      {send.isSuccess ? <p className="text-sm text-gray-700">{send.data.detail}</p> : (
        <>
          <p className="text-sm text-gray-600">{t('login.forgot_help')}</p>
          <Field label={t('login.forgot_email')}>
            <input className={inputClass} type="email" autoComplete="email" required autoFocus value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          {send.isError && <p className="text-sm text-prio-critical">{send.error.message}</p>}
          <Button type="submit" className="w-full" disabled={send.isPending}>{t('login.forgot_submit')}</Button>
        </>
      )}
      <button type="button" className="block w-full text-center text-sm font-semibold text-blue-700 hover:underline" onClick={onBack}>
        {t('login.back')}
      </button>
    </form>
  )
}
