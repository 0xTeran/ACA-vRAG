import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const r = await fetch(`${process.env.FLASK_INTERNAL_URL ?? 'http://localhost:5050'}/modelos`)
    return NextResponse.json(await r.json())
  } catch {
    return NextResponse.json({ modelos: [] })
  }
}
