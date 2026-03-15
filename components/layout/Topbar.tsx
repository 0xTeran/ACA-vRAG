'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Sun, Moon, ChevronDown, LogOut } from 'lucide-react'
import { useState } from 'react'
import { Logo } from '@/components/ui/Logo'
import { useTheme } from './ThemeProvider'
import { useAuth } from '@/hooks/useAuth'
import { useAuthModal } from '@/components/auth/AuthModal'

export function Topbar() {
  const pathname = usePathname()
  const { theme, toggle } = useTheme()
  const { user, isAdmin, logout } = useAuth()
  const { open: openAuth } = useAuthModal()
  const [menuOpen, setMenuOpen] = useState(false)

  const navPill = (href: string, label: string) => {
    const active = pathname === href || (href !== '/' && pathname.startsWith(href))
    return (
      <Link
        href={href}
        style={{
          background: active ? 'rgba(128,128,128,0.15)' : 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: active ? 'var(--text)' : 'var(--text-3)',
          fontFamily: 'inherit',
          fontSize: '.82rem',
          fontWeight: 500,
          padding: '6px 14px',
          borderRadius: '99px',
          textDecoration: 'none',
          transition: 'background .15s, color .15s',
        }}
      >
        {label}
      </Link>
    )
  }

  return (
    <header style={{
      position: 'fixed', top: 0, left: 0, right: 0, height: 'var(--topbar-h)',
      display: 'flex', alignItems: 'center', padding: '0 20px', zIndex: 100,
      borderBottom: '1px solid var(--topbar-border)',
      background: 'var(--topbar-bg)', backdropFilter: 'blur(16px)',
    }}>
      <Link href="/" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
        <Logo height={22} />
      </Link>

      <nav style={{ display: 'flex', gap: 4, marginLeft: 'auto' }}>
        {navPill('/historial', 'Historial')}
        {user && isAdmin && navPill('/importar', 'Importar')}
      </nav>

      {/* Auth */}
      {user ? (
        <div style={{ position: 'relative', marginLeft: 12 }}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            style={{
              display: 'flex', alignItems: 'center', gap: 7,
              background: 'rgba(128,128,128,0.09)', border: '1px solid var(--border)',
              borderRadius: '99px', padding: '5px 12px 5px 6px',
              cursor: 'pointer', fontSize: '.76rem', color: 'var(--text-2)',
              transition: 'all .15s',
            }}
          >
            <span style={{
              width: 20, height: 20, borderRadius: '50%',
              background: 'var(--text)', color: 'var(--bg)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '.65rem', fontWeight: 700,
            }}>
              {user.email[0].toUpperCase()}
            </span>
            {user.email.length > 20 ? user.email.slice(0, 18) + '…' : user.email}
            <ChevronDown size={12} />
          </button>

          {menuOpen && (
            <div
              onClick={() => setMenuOpen(false)}
              style={{
                position: 'fixed', inset: 0, zIndex: 149,
              }}
            />
          )}

          {menuOpen && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 8px)', right: 0, zIndex: 150,
              background: 'var(--card)', border: '1px solid var(--border-2)',
              borderRadius: 10, padding: 8, minWidth: 180,
              boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            }}>
              <div style={{ padding: '8px 10px 12px', borderBottom: '1px solid var(--border)' }}>
                <div style={{ fontSize: '.78rem', fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>{user.email}</div>
                <div style={{ fontSize: '.72rem', color: 'var(--text-3)' }}>Beta gratuito</div>
              </div>
              <button
                onClick={() => { logout(); setMenuOpen(false) }}
                style={{
                  width: '100%', background: 'none', border: 'none', cursor: 'pointer',
                  textAlign: 'left', padding: '9px 10px', color: 'var(--text-2)',
                  fontFamily: 'inherit', fontSize: '.79rem', borderRadius: 6,
                  marginTop: 4, display: 'flex', alignItems: 'center', gap: 8,
                  transition: 'background .15s',
                }}
                onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(128,128,128,0.1)')}
                onMouseOut={(e) => (e.currentTarget.style.background = 'none')}
              >
                <LogOut size={13} /> Cerrar sesión
              </button>
            </div>
          )}
        </div>
      ) : (
        <button
          onClick={() => openAuth()}
          style={{
            marginLeft: 12, padding: '6px 16px', borderRadius: '99px',
            background: 'var(--text)', color: 'var(--bg)',
            border: 'none', cursor: 'pointer', fontFamily: 'inherit',
            fontSize: '.8rem', fontWeight: 600, transition: 'opacity .15s',
          }}
          onMouseOver={(e) => (e.currentTarget.style.opacity = '0.85')}
          onMouseOut={(e) => (e.currentTarget.style.opacity = '1')}
        >
          Login
        </button>
      )}

      {/* Theme toggle */}
      <button
        onClick={toggle}
        style={{
          marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-3)', padding: 7, display: 'flex',
          alignItems: 'center', borderRadius: '50%', transition: 'background .15s',
        }}
        onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(128,128,128,0.1)')}
        onMouseOut={(e) => (e.currentTarget.style.background = 'none')}
        title="Cambiar tema"
      >
        {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
      </button>
    </header>
  )
}
