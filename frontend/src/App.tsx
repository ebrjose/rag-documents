import { useEffect, useState } from 'react'
import { FileText, MessageSquare, Moon, Sun } from 'lucide-react'
import { DocumentsPage } from './pages/DocumentsPage'
import { ChatPage } from './pages/ChatPage'
import { useTheme } from './lib/theme'

type Page = 'documents' | 'chat'

export default function App() {
  const [page, setPage] = useState<Page>('chat')
  const { theme, toggle } = useTheme()

  useEffect(() => {
    const handler = (e: Event) => {
      const target = (e as CustomEvent<string>).detail as Page
      if (target === 'documents' || target === 'chat') setPage(target)
    }
    window.addEventListener('go', handler as EventListener)
    return () => window.removeEventListener('go', handler as EventListener)
  }, [])

  return (
    <div className="min-h-screen bg-[var(--color-paper-soft)]">
      <header className="sticky top-0 z-30 border-b border-[var(--color-rule)] bg-[color-mix(in_oklab,var(--color-paper)_85%,transparent)] backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-[var(--color-accent)]" />
            <span className="text-[15px] font-semibold tracking-tight">Disposiciones · RAG</span>
          </div>
          <div className="flex items-center gap-3">
            <nav className="flex items-center gap-1 rounded-full bg-[var(--color-paper)] p-1 ring-1 ring-[var(--color-rule)]">
              <NavTab active={page === 'documents'} onClick={() => setPage('documents')} icon={<FileText className="h-3.5 w-3.5" strokeWidth={1.6} />}>
                Documentos
              </NavTab>
              <NavTab active={page === 'chat'} onClick={() => setPage('chat')} icon={<MessageSquare className="h-3.5 w-3.5" strokeWidth={1.6} />}>
                Chat
              </NavTab>
            </nav>
            <button
              onClick={toggle}
              aria-label={theme === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
              title={theme === 'dark' ? 'Tema claro' : 'Tema oscuro'}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-paper)] text-[var(--color-ink-muted)] ring-1 ring-[var(--color-rule)] hover:text-[var(--color-ink)] transition-colors"
            >
              {theme === 'dark' ? (
                <Sun className="h-4 w-4" strokeWidth={1.7} />
              ) : (
                <Moon className="h-4 w-4" strokeWidth={1.7} />
              )}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-10">
        {page === 'documents' ? <DocumentsPage /> : <ChatPage />}
      </main>
    </div>
  )
}

function NavTab({
  children,
  active,
  onClick,
  icon,
}: {
  children: React.ReactNode
  active: boolean
  onClick: () => void
  icon: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[13.5px] font-medium transition-all ${
        active
          ? 'bg-[var(--color-ink)] text-[var(--color-paper)] dark:bg-white/10 dark:text-[var(--color-ink)]'
          : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]'
      }`}
    >
      {icon}
      {children}
    </button>
  )
}
