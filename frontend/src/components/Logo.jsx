// Marca de PlaneAI: una "P" trazada como un camino de prerrequisitos (nodos + aristas).
// Para usar el logo definitivo, reemplaza este SVG o pon el archivo en /public y usa <img>.
export function LogoMarca({ size = 34, className = "" }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 48 48" role="img" aria-label="PlaneAI">
      <rect width="48" height="48" rx="12" fill="var(--verde)" />
      <path d="M16 36V12h9a8 8 0 0 1 0 16h-9" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="16" cy="36" r="3.6" fill="#fff" />
      <circle cx="16" cy="12" r="3.6" fill="#fff" />
      <circle cx="33" cy="20" r="4.4" fill="var(--oro)" />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="logo">
      <LogoMarca />
      <span className="logo-texto">
        <b>PlaneAI</b>
        <small>Ingeniería de Sistemas UdeA</small>
      </span>
    </span>
  );
}
