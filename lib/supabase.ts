import { createClient } from '@supabase/supabase-js'
import { ClasificacionRecord } from '@/types'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// ── Clasificaciones ──

export async function listarClasificaciones(opts: {
  estado?: string
  limit?: number
  anonId?: string
} = {}): Promise<ClasificacionRecord[]> {
  let q = supabase
    .from('clasificaciones')
    .select('id,ficha_tecnica,subpartida,estado,costo_cop,costo_usd,tokens_total,tiempo_segundos,created_at,fuente_tipo,fuente_nombre')
    .order('created_at', { ascending: false })
    .limit(opts.limit ?? 100)

  if (opts.anonId) {
    q = q.eq('anon_id', opts.anonId)
  }

  if (opts.estado && opts.estado !== 'todas') {
    q = q.eq('estado', opts.estado)
  }

  const { data, error } = await q
  if (error) throw error
  return (data ?? []) as ClasificacionRecord[]
}

export async function getClasificacion(id: string): Promise<ClasificacionRecord | null> {
  const { data, error } = await supabase
    .from('clasificaciones')
    .select('*')
    .eq('id', id)
    .single()
  if (error) return null
  return data as ClasificacionRecord
}

export async function actualizarEstado(
  id: string,
  estado: string,
  notas?: string
): Promise<ClasificacionRecord | null> {
  const updates: Record<string, unknown> = { estado }
  if (notas !== undefined) updates.notas = notas
  const { data, error } = await supabase
    .from('clasificaciones')
    .update(updates)
    .eq('id', id)
    .select()
    .single()
  if (error) throw error
  return data as ClasificacionRecord
}

// ── Conocimiento ──

export async function statsConocimiento() {
  const { count, error } = await supabase
    .from('conocimiento')
    .select('id', { count: 'exact', head: true })
  if (error) throw error
  return { total_registros: count ?? 0 }
}

// ── Auth: Usuarios ──

export async function getUsuario(id: string) {
  const { data } = await supabase.from('usuarios').select('*').eq('id', id).single()
  return data
}

export async function getOrCreateUsuario(email: string) {
  const { data: existing } = await supabase
    .from('usuarios')
    .select('*')
    .eq('email', email)
    .single()
  if (existing) return existing

  const { data: created, error } = await supabase
    .from('usuarios')
    .insert({ email, verificado: true })
    .select()
    .single()
  if (error) throw error
  return created
}

// ── Auth: Verificaciones ──

export async function crearVerificacion(email: string, codigo: string, minutes = 15) {
  await supabase
    .from('verificaciones')
    .update({ usado: true })
    .eq('email', email)
    .eq('usado', false)

  const expiresAt = new Date(Date.now() + minutes * 60 * 1000).toISOString()
  const { error } = await supabase
    .from('verificaciones')
    .insert({ email, codigo, expires_at: expiresAt, usado: false })
  if (error) throw error
}

export async function verificarCodigo(email: string, codigo: string): Promise<boolean> {
  const { data } = await supabase
    .from('verificaciones')
    .select('*')
    .eq('email', email)
    .eq('codigo', codigo.toUpperCase())
    .eq('usado', false)
    .single()

  if (!data) return false
  if (new Date(data.expires_at) < new Date()) return false

  await supabase.from('verificaciones').update({ usado: true }).eq('id', data.id)
  return true
}

// ── Auth: Anónimos ──

export async function getAnonCount(anonId: string): Promise<number> {
  const { data } = await supabase
    .from('anon_usos')
    .select('count')
    .eq('anon_id', anonId)
    .single()
  return data?.count ?? 0
}

export async function incrementAnonCount(anonId: string): Promise<number> {
  const current = await getAnonCount(anonId)
  if (current === 0) {
    await supabase.from('anon_usos').insert({ anon_id: anonId, count: 1 })
    return 1
  }
  const next = current + 1
  await supabase.from('anon_usos').update({ count: next }).eq('anon_id', anonId)
  return next
}
