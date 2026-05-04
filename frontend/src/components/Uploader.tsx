import { useCallback, useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import { uploadDocuments } from '../lib/api'

export function Uploader({ onUploaded }: { onUploaded: () => void }) {
  const [busy, setBusy] = useState(false)
  const [drag, setDrag] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(
    async (files: File[]) => {
      const pdfs = files.filter((f) => /\.pdf$/i.test(f.name))
      if (pdfs.length === 0) return
      setBusy(true)
      try {
        await uploadDocuments(pdfs)
        onUploaded()
      } finally {
        setBusy(false)
      }
    },
    [onUploaded]
  )

  return (
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
          ? 'border-[var(--color-accent)] bg-[color-mix(in_oklab,var(--color-accent)_6%,white)]'
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
        <div className="rounded-full bg-[color-mix(in_oklab,var(--color-accent)_8%,white)] p-3">
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
  )
}
