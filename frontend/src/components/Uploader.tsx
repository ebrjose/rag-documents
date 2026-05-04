import { useCallback, useRef, useState } from 'react'
import { AlertCircle, Upload, X } from 'lucide-react'
import { uploadDocuments } from '../lib/api'
import type { UploadResult } from '../types'

export function Uploader({ onUploaded }: { onUploaded: () => void }) {
  const [busy, setBusy] = useState(false)
  const [drag, setDrag] = useState(false)
  const [rejected, setRejected] = useState<UploadResult[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(
    async (files: File[]) => {
      const pdfs = files.filter((f) => /\.pdf$/i.test(f.name))
      if (pdfs.length === 0) return
      setBusy(true)
      try {
        const res = await uploadDocuments(pdfs)
        setRejected(res.results.filter((r) => !r.accepted))
        onUploaded()
      } finally {
        setBusy(false)
      }
    },
    [onUploaded]
  )

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDrag(true)
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDrag(false)
          handleFiles(Array.from(e.dataTransfer.files))
        }}
        onClick={() => inputRef.current?.click()}
        className={`group relative cursor-pointer rounded-2xl border border-dashed transition-all px-8 py-14 text-center ${
          drag
            ? 'border-[var(--color-accent)] bg-[color-mix(in_oklab,var(--color-accent)_6%,transparent)]'
            : 'border-[var(--color-rule)] bg-[var(--color-paper)] hover:border-[var(--color-ink-soft)]'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={(e) =>
            e.target.files && handleFiles(Array.from(e.target.files))
          }
        />
        <div className="flex flex-col items-center gap-3">
          <div className="rounded-full bg-[color-mix(in_oklab,var(--color-accent)_8%,transparent)] p-3">
            <Upload className="h-6 w-6 text-[var(--color-accent)]" strokeWidth={1.6} />
          </div>
          <div className="text-[15px] font-medium text-[var(--color-ink)]">
            {busy ? 'Subiendo…' : 'Arrastra PDFs aquí o haz clic para seleccionar'}
          </div>
          <div className="text-[13px] text-[var(--color-ink-muted)]">
            Hasta 20 archivos. Solo PDFs con texto extraíble.
          </div>
        </div>
      </div>

      {rejected.length > 0 && (
        <RejectedPanel results={rejected} onDismiss={() => setRejected([])} />
      )}
    </div>
  )
}

function RejectedPanel({
  results,
  onDismiss,
}: {
  results: UploadResult[]
  onDismiss: () => void
}) {
  const headline =
    results.length === 1
      ? '1 archivo no se procesó'
      : `${results.length} archivos no se procesaron`
  return (
    <div className="relative rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-500/30 dark:bg-amber-500/10">
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Cerrar"
        className="absolute right-2.5 top-2.5 rounded-full p-1 text-amber-700 transition-colors hover:bg-amber-100 dark:text-amber-300 dark:hover:bg-amber-500/20"
      >
        <X className="h-3.5 w-3.5" strokeWidth={2} />
      </button>
      <div className="mb-1.5 flex items-center gap-2 text-amber-800 dark:text-amber-200">
        <AlertCircle className="h-4 w-4" strokeWidth={1.7} />
        <span className="text-[13px] font-semibold">{headline}</span>
      </div>
      <ul className="space-y-0.5 pl-6 text-[13.5px]">
        {results.map((r, i) => (
          <li key={i} className="flex flex-wrap items-baseline gap-x-1.5 text-amber-900 dark:text-amber-100/90">
            <span className="font-medium">{r.filename}</span>
            <span className="text-amber-700 dark:text-amber-300/80">— {r.reason}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
