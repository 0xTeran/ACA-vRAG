import { NextRequest, NextResponse } from 'next/server'
import { getSession } from '@/lib/auth'
import { getClasificacion } from '@/lib/supabase'

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await getSession()
  if (!session.userId) {
    return NextResponse.json({ error: 'No autorizado.' }, { status: 401 })
  }

  const { id } = await params
  const record = await getClasificacion(id)
  if (!record) return NextResponse.json({ error: 'No encontrado.' }, { status: 404 })

  return NextResponse.json(record)
}
