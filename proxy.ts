import { NextRequest, NextResponse } from 'next/server'
import { getIronSession } from 'iron-session'
import { sessionOptions, SessionData } from '@/lib/auth'

export async function proxy(req: NextRequest) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const session = await getIronSession<SessionData>(req.cookies as any, sessionOptions)

  const isProtected = req.nextUrl.pathname.startsWith('/importar')

  if (isProtected && !session.userId) {
    return NextResponse.redirect(new URL('/', req.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/importar/:path*'],
}
