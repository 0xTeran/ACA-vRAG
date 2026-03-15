'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Upload } from 'lucide-react'

export default function ImportarPage() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: stats, refetch } = useQuery({
    queryKey: ['conocimiento-stats'],
    queryFn: () => fetch('/api/conocimiento/stats').then((r) => r.json()),
  })

  const submit = async () => {
    if (!file || loading) return
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('archivo', file)
      const r = await fetch('/api/importar', { method: 'POST', body: fd })
      const d = await r.json()
      if (!r.ok) { setError(d.error ?? 'Error al importar'); return }
      setResult(`Importados ${d.importados} de ${d.total_enviados} registros.`)
      setFile(null)
      refetch()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: '32px 20px' }}>
      <h1 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 8 }}>Importar base de conocimiento</h1>
      <p style={{ fontSize: '.86rem', color: 'var(--text-3)', marginBottom: 24 }}>
        Sube un archivo CSV o JSON con precedentes para la base de conocimiento.
      </p>

      {stats && (
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 16px', marginBottom: 20, fontSize: '.86rem', color: 'var(--text-2)' }}>
          Base de conocimiento: <strong style={{ color: 'var(--text)' }}>{stats.total_registros}</strong> registros
        </div>
      )}

      <div
        style={{
          border: '2px dashed var(--border-2)', borderRadius: 'var(--r)',
          padding: '40px 20px', textAlign: 'center', cursor: 'pointer',
          transition: 'border-color .15s', marginBottom: 16,
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) setFile(f) }}
        onClick={() => document.getElementById('file-input')?.click()}
        onMouseOver={(e) => (e.currentTarget.style.borderColor = 'var(--text-3)')}
        onMouseOut={(e) => (e.currentTarget.style.borderColor = 'var(--border-2)')}
      >
        <input
          id="file-input"
          type="file"
          accept=".csv,.json"
          style={{ display: 'none' }}
          onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
        />
        <Upload size={24} style={{ color: 'var(--text-3)', margin: '0 auto 10px' }} />
        {file
          ? <div style={{ fontSize: '.88rem', color: 'var(--text)' }}>{file.name}</div>
          : <div style={{ fontSize: '.88rem', color: 'var(--text-3)' }}>Arrastra un CSV o JSON aquí, o haz clic</div>
        }
      </div>

      <button
        onClick={submit}
        disabled={!file || loading}
        style={{
          width: '100%', padding: '12px', borderRadius: 99,
          background: !file || loading ? 'rgba(128,128,128,.15)' : 'var(--text)',
          color: !file || loading ? 'var(--text-3)' : 'var(--bg)',
          border: 'none', cursor: !file || loading ? 'not-allowed' : 'pointer',
          fontFamily: 'inherit', fontSize: '.92rem', fontWeight: 600,
        }}
      >
        {loading ? 'Importando…' : 'Importar'}
      </button>

      {result && (
        <div style={{ marginTop: 12, padding: '10px 14px', background: 'rgba(74,222,128,.08)', border: '1px solid rgba(74,222,128,.2)', borderRadius: 8, color: 'var(--green)', fontSize: '.86rem' }}>
          {result}
        </div>
      )}
      {error && (
        <div style={{ marginTop: 12, padding: '10px 14px', background: 'rgba(248,113,113,.08)', border: '1px solid rgba(248,113,113,.2)', borderRadius: 8, color: 'var(--red)', fontSize: '.86rem' }}>
          {error}
        </div>
      )}
    </div>
  )
}
