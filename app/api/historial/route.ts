import { NextRequest, NextResponse } from 'next/server'
import { getSession, getAnonIdFromRequest } from '@/lib/auth'
import { listarClasificaciones } from '@/lib/supabase'

export async function GET(req: NextRequest) {
  const session = await getSession()
  const { searchParams } = new URL(req.url)
  const estado = searchParams.get('estado') ?? undefined

  if (session.userId) {
    // Autenticado: ve todas
    const registros = await listarClasificaciones({ estado, limit: 100 })
    return NextResponse.json({ registros })
  }

  // Anónimo: solo las suyas por cookie
  const anonId = getAnonIdFromRequest(req)
  const registros = await listarClasificaciones({ estado, limit: 100, anonId })
  return NextResponse.json({ registros })
}
