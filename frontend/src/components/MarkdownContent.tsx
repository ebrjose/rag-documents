import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * Renderiza markdown con estilos consistentes con la paleta de la app
 * (Apple-ish, escala tipográfica suave, sin contornos pesados). Los links
 * van al color de acento; el código y tablas se diferencian sutilmente.
 *
 * Pensado para mensajes del asistente. Tolera markdown incompleto durante
 * streaming — react-markdown rerendea progresivamente.
 */
export function MarkdownContent({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => (
          <p className="my-2 first:mt-0 last:mb-0 text-[15.5px] leading-relaxed text-[var(--color-ink)]">
            {children}
          </p>
        ),
        h1: ({ children }) => (
          <h1 className="mt-4 mb-2 text-[20px] font-semibold tracking-tight text-[var(--color-ink)] first:mt-0">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="mt-4 mb-2 text-[18px] font-semibold tracking-tight text-[var(--color-ink)] first:mt-0">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="mt-3 mb-1.5 text-[16.5px] font-semibold tracking-tight text-[var(--color-ink)] first:mt-0">
            {children}
          </h3>
        ),
        ul: ({ children }) => (
          <ul className="my-2 ml-5 list-disc space-y-1 text-[15.5px] leading-relaxed marker:text-[var(--color-ink-soft)]">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="my-2 ml-5 list-decimal space-y-1 text-[15.5px] leading-relaxed marker:text-[var(--color-ink-soft)]">
            {children}
          </ol>
        ),
        li: ({ children }) => <li className="pl-1">{children}</li>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="text-[var(--color-accent)] underline-offset-2 hover:underline hover:text-[var(--color-accent-hover)]"
          >
            {children}
          </a>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-[var(--color-ink)]">{children}</strong>
        ),
        em: ({ children }) => <em className="italic">{children}</em>,
        code: ({ className, children, ...props }) => {
          const isBlock = /language-/.test(className || '')
          if (isBlock) {
            return (
              <code className={`${className ?? ''} font-mono text-[13.5px]`} {...props}>
                {children}
              </code>
            )
          }
          return (
            <code className="rounded-md bg-[color-mix(in_oklab,var(--color-ink)_8%,transparent)] px-1.5 py-0.5 font-mono text-[0.9em]">
              {children}
            </code>
          )
        },
        pre: ({ children }) => (
          <pre className="my-3 overflow-x-auto rounded-xl border border-[var(--color-rule)] bg-[var(--color-paper-soft)] p-3 text-[13.5px] leading-relaxed">
            {children}
          </pre>
        ),
        blockquote: ({ children }) => (
          <blockquote className="my-3 border-l-2 border-[var(--color-rule)] pl-3 text-[var(--color-ink-muted)] italic">
            {children}
          </blockquote>
        ),
        hr: () => <hr className="my-4 border-[var(--color-rule)]" />,
        table: ({ children }) => (
          <div className="my-3 overflow-x-auto">
            <table className="min-w-full border-collapse text-[14px]">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="border-b border-[var(--color-rule)] text-left text-[12px] font-medium uppercase tracking-wider text-[var(--color-ink-muted)]">
            {children}
          </thead>
        ),
        th: ({ children }) => <th className="px-3 py-2">{children}</th>,
        td: ({ children }) => (
          <td className="border-b border-[var(--color-rule)] px-3 py-2 align-top">{children}</td>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  )
}
