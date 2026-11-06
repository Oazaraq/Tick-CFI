import fr from './fr.json'

const dict: Record<string, string> = fr

/** Texte d'interface : t('cle', { n: 3 }) remplace {n}. Une clé absente s'affiche telle quelle. */
export function t(key: string, vars?: Record<string, string | number>): string {
  let s = dict[key] ?? key
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v))
  return s
}
