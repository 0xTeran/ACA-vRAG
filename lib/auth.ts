import { getIronSession, IronSession } from 'iron-session'
import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

export interface SessionData {
  userId?: string
}

export const sessionOptions = {
  password: process.env.SECRET_KEY ?? 'dev-insecure-change-in-production-32chars',
  cookieName: 'aca_session',
  cookieOptions: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    sameSite: 'lax' as const,
    maxAge: 60 * 60 * 24 * 30,
  },
}

export async function getSession(): Promise<IronSession<SessionData>> {
  const cookieStore = await cookies()
  return getIronSession<SessionData>(cookieStore, sessionOptions)
}

export function isAdmin(email: string): boolean {
  const adminEmails = (process.env.ADMIN_EMAILS ?? '')
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean)
  return adminEmails.includes(email.toLowerCase())
}

export function getAnonIdFromRequest(req: NextRequest): string {
  return req.cookies.get('aca_anon')?.value ?? crypto.randomUUID()
}

export function setAnonCookie(res: NextResponse, anonId: string): void {
  res.cookies.set('aca_anon', anonId, {
    maxAge: 60 * 60 * 24 * 365,
    sameSite: 'lax',
    httpOnly: true,
    path: '/',
  })
}
