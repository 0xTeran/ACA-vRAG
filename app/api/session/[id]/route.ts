import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const flaskUrl = `${process.env.FLASK_INTERNAL_URL ?? 'http://localhost:5050'}/c/${id}/data`

  try {
    const flaskRes = await fetch(flaskUrl)
    const data = await flaskRes.json()
    return NextResponse.json(data, { status: flaskRes.status })
  } catch {
    return NextResponse.json({ error: 'Servicio no disponible.' }, { status: 503 })
  }
}
