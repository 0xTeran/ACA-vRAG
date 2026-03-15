import { NextRequest, NextResponse } from 'next/server'
import { listarClasificaciones } from '@/lib/supabase'

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const estado = searchParams.get('estado') ?? undefined
  const registros = await listarClasificaciones({ estado, limit: 100 })
  return NextResponse.json({ registros })
}
