'use client'

type Step = { label: string; status: 'idle' | 'running' | 'done' }

export function LoadingCard({ steps }: { steps: Step[] }) {
  return (
    <div style={{ maxWidth: 640, margin: '32px auto', padding: '0 20px' }}>
      <div style={{
        background: 'var(--card)', border: '1px solid var(--border-2)',
        borderRadius: 'var(--r)', padding: '20px 24px',
        display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        {steps.map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: s.status === 'done' ? 'rgba(74,222,128,.15)' : s.status === 'running' ? 'rgba(96,165,250,.15)' : 'var(--card-2)',
              border: `1px solid ${s.status === 'done' ? 'rgba(74,222,128,.3)' : s.status === 'running' ? 'rgba(96,165,250,.3)' : 'var(--border)'}`,
            }}>
              {s.status === 'done' && (
                <svg width="10" height="10" fill="none" stroke="var(--green)" strokeWidth="3" viewBox="0 0 24 24">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
              {s.status === 'running' && (
                <svg className="spin" width="10" height="10" fill="none" stroke="var(--blue)" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path d="M21 12a9 9 0 1 1-6.22-8.56" />
                </svg>
              )}
              {s.status === 'idle' && (
                <span style={{ fontSize: '.65rem', color: 'var(--text-3)', fontWeight: 600 }}>{i + 1}</span>
              )}
            </div>
            <span style={{
              fontSize: '.84rem',
              color: s.status === 'done' ? 'var(--text-2)' : s.status === 'running' ? 'var(--text)' : 'var(--text-3)',
            }}>
              {s.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
