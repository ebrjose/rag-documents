import { useEffect, useRef, useState } from 'react'
import { ArrowUp, FileText, Sparkles } from 'lucide-react'
import type { Citation, DocumentOut } from '../types'
import { fileUrl, listDocuments, streamChat } from '../lib/api'

const SUGGESTIONS = [
  '¿Qué establece la disposición sobre viáticos para viajes de servicio?',
  '¿Cuáles son los requisitos para solicitar un viaje oficial?',
  '¿Qué reglas se aplican a los consultores contratados por la Secretaría General?',
]

type Message =
  | { role: 'user'; text: string }
  | { role: 'assistant'; text: string; citations: Citation[]; streaming: boolean }

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [hasIndexed, setHasIndexed] = useState<boolean | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    listDocuments()
      .then((ds: DocumentOut[]) => setHasIndexed(ds.some((d) => d.status === 'indexed')))
      .catch(() => setHasIndexed(false))
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function send(textOverride?: string) {
    const q = (textOverride ?? input).trim()
    if (!q || busy) return
    if (textOverride === undefined) setInput('')
    setBusy(true)
    setMessages((m) => [
      ...m,
      { role: 'user', text: q },
      { role: 'assistant', text: '', citations: [], streaming: true },
    ])
    try {
      await streamChat(q, {
        onToken: (t) =>
          setMessages((m) => {
            const next = [...m]
            const last = next[next.length - 1] as Extract<Message, { role: 'assistant' }>
            next[next.length - 1] = { ...last, text: last.text + t }
            return next
          }),
        onCitations: (cs) =>
          setMessages((m) => {
            const next = [...m]
            const last = next[next.length - 1] as Extract<Message, { role: 'assistant' }>
            next[next.length - 1] = { ...last, citations: cs }
            return next
          }),
        onDone: () =>
          setMessages((m) => {
            const next = [...m]
            const last = next[next.length - 1] as Extract<Message, { role: 'assistant' }>
            next[next.length - 1] = { ...last, streaming: false }
            return next
          }),
        onError: (msg) =>
          setMessages((m) => {
            const next = [...m]
            const last = next[next.length - 1] as Extract<Message, { role: 'assistant' }>
            next[next.length - 1] = { ...last, text: `Error: ${msg}`, streaming: false }
            return next
          }),
      })
    } finally {
      setBusy(false)
    }
  }

  if (hasIndexed === false) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="mb-4 rounded-full bg-[color-mix(in_oklab,var(--color-accent)_8%,white)] p-4">
          <FileText className="h-7 w-7 text-[var(--color-accent)]" strokeWidth={1.5} />
        </div>
        <h2 className="text-[24px] font-semibold tracking-tight">Aún no hay documentos indexados</h2>
        <p className="mt-2 text-[var(--color-ink-muted)]">
          Sube algunas disposiciones para empezar a hacer preguntas.
        </p>
        <a
          href="#documents"
          onClick={(e) => {
            e.preventDefault()
            window.dispatchEvent(new CustomEvent('go', { detail: 'documents' }))
          }}
          className="mt-6 inline-flex items-center rounded-full bg-[var(--color-accent)] px-5 py-2 text-[15px] font-medium text-white hover:bg-[var(--color-accent-hover)]"
        >
          Ir a Documentos
        </a>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-140px)] flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto pb-6">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center px-4 text-center">
            <h2 className="text-[28px] font-semibold tracking-tight">¿En qué te puedo ayudar?</h2>
            <p className="mt-2 max-w-md text-[var(--color-ink-muted)]">
              Pregunta en lenguaje natural sobre el contenido de las disposiciones cargadas.
            </p>
            <div className="mt-8 flex w-full max-w-2xl flex-col gap-2">
              <div className="mb-1 flex items-center gap-1.5 text-[12px] font-medium uppercase tracking-wider text-[var(--color-ink-soft)]">
                <Sparkles className="h-3 w-3" strokeWidth={1.7} />
                Sugerencias
              </div>
              {SUGGESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  disabled={busy}
                  className="group flex items-center justify-between gap-3 rounded-2xl border border-[var(--color-rule)] bg-[var(--color-paper)] px-4 py-3 text-left text-[14.5px] text-[var(--color-ink)] transition-all hover:border-[var(--color-ink-soft)] hover:shadow-sm disabled:opacity-50"
                >
                  <span>{q}</span>
                  <ArrowUp className="h-3.5 w-3.5 rotate-45 text-[var(--color-ink-soft)] transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--color-accent)]" strokeWidth={1.8} />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-6 px-2 pt-4">
            {messages.map((m, i) => (
              <MessageView key={i} m={m} />
            ))}
          </div>
        )}
      </div>

      <div className="mx-auto w-full max-w-3xl">
        <div className="flex items-end gap-2 rounded-3xl border border-[var(--color-rule)] bg-[var(--color-paper)] p-2 pl-5 shadow-sm focus-within:border-[var(--color-ink-soft)]">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            placeholder="Pregunta algo sobre las disposiciones…"
            rows={1}
            className="max-h-40 flex-1 resize-none bg-transparent py-2.5 outline-none placeholder:text-[var(--color-ink-soft)]"
          />
          <button
            onClick={() => send()}
            disabled={busy || !input.trim()}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] disabled:opacity-30 transition-opacity"
            aria-label="Enviar"
          >
            <ArrowUp className="h-4 w-4" strokeWidth={2.2} />
          </button>
        </div>
        <div className="mt-2 px-2 text-[12px] text-[var(--color-ink-soft)]">
          Las respuestas se basan únicamente en los documentos indexados.
        </div>
      </div>
    </div>
  )
}

function MessageView({ m }: { m: Message }) {
  if (m.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-3xl bg-[var(--color-accent)] px-5 py-3 text-[15px] text-white shadow-sm">
          {m.text}
        </div>
      </div>
    )
  }
  return (
    <div className="space-y-2">
      <div className="whitespace-pre-wrap text-[15.5px] leading-relaxed text-[var(--color-ink)]">
        {m.text}
        {m.streaming && <span className="ml-0.5 inline-block h-4 w-2 animate-pulse bg-[var(--color-ink-soft)] align-middle" />}
      </div>
      {m.citations.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-2">
          {m.citations.map((c, i) => (
            <a
              key={i}
              href={fileUrl(c.document_id)}
              target="_blank"
              rel="noreferrer"
              className="group inline-flex items-center gap-1.5 rounded-full border border-[var(--color-rule)] bg-[var(--color-paper)] px-3 py-1 text-[12.5px] text-[var(--color-ink-muted)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] transition-colors"
            >
              <FileText className="h-3 w-3" strokeWidth={1.7} />
              <span>{c.filename}</span>
              <span className="text-[var(--color-ink-soft)] group-hover:text-[var(--color-accent)]">· pág. {c.page}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
