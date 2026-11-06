/** Affichage : dates JJ/MM/AAAA, heures en fuseau Europe/Paris (Q17). */
const TZ = 'Europe/Paris'

type Named = { first_name: string; last_name: string }

export const fullName = (u?: Named | null) => (u ? `${u.first_name} ${u.last_name}` : '')
export const initials = (u: Named) => `${u.first_name.charAt(0)}${u.last_name.charAt(0)}`.toUpperCase()

/** Date du jour à Paris, au format AAAA-MM-JJ (comparable aux dates de l'API). */
export const todayParis = () => new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(new Date())

export function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

export const fmtDate = (iso: string | null) => (iso ? iso.split('-').reverse().join('/') : '')

export const fmtDateTime = (iso: string) =>
  new Intl.DateTimeFormat('fr-FR', {
    timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(new Date(iso)).replace(',', '')

/** Nombre de jours/homme à la française : 2,5 */
export const fmtDays = (n: number | null | undefined) => (n ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 1 })

export const daysSince =(iso: string) => Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000))

/** Échéance dépassée : rouge ; dans moins de `soonDays` jours : orange (DFB §4.2). */
export function dueClass(due: string | null, closed: boolean, soonDays: number): string {
  if (!due || closed) return ''
  const today = todayParis()
  if (due < today) return 'font-medium text-prio-critical'
  return due < addDays(today, soonDays) ? 'text-prio-high' : ''
}
