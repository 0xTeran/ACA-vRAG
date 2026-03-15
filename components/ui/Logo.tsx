export function Logo({ height = 24, className = '' }: { height?: number; className?: string }) {
  const w = (height * 126) / 62
  return (
    <svg
      viewBox="0 0 126 62"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      height={height}
      width={w}
      className={className}
      style={{ color: 'var(--text)' }}
    >
      <polyline points="2,58 21,4 40,58" stroke="currentColor" strokeWidth="5.5" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="11" y1="38" x2="31" y2="38" stroke="currentColor" strokeWidth="5.5" strokeLinecap="round" />
      <path d="M 81 17 A 22 22 0 1 0 81 45" stroke="currentColor" strokeWidth="5.5" strokeLinecap="round" fill="none" />
      <polyline points="85,58 104,4 123,58" stroke="currentColor" strokeWidth="5.5" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="92" y1="38" x2="116" y2="38" stroke="currentColor" strokeWidth="5.5" strokeLinecap="round" />
    </svg>
  )
}
