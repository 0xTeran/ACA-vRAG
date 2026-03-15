'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { PenSquare, PanelLeftClose, PanelLeft, Menu, Clock, Search, Database, Settings, MoreHorizontal, Trash2, CheckCircle, XCircle, Microscope, X } from 'lucide-react'
import { Logo } from '@/components/ui/Logo'
import { useAppStore } from '@/store/appStore'
import { ClasificacionRecord } from '@/types'

function timeAgo(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000)
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
  if (r.subpartida && ficha) return `${r.subpartida} — ${ficha.slice(0, 35)}`
  return ficha.slice(0, 50) || r.subpartida || 'Sin título'
}

function useIsMobile() {
  const [mobile, setMobile] = useState(false)
  useEffect(() => {
    const check = () => setMobile(window.innerWidth < 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])
  return mobile
}

// Global toggle for mobile sidebar (called from Topbar)
let _openMobileSidebar: (() => void) | null = null
export function openMobileSidebar() { _openMobileSidebar?.() }

export function Sidebar() {
  const [desktopOpen, setDesktopOpen] = useState(true)
  const [mobileOpen, setMobileOpen] = useState(false)

  // Register global toggle
  useEffect(() => {
    _openMobileSidebar = () => setMobileOpen(true)
    return () => { _openMobileSidebar = null }
  }, [])
  const [records, setRecords] = useState<ClasificacionRecord[]>([])
  const [search, setSearch] = useState('')
  const [menuId, setMenuId] = useState<string | null>(null)
  const [hoverId, setHoverId] = useState<string | null>(null)
  const pathname = usePathname()
  const router = useRouter()
  const { isAdmin } = useAppStore()
  const menuRef = useRef<HTMLDivElement>(null)
  const isMobile = useIsMobile()

  const refreshHistorial = useCallback(() => {
    fetch('/api/historial').then(r => r.json()).then(d => setRecords(d.registros ?? [])).catch(() => {})
  }, [])

  useEffect(() => { refreshHistorial() }, [pathname, refreshHistorial])

  // Listen for new classification events from ClasificarPage
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail?.temp) {
        // Add temporary entry at top immediately
        setRecords(prev => [{
          id: detail.id,
          ficha_tecnica: detail.ficha_tecnica,
          subpartida: '',
          estado: 'pendiente' as const,
          costo_cop: 0,
          costo_usd: 0,
          tokens: 0,
          tiempo_segundos: 0,
          created_at: new Date().toISOString(),
        }, ...prev])
      } else {
        // Real result arrived, refresh from API
        refreshHistorial()
      }
    }
    window.addEventListener('aca:clasificacion', handler)
    return () => window.removeEventListener('aca:clasificacion', handler)
  }, [refreshHistorial])

  // Close mobile sidebar on navigation
  useEffect(() => { setMobileOpen(false) }, [pathname])

  useEffect(() => {
    if (!menuId) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuId(null)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuId])

  const filtered = search.trim()
    ? records.filter(r => {
        const s = search.trim().toLowerCase()
        return (r.ficha_tecnica ?? '').toLowerCase().includes(s) || (r.subpartida ?? '').includes(s)
      })
    : records

  const groups = groupByDate(filtered)
  const activeId = pathname.match(/^\/c\/([a-f0-9-]+)/i)?.[1]

  const deleteRecord = async (id: string) => {
    setMenuId(null)
    try {
      await fetch('/api/estado', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id, estado: 'eliminada', notas: '' }) })
      setRecords(prev => prev.filter(r => r.id !== id))
      if (activeId === id) router.push('/')
    } catch {}
  }

  const setEstado = async (id: string, estado: string) => {
    setMenuId(null)
    try {
      await fetch('/api/estado', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id, estado, notas: '' }) })
      setRecords(prev => prev.map(r => r.id === id ? { ...r, estado: estado as ClasificacionRecord['estado'] } : r))
    } catch {}
  }

  // ── Sidebar content (shared between desktop and mobile) ──
  const sidebarContent = (
    <>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 12px 0' }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}><Logo height={20} /></Link>
        <button onClick={() => isMobile ? setMobileOpen(false) : setDesktopOpen(false)} style={iconBtnStyle}>
          {isMobile ? <X size={18} /> : <PanelLeftClose size={16} />}
        </button>
      </div>

      {/* Action buttons */}
      <div style={{ padding: '12px 12px 8px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        <button onClick={() => setSearch(search ? '' : ' ')} style={sideBtnStyle}
          onMouseOver={e => e.currentTarget.style.background = 'rgba(128,128,128,.1)'}
          onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
          <Search size={16} /> Buscar
        </button>
        <Link href="/" onClick={() => setMobileOpen(false)} style={{ ...sideBtnStyle, textDecoration: 'none' }}
          onMouseOver={e => e.currentTarget.style.background = 'rgba(128,128,128,.1)'}
          onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
          <PenSquare size={16} /> Nueva clasificación
        </Link>
      </div>

      {/* Search input */}
      {search !== '' && (
        <div style={{ padding: '0 12px 8px' }}>
          <input autoFocus value={search === ' ' ? '' : search}
            onChange={e => setSearch(e.target.value || ' ')}
            onBlur={() => { if (search.trim() === '') setSearch('') }}
            placeholder="Buscar por producto o subpartida..."
            style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '8px 12px', outline: 'none', color: 'var(--text)', fontFamily: 'inherit', fontSize: '.8rem' }}
          />
        </div>
      )}

      {/* History list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px' }}>
        {groups.map((group) => (
          <div key={group.label} style={{ marginBottom: 4 }}>
            <div style={{ fontSize: '.68rem', fontWeight: 600, color: 'var(--text-3)', padding: '10px 8px 4px', textTransform: 'uppercase', letterSpacing: '.04em' }}>
              {group.label}
            </div>
            {group.items.map((r) => (
              <div key={r.id} style={{ position: 'relative' }}
                onMouseEnter={() => setHoverId(r.id)} onMouseLeave={() => setHoverId(null)}>
                <Link href={`/c/${r.id}`} onClick={() => setMobileOpen(false)} title={r.ficha_tecnica?.slice(0, 300) || ''} style={{
                  display: 'flex', flexDirection: 'column', padding: '8px 10px', borderRadius: 8,
                  textDecoration: 'none', fontSize: '.82rem', lineHeight: 1.4,
                  color: activeId === r.id ? 'var(--text)' : 'var(--text-2)',
                  background: activeId === r.id ? 'rgba(128,128,128,.12)' : 'transparent',
                  transition: 'background .15s', gap: 2,
                }}
                  onMouseOver={e => { if (activeId !== r.id) e.currentTarget.style.background = 'rgba(128,128,128,.06)' }}
                  onMouseOut={e => { if (activeId !== r.id) e.currentTarget.style.background = 'transparent' }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: 20 }}>
                    {getTitle(r)}
                  </span>
                  {activeId === r.id && r.ficha_tecnica && (
                    <span style={{
                      fontSize: '.7rem', color: 'var(--text-3)', lineHeight: 1.35,
                      display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' as const,
                      overflow: 'hidden', whiteSpace: 'normal',
                    }}>
                      {r.ficha_tecnica.slice(0, 200)}
                    </span>
                  )}
                </Link>

                {(hoverId === r.id || menuId === r.id) && (
                  <button onClick={e => { e.preventDefault(); e.stopPropagation(); setMenuId(menuId === r.id ? null : r.id) }}
                    style={{ position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)', background: 'var(--sidebar-bg, var(--bg))', border: 'none', cursor: 'pointer', color: 'var(--text-3)', padding: 4, borderRadius: 6, display: 'flex' }}
                    onMouseOver={e => e.currentTarget.style.color = 'var(--text)'} onMouseOut={e => e.currentTarget.style.color = 'var(--text-3)'}>
                    <MoreHorizontal size={15} />
                  </button>
                )}

                {menuId === r.id && (
                  <div ref={menuRef} style={{ position: 'absolute', right: 0, top: '100%', zIndex: 300, background: 'var(--card)', border: '1px solid var(--border-2)', borderRadius: 10, padding: 6, minWidth: 180, boxShadow: '0 8px 32px rgba(0,0,0,.4)' }}>
                    <button onClick={() => setEstado(r.id, 'aprobada')} style={menuItemStyle} onMouseOver={e => e.currentTarget.style.background = 'rgba(128,128,128,.1)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
                      <CheckCircle size={14} style={{ color: 'var(--green)' }} /> Aprobar
                    </button>
                    <button onClick={() => setEstado(r.id, 'rechazada')} style={menuItemStyle} onMouseOver={e => e.currentTarget.style.background = 'rgba(128,128,128,.1)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
                      <XCircle size={14} style={{ color: 'var(--red)' }} /> Rechazar
                    </button>
                    <button onClick={() => setEstado(r.id, 'investigar')} style={menuItemStyle} onMouseOver={e => e.currentTarget.style.background = 'rgba(128,128,128,.1)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
                      <Microscope size={14} style={{ color: 'var(--yellow)' }} /> Investigar
                    </button>
                    <div style={{ height: 1, background: 'var(--border)', margin: '4px 0' }} />
                    <button onClick={() => deleteRecord(r.id)} style={{ ...menuItemStyle, color: 'var(--red)' }} onMouseOver={e => e.currentTarget.style.background = 'rgba(248,113,113,.08)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
                      <Trash2 size={14} /> Eliminar
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
        {records.length === 0 && (
          <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-3)', fontSize: '.82rem' }}>No hay clasificaciones aún</div>
        )}
      </div>

      {/* Bottom */}
      <div style={{ borderTop: '1px solid var(--border)', padding: 8 }}>
        <Link href="/historial" onClick={() => setMobileOpen(false)} style={bottomLinkStyle}
          onMouseOver={e => e.currentTarget.style.background = 'rgba(128,128,128,.08)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
          <Clock size={14} /> Historial completo
        </Link>
        {isAdmin && (
          <>
            <Link href="/importar" onClick={() => setMobileOpen(false)} style={bottomLinkStyle}
              onMouseOver={e => e.currentTarget.style.background = 'rgba(128,128,128,.08)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
              <Database size={14} /> Importar BD
            </Link>
            <Link href="/config" onClick={() => setMobileOpen(false)} style={bottomLinkStyle}
              onMouseOver={e => e.currentTarget.style.background = 'rgba(128,128,128,.08)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
              <Settings size={14} /> Configuración
            </Link>
          </>
        )}
      </div>
    </>
  )

  // ── MOBILE: hamburger button + overlay sidebar ──
  if (isMobile) {
    return (
      <>
        {/* Mobile hamburger is rendered inside Topbar via window event */}

        {/* Overlay */}
        {mobileOpen && (
          <>
            <div onClick={() => setMobileOpen(false)} style={{
              position: 'fixed', inset: 0, zIndex: 199,
              background: 'rgba(0,0,0,.5)', backdropFilter: 'blur(2px)',
            }} />
            <div style={{
              position: 'fixed', top: 0, left: 0, bottom: 0, width: 300, zIndex: 250,
              display: 'flex', flexDirection: 'column',
              background: 'var(--sidebar-bg, var(--bg))',
              boxShadow: '4px 0 24px rgba(0,0,0,.3)',
            }}>
              {sidebarContent}
            </div>
          </>
        )}

        <style>{`:root { --sidebar-w: 0px; }`}</style>
      </>
    )
  }

  // ── DESKTOP: collapsed ──
  if (!desktopOpen) {
    return (
      <div style={{
        position: 'fixed', top: 0, left: 0, bottom: 0, width: 50, zIndex: 200,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        paddingTop: 14, gap: 8,
        background: 'var(--sidebar-bg, var(--bg))', borderRight: '1px solid var(--border)',
      }}>
        <button onClick={() => setDesktopOpen(true)} style={iconBtnStyle}><PanelLeft size={18} /></button>
        <Link href="/" style={iconBtnStyle}><PenSquare size={18} /></Link>
      </div>
    )
  }

  // ── DESKTOP: open ──
  return (
    <>
      <div style={{
        position: 'fixed', top: 0, left: 0, bottom: 0, width: 280, zIndex: 200,
        display: 'flex', flexDirection: 'column',
        background: 'var(--sidebar-bg, var(--bg))', borderRight: '1px solid var(--border)',
      }}>
        {sidebarContent}
      </div>
      <style>{`:root { --sidebar-w: 280px; }`}</style>
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
  fontWeight: 400, transition: 'background .15s', width: '100%', textAlign: 'left',
}

const menuItemStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 10, width: '100%',
  padding: '8px 10px', borderRadius: 7, background: 'transparent',
  border: 'none', cursor: 'pointer', color: 'var(--text)',
  fontFamily: 'inherit', fontSize: '.82rem', transition: 'background .15s', textAlign: 'left',
}

const bottomLinkStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 10,
  padding: '9px 10px', borderRadius: 8,
  textDecoration: 'none', fontSize: '.82rem',
  color: 'var(--text-2)', transition: 'background .15s',
}
