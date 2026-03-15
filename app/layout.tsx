import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from '@/components/layout/ThemeProvider'
import { AuthModalProvider } from '@/components/auth/AuthModal'
import { Topbar } from '@/components/layout/Topbar'
import { Sidebar } from '@/components/layout/Sidebar'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'ACA — Agente de Clasificación Arancelaria',
  description: 'Clasifica mercancías bajo el Decreto 1881/2021 con IA',
}

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
              <Sidebar />
              <div style={{ marginLeft: 'var(--sidebar-w, 0px)' }}>
                <Topbar />
                <main style={{ paddingTop: 'var(--topbar-h)' }}>
                  {children}
                </main>
              </div>
            </AuthModalProvider>
          </ThemeProvider>
        </Providers>
      </body>
    </html>
  )
}
