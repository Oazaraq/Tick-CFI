/** Logo Tick’ : un billet (encoches, perforation, talon) frappé d'un T arrondi épais. Couleur : currentColor. */
export function LogoMark({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 40" className={className} fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path strokeWidth={3} d="M9 4H40A4 4 0 0 0 48 4H55A5 5 0 0 1 60 9V31A5 5 0 0 1 55 36H48A4 4 0 0 0 40 36H9A5 5 0 0 1 4 31V9A5 5 0 0 1 9 4Z" />
      <path strokeWidth={3} d="M44 13.5V15M44 19.5V20.5M44 25V26.5" />
      <path strokeWidth={3} d="M51.5 14H55M51.5 20H55M51.5 26H55" />
      <path strokeWidth={6.5} d="M14.5 13.5H31.5M23 13.5V28" />
    </svg>
  )
}

/** Logo et nom, pour l'en-tête et l'écran de connexion. */
export function Logo({ className = '', size = 'md' }: { className?: string; size?: 'md' | 'lg' }) {
  const lg = size === 'lg'
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <LogoMark className={lg ? 'h-10 w-16' : 'h-6 w-10'} />
      <span className={`font-extrabold tracking-tight ${lg ? 'text-3xl' : 'text-lg'}`}>Tick’</span>
    </span>
  )
}
