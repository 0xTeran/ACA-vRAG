'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Send, Paperclip, X, BookmarkPlus } from 'lucide-react'
import { Logo } from '@/components/ui/Logo'
import { LoadingCard } from './LoadingCard'
import { ResultsView } from './ResultsView'
import { useAuthModal } from '@/components/auth/AuthModal'
import { useAppStore } from '@/store/appStore'
import { ClasificarResult, ChatMessage } from '@/types'

type Step = { label: string; status: 'idle' | 'running' | 'done' }

type Message =
  | { type: 'user'; text: string; fileName?: string }
  | { type: 'loading'; steps: Step[] }
  | { type: 'result'; result: ClasificarResult }
  | { type: 'chat-reply'; html: string; raw: string }
  | { type: 'thinking' }
  | { type: 'error'; text: string }

const extractUrl = (t: string): string | null => {
  const m = t.match(/https?:\/\/\S+/)
  return m ? m[0] : null
}

interface Props {
  sessionId?: string
}

export function ClasificarPage({ sessionId }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [currentSessionId, setCurrentSessionId] = useState(sessionId ?? '')
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
  const [chatContext, setChatContext] = useState<{
    ficha_tecnica: string; clasificacion: string; validacion: string; investigacion: string
  }>({ ficha_tecnica: '', clasificacion: '', validacion: '', investigacion: '' })

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])
  const { open: openAuth } = useAuthModal()
  const { anonUsed, anonLimit, user } = useAppStore()
  const sessionLoaded = useRef(false)

  const hasResult = currentSessionId !== ''
  const isEmpty = messages.length === 0
  const [dragging, setDragging] = useState(false)
  const [savedLesson, setSavedLesson] = useState<number | null>(null)

  const saveAsLesson = async (raw: string, idx: number) => {
    try {
      await fetch('/api/lecciones', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          regla: raw.substring(0, 500),
          keywords: chatContext.ficha_tecnica.substring(0, 200),
          agente: 'clasificador',
          subpartida: '',
          producto: chatContext.ficha_tecnica.substring(0, 300),
          fuente: `chat sesión ${currentSessionId.substring(0, 8)}`,
          clasificacion_id: currentSessionId,
        }),
      })
      setSavedLesson(idx)
      setTimeout(() => setSavedLesson(null), 3000)
    } catch {}
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load existing session
  useEffect(() => {
    if (sessionId && !sessionLoaded.current) {
      sessionLoaded.current = true
      loadSession(sessionId)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  async function loadSession(id: string) {
    try {
      const r = await fetch(`/api/session/${id}`)
      if (!r.ok) return
      const data = await r.json()

      setCurrentSessionId(id)
      setChatContext({
        ficha_tecnica: data.ficha_tecnica ?? '',
        clasificacion: data.clasificacion ?? '',
        validacion: data.validacion ?? '',
        investigacion: data.investigacion ?? '',
      })

      const loaded: Message[] = []

      // Add original ficha as user message
      if (data.ficha_tecnica) {
        const preview = data.ficha_tecnica.substring(0, 150) + (data.ficha_tecnica.length > 150 ? '…' : '')
        loaded.push({ type: 'user', text: preview })
      }

      // Add result
      loaded.push({
        type: 'result',
        result: {
          id: data.id,
          subpartida: data.subpartida ?? '',
          investigacion_html: data.investigacion_html ?? '',
          clasificacion_html: data.clasificacion_html ?? '',
          validacion_html: data.validacion_html ?? '',
          investigacion_raw: data.investigacion ?? '',
          clasificacion_raw: data.clasificacion ?? '',
          validacion_raw: data.validacion ?? '',
          ficha_tecnica: data.ficha_tecnica,
          fuentes: data.fuentes ?? [],
          tiempo_segundos: data.tiempo_segundos ?? 0,
          costo_cop: data.costo_cop ?? 0,
          costo_usd: data.costo_usd ?? 0,
          tokens: data.tokens_total ?? data.tokens ?? 0,
        },
      })

      // Add chat messages
      const chatMsgs: ChatMessage[] = data.chat_messages ?? []
      for (const msg of chatMsgs) {
        if (msg.role === 'user') {
          loaded.push({ type: 'user', text: msg.content })
        } else {
          loaded.push({ type: 'chat-reply', html: msg.content })
        }
      }
      setChatHistory(chatMsgs)
      setMessages(loaded)
    } catch (e) {
      console.error('Error loading session:', e)
    }
  }

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

  // ── Send chat message (follow-up after classification) ──
  const sendChatMessage = useCallback(async (msg: string) => {
    setMessages((prev) => [...prev, { type: 'user', text: msg }, { type: 'thinking' }])
    setLoading(true)

    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msg,
          clasificacion_id: currentSessionId,
          ficha_tecnica: chatContext.ficha_tecnica,
          clasificacion: chatContext.clasificacion,
          validacion: chatContext.validacion,
          investigacion: chatContext.investigacion,
          history: chatHistory,
        }),
      })
      const data = await r.json()

      // Remove thinking indicator
      setMessages((prev) => prev.filter((m) => m.type !== 'thinking'))

      if (!r.ok) {
        setMessages((prev) => [...prev, { type: 'error', text: data.error ?? 'Error' }])
        return
      }

      setMessages((prev) => [...prev, { type: 'chat-reply', html: data.reply_html, raw: data.reply }])
      setChatHistory((prev) => {
        const updated = [...prev, { role: 'user' as const, content: msg }, { role: 'assistant' as const, content: data.reply }]
        return updated.length > 20 ? updated.slice(-20) : updated
      })
    } catch {
      setMessages((prev) => prev.filter((m) => m.type !== 'thinking'))
      setMessages((prev) => [...prev, { type: 'error', text: 'Error de conexión.' }])
    } finally {
      setLoading(false)
    }
  }, [currentSessionId, chatContext, chatHistory])

  // ── Submit: classify or chat ──
  const submit = useCallback(async () => {
    if (loading || (!text.trim() && !file)) return

    const userText = file ? file.name : text.trim()
    setText('')
    setFile(null)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    // If we already have a result: file → new classification, text → chat
    if (hasResult && !file) {
      await sendChatMessage(userText)
      return
    }

    // ── First message: classify ──
    const inputType = detectInputType(text, file)

    setMessages((prev) => [...prev, {
      type: 'user',
      text: userText,
      fileName: file ? file.name : undefined,
    }])

    const initialSteps: Step[] = [
      { label: 'Investigador — buscando resoluciones DIAN + Perplexity', status: 'running' },
      { label: 'Clasificador — pendiente', status: 'idle' },
      { label: 'Validador — pendiente', status: 'idle' },
    ]
    setMessages((prev) => [...prev, { type: 'loading', steps: initialSteps }])
    setLoading(true)

    // Change URL immediately (like ChatGPT) and add to sidebar
    const tempId = crypto.randomUUID()
    window.history.replaceState(null, '', `/c/${tempId}`)
    document.title = 'ACA — Clasificando...'
    window.dispatchEvent(new CustomEvent('aca:clasificacion', {
      detail: { id: tempId, ficha_tecnica: userText.substring(0, 80), temp: true }
    }))

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

      setMessages((prev) => prev.filter((m) => m.type !== 'loading'))

      if (r.status === 402 || d.error === 'limit_reached') {
        openAuth(`Agotaste tus ${anonLimit} análisis gratuitos. Regístrate gratis para continuar.`)
        return
      }

      if (!r.ok) {
        setMessages((prev) => [...prev, { type: 'error', text: d.error ?? 'Error desconocido' }])
        return
      }

      // Set session
      const newId = d.id || ''
      setCurrentSessionId(newId)
      setChatContext({
        ficha_tecnica: d.ficha_tecnica ?? '',
        clasificacion: d.clasificacion_raw ?? '',
        validacion: d.validacion_raw ?? '',
        investigacion: d.investigacion_raw ?? '',
      })
      setChatHistory([])

      // Update URL with real session ID and refresh sidebar
      if (newId) {
        const subpartida = d.clasificacion_raw?.match(/\d{4}\.\d{2}\.\d{2}\.\d{2}/)?.[0] ?? ''
        window.history.replaceState(null, '', `/c/${newId}`)
        document.title = `ACA — ${subpartida || 'Clasificación'}`
        window.dispatchEvent(new CustomEvent('aca:clasificacion', { detail: { id: newId } }))
      }

      setMessages((prev) => [...prev, { type: 'result', result: d }])
    } catch {
      clearTimers()
      setMessages((prev) => prev.filter((m) => m.type !== 'loading'))
      setMessages((prev) => [...prev, { type: 'error', text: 'Error de conexión. Intenta de nuevo.' }])
      // Revert URL on error
      window.history.replaceState(null, '', '/')
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, text, file, anonLimit, openAuth, hasResult, sendChatMessage])

  return (
    <div
      style={{
        position: 'fixed', inset: 0, paddingTop: 'var(--topbar-h)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
        ...(dragging ? { outline: '2px dashed var(--blue)', outlineOffset: -4 } : {}),
      }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={(e) => { if (e.currentTarget === e.target) setDragging(false) }}
      onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f) }}
    >
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
              Agente de Clasificación Arancelaria
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

              if (msg.type === 'thinking') return (
                <div key={i} style={{ marginBottom: 16 }}>
                  <div style={{
                    background: 'var(--card)', border: '1px solid var(--border-2)',
                    borderRadius: '16px 16px 16px 4px', padding: '14px 18px',
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                    <style>{`
                      @keyframes dotPulse {
                        0%, 60%, 100% { opacity: .25; transform: scale(.8) }
                        30% { opacity: 1; transform: scale(1) }
                      }
                      .thinking-dot {
                        width: 7px; height: 7px; border-radius: 50%;
                        background: var(--text-3);
                        animation: dotPulse 1.4s ease-in-out infinite;
                      }
                      .thinking-dot:nth-child(2) { animation-delay: .15s }
                      .thinking-dot:nth-child(3) { animation-delay: .3s }
                    `}</style>
                    <div className="thinking-dot" />
                    <div className="thinking-dot" />
                    <div className="thinking-dot" />
                  </div>
                </div>
              )

              if (msg.type === 'chat-reply') return (
                <div key={i} style={{ marginBottom: 16 }}>
                  <div style={{
                    background: 'var(--card)', border: '1px solid var(--border-2)',
                    borderRadius: '16px 16px 16px 4px', padding: '12px 16px',
                    fontSize: '.88rem', color: 'var(--text)',
                  }}>
                    <div
                      className="markdown-body"
                      dangerouslySetInnerHTML={{ __html: msg.html }}
                    />
                    <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => saveAsLesson(msg.raw, i)}
                        disabled={savedLesson === i}
                        style={{
                          background: 'none', border: 'none', cursor: 'pointer',
                          color: savedLesson === i ? 'var(--green)' : 'var(--text-3)',
                          fontSize: '.72rem', display: 'flex', alignItems: 'center', gap: 4,
                          padding: '2px 6px', borderRadius: 6, transition: 'color .15s',
                        }}
                        onMouseOver={e => { if (savedLesson !== i) e.currentTarget.style.color = 'var(--text-2)' }}
                        onMouseOut={e => { if (savedLesson !== i) e.currentTarget.style.color = 'var(--text-3)' }}
                        title="Guardar como lección para futuras clasificaciones"
                      >
                        <BookmarkPlus size={12} />
                        {savedLesson === i ? 'Guardado ✓' : 'Guardar como lección'}
                      </button>
                    </div>
                  </div>
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
              placeholder={hasResult
                ? 'Pregunta sobre la clasificación, pega un link de la DIAN…'
                : 'Describe el producto, pega una URL o adjunta imagen/PDF…'
              }
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
              title="Adjuntar imagen o PDF"
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
          {hasResult ? 'Sesión activa — haz preguntas de seguimiento' : 'ACA puede cometer errores. Verifica con un agente aduanero.'}
        </div>
      </div>
    </div>
  )
}
