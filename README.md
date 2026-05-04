# RAG de Disposiciones Administrativas

Sistema RAG local para consultar disposiciones administrativas en lenguaje natural, con citas verificables al PDF y página de origen. Modelos 100% locales (Ollama en RTX 5090).

## Especificaciones

La fuente de verdad del proyecto vive en `specs/`:

- **`specs/requirements.md`** — qué hace el sistema y por qué.
- **`specs/design.md`** — cómo está construido (stack, ADRs, contratos).
- **`specs/production.md`** — perfil productivo (post-MVP, hardware dedicado, reranker).
- **`specs/tasks.md`** — plan incremental de implementación.
- **`specs/api.md`** — contrato HTTP (pendiente Fase 1).

## Stack

**Backend:** Python 3.12 · FastAPI · Qdrant · SQLite · PyMuPDF · Ollama
**Frontend:** React 19 · Vite · TypeScript · TanStack (Router/Query/Table) · assistant-ui · Tailwind v4 · Radix
**Modelos:** `gemma4:31b` (chat) · `qwen3-embedding:4b` (embeddings)

## Estado

En planificación. Siguiendo enfoque **API-first** (ver `design.md` ADR-013): contrato API → frontend con mocks → backend → integración.

## Setup local

Pendiente. Ver `specs/tasks.md` Fase 0.
