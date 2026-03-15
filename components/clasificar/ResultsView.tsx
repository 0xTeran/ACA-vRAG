'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import { CheckCircle, XCircle, Search, Clock, DollarSign, Zap, ExternalLink } from 'lucide-react'
import { ClasificarResult } from '@/types'

export function ResultsView({ result }: { result: ClasificarResult }) {
  const [estado, setEstado] = useState<string | null>(null)
  const [notas, setNotas] = useState('')
  const [chatInput, setChatInput] = useState('')
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([])
  const [chatLoading, setChatLoading] = useState(false)
  const [savingEstado, setSavingEstado] = useState(false)

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

  const sendChat = async () => {
    if (!chatInput.trim() || chatLoading) return
    const msg = chatInput.trim()
    setChatInput('')
    const newHistory = [...chatHistory, { role: 'user', content: msg }]
    setChatHistory(newHistory)
    setChatLoading(true)
    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pregunta: msg,
          historial: newHistory,
          contexto: {
            ficha_tecnica: result.ficha_tecnica,
            clasificacion: result.clasificacion_raw,
            validacion: result.validacion_raw,
            investigacion: result.investigacion_raw,
          },
        }),
      })
      const d = await r.json()
      setChatHistory([...newHistory, { role: 'assistant', content: d.respuesta ?? d.error ?? 'Sin respuesta' }])
    } finally {
      setChatLoading(false)
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
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 20px 24px' }}>

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

      {/* Ficha técnica */}
      {result.ficha_tecnica && (
        <div style={{ background: 'var(--card)', border: '1px solid var(--border-2)', borderRadius: 'var(--r)', padding: '12px 16px', marginBottom: 12, fontSize: '.85rem', color: 'var(--text-2)', whiteSpace: 'pre-wrap' }}>
          <span style={{ fontSize: '.72rem', fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.04em', display: 'block', marginBottom: 6 }}>Ficha técnica</span>
          {result.ficha_tecnica}
        </div>
      )}

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

      {/* Decision */}
      {!estado && (
        <div style={{ background: 'var(--card)', border: '1px solid var(--border-2)', borderRadius: 'var(--r)', padding: '16px', marginBottom: 12 }}>
          <div style={{ fontSize: '.8rem', fontWeight: 600, color: 'var(--text-3)', marginBottom: 10 }}>¿Esta clasificación es correcta?</div>
          <textarea
            value={notas}
            onChange={(e) => setNotas(e.target.value)}
            placeholder="Notas opcionales…"
            style={{ width: '100%', background: 'var(--card-2)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', color: 'var(--text)', fontFamily: 'inherit', fontSize: '.84rem', resize: 'none', outline: 'none', marginBottom: 10 }}
            rows={2}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => saveEstado('aprobada')} disabled={savingEstado} style={{ flex: 1, padding: '9px', borderRadius: 8, background: 'rgba(74,222,128,.1)', border: '1px solid rgba(74,222,128,.25)', color: 'var(--green)', cursor: 'pointer', fontFamily: 'inherit', fontSize: '.82rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <CheckCircle size={13} /> Aprobar
            </button>
            <button onClick={() => saveEstado('rechazada')} disabled={savingEstado} style={{ flex: 1, padding: '9px', borderRadius: 8, background: 'rgba(248,113,113,.1)', border: '1px solid rgba(248,113,113,.25)', color: 'var(--red)', cursor: 'pointer', fontFamily: 'inherit', fontSize: '.82rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <XCircle size={13} /> Rechazar
            </button>
            <button onClick={() => saveEstado('investigar')} disabled={savingEstado} style={{ flex: 1, padding: '9px', borderRadius: 8, background: 'rgba(251,191,36,.1)', border: '1px solid rgba(251,191,36,.25)', color: 'var(--yellow)', cursor: 'pointer', fontFamily: 'inherit', fontSize: '.82rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <Search size={13} /> Investigar
            </button>
          </div>
        </div>
      )}

      {estado && (
        <div style={{
          padding: '10px 14px', borderRadius: 8, marginBottom: 12,
          background: estado === 'aprobada' ? 'rgba(74,222,128,.08)' : estado === 'rechazada' ? 'rgba(248,113,113,.08)' : 'rgba(251,191,36,.08)',
          border: `1px solid ${estado === 'aprobada' ? 'rgba(74,222,128,.2)' : estado === 'rechazada' ? 'rgba(248,113,113,.2)' : 'rgba(251,191,36,.2)'}`,
          color: estado === 'aprobada' ? 'var(--green)' : estado === 'rechazada' ? 'var(--red)' : 'var(--yellow)',
          fontSize: '.84rem',
        }}>
          Clasificación marcada como <strong>{estado}</strong>
        </div>
      )}

      {/* Chat */}
      <div style={{ background: 'var(--card)', border: '1px solid var(--border-2)', borderRadius: 'var(--r)', padding: '14px 16px', marginBottom: 12 }}>
        <div style={{ fontSize: '.78rem', fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 10 }}>Consultar sobre esta clasificación</div>
        {chatHistory.map((m, i) => (
          <div key={i} style={{ marginBottom: 10 }}>
            <div style={{ fontSize: '.75rem', color: 'var(--text-3)', marginBottom: 3 }}>{m.role === 'user' ? 'Tú' : 'ACA'}</div>
            {m.role === 'assistant'
              ? <div className="prose" style={{ fontSize: '.86rem' }}><ReactMarkdown rehypePlugins={[rehypeSanitize]}>{m.content}</ReactMarkdown></div>
              : <div style={{ fontSize: '.86rem', color: 'var(--text-2)' }}>{m.content}</div>
            }
          </div>
        ))}
        {chatLoading && <div style={{ fontSize: '.84rem', color: 'var(--text-3)' }}>Pensando…</div>}
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendChat()}
            placeholder="¿Tienes alguna duda?"
            style={{ flex: 1, background: 'var(--card-2)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', color: 'var(--text)', fontFamily: 'inherit', fontSize: '.84rem', outline: 'none' }}
          />
          <button onClick={sendChat} disabled={chatLoading} style={{ background: 'var(--text)', color: 'var(--bg)', border: 'none', borderRadius: 8, padding: '8px 14px', cursor: 'pointer', fontFamily: 'inherit', fontSize: '.82rem' }}>
            Enviar
          </button>
        </div>
      </div>

    </div>
  )
}
