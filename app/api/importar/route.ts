import { NextRequest, NextResponse } from 'next/server'
import { getSession, isAdmin } from '@/lib/auth'
import { getUsuario } from '@/lib/supabase'

export async function POST(req: NextRequest) {
  const session = await getSession()
  if (!session.userId) {
    return NextResponse.json({ error: 'No autorizado.' }, { status: 401 })
  }

  const user = await getUsuario(session.userId)
  if (!user || !isAdmin(user.email)) {
    return NextResponse.json({ error: 'Acceso restringido.' }, { status: 403 })
  }

  const formData = await req.formData()
  const flaskUrl = `${process.env.FLASK_INTERNAL_URL ?? 'http://localhost:5050'}/importar`

  try {
    const flaskRes = await fetch(flaskUrl, { method: 'POST', body: formData })
    const data = await flaskRes.json()
    return NextResponse.json(data, { status: flaskRes.status })
  } catch {
    return NextResponse.json({ error: 'Servicio no disponible.' }, { status: 503 })
  }
}
