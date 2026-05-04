# Tasks — RAG de Disposiciones Administrativas (MVP)

> Plan incremental por fases (enfoque **API-first** — ADR-013).
> Cada fase termina con algo verificable manualmente, no con "el módulo X implementado".
> Orden pensado para validar incertidumbre temprano: contrato API → frontend con mocks → backend → integración.

## Fase 0 — Decisiones bloqueantes y bootstrap

**Objetivo.** Resolver TBDs del `design.md` y dejar el proyecto listo.

- [ ] **0.1** Confirmar modelo de embeddings → `qwen3-embedding:4b` (ya descargado en `homelab`, alineado con `production.md`). Medir tiempo de embedding sobre 10 párrafos en español como sanity check.
- [ ] **0.2** Decidir modelo LLM entre `gpt-oss:20b` y `gemma4:31b` (ambos descargados en `homelab`). Probar con preguntas de muestra contra texto pegado a mano (sin RAG todavía).
- [x] **0.3** Ollama accesible en `homelab` (mismo host que el backend): `curl http://localhost:11434/api/tags` responde con los modelos descargados.
- [ ] **0.4** Confirmar política de duplicados (ADR-008: rechazar).
- [ ] **0.5** Inicializar `pyproject.toml` con dependencias backend (FastAPI, uvicorn, qdrant-client[fastembed], pymupdf, httpx, pydantic-settings, **`psycopg[binary]>=3`**).
- [ ] **0.6** Inicializar `frontend/` con Vite + React + TS (`npm create vite@latest frontend -- --template react-ts`).
- [ ] **0.7** Crear `.env.example` (backend) y `frontend/.env.example` con todas las variables del `design.md` §8.
- [ ] **0.8** `.gitignore` (`volumes/`, `.venv`, `node_modules`, `dist`, `.env`).
- [ ] **0.9** Crear `docker-compose.yml` con servicios `postgres` (`postgres:16-alpine`, puerto 5432, volumen `./volumes/postgres`, healthcheck `pg_isready`) y `qdrant` (`qdrant/qdrant`, puertos 6333/6334, volumen `./volumes/qdrant`).
- [ ] **0.10** Crear `docker/postgres/init.sql` con el esquema de `design.md` §4 + `CREATE EXTENSION IF NOT EXISTS pgcrypto;`. Montar en `/docker-entrypoint-initdb.d/` del servicio Postgres.

**Verificable.** `uv sync` instala backend; `npm install` en `frontend/` no rompe; `curl http://localhost:11434/api/tags` responde; `docker compose up -d` levanta Postgres + Qdrant; `psql $DATABASE_URL -c '\dt'` muestra `documents`; `curl http://localhost:6333/collections` responde.

---

## Fase 1 — Contrato API (`specs/api.md`)

**Objetivo.** Formalizar el contrato HTTP completo antes de implementar nada.

- [ ] **1.1** Para cada endpoint de `design.md` §7, documentar en `specs/api.md`:
  - Método, path, descripción.
  - Request: headers, query params, body (JSON schema o multipart).
  - Response success: status, headers, body con ejemplo JSON real.
  - Response errores: códigos HTTP, body de error.
- [ ] **1.2** Documentar protocolo SSE de `/api/chat`:
  - Formato exacto de cada evento (`token`, `citations`, `done`, `error`).
  - Ejemplo de stream completo.
- [ ] **1.3** Definir tipos TypeScript en `frontend/src/types.ts` espejo de los Pydantic (sin generador automático todavía; manual).
- [ ] **1.4** Revisión final del contrato leyendo flujos completos: "subir → ver estado → preguntar → ver citas".

**Verificable.** `specs/api.md` revisado y aprobado. Cualquier desarrollador (o agente) puede implementar back y front leyendo solo ese documento.

**Hito de decisión.** Antes de avanzar, ¿el contrato cubre todos los flujos del MVP? Si falta algo, mejor agregarlo aquí.

---

## Fase 2 — Frontend con mocks

**Objetivo.** Frontend completo y demostrable, funcionando con mocks. Cero backend todavía.

