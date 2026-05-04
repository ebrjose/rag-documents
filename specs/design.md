# Design — RAG de Disposiciones Administrativas (MVP)

> Documento de **CÓMO**. Acompaña a `requirements.md` (QUÉ y POR QUÉ).
> Las decisiones aquí registradas son revisables; cada cambio significativo debe quedar reflejado en este archivo (no en commits silenciosos).

## 1. Visión general

```
┌─────────────────────────────────────┐
│  Frontend React (Vite + TS)         │
│  - Pantalla "Documentos"            │
│  - Pantalla "Chat"                  │
└────────────────┬────────────────────┘
                 │ HTTP/JSON + SSE (contrato fijo)
                 ▼
┌─────────────────────────────────────┐
│  Backend FastAPI                    │
│  - Documents API                    │
│  - Chat API (SSE)                   │
│  - Health                           │
└──┬───────────┬───────────┬──────────┘
   │           │           │
   ▼           ▼           ▼
┌────────┐  ┌────────┐  ┌──────────────┐
│ Qdrant │  │ SQLite │  │ Ollama (LAN) │ ← RTX 5090
│ local  │  │ catálo │  │  - Embeddings│
│ (vec)  │  │ go doc │  │  - LLM       │
└────────┘  └────────┘  └──────────────┘
```

Backend FastAPI único. Qdrant en modo embebido (vectores). SQLite (catálogo de documentos y estados). Ollama en la máquina con la RTX 5090, accesible por LAN. Frontend React desacoplado: solo consume la API HTTP.

**Enfoque de desarrollo: API-first.** El contrato HTTP se define antes de implementar back o front. Frontend se construye contra mocks; backend cumple el contrato. Detalles en ADR-013.

## 2. Stack tecnológico

### Backend

| Capa | Elección | Justificación |
|---|---|---|
| Lenguaje | Python 3.12+ | Ecosistema RAG maduro |
| Paquetes | uv | Rápido, lockfile claro, ya en uso |
| Web framework | FastAPI | Async nativo, OpenAPI gratis, SSE simple |
| ASGI | uvicorn | Estándar |
| Vector store | Qdrant embebido | Hybrid search RRF nativo, mismo API local/remoto |
| Cliente Qdrant | qdrant-client[fastembed] | Soporte oficial, BM25 vía FastEmbed |
| Catálogo | SQLite (stdlib) | Estado de documentos, sin servidor (ADR-009) |
| Parsing PDF | PyMuPDF (`pymupdf`) | Mejor que pypdf, preserva páginas |
| Embeddings + LLM | Ollama (REST) → modelos TBD | Local, en RTX 5090 |
| Cliente Ollama | httpx | Sin SDK; control total sobre streaming |
| Validación | Pydantic v2 | Estándar FastAPI |
| Logging | stdlib + structlog | Sin overkill |

### Frontend

| Capa | Elección | Justificación |
|---|---|---|
| Build tool | Vite | Estándar 2026, HMR rapidísimo |
| Lenguaje | TypeScript | API tipada, vale la pena |
| Framework | React 19 | Última estable |
| Routing | TanStack Router | Type-safe, ideal para 2 páginas con futuro crecimiento |
| Data fetching | TanStack Query | Caching, polling automático, estándar |
| Tabla documentos | TanStack Table (headless) | Look 100% custom (ADR-010) |
| Uploader | react-dropzone | Universal, simple |
| Chat | **assistant-ui** | Librería específica para chats con LLM (ADR-011) |
| Streaming SSE | `@microsoft/fetch-event-source` | Mejor que EventSource nativo |
| Estilos | Tailwind CSS v4 | Velocidad de iteración |
| Primitivos UI | Radix UI (Dialog, Toast, Tooltip, Dropdown) | Accesibilidad lista, look custom |
| Animaciones | Motion (ex Framer Motion) | Transiciones tipo Apple |
| Tipografía | Inter (web) + SF Pro nativo en macOS | SF Pro no es libre fuera de Apple |
| Iconos | lucide-react (`stroke-width={1.5}`) | Cercano a SF Symbols con stroke fino |
| Markdown | react-markdown | Respuestas del LLM |

### Pendiente decidir (TBD, Fase 0)

- Modelo de embeddings (candidatos: `bge-m3`, `nomic-embed-text`, `multilingual-e5`).
- Modelo LLM (candidatos: `gpt-oss-20b`, `qwen2.5:14b`, `gemma`-verificar).
- Política de duplicados (rechazar vs reemplazar) — ADR-008 propone rechazar.

