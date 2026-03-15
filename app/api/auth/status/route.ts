import { NextRequest, NextResponse } from 'next/server'
import { getSession, isAdmin, getAnonIdFromRequest, setAnonCookie } from '@/lib/auth'
import { getUsuario, getAnonCount } from '@/lib/supabase'

export async function GET(req: NextRequest) {
  const session = await getSession()
  const anonId = getAnonIdFromRequest(req)

  let user = null
  let anonUsed = 0

  if (session.userId) {
    user = await getUsuario(session.userId)
  } else {
    anonUsed = await getAnonCount(anonId)
  }

  const res = NextResponse.json({
    user: user ? { id: user.id, email: user.email, nombre: user.nombre } : null,
    anon_used: anonUsed,
    limit: Number(process.env.FREE_ANON_LIMIT ?? 3),
    is_free: !user,
    is_admin: user ? isAdmin(user.email) : false,
  })

  if (!req.cookies.get('aca_anon')) {
    setAnonCookie(res, anonId)
  }

  return res
}
