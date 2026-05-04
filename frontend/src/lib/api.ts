import type { DocumentOut, UploadResponse } from '../types'

const BASE = ''

export async function listDocuments(): Promise<DocumentOut[]> {
  const r = await fetch(`${BASE}/api/documents`)
  if (!r.ok) throw new Error(`list documents failed: ${r.status}`)
  return r.json()
}

export async function uploadDocuments(files: File[]): Promise<UploadResponse> {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  const r = await fetch(`${BASE}/api/documents`, { method: 'POST', body: fd })
  if (!r.ok) throw new Error(`upload failed: ${r.status}`)
  return r.json()
}

export async function deleteDocument(id: string): Promise<void> {
  const r = await fetch(`${BASE}/api/documents/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`delete failed: ${r.status}`)
}

export function fileUrl(id: string): string {
  return `${BASE}/api/documents/${id}/file`
}

export interface ChatStreamHandlers {
  onToken: (text: string) => void
  onCitations: (citations: { document_id: string; filename: string; page: number }[]) => void
  onDone: () => void
  onError: (msg: string) => void
}

export async function streamChat(question: string, handlers: ChatStreamHandlers, signal?: AbortSignal) {
  const r = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    signal,
  })
  if (!r.ok || !r.body) {
    handlers.onError(`HTTP ${r.status}`)
    return
  }
  const reader = r.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      const block = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const lines = block.split('\n')
      let event = 'message'
      let data = ''
      for (const line of lines) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) data += line.slice(5).trim()
      }
      if (!data) continue
      try {
        const obj = JSON.parse(data)
        if (event === 'token') handlers.onToken(obj.text || '')
        else if (event === 'citations') handlers.onCitations(obj.citations || [])
        else if (event === 'done') handlers.onDone()
        else if (event === 'error') handlers.onError(obj.message || 'error')
      } catch {
        // ignore parse errors
      }
    }
  }
}