## 3. Decisiones de arquitectura (ADRs)

### ADR-001: Backend FastAPI desacoplado, frontend React
**Contexto.** Frontend y backend con responsabilidades distintas; el frontend final será React.
**Decisión.** Backend FastAPI expone HTTP/JSON+SSE. Frontend React lo consume.
**Consecuencias.** Contratos testables, cualquier cliente (Postman, CLI) puede usar la API. CORS necesario en dev.

### ADR-002: Qdrant embebido en lugar de servicio Docker
**Contexto.** MVP local; Docker añade fricción.
**Decisión.** Qdrant embebido con persistencia en `data/qdrant/`. API idéntica a Qdrant remoto.
**Consecuencias.** Migrar a Qdrant servicio en el futuro = cambiar el constructor. Cero impacto en el resto.

### ADR-003: Hybrid Search (Dense 70% + Sparse 30%)
**Contexto.** Las DAs tienen vocabulario técnico-legal, números de norma, fechas exactas. Búsqueda semántica pura falla con identificadores.
**Decisión.** Hybrid search con fusión RRF (Qdrant nativo). Pesos iniciales 70/30, configurables.
**Consecuencias.** Ingesta genera dos vectores por chunk. Mejor recall en consultas tipo *"DA 1503"*.

### ADR-004: Sin orchestrator (LangChain / LlamaIndex) en MVP
**Contexto.** Frameworks añaden indirecciones, breaking changes, dependencias.
**Decisión.** Código directo: `retrieve()` → `format_context()` → `generate()`. ~150 líneas.
**Consecuencias.** Si se necesita tool calling/agentes, se evalúa orchestrator después.

### ADR-005: Streaming vía SSE, no WebSockets
**Contexto.** Chat necesita streaming token-a-token.
**Decisión.** SSE (`StreamingResponse` FastAPI). Compatible con `fetch-event-source` en React.
**Consecuencias.** Solo flujo servidor→cliente (suficiente). WebSockets si hace falta bidireccionalidad.

### ADR-006: Sin reranking, sin adjacent chunks en MVP
**Contexto.** Bentley los considera estándar de producción; añaden modelos extra.
**Decisión.** Aplazar a Fase 2. Validar primero si hybrid search basta.
**Consecuencias.** Posibles fallos de precisión. Aceptable para validación. El perfil de producción con L40S y `Qwen3-Reranker-4B` se documenta en `production.md`.

### ADR-007: Detección, no OCR, en el MVP
**Contexto.** Parte del corpus puede estar escaneado.
**Decisión.** Si un PDF no devuelve texto, marcar `requires_ocr` y no indexar.
**Consecuencias.** Usuario ve qué archivos quedaron fuera. OCR en Fase 2.

### ADR-008: Deduplicación por SHA-256
**Contexto.** Nombres de archivo pueden repetirse o tener sufijos. Mismo contenido indexado dos veces contamina respuestas.
**Decisión.** SHA-256 del binario al subir. Si existe, **rechazar** con mensaje claro (eliminar primero si quieres re-indexar).
**Consecuencias.** Hash guardado como metadata. Política revisable cuando llegue versionado.

### ADR-009: SQLite para catálogo de documentos (Qdrant + SQLite, no solo Qdrant)
**Contexto.** Qdrant guarda chunks; el catálogo de documentos tiene estados (`pending`, `processing`, `error`, `requires_ocr`) que existen *antes* de que haya chunks.
**Decisión.** SQLite (un archivo, en stdlib) para catálogo de documentos. Qdrant solo para vectores+metadata de chunk.
**Consecuencias.** Dos stores que mantener consistentes (transacciones lógicas). Listar documentos, dedupe por hash y estados intermedios son triviales en SQL. Postgres si crece a multi-usuario.

### ADR-010: TanStack Table headless en lugar de un sistema de diseño completo
**Contexto.** Sistemas como shadcn, Mantine, MUI traen estética propia que pelea con la dirección "minimalismo Apple".
**Decisión.** TanStack Table (sin estilos) + Tailwind para custom look. Radix UI solo para primitivos accesibles (Dialog, Toast).
**Consecuencias.** Más CSS a escribir; control total sobre el look. Sin lock-in con un sistema de diseño.

### ADR-011: assistant-ui para la pantalla de Chat
**Contexto.** Construir un chat con streaming, citas, scroll automático, estados de carga, edición y reintentos requiere ~600 LOC.
**Decisión.** Usar `assistant-ui` (librería específica para chats con LLM). Nuestro adapter conecta su runtime con nuestro endpoint SSE.
**Consecuencias.** Menos código propio del chat. Depende de que `assistant-ui` mantenga API estable. Mitigación: el wrapper queda en `lib/runtime.ts` y aísla el resto del código.