### 2.A — Setup base
- [ ] **2.A.1** Instalar dependencias frontend: `tanstack-router`, `tanstack-query`, `tanstack-table`, `react-dropzone`, `@assistant-ui/react`, `@radix-ui/*` (lo que se use), `motion`, `tailwindcss@v4`, `@microsoft/fetch-event-source`, `lucide-react`, `react-markdown`.
- [ ] **2.A.2** Configurar Tailwind v4 + tokens base (colores, tipografía Inter, spacing, radius).
- [ ] **2.A.3** Configurar TanStack Router con dos rutas: `/documents`, `/chat`. Layout `__root.tsx` con header de navegación.
- [ ] **2.A.4** Configurar TanStack Query (`QueryClient` global).

### 2.B — Mocks
- [ ] **2.B.1** `lib/mocks.ts`: dataset de 5 documentos en distintos estados (`indexed`, `processing`, `error`, `requires_ocr`).
- [ ] **2.B.2** `mockUploadFlow()`: simular paso de `pending` → `processing` → `indexed` en ~3s.
- [ ] **2.B.3** `mockChatStream()`: generador async que emite tokens + evento `citations` + `done`.
- [ ] **2.B.4** `lib/api.ts` con flag `VITE_USE_MOCKS`: si true, devuelve mocks; si false, llama al backend real.

### 2.C — Pantalla "Documentos"
- [ ] **2.C.1** `DocumentUploader`: drag-and-drop con react-dropzone, validación de extensión, feedback visual.
- [ ] **2.C.2** `DocumentsTable`: TanStack Table con columnas (Nombre, Estado, Páginas, Chunks, Subido, Acciones). Sorting.
- [ ] **2.C.3** `StatusBadge`: pill con texto y opacity por estado, sin colores agresivos (ADR-012).
- [ ] **2.C.4** `DeleteDialog`: Radix Dialog de confirmación.
- [ ] **2.C.5** Polling automático con TanStack Query (`refetchInterval` condicional).
- [ ] **2.C.6** Estado vacío con mensaje guía.

### 2.D — Pantalla "Chat"
- [ ] **2.D.1** `lib/runtime.ts`: adapter de assistant-ui que consume nuestro endpoint SSE (mock por ahora).
- [ ] **2.D.2** `ChatThread`: integrar `<Thread />` de assistant-ui con runtime.
- [ ] **2.D.3** Renderizado de citas como links que abren PDF en pestaña nueva.
- [ ] **2.D.4** Estado vacío si no hay docs `indexed`: CTA "Ir a Documentos".

### 2.E — Look final (estética Apple)
- [ ] **2.E.1** Invocar skill `frontend-design` con brief: minimalismo apple.com, tokens del ADR-012, 2 pantallas a refinar.
- [ ] **2.E.2** Aplicar refinamientos: tipografía, espaciado, animaciones de entrada (Motion), micro-interacciones.
- [ ] **2.E.3** Modo oscuro respetando `prefers-color-scheme` + toggle manual.

**Verificable.** Demo en navegador con `VITE_USE_MOCKS=true`:
- Subes 2 PDFs → aparecen como `processing` → cambian a `indexed`.
- Eliminas uno con confirmación.
- Vas a `/chat`, escribes una pregunta → respuesta en streaming token-a-token + citas clicables.
- Sin documentos → mensaje guía.
- Dark mode funciona.

**Hito.** App "se siente real". Lista para mostrarse a stakeholders.

---

## Fase 3 — Backend cumpliendo el contrato

**Objetivo.** Implementar la API tal como está definida en `specs/api.md`.

### 3.A — Infra base
- [ ] **3.A.1** `backend/main.py`: FastAPI + CORSMiddleware (origin: `localhost:5173`) + lifespan.
- [ ] **3.A.2** `backend/settings.py`: `pydantic-settings`.
- [ ] **3.A.3** `backend/schemas.py`: modelos Pydantic exactos al contrato.
- [ ] **3.A.4** `backend/core/catalog.py`: cliente Postgres con `psycopg[binary]>=3` (pool de conexiones, CRUD de `documents`). Esquema ya creado por `init.sql`.
- [ ] **3.A.5** `backend/core/store.py`: cliente Qdrant apuntando a `QDRANT_URL`; crear collection `disposiciones` con vector denso + sparse si no existe.
- [ ] **3.A.6** `backend/core/ollama_client.py`: wrapper httpx (`embed`, `chat` streaming).

