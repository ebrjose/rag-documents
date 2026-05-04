# RAG de Disposiciones Administrativas

Sistema RAG local para consultar disposiciones administrativas en lenguaje natural, con citas verificables al PDF y página de origen. Modelos 100% locales (Ollama en RTX 5090).

## Especificaciones

La fuente de verdad del proyecto vive en `specs/`:

- **`specs/requirements.md`** — qué hace el sistema y por qué.
- **`specs/design.md`** — cómo está construido (stack, ADRs, contratos).
- **`specs/production.md`** — perfil productivo (post-MVP, hardware dedicado, reranker).
- **`specs/tasks.md`** — plan incremental de implementación.

## Stack

**Backend:** Python 3.12 · FastAPI · Qdrant · Postgres 16 · PyMuPDF · Ollama · Surya OCR
**Frontend:** React 19 · Vite · TypeScript · Tailwind v4
**Modelos:** `gemma4:31b` (chat) · `qwen3-embedding:4b` (embeddings) · Surya (OCR sobre GPU)

## Modos de ejecución

El proyecto admite dos modos de desarrollo. Los servicios de datos (Postgres + Qdrant) corren en Docker en ambos modos. Lo que cambia es dónde corren backend y frontend.

### Modo host (desarrollo rápido, hot-reload nativo)

Backend y frontend corren directamente en el host. Usa este modo cuando estés iterando sobre el código.

```bash
# 1. Servicios de datos
docker compose up -d                # postgres + qdrant

# 2. Backend (desde la raíz del repo)
uv sync
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 3. Frontend (en otra terminal)
cd frontend
npm install
npm run dev
```

Acceso:
- Frontend: http://localhost:5173 (o IP LAN, ej. http://192.168.100.110:5173)
- Backend: http://localhost:8000 (`/docs` para OpenAPI)

### Modo Docker (todo containerizado)

Backend y frontend también corren en contenedores. Usa este modo para reproducir el setup productivo, o cuando quieras evitar instalar dependencias en el host.

```bash
# Build (la primera vez tarda — torch + cuda libs son ~3-5 GB)
docker compose --profile app build

# Up (postgres + qdrant + backend + frontend)
docker compose --profile app up -d

# Logs
docker compose logs -f backend
docker compose logs -f frontend
```

Acceso: igual que en modo host (los puertos 8000 y 5173 se mapean al host).

**Diferencias clave del modo Docker:**
- Backend usa GPU vía NVIDIA Container Toolkit (`runtime: nvidia`).
- Backend alcanza Ollama del host vía `host.docker.internal:11434`.
- Backend se conecta a Postgres/Qdrant por la red interna de Docker (`postgres:5432`, `qdrant:6333`).
- Cache de modelos Surya/HuggingFace se persiste en `./volumes/{surya,huggingface}` para evitar re-descargas.

### Cambiar entre modos

No mezcles modos al mismo tiempo en los mismos puertos. Para cambiar:

```bash
# De host a Docker
pkill -f "uvicorn backend"
pkill -f "vite"
docker compose --profile app up -d

# De Docker a host
docker compose --profile app stop backend frontend
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
cd frontend && npm run dev &
```

## Configuración

`backend/.env` (copia desde `backend/.env.example`). Configura modelos Ollama, URLs de servicios, OCR, chunking, retrieval, etc. Todo configurable — no hay valores hardcoded en código.

En modo Docker, `docker-compose.yml` sobreescribe las URLs internas (`OLLAMA_BASE_URL`, `DATABASE_URL`, `QDRANT_URL`) — el resto del config sigue viniendo del `.env`.

## Persistencia

Todo lo persistente vive bajo `./volumes/` (gitignored):

```
volumes/
├── postgres/        # datos del catálogo
├── qdrant/          # vectores + metadata de chunks
├── uploads/         # PDFs originales
├── surya/           # cache de modelos Surya OCR (~1.3 GB)
├── huggingface/     # cache de transformers (cuando aplica)
└── torch/           # cache de torch
```

Backup completo: `tar -czf backup.tgz volumes/`. Restaurar: descomprimir sobre `volumes/`.
