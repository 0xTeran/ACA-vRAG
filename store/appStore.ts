'use client'

import { create } from 'zustand'
import { User } from '@/types'

interface AppStore {
  user: User | null
  anonUsed: number
  anonLimit: number
  isAdmin: boolean
  authReady: boolean
  setAuthState: (state: {
    user: User | null
    anonUsed: number
    anonLimit: number
    isAdmin: boolean
  }) => void
  logout: () => void
}

export const useAppStore = create<AppStore>((set) => ({
  user: null,
  anonUsed: 0,
  anonLimit: 3,
  isAdmin: false,
  authReady: false,
  setAuthState: (state) => set({ ...state, authReady: true }),
  logout: () => set({ user: null, anonUsed: 0, isAdmin: false, authReady: true }),
}))
