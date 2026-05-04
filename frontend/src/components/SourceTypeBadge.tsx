import type { SourceType } from '../types'

const STYLE: Record<SourceType, string> = {
  pdf: 'bg-zinc-100 text-zinc-700 ring-zinc-200 dark:bg-zinc-500/10 dark:text-zinc-300 dark:ring-zinc-500/30',
  docx: 'bg-sky-50 text-sky-700 ring-sky-200 dark:bg-sky-500/10 dark:text-sky-300 dark:ring-sky-500/30',
}

const LABEL: Record<SourceType, string> = {
  pdf: 'PDF',
  docx: 'DOCX',
}

export function SourceTypeBadge({ source }: { source: SourceType }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[11px] font-semibold tracking-wider rounded-md ring-1 ring-inset ${STYLE[source]}`}
    >
      {LABEL[source]}
    </span>
  )
}
