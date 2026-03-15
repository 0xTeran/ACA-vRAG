'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { PenSquare, PanelLeftClose, PanelLeft, Clock, Search, Database, Settings } from 'lucide-react'
import { Logo } from '@/components/ui/Logo'
import { ClasificacionRecord } from '@/types'

function timeAgo(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffDays = Math.floor(diffMs / 86400000)
  if (diffDays === 0) return 'Hoy'
  if (diffDays === 1) return 'Ayer'
  if (diffDays < 7) return `Hace ${diffDays} días`
  if (diffDays < 30) return `Hace ${Math.floor(diffDays / 7)} semanas`
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })
}

function groupByDate(records: ClasificacionRecord[]): { label: string; items: ClasificacionRecord[] }[] {
  const groups: Record<string, ClasificacionRecord[]> = {}
  for (const r of records) {
    const label = timeAgo(r.created_at)
    if (!groups[label]) groups[label] = []
    groups[label].push(r)
  }
  return Object.entries(groups).map(([label, items]) => ({ label, items }))
}

function getTitle(r: ClasificacionRecord): string {
  const ficha = r.ficha_tecnica ?? r.fuente_nombre ?? ''
  if (r.subpartida && ficha) {
    return `${r.subpartida} — ${ficha.slice(0, 40)}`
  }
  return ficha.slice(0, 50) || r.subpartida || 'Sin título'
}

export function Sidebar() {
  const [open, setOpen] = useState(true)
  const [records, setRecords] = useState<ClasificacionRecord[]>([])
  const [search, setSearch] = useState('')
  const pathname = usePathname()

  useEffect(() => {
    fetch('/api/historial')
      .then(r => r.json())
      .then(d => setRecords(d.registros ?? []))
      .catch(() => {})
  }, [pathname])

  const filtered = search.trim()
    ? records.filter(r => {
        const s = search.trim().toLowerCase()
        return (r.ficha_tecnica ?? '').toLowerCase().includes(s)
          || (r.subpartida ?? '').includes(s)
          || (r.fuente_nombre ?? '').toLowerCase().includes(s)
      })
    : records

  const groups = groupByDate(filtered)
  const activeId = pathname.match(/^\/c\/([a-f0-9-]+)/i)?.[1]

  if (!open) {
    return (
      <div style={{
        position: 'fixed', top: 0, left: 0, bottom: 0, width: 50, zIndex: 200,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        paddingTop: 14, gap: 8,
        background: 'var(--sidebar-bg, var(--bg))',
        borderRight: '1px solid var(--border)',
      }}>
        <button onClick={() => setOpen(true)} style={iconBtnStyle} title="Abrir sidebar">
          <PanelLeft size={18} />
        </button>
        <Link href="/" style={iconBtnStyle} title="Nueva clasificación">
          <PenSquare size={18} />
        </Link>
      </div>
    )
  }

  return (
    <>
      <div style={{
        position: 'fixed', top: 0, left: 0, bottom: 0, width: 280, zIndex: 200,
        display: 'flex', flexDirection: 'column',
        background: 'var(--sidebar-bg, var(--bg))',
        borderRight: '1px solid var(--border)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 12px 0' }}>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
            <Logo height={20} />
          </Link>
          <button onClick={() => setOpen(false)} style={iconBtnStyle} title="Cerrar sidebar">
            <PanelLeftClose size={16} />
          </button>
        </div>

        {/* Search + New chat buttons */}
        <div style={{ padding: '12px 12px 8px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          <button
            onClick={() => setSearch(search ? '' : ' ')}
            style={sideBtnStyle}
            onMouseOver={e => e.currentTarget.style.background = 'rgba(128,128,128,.1)'}
            onMouseOut={e => e.currentTarget.style.background = 'transparent'}
          >
            <Search size={16} /> Buscar
          </button>
          <Link href="/" style={{ ...sideBtnStyle, textDecoration: 'none' }}
            onMouseOver={e => e.currentTarget.style.background = 'rgba(128,128,128,.1)'}
            onMouseOut={e => e.currentTarget.style.background = 'transparent'}
          >
            <PenSquare size={16} /> Nueva clasificación
          </Link>
        </div>

        {/* Search input (expandable) */}
        {search !== '' && (
          <div style={{ padding: '0 12px 8px' }}>
            <input
              autoFocus
              value={search === ' ' ? '' : search}
              onChange={e => setSearch(e.target.value || ' ')}
              onBlur={() => { if (search.trim() === '') setSearch('') }}
              placeholder="Buscar por producto o subpartida..."
              style={{
                width: '100%', background: 'var(--card)', border: '1px solid var(--border)',
                borderRadius: 10, padding: '8px 12px', outline: 'none',
                color: 'var(--text)', fontFamily: 'inherit', fontSize: '.8rem',
              }}
            />
          </div>
        )}

        {/* History list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px' }}>
          {groups.map((group) => (
            <div key={group.label} style={{ marginBottom: 6 }}>
              <div style={{
                fontSize: '.68rem', fontWeight: 600, color: 'var(--text-3)',
                padding: '10px 8px 4px', textTransform: 'uppercase', letterSpacing: '.04em',
              }}>
                {group.label}
              </div>
              {group.items.map((r) => (
                <Link
                  key={r.id}
                  href={`/c/${r.id}`}
                  style={{
                    display: 'block', padding: '8px 10px', borderRadius: 8,
                    textDecoration: 'none', fontSize: '.82rem', lineHeight: 1.4,
                    color: activeId === r.id ? 'var(--text)' : 'var(--text-2)',
                    background: activeId === r.id ? 'rgba(128,128,128,.12)' : 'transparent',
                    transition: 'background .15s',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}
                  onMouseOver={(e) => { if (activeId !== r.id) e.currentTarget.style.background = 'rgba(128,128,128,.06)' }}
                  onMouseOut={(e) => { if (activeId !== r.id) e.currentTarget.style.background = 'transparent' }}
                >
                  {getTitle(r)}
                </Link>
              ))}
            </div>
          ))}

          {records.length === 0 && (
            <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-3)', fontSize: '.82rem' }}>
              No hay clasificaciones aún
            </div>
          )}
        </div>

        {/* Bottom nav */}
        <div style={{ borderTop: '1px solid var(--border)', padding: 8 }}>
          <Link href="/historial" style={bottomLinkStyle}>
            <Clock size={14} /> Historial completo
          </Link>
          <Link href="/importar" style={bottomLinkStyle}>
            <Database size={14} /> Importar BD
          </Link>
        </div>
      </div>

      {/* Spacer to push main content */}
      <style>{`
        :root { --sidebar-w: 280px; }
        @media (max-width: 768px) { :root { --sidebar-w: 0px; } }
      `}</style>
    </>
  )
}

const iconBtnStyle: React.CSSProperties = {
  background: 'none', border: 'none', cursor: 'pointer',
  color: 'var(--text-3)', padding: 6, borderRadius: 8,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  transition: 'background .15s', textDecoration: 'none',
}

const sideBtnStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 12,
  padding: '10px 12px', borderRadius: 10,
  background: 'transparent', border: 'none', cursor: 'pointer',
  color: 'var(--text)', fontFamily: 'inherit', fontSize: '.88rem',
  fontWeight: 400, transition: 'background .15s', width: '100%',
  textAlign: 'left',
}

const bottomLinkStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 10,
  padding: '9px 10px', borderRadius: 8,
  textDecoration: 'none', fontSize: '.82rem',
  color: 'var(--text-2)', transition: 'background .15s',
}
