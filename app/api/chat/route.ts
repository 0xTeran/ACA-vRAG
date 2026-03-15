import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  const body = await req.json()
  const flaskUrl = `${process.env.FLASK_INTERNAL_URL ?? 'http://localhost:5050'}/chat`

  try {
    const flaskRes = await fetch(flaskUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await flaskRes.json()
    return NextResponse.json(data, { status: flaskRes.status })
  } catch {
    return NextResponse.json({ error: 'Servicio de chat no disponible.' }, { status: 503 })
  }
}
