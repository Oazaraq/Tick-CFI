import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { api, qs } from '../api/client'
import type { EmailLog } from '../api/types'
import { Empty, ErrorState, inputBase, Spinner } from '../components/ui'
import { t } from '../i18n'
import { fmtDateTime } from '../lib/format'

/** Journal des emails (administrateur) : 300 derniers envois, réussis ou en échec. */
export default function EmailsPage() {
  const [status, setStatus] = useState('')
  const logs = useQuery({ queryKey: ['email-logs', status], queryFn: () => api.get<EmailLog[]>(`/email-logs${qs({ status })}`) })
  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-extrabold text-blue-900">{t('emails.title')}</h1>
        <select className={inputBase} value={status} onChange={(e) => setStatus(e.target.value)} aria-label={t('emails.filter')}>
          <option value="">{t('emails.all')}</option>
          <option value="sent">{t('emails.status.sent')}</option>
          <option value="failed">{t('emails.status.failed')}</option>
        </select>
      </div>
      {logs.isPending ? <Spinner /> : logs.isError ? <ErrorState error={logs.error} /> : !logs.data.length ? <Empty text={t('emails.empty')} /> : (
        <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500">
                {['date', 'recipient', 'subject', 'status'].map((k) => <th key={k} className="px-3 py-2 font-medium">{t(`emails.col.${k}`)}</th>)}
              </tr>
            </thead>
            <tbody>
              {logs.data.map((e) => (
                <tr key={e.id} className="border-b border-gray-100 align-top">
                  <td className="whitespace-nowrap px-3 py-2">{fmtDateTime(e.created_at)}</td>
                  <td className="px-3 py-2">{e.recipient_email}</td>
                  <td className="px-3 py-2">
                    {e.project_id ? <Link to={`/projects/${e.project_id}`} className="text-blue-700 hover:underline">{e.subject}</Link> : e.subject}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`rounded-lg px-1.5 py-0.5 text-xs font-medium ${e.status === 'sent' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {t(`emails.status.${e.status}`)}
                    </span>
                    {e.error && <p className="mt-1 max-w-md text-xs text-red-800">{e.error}</p>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
