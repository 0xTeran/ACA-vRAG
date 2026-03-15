import { NextRequest, NextResponse } from 'next/server'
import { crearVerificacion } from '@/lib/supabase'
import { enviarCodigoVerificacion } from '@/lib/email'

function genCodigo(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
  return Array.from({ length: 6 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
}

export async function POST(req: NextRequest) {
  const body = await req.json()
  const email = (body.email ?? '').trim().toLowerCase()

  if (!email || !email.includes('@') || !email.split('@')[1]?.includes('.')) {
    return NextResponse.json({ error: 'Correo inválido.' }, { status: 400 })
  }

  const codigo = genCodigo()
  await crearVerificacion(email, codigo)
  const ok = await enviarCodigoVerificacion(email, codigo)

  if (!ok) {
    return NextResponse.json({ error: 'No se pudo enviar el correo. Intenta de nuevo.' }, { status: 500 })
  }

  return NextResponse.json({ ok: true, email })
}
