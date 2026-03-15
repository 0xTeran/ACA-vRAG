'use client'

import { useState } from 'react'
import { CheckCircle, XCircle, Search, Clock, DollarSign, Zap, ExternalLink } from 'lucide-react'
import { ClasificarResult } from '@/types'

export function ResultsView({ result }: { result: ClasificarResult }) {
  const [estado, setEstado] = useState<string | null>(null)
  const [notas, setNotas] = useState('')
  const [savingEstado, setSavingEstado] = useState(false)
  const [showNotas, setShowNotas] = useState(false)

  const saveEstado = async (e: string) => {
    setSavingEstado(true)
    try {
      await fetch('/api/estado', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: result.id, estado: e, notas }),
      })
      setEstado(e)
    } finally {
      setSavingEstado(false)
    }
  }

  const card = (title: string, html: string) => (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border-2)', borderRadius: 'var(--r)', overflow: 'hidden', marginBottom: 12 }}>
      <div style={{ padding: '12px 16px 10px', borderBottom: '1px solid var(--border)', fontSize: '.78rem', fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.04em' }}>
        {title}
      </div>
      <div className="prose" style={{ padding: '14px 16px', fontSize: '.88rem' }} dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )

  return (
    <div>
      {/* Metrics */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
        {[
          { icon: <Clock size={11} />, val: `${result.tiempo_segundos}s` },
          { icon: <DollarSign size={11} />, val: `$${Number(result.costo_cop).toLocaleString('es-CO')} COP` },
          { icon: <DollarSign size={11} />, val: `$${Number(result.costo_usd).toFixed(4)} USD` },
          { icon: <Zap size={11} />, val: `${Number(result.tokens).toLocaleString()} tok` },
        ].map((m, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 5,
            background: 'var(--card)', border: '1px solid var(--border)',
            borderRadius: 99, padding: '4px 10px', fontSize: '.75rem', color: 'var(--text-3)',
          }}>
            {m.icon} {m.val}
          </div>
        ))}
      </div>

      {card('Investigación', result.investigacion_html)}
      {card('Clasificación arancelaria', result.clasificacion_html)}
      {card('Validación', result.validacion_html)}

      {/* Fuentes */}
      {result.fuentes?.length > 0 && (
        <div style={{ background: 'var(--card)', border: '1px solid var(--border-2)', borderRadius: 'var(--r)', padding: '14px 16px', marginBottom: 12 }}>
          <div style={{ fontSize: '.78rem', fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 10 }}>Fuentes</div>
          {result.fuentes.map((f, i) => (
            <div key={i} style={{ marginBottom: 10, paddingBottom: 10, borderBottom: i < result.fuentes.length - 1 ? '1px solid var(--border)' : 'none' }}>
              <a href={f.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--blue)', fontSize: '.84rem', display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none' }}>
                {f.title} <ExternalLink size={11} />
              </a>
              {f.snippet && <p style={{ fontSize: '.78rem', color: 'var(--text-3)', marginTop: 3 }}>{f.snippet}</p>}
            </div>
          ))}
        </div>
      )}

      {/* Decision - floating style */}
      {!estado && (
        <div style={{
          background: 'var(--card)', border: '1px solid var(--border-2)',
          borderRadius: 14, padding: '10px 14px', marginBottom: 12,
        }}>
          {showNotas && (
            <textarea
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              placeholder="Notas opcionales…"
              style={{ width: '100%', background: 'var(--card-2)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', color: 'var(--text)', fontFamily: 'inherit', fontSize: '.82rem', resize: 'none', outline: 'none', marginBottom: 8 }}
              rows={2}
            />
          )}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <button onClick={() => saveEstado('aprobada')} disabled={savingEstado} style={{ flex: 1, padding: '7px', borderRadius: 8, background: 'rgba(74,222,128,.08)', border: '1px solid rgba(74,222,128,.2)', color: 'var(--green)', cursor: 'pointer', fontFamily: 'inherit', fontSize: '.78rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
              <CheckCircle size={12} /> Aprobar
            </button>
            <button onClick={() => saveEstado('rechazada')} disabled={savingEstado} style={{ flex: 1, padding: '7px', borderRadius: 8, background: 'rgba(248,113,113,.08)', border: '1px solid rgba(248,113,113,.2)', color: 'var(--red)', cursor: 'pointer', fontFamily: 'inherit', fontSize: '.78rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
              <XCircle size={12} /> Rechazar
            </button>
            <button onClick={() => saveEstado('investigar')} disabled={savingEstado} style={{ flex: 1, padding: '7px', borderRadius: 8, background: 'rgba(251,191,36,.08)', border: '1px solid rgba(251,191,36,.2)', color: 'var(--yellow)', cursor: 'pointer', fontFamily: 'inherit', fontSize: '.78rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
              <Search size={12} /> Investigar
            </button>
            {!showNotas && (
              <button onClick={() => setShowNotas(true)} style={{ padding: '7px 10px', borderRadius: 8, background: 'none', border: '1px solid var(--border)', color: 'var(--text-3)', cursor: 'pointer', fontFamily: 'inherit', fontSize: '.72rem' }}>
                + Nota
              </button>
            )}
          </div>
        </div>
      )}

      {estado && (
        <div style={{
          padding: '8px 14px', borderRadius: 8, marginBottom: 12,
          background: estado === 'aprobada' ? 'rgba(74,222,128,.08)' : estado === 'rechazada' ? 'rgba(248,113,113,.08)' : 'rgba(251,191,36,.08)',
          border: `1px solid ${estado === 'aprobada' ? 'rgba(74,222,128,.2)' : estado === 'rechazada' ? 'rgba(248,113,113,.2)' : 'rgba(251,191,36,.2)'}`,
          color: estado === 'aprobada' ? 'var(--green)' : estado === 'rechazada' ? 'var(--red)' : 'var(--yellow)',
          fontSize: '.82rem',
        }}>
          Clasificación marcada como <strong>{estado}</strong>
        </div>
      )}
    </div>
  )
}
