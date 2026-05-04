import { useCallback, useEffect, useState } from 'react'
import type { DocumentOut, DocumentStatus } from '../types'
import { listDocuments } from '../lib/api'
import { Uploader } from '../components/Uploader'
import { DocumentsTable } from '../components/DocumentsTable'

const POLLING_INTERVAL_MS = 2000
const IN_PROGRESS_STATUSES = new Set<DocumentStatus>([
  'pending',
  'processing',
  'ocr_processing',
])

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

  // Polling automático mientras algún documento esté en algún paso del pipeline
  useEffect(() => {
    const inFlight = docs.some((d) => IN_PROGRESS_STATUSES.has(d.status))
    if (!inFlight) return
    const id = setInterval(refresh, POLLING_INTERVAL_MS)
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