### ADR-012: Dirección estética — minimalismo apple.com
**Contexto.** El usuario pidió estética minimalista al estilo apple.com.
**Decisión.** Sistema visual con: tipografía Inter (fallback SF Pro), grises neutros, **un solo color de acento** (`#0071E3`), padding generoso, radius alto (12–16px en cards, pill en botones), animaciones suaves (cubic-bezier 0.28,0,0.22,1), modo claro por defecto con respeto a `prefers-color-scheme`. Cero gradientes decorativos. Sombras casi inexistentes.
**Consecuencias.** Look diferenciado de los RAG genéricos. Skill `frontend-design` se invoca con este brief en Fase 3.

### ADR-013: Desarrollo API-first
**Contexto.** El backend RAG es la parte más arriesgada del proyecto (calidad de retrieval, modelos locales). Construir backend primero retrasa la validación de UX. Construir frontend primero sin contrato lleva a iteraciones costosas.
**Decisión.** Definir contrato API completo en `specs/api.md` antes de implementar. Frontend se construye contra mocks (`frontend/src/lib/mocks.ts`). Backend implementa cumpliendo el contrato. Switch flag `useMocks` en frontend para alternar.
**Consecuencias.** Frontend demostrable rápido (sin Ollama/Qdrant funcionando). Backend y frontend pueden avanzar en paralelo. Riesgo: contrato puede pedir algo costoso para el RAG (mitigado con spike mental ya hecho en §5–6).

## 4. Modelo de datos

### Catálogo de documentos (SQLite)

```sql
CREATE TABLE documents (
    document_id    TEXT PRIMARY KEY,        -- uuid4
    filename       TEXT NOT NULL,
    sha256         TEXT UNIQUE NOT NULL,
    status         TEXT NOT NULL,           -- pending|processing|indexed|error|requires_ocr
    uploaded_at    DATETIME NOT NULL,
    page_count     INTEGER,
    chunk_count    INTEGER,
    storage_path   TEXT NOT NULL,
    error_message  TEXT
);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_sha256 ON documents(sha256);
```

### Chunk (Qdrant)

Cada chunk es un *point* en Qdrant:

- **id**: `f"{document_id}:{chunk_index}"`
- **vector denso**: dim según modelo de embeddings
- **vector sparse**: BM25 (FastEmbed)
- **payload**:
  ```
  document_id     str
  filename        str
  page_start      int
  page_end        int
  chunk_index     int
  chunk_total     int
  text            str
  ```

## 5. Pipeline de ingesta

```
PDF subido
   ↓
[1] Validar cabecera %PDF-           → no: status=error
   ↓
[2] SHA-256 del binario              → existe: rechazar
   ↓
[3] INSERT documents (status=pending)
   ↓
[4] Persistir archivo (data/uploads/{document_id}.pdf)
   ↓
[5] Background task: status=processing
   ↓
[6] Extraer texto por página (PyMuPDF)
   ↓
[7] ¿Texto extraíble?                → no: status=requires_ocr, fin
   ↓
[8] Chunking
       - Tamaño objetivo: 500 tokens (rango 400–600)
       - Overlap: 75 tokens (~15%)
       - Cortes: párrafo > oración > carácter
       - Cada chunk preserva page_start / page_end
   ↓
[9] Embedding denso (Ollama) + sparse BM25 (FastEmbed)
   ↓
[10] Upsert en Qdrant (collection `disposiciones`)
   ↓
[11] UPDATE documents SET status=indexed, page_count, chunk_count
```

**Notas:**
- MVP: 1 documento a la vez (sin paralelismo). Mejora en Fase 2.
- `SimplePdfExtractor` (Bentley): texto plano del PDF; sin secciones aún.
- Tokenización con tokenizer del modelo de embeddings (TBD).

## 6. Pipeline de retrieval + generación

```
User query
   ↓
[1] Listar document_id con status='indexed' desde SQLite
   ↓
[2] Pre-procesamiento ligero (trim, normalización Unicode)
   ↓
[3] Embedding denso del query (Ollama)
   ↓
[4] Hybrid search en Qdrant (RRF, 70/30) filtrando por document_id
       top_k = 8
   ↓
[5] Construir contexto (chunks formateados con header de cita)
   ↓
[6] Llamar a Ollama LLM con system + user + context
   ↓
[7] Stream tokens vía SSE
   ↓
[8] Evento SSE `citations` al final: lista de {document_id, filename, page}
```

