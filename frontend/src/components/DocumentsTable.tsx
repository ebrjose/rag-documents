import { useMemo, useState } from 'react'
import { Trash2 } from 'lucide-react'
import type { DocumentOut } from '../types'
import { StatusBadge } from './StatusBadge'
import { SourceTypeBadge } from './SourceTypeBadge'
import { OcrMarker } from './OcrMarker'
import { formatDate } from '../lib/utils'
import { deleteDocument, fileUrl } from '../lib/api'

type SortKey = 'filename' | 'source_type' | 'status' | 'uploaded_at'

export function DocumentsTable({
  documents,
  onChanged,
}: {
  documents: DocumentOut[]
  onChanged: () => void
}) {
  const [sortKey, setSortKey] = useState<SortKey>('uploaded_at')
  const [sortAsc, setSortAsc] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)

  const sorted = useMemo(() => {
    const arr = [...documents]
    arr.sort((a, b) => {
      const A = (a as any)[sortKey] ?? ''
      const B = (b as any)[sortKey] ?? ''
      if (A < B) return sortAsc ? -1 : 1
      if (A > B) return sortAsc ? 1 : -1
      return 0
    })
    return arr
  }, [documents, sortKey, sortAsc])

  function toggleSort(k: SortKey) {
    if (sortKey === k) setSortAsc(!sortAsc)
    else {
      setSortKey(k)
      setSortAsc(true)
    }
  }

  async function handleDelete(d: DocumentOut) {
    if (!confirm(`¿Eliminar "${d.filename}"? Esta acción no se puede deshacer.`)) return
    setDeleting(d.document_id)
    try {
      await deleteDocument(d.document_id)
      onChanged()
    } finally {
      setDeleting(null)
    }
  }

  if (documents.length === 0) {
    return (
      <div className="rounded-2xl border border-[var(--color-rule)] bg-[var(--color-paper)] p-12 text-center">
        <div className="text-[15px] text-[var(--color-ink-muted)]">
          No hay documentos cargados todavía.
        </div>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-[var(--color-rule)] bg-[var(--color-paper)]">
      <table className="w-full text-[14px]">
        <thead className="border-b border-[var(--color-rule)] bg-[var(--color-paper-soft)]">
          <tr className="text-left text-[12px] font-medium uppercase tracking-wider text-[var(--color-ink-muted)]">
            <Th onClick={() => toggleSort('filename')} active={sortKey === 'filename'} asc={sortAsc}>
              Archivo
            </Th>
            <Th onClick={() => toggleSort('source_type')} active={sortKey === 'source_type'} asc={sortAsc}>
              Tipo
            </Th>
            <Th onClick={() => toggleSort('status')} active={sortKey === 'status'} asc={sortAsc}>
              Estado
            </Th>
            <th className="px-4 py-3 text-right">Páginas</th>
            <th className="px-4 py-3 text-right">Chunks</th>
            <Th onClick={() => toggleSort('uploaded_at')} active={sortKey === 'uploaded_at'} asc={sortAsc}>
              Subido
            </Th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-rule)]">
          {sorted.map((d) => (
            <tr key={d.document_id} className="hover:bg-[var(--color-paper-soft)] transition-colors">
              <td className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <a
                    href={fileUrl(d.document_id)}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-[var(--color-accent)] underline-offset-2 hover:underline hover:text-[var(--color-accent-hover)]"
                  >
                    {d.filename}
                  </a>
                  {d.used_ocr && <OcrMarker />}
                </div>
                {d.error_message && (
                  <div className="mt-0.5 text-[12px] text-[var(--color-ink-muted)]">
                    {d.error_message}
                  </div>
                )}
              </td>
              <td className="px-4 py-3"><SourceTypeBadge source={d.source_type} /></td>
              <td className="px-4 py-3"><StatusBadge status={d.status} /></td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-ink-muted)]">
                {d.page_count ?? '—'}
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-ink-muted)]">
                {d.chunk_count ?? '—'}
              </td>
              <td className="px-4 py-3 text-[var(--color-ink-muted)]">{formatDate(d.uploaded_at)}</td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => handleDelete(d)}
                  disabled={deleting === d.document_id}
                  className="rounded-full p-1.5 text-[var(--color-ink-soft)] hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/10 dark:hover:text-rose-400 disabled:opacity-50 transition-colors"
                  aria-label="Eliminar"
                >
                  <Trash2 className="h-4 w-4" strokeWidth={1.6} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Th({
  children,
  onClick,
  active,
  asc,
}: {
  children: React.ReactNode
  onClick: () => void
  active: boolean
  asc: boolean
}) {
  return (
    <th
      onClick={onClick}
      className="cursor-pointer px-4 py-3 select-none hover:text-[var(--color-ink)]"
    >
      {children}
      {active && <span className="ml-1">{asc ? '↑' : '↓'}</span>}
    </th>
  )
}
