'use client'

import { createContext, useContext, useEffect, useState } from 'react'

type Theme = 'dark' | 'light'

const ThemeContext = createContext<{ theme: Theme; toggle: () => void }>({
  theme: 'dark',
  toggle: () => {},
})

function readTheme(): Theme {
  try {
    const v = localStorage.getItem('aca-theme')
    if (v === 'dark' || v === 'light') return v
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Empieza en 'dark' en servidor para match con SSR.
  // useEffect aplica el tema real (localStorage) después del mount, sin causar flash
  // porque el script síncrono en <head> ya puso el data-theme correcto antes del primer paint.
  const [theme, setTheme] = useState<Theme>('dark')

  useEffect(() => {
    const t = readTheme()
    document.documentElement.setAttribute('data-theme', t)
    setTheme(t)
  }, [])

  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.setAttribute('data-theme', next)
    localStorage.setItem('aca-theme', next)
    setTheme(next)
  }

  return <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>
}

export const useTheme = () => useContext(ThemeContext)