### Prompt del sistema (borrador, español)

```
Eres un asistente que responde preguntas sobre disposiciones administrativas
basándote ÚNICAMENTE en los fragmentos de documentos que se te proporcionan
como contexto.

Reglas:
1. Si la información no está en el contexto, responde exactamente:
   "No encuentro información sobre eso en las disposiciones cargadas."
2. No inventes datos, números, fechas ni referencias.
3. Cita siempre la fuente al final de cada afirmación, en formato:
   [DA_<número>.pdf, pág. N]
4. Responde en español, tono formal y preciso.
5. Si la pregunta es ambigua, pide aclaración.
```

## 7. Contrato de API (resumen — detalle completo en `specs/api.md`)

**Base URL**: `http://localhost:8000` · **Prefijo**: `/api`

| Método | Endpoint | Descripción |
|---|---|---|
| `POST`   | `/api/documents`              | Subir 1+ PDFs (multipart). Inicia ingesta async. |
| `GET`    | `/api/documents`              | Listar documentos con estado. |
| `GET`    | `/api/documents/{id}`         | Detalle de un documento. |
| `GET`    | `/api/documents/{id}/file`    | Sirve el PDF original. |
| `DELETE` | `/api/documents/{id}`         | Elimina archivo + chunks de Qdrant. |
| `POST`   | `/api/chat`                   | Pregunta al RAG. Respuesta SSE. |
| `GET`    | `/api/health`                 | Ping a Ollama y Qdrant. |

### Esquemas (resumen Pydantic)

```python
class DocumentOut:
    document_id: str
    filename: str
    status: Literal["pending","processing","indexed","error","requires_ocr"]
    uploaded_at: datetime
    page_count: int | None
    chunk_count: int | None
    error_message: str | None

class ChatRequest:
    question: str
    top_k: int = 8

# SSE events:
# event: token     → data: {"text": "..."}
# event: citations → data: {"citations": [{"filename": "...", "page": N, "document_id": "..."}]}
# event: done      → data: {}
# event: error     → data: {"message": "..."}
```

El contrato completo (incluyendo errores HTTP, content-types, ejemplos JSON, eventos SSE) vive en `specs/api.md` para mantener este documento legible.

## 8. Configuración

`.env` cargado vía `pydantic-settings`:

