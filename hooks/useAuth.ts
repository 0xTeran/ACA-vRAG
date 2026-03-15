'use client'

import { useEffect } from 'react'
import { useAppStore } from '@/store/appStore'

export function useAuth() {
  const { user, anonUsed, anonLimit, isAdmin, authReady, setAuthState, logout } = useAppStore()

  useEffect(() => {
    if (authReady) return
    fetch('/api/auth/status')
      .then((r) => r.json())
      .then((d) => {
        setAuthState({
          user: d.user ?? null,
          anonUsed: d.anon_used ?? 0,
          anonLimit: d.limit ?? 3,
          isAdmin: d.is_admin ?? false,
        })
      })
      .catch(() => setAuthState({ user: null, anonUsed: 0, anonLimit: 3, isAdmin: false }))
  }, [authReady, setAuthState])

  const doLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    logout()
  }

  return { user, anonUsed, anonLimit, isAdmin, authReady, logout: doLogout }
}
