import { useCallback, useEffect, useState } from 'react'
import type { DocumentOut } from '../types'
import { listDocuments } from '../lib/api'
import { Uploader } from '../components/Uploader'
import { DocumentsTable } from '../components/DocumentsTable'

export function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentOut[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      setDocs(await listDocuments())
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  // Polling automático mientras haya pending/processing
  useEffect(() => {
    const inFlight = docs.some(
      (d) => d.status === 'pending' || d.status === 'processing'
    )
    if (!inFlight) return
    const id = setInterval(refresh, 2000)
    return () => clearInterval(id)
  }, [docs, refresh])

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-[40px] font-semibold tracking-tight text-[var(--color-ink)]">
          Documentos
        </h1>
        <p className="mt-2 text-[17px] text-[var(--color-ink-muted)]">
          Sube disposiciones administrativas en PDF para indexarlas y consultarlas en el chat.
        </p>
      </header>
      <Uploader onUploaded={refresh} />
      {loading ? (
        <div className="text-[var(--color-ink-muted)]">Cargando…</div>
      ) : (
        <DocumentsTable documents={docs} onChanged={refresh} />
      )}
    </div>
  )
}
