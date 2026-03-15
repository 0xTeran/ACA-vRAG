import { NextRequest, NextResponse } from 'next/server'
import { verificarCodigo, getOrCreateUsuario } from '@/lib/supabase'
import { getSession, isAdmin } from '@/lib/auth'

export async function POST(req: NextRequest) {
  const body = await req.json()
  const email = (body.email ?? '').trim().toLowerCase()
  const codigo = (body.codigo ?? '').trim().toUpperCase()

  if (!email || !codigo) {
    return NextResponse.json({ error: 'Faltan datos.' }, { status: 400 })
  }

  const valid = await verificarCodigo(email, codigo)
  if (!valid) {
    return NextResponse.json({ error: 'Código incorrecto o expirado.' }, { status: 400 })
  }

  const user = await getOrCreateUsuario(email)
  const session = await getSession()
  session.userId = user.id
  await session.save()

  return NextResponse.json({
    ok: true,
    user: { id: user.id, email: user.email, nombre: user.nombre },
    is_admin: isAdmin(user.email),
  })
}
