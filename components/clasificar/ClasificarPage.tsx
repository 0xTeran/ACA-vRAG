'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { Send, Paperclip, X } from 'lucide-react'
import { Logo } from '@/components/ui/Logo'
import { LoadingCard } from './LoadingCard'
import { ResultsView } from './ResultsView'
import { useAuthModal } from '@/components/auth/AuthModal'
import { useAppStore } from '@/store/appStore'
import { ClasificarResult } from '@/types'

type Step = { label: string; status: 'idle' | 'running' | 'done' }

type Message =
  | { type: 'user'; text: string; fileName?: string }
  | { type: 'loading'; steps: Step[] }
  | { type: 'result'; result: ClasificarResult }
  | { type: 'error'; text: string }

const extractUrl = (t: string): string | null => {
  const m = t.match(/https?:\/\/\S+/)
  return m ? m[0] : null
}

const INITIAL_STEPS: Step[] = [
  { label: 'Investigador — pendiente', status: 'idle' },
  { label: 'Clasificador — pendiente', status: 'idle' },
  { label: 'Validador — pendiente', status: 'idle' },
]

export function ClasificarPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])
  const { open: openAuth } = useAuthModal()
  const { anonUsed, anonLimit, user } = useAppStore()

  const isEmpty = messages.length === 0

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const updateLoadingSteps = (updater: (steps: Step[]) => Step[]) => {
    setMessages((prev) => {
      const idx = prev.findLastIndex((m) => m.type === 'loading')
      if (idx === -1) return prev
      const msg = prev[idx] as { type: 'loading'; steps: Step[] }
      const next = [...prev]
      next[idx] = { ...msg, steps: updater(msg.steps) }
      return next
    })
  }

  const clearTimers = () => { timers.current.forEach(clearTimeout); timers.current = [] }

  const detectInputType = (t: string, f: File | null) => {
    if (f) return 'archivo'
    if (extractUrl(t)) return 'url'
    return 'texto'
  }

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    const ta = e.target
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
  }

  const handleFile = (f: File) => { setFile(f) }

  const submit = useCallback(async () => {
    if (loading || (!text.trim() && !file)) return

    const inputType = detectInputType(text, file)
    const userText = file ? file.name : text.trim()

    // Add user bubble and clear input immediately
    setMessages((prev) => [...prev, {
      type: 'user',
      text: userText,
      fileName: file ? file.name : undefined,
    }])
    setText('')
    setFile(null)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    // Add loading bubble
    const initialSteps: Step[] = [
      { label: 'Investigador — buscando resoluciones DIAN + Perplexity', status: 'running' },
      { label: 'Clasificador — pendiente', status: 'idle' },
      { label: 'Validador — pendiente', status: 'idle' },
    ]
    setMessages((prev) => [...prev, { type: 'loading', steps: initialSteps }])
    setLoading(true)

    clearTimers()
    timers.current.push(setTimeout(() => {
      updateLoadingSteps((steps) => steps.map((s, i) =>
        i === 0 ? { ...s, status: 'done', label: 'Investigador — completado' } :
        i === 1 ? { ...s, status: 'running', label: 'Clasificador — analizando con base de conocimiento' } : s
      ))
    }, 22000))
    timers.current.push(setTimeout(() => {
      updateLoadingSteps((steps) => steps.map((s, i) =>
        i === 1 ? { ...s, status: 'done', label: 'Clasificador — completado' } :
        i === 2 ? { ...s, status: 'running', label: 'Validador — verificando subpartida' } : s
      ))
    }, 46000))

    try {
      const fd = new FormData()
      if (file) {
        fd.append('input_type', 'archivo')
        fd.append('ficha_archivo', file)
      } else if (inputType === 'url') {
        fd.append('input_type', 'url')
        fd.append('ficha_url', extractUrl(text.trim()) ?? text.trim())
      } else {
        fd.append('input_type', 'texto')
        fd.append('ficha_texto', text.trim())
      }

      const r = await fetch('/api/clasificar', { method: 'POST', body: fd })
      const d = await r.json()
      clearTimers()

      // Remove loading bubble
      setMessages((prev) => prev.filter((m) => m.type !== 'loading'))

      if (r.status === 402 || d.error === 'limit_reached') {
        openAuth(`Agotaste tus ${anonLimit} análisis gratuitos. Regístrate gratis para continuar.`)
        return
      }

      if (!r.ok) {
        setMessages((prev) => [...prev, { type: 'error', text: d.error ?? 'Error desconocido' }])
        return
      }

      setMessages((prev) => [...prev, { type: 'result', result: d }])
    } catch {
      clearTimers()
      setMessages((prev) => prev.filter((m) => m.type !== 'loading'))
      setMessages((prev) => [...prev, { type: 'error', text: 'Error de conexión. Intenta de nuevo.' }])
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, text, file, anonLimit, openAuth])

  return (
    <div style={{
      position: 'fixed', inset: 0, paddingTop: 'var(--topbar-h)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Chat scroll area */}
      <div style={{ flex: 1, overflowY: 'auto', overscrollBehavior: 'contain' }}>

        {/* Empty state */}
        {isEmpty && (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            minHeight: 'calc(100dvh - var(--topbar-h) - 120px)',
            textAlign: 'center', gap: 12, padding: '40px 20px',
          }}>
            <Logo height={54} />
            <p style={{ color: 'var(--text-3)', fontSize: '.88rem', maxWidth: 340, lineHeight: 1.6 }}>
              Clasifica mercancías bajo el Decreto 1881/2021 —<br />ingresa una descripción, URL o adjunta una imagen
            </p>
            {!user && (
              <p style={{ color: 'var(--text-3)', fontSize: '.75rem' }}>
                {anonLimit - anonUsed} análisis gratuitos disponibles
              </p>
            )}
          </div>
        )}

        {/* Messages */}
        {!isEmpty && (
          <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 20px 0' }}>
            {messages.map((msg, i) => {
              if (msg.type === 'user') return (
                <div key={i} style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
                  <div style={{
                    maxWidth: '80%', background: 'var(--card)',
                    border: '1px solid var(--border-2)', borderRadius: '16px 16px 4px 16px',
                    padding: '10px 14px', fontSize: '.9rem', color: 'var(--text)',
                    wordBreak: 'break-word',
                  }}>
                    {msg.fileName
                      ? <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-2)' }}>
                          <Paperclip size={13} /> {msg.fileName}
                        </span>
                      : msg.text
                    }
                  </div>
                </div>
              )

              if (msg.type === 'loading') return (
                <div key={i} style={{ marginBottom: 16 }}>
                  <LoadingCard steps={msg.steps} />
                </div>
              )

              if (msg.type === 'error') return (
                <div key={i} style={{ marginBottom: 16 }}>
                  <div style={{
                    background: 'rgba(248,113,113,.07)', border: '1px solid rgba(248,113,113,.2)',
                    borderRadius: 'var(--r)', padding: '12px 16px', color: 'var(--red)', fontSize: '.88rem',
                  }}>
                    {msg.text}
                  </div>
                </div>
              )

              if (msg.type === 'result') return (
                <div key={i} style={{ marginBottom: 16 }}>
                  <ResultsView result={msg.result} />
                </div>
              )

              return null
            })}
            <div ref={bottomRef} style={{ height: 120 }} />
          </div>
        )}
        {isEmpty && <div ref={bottomRef} />}
      </div>

      {/* Input dock */}
      <div style={{
        position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)',
        width: 'calc(100% - 32px)', maxWidth: 720, zIndex: 50,
      }}>
        <div
          style={{
            background: 'var(--card)', border: '1px solid var(--border-2)',
            borderRadius: 18, boxShadow: '0 4px 32px rgba(0,0,0,0.35)',
          }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFile(f) }}
        >
          {file && (
            <div style={{ padding: '8px 14px 0', display: 'flex', alignItems: 'center', gap: 8, fontSize: '.78rem', color: 'var(--text-2)' }}>
              <Paperclip size={12} /> {file.name}
              <button onClick={() => setFile(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', display: 'flex', padding: 2 }}>
                <X size={12} />
              </button>
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'flex-end', padding: '8px 8px 8px 14px', gap: 8 }}>
            <textarea
              ref={textareaRef}
              rows={1}
              placeholder="Describe el producto, pega una URL o adjunta imagen/PDF…"
              value={text}
              onChange={handleTextChange}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
              disabled={loading}
              style={{
                flex: 1, background: 'none', border: 'none', outline: 'none',
                color: 'var(--text)', fontFamily: 'inherit', fontSize: '.92rem',
                resize: 'none', lineHeight: 1.5, maxHeight: 160, overflowY: 'auto',
                padding: '4px 0',
              }}
            />
            <input ref={fileRef} type="file" accept="image/*,.pdf" style={{ display: 'none' }}
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={loading}
              style={{
                background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)',
                padding: 7, borderRadius: 8, display: 'flex', transition: 'background .15s',
              }}
              onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(128,128,128,.1)')}
              onMouseOut={(e) => (e.currentTarget.style.background = 'none')}
              title="Adjuntar"
            >
              <Paperclip size={15} />
            </button>
            <button
              onClick={submit}
              disabled={loading || (!text.trim() && !file)}
              style={{
                background: loading || (!text.trim() && !file) ? 'rgba(128,128,128,.15)' : 'var(--text)',
                color: loading || (!text.trim() && !file) ? 'var(--text-3)' : 'var(--bg)',
                border: 'none', borderRadius: 10, padding: '8px 10px',
                cursor: loading || (!text.trim() && !file) ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all .15s',
              }}
            >
              {loading
                ? <svg className="spin" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-6.22-8.56" /></svg>
                : <Send size={13} />
              }
            </button>
          </div>
        </div>
        <div style={{ textAlign: 'center', fontSize: '.7rem', color: 'var(--text-3)', marginTop: 6 }}>
          ACA puede cometer errores. Verifica la subpartida con un agente aduanero.
        </div>
      </div>
    </div>
  )
}