```
# Ollama
OLLAMA_BASE_URL=http://<ip-rtx5090>:11434
OLLAMA_LLM_MODEL=<TBD>
OLLAMA_EMBED_MODEL=<TBD>

# Qdrant
QDRANT_PATH=./data/qdrant
QDRANT_COLLECTION=disposiciones

# SQLite
CATALOG_DB_PATH=./data/catalog.db

# Storage
UPLOADS_DIR=./data/uploads

# Chunking
CHUNK_TARGET_TOKENS=500
CHUNK_OVERLAP_TOKENS=75

# Retrieval
TOP_K=8
DENSE_WEIGHT=0.7
SPARSE_WEIGHT=0.3

# Server
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

Frontend (`frontend/.env`):

```
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCKS=true   # cambia a false cuando el backend esté listo
```

## 9. Estructura de carpetas

```
rag-da/
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + CORS + lifespan
│   ├── settings.py
│   ├── routers/
│   │   ├── documents.py
│   │   ├── chat.py
│   │   └── health.py
│   ├── core/
│   │   ├── ingest.py
│   │   ├── extract.py          # PyMuPDF wrapper
│   │   ├── chunk.py            # text splitter
│   │   ├── retrieve.py         # hybrid search
│   │   ├── generate.py         # LLM, streaming
│   │   ├── store.py            # cliente Qdrant + collection
│   │   ├── catalog.py          # SQLite ops (ADR-009)
│   │   └── ollama_client.py    # httpx wrapper
│   └── schemas.py              # Pydantic
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── routes/             # TanStack Router
│       │   ├── __root.tsx      # layout: header con nav
│       │   ├── index.tsx       # / → redirect /documents
│       │   ├── documents.tsx   # PÁGINA 1
│       │   └── chat.tsx        # PÁGINA 2
│       ├── components/
│       │   ├── DocumentsTable.tsx
│       │   ├── DocumentUploader.tsx
│       │   ├── StatusBadge.tsx
│       │   ├── DeleteDialog.tsx
│       │   └── ChatThread.tsx  # wrapper de assistant-ui
│       ├── lib/
│       │   ├── api.ts          # cliente HTTP real
│       │   ├── mocks.ts        # mocks (ADR-013)
│       │   ├── runtime.ts      # adapter assistant-ui ↔ /api/chat
│       │   └── query.ts        # TanStack Query setup
│       └── types.ts            # tipos espejo de Pydantic
├── data/                       # gitignored
│   ├── qdrant/
│   ├── uploads/
│   └── catalog.db
├── specs/
│   ├── requirements.md
│   ├── design.md
│   ├── api.md                  # contrato completo (ADR-013)
│   └── tasks.md
├── docs/
├── scripts/
├── .env.example
├── pyproject.toml
└── README.md
```

## 10. Páginas y navegación

### Layout global

Header fijo con dos enlaces de navegación: **Documentos** · **Chat**. Logo/título a la izquierda. Toggle de tema (claro/oscuro) a la derecha. Layout centrado con `max-w-5xl`, padding generoso.

### Pantalla 1 — `/documents`

**Propósito.** Gestión de documentos: subir, ver estado, eliminar.

**Composición:**
- Encabezado de página: título "Documentos" + subtítulo descriptivo.
- Uploader prominente (drag-and-drop) en la parte superior.
- Tabla de documentos debajo con columnas: Nombre · Estado · Páginas · Chunks · Subido · (Acciones).
- Sorting por nombre, estado, fecha.
- Refresco automático cada 2s mientras existan documentos en `pending` o `processing` (TanStack Query con `refetchInterval` condicional).
- Estado vacío con mensaje guía cuando no hay documentos.
- Confirmación al eliminar (Radix Dialog).

### Pantalla 2 — `/chat`

**Propósito.** Conversación en lenguaje natural sobre el corpus indexado.

**Composición:**
- `assistant-ui` `<Thread />` ocupando el contenido principal.
- Citas en cada mensaje del asistente, links que abren `/api/documents/{id}/file` en pestaña nueva.
- Estado vacío si no hay documentos `indexed`: mensaje y CTA "Ir a Documentos".
- Indicador de streaming durante la generación.

## 11. Trazabilidad con `requirements.md`

| Requisito | Cubierto por |
|---|---|
| R-1 (Carga) | `POST /api/documents`, react-dropzone en pantalla Documentos, ADR-008 (dedup) |
| R-2 (Procesamiento) | Pipeline §5, ADR-003 (hybrid), ADR-009 (catálogo) |
| R-3 (Pantalla Documentos) | §10 Pantalla 1, ADR-010 (TanStack Table), `GET/DELETE /api/documents` |
| R-4 (Pantalla Chat) | §10 Pantalla 2, ADR-011 (assistant-ui), `POST /api/chat` SSE |
| R-5 (Citas) | Payload chunks §4, evento SSE `citations`, endpoint `/file` |
| R-6 (Local) | ADR-002, configuración Ollama §8 |
| R-7 (OCR detection) | Pipeline §5 paso [7], status `requires_ocr` |
| NF-1 (Rendimiento) | RTX 5090, streaming SSE, Qdrant local |
| NF-3 (Mantenibilidad) | ADR-001, ADR-013 (API-first), §8 (config) |
| NF-4 (Privacidad) | ADR-002, R-6 |
| Estética Apple | ADR-012 |

## 12. Riesgos técnicos conocidos

| Riesgo | Mitigación en MVP | Plan futuro |
|---|---|---|
| Hybrid search no basta sin reranking | Aceptar; validar con usuario | Cross-encoder en Fase 2 |
| Modelo LLM local alucina pese a prompt | Prompt estricto + comparar 2 modelos | Reranker + adjacent chunks |
| PDFs escaneados = mayoría real | Detectar y reportar | OCR en Fase 2 |
| RTX 5090 no accesible | Healthcheck visible en UI | Fallback opcional |
| Qdrant embebido se corrompe | Backups del directorio | Migrar a servicio Docker |
| Contrato API mal diseñado (riesgo API-first) | Spike mental ya hecho §5-6; iterable antes de Fase 3 | Revisión al final de Fase 2 |
| `assistant-ui` API breaking change | Adapter aislado en `lib/runtime.ts` | Cambio puntual sin tocar resto |

## 13. Decisiones pendientes (bloqueantes antes de codear backend)

1. **Modelo de embeddings**: `bge-m3` vs `nomic-embed-text` vs `multilingual-e5`.
2. **Modelo LLM**: `gpt-oss-20b` vs `qwen2.5:14b` vs `gemma`.
3. **Política de duplicados**: ADR-008 propone rechazar (confirmar).
