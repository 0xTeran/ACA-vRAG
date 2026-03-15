import { NextRequest, NextResponse } from 'next/server'

const FLASK = process.env.FLASK_INTERNAL_URL ?? 'http://localhost:5050'

export async function GET() {
  try {
    const r = await fetch(`${FLASK}/lecciones`)
    return NextResponse.json(await r.json())
  } catch {
    return NextResponse.json({ error: 'Servicio no disponible.' }, { status: 503 })
  }
}

export async function POST(req: NextRequest) {
  const body = await req.json()
  try {
    const r = await fetch(`${FLASK}/lecciones`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return NextResponse.json(await r.json(), { status: r.status })
  } catch {
    return NextResponse.json({ error: 'Servicio no disponible.' }, { status: 503 })
  }
}
