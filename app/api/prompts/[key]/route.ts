import { NextRequest, NextResponse } from 'next/server'
import { getSession } from '@/lib/auth'

const ADMIN_EMAIL = 'lufecano1@gmail.com'

export async function PUT(req: NextRequest, { params }: { params: Promise<{ key: string }> }) {
  const session = await getSession()
  if (!session.userId) {
    return NextResponse.json({ error: 'No autorizado.' }, { status: 401 })
  }

  // Verify admin by checking user email
  const { getUsuario } = await import('@/lib/supabase')
  const user = await getUsuario(session.userId)
  if (!user || user.email?.toLowerCase() !== ADMIN_EMAIL) {
    return NextResponse.json({ error: 'Solo el administrador puede editar prompts.' }, { status: 403 })
  }

  const { key } = await params
  const body = await req.json()
  const flaskUrl = `${process.env.FLASK_INTERNAL_URL ?? 'http://localhost:5050'}/prompts/${key}`

  try {
    const r = await fetch(flaskUrl, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await r.json()
    return NextResponse.json(data, { status: r.status })
  } catch {
    return NextResponse.json({ error: 'Servicio no disponible.' }, { status: 503 })
  }
}
