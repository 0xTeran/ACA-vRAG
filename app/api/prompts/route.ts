import { NextResponse } from 'next/server'

export async function GET() {
  const flaskUrl = `${process.env.FLASK_INTERNAL_URL ?? 'http://localhost:5050'}/prompts`
  try {
    const r = await fetch(flaskUrl)
    const data = await r.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'Servicio no disponible.' }, { status: 503 })
  }
}
