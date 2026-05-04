import type { DocumentStatus } from '../types'
import { statusLabel } from '../lib/utils'

const STYLE: Record<DocumentStatus, string> = {
  indexed:
    'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-500/30',
  processing:
    'bg-blue-50 text-blue-700 ring-blue-200 animate-pulse dark:bg-blue-500/10 dark:text-blue-300 dark:ring-blue-500/30',
  ocr_processing:
    'bg-violet-50 text-violet-700 ring-violet-200 animate-pulse dark:bg-violet-500/10 dark:text-violet-300 dark:ring-violet-500/30',
  pending:
    'bg-zinc-100 text-zinc-600 ring-zinc-200 dark:bg-zinc-500/10 dark:text-zinc-300 dark:ring-zinc-500/30',
  requires_ocr:
    'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-500/30',
  error:
    'bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-500/30',
}

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 text-xs font-medium tracking-wide rounded-full ring-1 ring-inset ${STYLE[status]}`}
    >
      {statusLabel(status)}
    </span>
  )
}