### 3.B — Pipeline RAG
- [ ] **3.B.1** `extract.py`: PyMuPDF, `(page_number, text)` por página.
- [ ] **3.B.2** `chunk.py`: splitter recursivo (párrafo → oración → carácter), 500 tokens, overlap 75, preserva `page_start`/`page_end`.
- [ ] **3.B.3** `ingest.py`: orquesta validar → hash → SQLite insert → extract → chunk → embed → upsert Qdrant → SQLite update. Background task.
- [ ] **3.B.4** Detección PDF sin texto → `requires_ocr`.
- [ ] **3.B.5** `retrieve.py`: hybrid search con filtro por `document_id` (solo `indexed`).
- [ ] **3.B.6** `generate.py`: arma prompt + llamada Ollama streaming.

### 3.C — Endpoints
- [ ] **3.C.1** `routers/documents.py`: POST (multipart), GET (lista), GET (detalle), GET (file), DELETE.
- [ ] **3.C.2** `routers/chat.py`: POST con `StreamingResponse` SSE. Eventos `token`, `citations`, `done`, `error`.
- [ ] **3.C.3** `routers/health.py`: ping Ollama y Qdrant.
- [ ] **3.C.4** Validar respuestas contra `specs/api.md` con `curl` / Swagger UI.

**Verificable.** Con `curl` o `/docs`:
- POST PDF → `document_id` en respuesta. SQLite y disco actualizados.
- GET lista → estados cambian correctamente.
- POST chat → tokens en SSE + citations al final.
- DELETE → desaparece del listado y de Qdrant.

---

## Fase 4 — Integración y validación

**Objetivo.** Cambiar mocks por backend real. Cumplir criterios de aceptación de `requirements.md` §7.

- [ ] **4.1** En `frontend/.env`: `VITE_USE_MOCKS=false`.
- [ ] **4.2** Probar flujo end-to-end: subir PDF real → indexa → preguntar → respuesta con citas.
- [ ] **4.3** Ajustar discrepancias entre mocks y backend real (campos, formatos).
- [ ] **4.4** Seleccionar 20–30 disposiciones reales válidas (evitar placeholders, priorizar nativos).
- [ ] **4.5** Cargarlas vía la UI.
- [ ] **4.6** Preparar 10 preguntas representativas (mezcla específicas + temáticas).
- [ ] **4.7** Ejecutar y registrar en `specs/validation.md`: pregunta, respuesta, citas, valoración.
- [ ] **4.8** Calcular % de aciertos. Si <70%, iterar sobre chunking / modelo / prompt.

**Verificable.** `specs/validation.md` con resultados. Decisión explícita: ¿el MVP valida la idea?

---

## Out of scope (post-MVP)

- Reranker (cross-encoder).
- Adjacent chunks en retrieval.
- Múltiples extractores PDF (bookmarks, layout).
- OCR (Tesseract / PaddleOCR).
- Importación masiva del corpus + metadata desde el CSV.
- Autenticación, multi-tenant.
- Despliegue (Docker, systemd, reverse proxy, static serve del frontend desde FastAPI).
- Observabilidad (logs estructurados, métricas, tracing).
- Persistencia del historial de chat entre sesiones.

## Convenciones de trabajo

- **Una tarea = un commit (idealmente).** Mensaje en imperativo, prefijo de fase: `feat(F2.C.2): tabla de documentos con TanStack Table`.
- **Cada fase cierra con un commit que actualiza `specs/tasks.md`** marcando los `[x]`.
- **Si una decisión cambia el `design.md`, actualizar el ADR correspondiente en el mismo commit.**
- **Si el contrato API cambia durante Fase 3, actualizar `specs/api.md` ANTES de tocar código.**
- **No saltar fases.** Especialmente Fase 1 (contrato) — saltarla rompe el enfoque API-first.
