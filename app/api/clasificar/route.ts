import { NextRequest, NextResponse } from 'next/server'
import { getSession, getAnonIdFromRequest, setAnonCookie } from '@/lib/auth'
import { getAnonCount, incrementAnonCount } from '@/lib/supabase'

export async function POST(req: NextRequest) {
  const session = await getSession()
  const anonId = getAnonIdFromRequest(req)
  const freeLimit = Number(process.env.FREE_ANON_LIMIT ?? 3)

  if (!session.userId) {
    const used = await getAnonCount(anonId)
    if (used >= freeLimit) {
      const res = NextResponse.json({ error: 'limit_reached', anon_used: used }, { status: 402 })
      setAnonCookie(res, anonId)
      return res
    }
  }

  const formData = await req.formData()
  // Pasa el anon_id a Flask para que lo guarde en clasificaciones
  formData.set('anon_id', anonId)
  const flaskUrl = `${process.env.FLASK_INTERNAL_URL ?? 'http://localhost:5050'}/clasificar`

  let flaskRes: Response
  try {
    flaskRes = await fetch(flaskUrl, { method: 'POST', body: formData })
  } catch {
    return NextResponse.json({ error: 'Servicio de clasificación no disponible.' }, { status: 503 })
  }

  const data = await flaskRes.json()

  if (!flaskRes.ok) {
    return NextResponse.json(data, { status: flaskRes.status })
  }

  if (!session.userId) {
    await incrementAnonCount(anonId)
  }

  const res = NextResponse.json(data)
  if (!req.cookies.get('aca_anon')) setAnonCookie(res, anonId)
  return res
}
