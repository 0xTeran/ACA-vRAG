'use client'

import { useState, useEffect } from 'react'
import { Save, RotateCcw, Settings } from 'lucide-react'
import { useAppStore } from '@/store/appStore'

interface AgentPrompt {
  agent_key: string
  label: string
  system_prompt: string
  updated_at: string
}

const agentIcons: Record<string, string> = {
  investigador: '🔍',
  clasificador: '🏷️',
  validador: '✅',
  chat: '💬',
}

export default function ConfigPage() {
  const [prompts, setPrompts] = useState<AgentPrompt[]>([])
  const [editing, setEditing] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const { user, isAdmin } = useAppStore()

  useEffect(() => {
    fetch('/api/prompts')
      .then(r => r.json())
      .then(d => {
        setPrompts(d.prompts ?? [])
        const edits: Record<string, string> = {}
        for (const p of d.prompts ?? []) edits[p.agent_key] = p.system_prompt
        setEditing(edits)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const isAdminUser = user?.email?.toLowerCase() === 'lufecano1@gmail.com'

  if (!isAdminUser) {
    return (
      <div style={{ maxWidth: 600, margin: '0 auto', padding: '60px 20px', textAlign: 'center' }}>
        <Settings size={40} style={{ color: 'var(--text-3)', margin: '0 auto 16px' }} />
        <h1 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: 8 }}>Acceso restringido</h1>
        <p style={{ color: 'var(--text-3)', fontSize: '.88rem' }}>
          Solo el administrador puede editar la configuración de los agentes.
        </p>
      </div>
    )
  }

  const savePrompt = async (key: string) => {
    setSaving(key)
    setSaved(null)
    try {
      const r = await fetch(`/api/prompts/${key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ system_prompt: editing[key] }),
      })
      if (r.ok) {
        setSaved(key)
        setTimeout(() => setSaved(null), 3000)
      }
    } finally {
      setSaving(null)
    }
  }

  const resetPrompt = (key: string) => {
    const original = prompts.find(p => p.agent_key === key)
    if (original) setEditing(prev => ({ ...prev, [key]: original.system_prompt }))
  }

  if (loading) {
    return (
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '40px 20px', color: 'var(--text-3)' }}>
        Cargando configuración...
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 20px 60px' }}>
      <h1 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 10 }}>
        <Settings size={22} /> Configuración de Agentes
      </h1>
      <p style={{ color: 'var(--text-3)', fontSize: '.85rem', marginBottom: 28 }}>
        Edita los system prompts de cada agente. Los cambios se aplican inmediatamente.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {prompts.map(p => {
          const changed = editing[p.agent_key] !== p.system_prompt
          return (
            <div key={p.agent_key} style={{
              background: 'var(--card)', border: '1px solid var(--border-2)',
              borderRadius: 14, overflow: 'hidden',
            }}>
              {/* Header */}
              <div style={{
                padding: '14px 18px', borderBottom: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: '1.2rem' }}>{agentIcons[p.agent_key] ?? '🤖'}</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '.92rem' }}>{p.label}</div>
                    <div style={{ fontSize: '.72rem', color: 'var(--text-3)' }}>
                      {p.agent_key} · {new Date(p.updated_at).toLocaleDateString('es-CO')}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  {changed && (
                    <button onClick={() => resetPrompt(p.agent_key)} style={{
                      background: 'none', border: '1px solid var(--border)', borderRadius: 8,
                      padding: '6px 10px', cursor: 'pointer', color: 'var(--text-3)',
                      fontFamily: 'inherit', fontSize: '.78rem', display: 'flex', alignItems: 'center', gap: 5,
                    }}>
                      <RotateCcw size={12} /> Deshacer
                    </button>
                  )}
                  <button onClick={() => savePrompt(p.agent_key)} disabled={!changed || saving === p.agent_key} style={{
                    background: changed ? 'var(--text)' : 'rgba(128,128,128,.15)',
                    color: changed ? 'var(--bg)' : 'var(--text-3)',
                    border: 'none', borderRadius: 8, padding: '6px 14px',
                    cursor: changed ? 'pointer' : 'not-allowed',
                    fontFamily: 'inherit', fontSize: '.78rem', fontWeight: 600,
                    display: 'flex', alignItems: 'center', gap: 5,
                  }}>
                    <Save size={12} /> {saving === p.agent_key ? 'Guardando...' : saved === p.agent_key ? 'Guardado ✓' : 'Guardar'}
                  </button>
                </div>
              </div>

              {/* Textarea */}
              <textarea
                value={editing[p.agent_key] ?? ''}
                onChange={e => setEditing(prev => ({ ...prev, [p.agent_key]: e.target.value }))}
                style={{
                  width: '100%', minHeight: 200, padding: '14px 18px',
                  background: 'transparent', border: 'none', outline: 'none',
                  color: 'var(--text)', fontFamily: 'monospace', fontSize: '.8rem',
                  lineHeight: 1.6, resize: 'vertical',
                }}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
