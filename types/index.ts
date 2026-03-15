export interface User {
  id: string
  email: string
  nombre?: string
}

export interface AuthState {
  user: User | null
  anonUsed: number
  anonLimit: number
  isAdmin: boolean
}

export interface ClasificacionRecord {
  id: string
  descripcion?: string
  ficha_tecnica?: string
  subpartida: string
  estado: 'pendiente' | 'aprobada' | 'rechazada' | 'investigar'
  costo_cop: number
  costo_usd: number
  tokens: number
  tiempo_segundos: number
  created_at: string
  investigacion_html?: string
  clasificacion_html?: string
  validacion_html?: string
  investigacion_raw?: string
  clasificacion_raw?: string
  validacion_raw?: string
  ficha_tecnica?: string
  fuente_nombre?: string
  fuente_tipo?: string
  tokens_total?: number
  fuentes?: Fuente[]
  notas?: string
}

export interface Fuente {
  url: string
  title: string
  snippet?: string
}

export interface ClasificarResult {
  id: string
  subpartida: string
  investigacion_html: string
  clasificacion_html: string
  validacion_html: string
  investigacion_raw: string
  clasificacion_raw: string
  validacion_raw: string
  ficha_tecnica?: string
  fuentes: Fuente[]
  tiempo_segundos: number
  costo_cop: number
  costo_usd: number
  tokens: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatContext {
  ficha_tecnica?: string
  clasificacion: string
  validacion: string
  investigacion: string
}
