import { NextRequest, NextResponse } from 'next/server'
import { getSession } from '@/lib/auth'
import { actualizarEstado } from '@/lib/supabase'

const VALID_ESTADOS = ['aprobada', 'rechazada', 'investigar', 'pendiente']

export async function POST(req: NextRequest) {
  const session = await getSession()
  if (!session.userId) {
    return NextResponse.json({ error: 'No autorizado.' }, { status: 401 })
  }

  const { id, estado, notas } = await req.json()
  if (!id || !VALID_ESTADOS.includes(estado)) {
    return NextResponse.json({ error: 'Datos inválidos.' }, { status: 400 })
  }

  const record = await actualizarEstado(id, estado, notas)
  return NextResponse.json({ ok: true, registro: record })
}
