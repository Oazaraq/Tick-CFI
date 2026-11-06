import { t } from '../i18n'

/** Erreur d'API ; `body` contient la réponse JSON (ex. { detail, code, count } pour un 409). */
export class ApiError extends Error {
  status: number
  body: any
  constructor(status: number, body: any) {
    const detail = body?.detail
    super(typeof detail === 'string' ? detail : t(status === 422 ? 'error.invalid' : 'error.generic'))
    this.status = status
    this.body = body
  }
}

type Params = Record<string, string | number | boolean | null | undefined>

/** Chaîne de requête sans les filtres vides. */
export function qs(params: Params): string {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '' && v !== false) search.set(k, String(v))
  }
  const s = search.toString()
  return s ? `?${s}` : ''
}

/** En-tête exigé par le serveur sur les écritures (protection CSRF : un autre site ne peut pas le poser). */
const CSRF = { 'X-Requested-With': 'tickson' }

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/** Même origine (nginx relaie /api) : le cookie de session part automatiquement.
 *  502 / 503 : serveur en cours de démarrage (réveil en mode serverless, mise à jour), la requête n'a pas été
 *  traitée ; elle est renvoyée après 1, 2, 4 puis 8 s. Le 504 (délai dépassé) n'est jamais renvoyé : la requête
 *  a pu aboutir. */
async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const form = body instanceof FormData
  let res: Response
  for (let attempt = 0; ; attempt++) {
    res = await fetch(`/api${path}`, {
      method,
      credentials: 'same-origin',
      headers: body === undefined || form ? CSRF : { ...CSRF, 'Content-Type': 'application/json' },
      body: body === undefined || form ? (body as FormData | undefined) : JSON.stringify(body),
    })
    if (![502, 503].includes(res.status) || attempt === 4) break
    await wait(1000 * 2 ** attempt)
  }
  if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null))
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T = unknown>(path: string, body: unknown = {}) => request<T>('POST', path, body),
  patch: <T = unknown>(path: string, body: unknown) => request<T>('PATCH', path, body),
  del: (path: string) => request<void>('DELETE', path),
  upload: <T = unknown>(path: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<T>('POST', path, form)
  },
}
