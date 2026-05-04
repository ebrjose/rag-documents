export function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('es-PE', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function statusLabel(s: string): string {
  return (
    {
      pending: 'Pendiente',
      processing: 'Procesando',
      indexed: 'Indexado',
      error: 'Error',
      requires_ocr: 'Requiere OCR',
    } as Record<string, string>
  )[s] ?? s
}
