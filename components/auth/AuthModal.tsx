'use client'

import { createContext, useContext, useState, useRef, useEffect } from 'react'
import { X } from 'lucide-react'
import { Logo } from '@/components/ui/Logo'
import { useAppStore } from '@/store/appStore'

interface AuthModalCtx {
  open: (msg?: string) => void
  close: () => void
}

const AuthModalContext = createContext<AuthModalCtx>({ open: () => {}, close: () => {} })
export const useAuthModal = () => useContext(AuthModalContext)

export function AuthModalProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const [step, setStep] = useState<'email' | 'code'>('email')
  const [subMsg, setSubMsg] = useState('Ingresa tu correo para recibir un código de acceso.')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState(['', '', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [err1, setErr1] = useState('')
  const [err2, setErr2] = useState('')
  const [success, setSuccess] = useState(false)
  const emailRef = useRef<HTMLInputElement>(null)
  const codeRefs = useRef<(HTMLInputElement | null)[]>([])
  const setAuthState = useAppStore((s) => s.setAuthState)

  const open = (msg?: string) => {
    setStep('email')
    setEmail('')
    setCode(['', '', '', '', '', ''])
    setErr1('')
    setErr2('')
    setSuccess(false)
    if (msg) setSubMsg(msg)
    else setSubMsg('Ingresa tu correo para recibir un código de acceso.')
    setIsOpen(true)
  }

  const close = () => setIsOpen(false)

  useEffect(() => {
    if (isOpen && step === 'email') setTimeout(() => emailRef.current?.focus(), 100)
    if (step === 'code') setTimeout(() => codeRefs.current[0]?.focus(), 100)
  }, [isOpen, step])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  const sendCode = async () => {
    setErr1('')
    if (!email || !email.includes('@')) { setErr1('Ingresa un correo válido.'); return }
    setLoading(true)
    try {
      const r = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const d = await r.json()
      if (!r.ok) { setErr1(d.error ?? 'Error al enviar.'); return }
      setStep('code')
    } finally {
      setLoading(false)
    }
  }

  const verifyCode = async () => {
    setErr2('')
    const codigo = code.join('')
    if (codigo.length < 6) { setErr2('Completa los 6 dígitos.'); return }
    setLoading(true)
    try {
      const r = await fetch('/api/auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, codigo }),
      })
      const d = await r.json()
      if (!r.ok) { setErr2(d.error ?? 'Código incorrecto.'); return }
      setAuthState({ user: d.user, anonUsed: 0, anonLimit: 3, isAdmin: d.is_admin ?? false })
      setSuccess(true)
      setTimeout(close, 1200)
    } finally {
      setLoading(false)
    }
  }

  const handleCodeChange = (i: number, val: string) => {
    const v = val.toUpperCase().replace(/[^A-Z0-9]/g, '')
    const next = [...code]
    next[i] = v.slice(-1)
    setCode(next)
    if (v && i < 5) codeRefs.current[i + 1]?.focus()
  }

  const handleCodeKey = (i: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !code[i] && i > 0) codeRefs.current[i - 1]?.focus()
    if (e.key === 'Enter') verifyCode()
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const txt = e.clipboardData.getData('text').toUpperCase().replace(/[^A-Z0-9]/g, '')
    setCode(Array.from({ length: 6 }, (_, i) => txt[i] ?? ''))
    codeRefs.current[Math.min(txt.length, 5)]?.focus()
  }

  if (!isOpen) return (
    <AuthModalContext.Provider value={{ open, close }}>
      {children}
    </AuthModalContext.Provider>
  )

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '13px 16px', borderRadius: 12, boxSizing: 'border-box',
    border: '1px solid var(--border)', background: 'var(--input-bg)', color: 'var(--text)',
    fontFamily: 'inherit', fontSize: '.92rem', outline: 'none',
  }

  const primaryStyle: React.CSSProperties = {
    width: '100%', padding: 13, borderRadius: 99,
    background: 'var(--text)', color: 'var(--bg)', border: 'none',
    fontFamily: 'inherit', fontSize: '.92rem', fontWeight: 600, cursor: 'pointer',
    opacity: loading ? 0.5 : 1,
  }

  return (
    <AuthModalContext.Provider value={{ open, close }}>
      {children}

      <div style={{
        position: 'fixed', inset: 0, zIndex: 200, background: 'var(--bg)',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', flexShrink: 0 }}>
          <Logo height={22} />
          <button onClick={close} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', padding: 7, borderRadius: '50%', display: 'flex' }}>
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '20px 24px 80px' }}>
          <div style={{ width: '100%', maxWidth: 380, display: 'flex', flexDirection: 'column', gap: 16 }}>

            {step === 'email' && (
              <>
                <div style={{ fontSize: '1.7rem', fontWeight: 700, textAlign: 'center', lineHeight: 1.25 }}>
                  Inicia sesión en tu cuenta
                </div>
                <div style={{ fontSize: '.86rem', color: 'var(--text-3)', textAlign: 'center', lineHeight: 1.6 }}>
                  {subMsg}
                </div>
                <input
                  ref={emailRef}
                  style={inputStyle}
                  type="email"
                  placeholder="correo@ejemplo.com"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendCode()}
                />
                <button style={primaryStyle} disabled={loading} onClick={sendCode}>
                  {loading ? 'Enviando…' : 'Continuar'}
                </button>
                {err1 && <div style={{ fontSize: '.8rem', color: 'var(--red)', textAlign: 'center' }}>{err1}</div>}
              </>
            )}

            {step === 'code' && (
              <>
                <div style={{ fontSize: '1.7rem', fontWeight: 700, textAlign: 'center', lineHeight: 1.25 }}>
                  Revisa tu correo
                </div>
                <div style={{ fontSize: '.86rem', color: 'var(--text-3)', textAlign: 'center', lineHeight: 1.6 }}>
                  Ingresa el código de 6 dígitos enviado a <strong style={{ color: 'var(--text)' }}>{email}</strong>
                </div>
                <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }} onPaste={handlePaste}>
                  {code.map((v, i) => (
                    <input
                      key={i}
                      ref={(el) => { codeRefs.current[i] = el }}
                      maxLength={1}
                      inputMode="text"
                      value={v}
                      onChange={(e) => handleCodeChange(i, e.target.value)}
                      onKeyDown={(e) => handleCodeKey(i, e)}
                      style={{
                        width: 44, height: 52, textAlign: 'center', fontSize: '1.2rem', fontWeight: 700,
                        background: 'var(--input-bg)', border: '1.5px solid var(--border)',
                        borderRadius: 10, color: 'var(--text)', fontFamily: 'monospace',
                        outline: 'none', textTransform: 'uppercase',
                      }}
                    />
                  ))}
                </div>
                {success ? (
                  <div style={{ fontSize: '.8rem', color: 'var(--green)', textAlign: 'center' }}>¡Acceso concedido! Bienvenido a ACA.</div>
                ) : (
                  <button style={primaryStyle} disabled={loading} onClick={verifyCode}>
                    {loading ? 'Verificando…' : 'Verificar código'}
                  </button>
                )}
                {err2 && <div style={{ fontSize: '.8rem', color: 'var(--red)', textAlign: 'center' }}>{err2}</div>}
                <button
                  onClick={() => setStep('email')}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', fontFamily: 'inherit', fontSize: '.82rem', textAlign: 'center', textDecoration: 'underline' }}
                >
                  ← Cambiar correo
                </button>
              </>
            )}

          </div>
        </div>

        <div style={{ position: 'absolute', bottom: 24, left: 0, right: 0, fontSize: '.72rem', color: 'var(--text-3)', textAlign: 'center', padding: '0 24px', lineHeight: 1.6 }}>
          Al continuar, aceptas los Términos de Servicio y la Política de Privacidad de ACA.
        </div>
      </div>
    </AuthModalContext.Provider>
  )
}
