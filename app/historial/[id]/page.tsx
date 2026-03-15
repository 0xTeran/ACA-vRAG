'use client'

import { use } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { ClasificacionRecord } from '@/types'

export default function DetallePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

  const { data: record, isLoading } = useQuery({
    queryKey: ['clasificacion', id],
    queryFn: (): Promise<ClasificacionRecord> =>
      fetch(`/api/clasificacion/${id}`).then((r) => r.json()),
  })

  if (isLoading) return <div style={{ padding: 32, color: 'var(--text-3)' }}>Cargando…</div>
  if (!record) return <div style={{ padding: 32, color: 'var(--red)' }}>No encontrado.</div>

  const card = (title: string, html: string) => (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border-2)', borderRadius: 'var(--r)', overflow: 'hidden', marginBottom: 12 }}>
      <div style={{ padding: '12px 16px 10px', borderBottom: '1px solid var(--border)', fontSize: '.78rem', fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.04em' }}>
        {title}
      </div>
      <div className="prose" style={{ padding: '14px 16px', fontSize: '.88rem' }} dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 20px' }}>
      <Link href="/historial" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--text-3)', textDecoration: 'none', fontSize: '.84rem', marginBottom: 20 }}>
        <ArrowLeft size={13} /> Historial
      </Link>

      <h1 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 4 }}>{record.subpartida}</h1>
      <p style={{ fontSize: '.84rem', color: 'var(--text-2)', marginBottom: 20 }}>{record.descripcion}</p>

      {record.investigacion_html && card('Investigación', record.investigacion_html)}
      {record.clasificacion_html && card('Clasificación arancelaria', record.clasificacion_html)}
      {record.validacion_html && card('Validación', record.validacion_html)}

      {record.notas && (
        <div style={{ background: 'var(--card)', border: '1px solid var(--border-2)', borderRadius: 'var(--r)', padding: '12px 16px', marginBottom: 12 }}>
          <div style={{ fontSize: '.78rem', fontWeight: 600, color: 'var(--text-3)', marginBottom: 6 }}>Notas</div>
          <p style={{ fontSize: '.86rem', color: 'var(--text-2)' }}>{record.notas}</p>
        </div>
      )}
    </div>
  )
}
