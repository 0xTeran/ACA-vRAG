import { ClasificarPage } from '@/components/clasificar/ClasificarPage'

export default async function SessionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <ClasificarPage sessionId={id} />
}
