'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { ClasificacionRecord } from '@/types'

const ESTADOS = ['todas', 'pendiente', 'aprobada', 'rechazada', 'investigar']

const estadoColor: Record<string, string> = {
  pendiente: 'var(--text-3)',
  aprobada: 'var(--green)',
  rechazada: 'var(--red)',
  investigar: 'var(--yellow)',
}

export default function HistorialPage() {
  const [filtro, setFiltro] = useState('todas')

  const { data, isLoading } = useQuery({
    queryKey: ['historial', filtro],
    queryFn: () =>
      fetch(`/api/historial?estado=${filtro}`).then((r) => r.json()),
  })

  const registros: ClasificacionRecord[] = data?.registros ?? []

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 20px' }}>
      <h1 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 20 }}>Historial</h1>

      {/* Filtros */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
        {ESTADOS.map((e) => (
          <button
            key={e}
            onClick={() => setFiltro(e)}
            style={{
              padding: '5px 14px', borderRadius: 99, border: 'none', cursor: 'pointer',
              fontFamily: 'inherit', fontSize: '.8rem', fontWeight: 500, transition: 'all .15s',
              background: filtro === e ? 'rgba(128,128,128,0.2)' : 'transparent',
              color: filtro === e ? 'var(--text)' : 'var(--text-3)',
            }}
          >
            {e.charAt(0).toUpperCase() + e.slice(1)}
          </button>
        ))}
      </div>

      {isLoading && <div style={{ color: 'var(--text-3)', fontSize: '.88rem' }}>Cargando…</div>}

      {!isLoading && registros.length === 0 && (
        <div style={{ color: 'var(--text-3)', fontSize: '.88rem', textAlign: 'center', padding: '48px 0' }}>
          No hay clasificaciones{filtro !== 'todas' ? ` con estado "${filtro}"` : ''}.
        </div>
      )}

      {/* Tabla */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {registros.map((r) => (
          <Link
            key={r.id}
            href={`/historial/${r.id}`}
            style={{
              display: 'grid', gridTemplateColumns: '1fr auto auto',
              alignItems: 'center', gap: 12,
              background: 'var(--card)', border: '1px solid var(--border)',
              borderRadius: 10, padding: '12px 16px', textDecoration: 'none',
              transition: 'border-color .15s',
            }}
            onMouseOver={(e) => (e.currentTarget.style.borderColor = 'var(--border-2)')}
            onMouseOut={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
          >
            <div>
              <div style={{ fontSize: '.88rem', color: 'var(--text)', fontWeight: 500, marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {(r.ficha_tecnica ?? r.fuente_nombre ?? '').slice(0, 80) || 'Sin descripción'}
              </div>
              <div style={{ fontSize: '.78rem', color: 'var(--text-3)' }}>
                {r.subpartida} · {new Date(r.created_at).toLocaleDateString('es-CO')}
              </div>
            </div>
            <div style={{ fontSize: '.76rem', color: estadoColor[r.estado] ?? 'var(--text-3)', fontWeight: 500, whiteSpace: 'nowrap' }}>
              {r.estado}
            </div>
            <div style={{ fontSize: '.76rem', color: 'var(--text-3)', whiteSpace: 'nowrap' }}>
              {r.tiempo_segundos}s
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
