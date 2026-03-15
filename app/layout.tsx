import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from '@/components/layout/ThemeProvider'
import { AuthModalProvider } from '@/components/auth/AuthModal'
import { Topbar } from '@/components/layout/Topbar'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'ACA — Agente de Clasificación Arancelaria',
  description: 'Clasifica mercancías bajo el Decreto 1881/2021 con IA',
}

// Script que corre sincrónicamente antes del primer paint para evitar flash de tema
const themeScript = `(function(){try{var t=localStorage.getItem('aca-theme');var p=t||(window.matchMedia('(prefers-color-scheme:light)').matches?'light':'dark');document.documentElement.setAttribute('data-theme',p);}catch(e){}})()`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <Providers>
          <ThemeProvider>
            <AuthModalProvider>
              <Topbar />
              <main style={{ paddingTop: 'var(--topbar-h)' }}>
                {children}
              </main>
            </AuthModalProvider>
          </ThemeProvider>
        </Providers>
      </body>
    </html>
  )
}
