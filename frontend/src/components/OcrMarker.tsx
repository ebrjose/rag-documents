import { ScanLine } from 'lucide-react'

export function OcrMarker() {
  return (
    <span
      title="Indexado vía OCR (PDF escaneado)"
      className="inline-flex items-center gap-1 rounded-md bg-violet-50 px-1.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider text-violet-700 ring-1 ring-inset ring-violet-200 dark:bg-violet-500/10 dark:text-violet-300 dark:ring-violet-500/30"
    >
      <ScanLine className="h-2.5 w-2.5" strokeWidth={2.2} />
      OCR
    </span>
  )
}
