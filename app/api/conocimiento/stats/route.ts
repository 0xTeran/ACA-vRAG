import { NextResponse } from 'next/server'
import { statsConocimiento } from '@/lib/supabase'

export async function GET() {
  const stats = await statsConocimiento()
  return NextResponse.json(stats)
}
