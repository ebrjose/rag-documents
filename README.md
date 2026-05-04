# RAG de Disposiciones Administrativas

Sistema RAG local para consultar disposiciones administrativas en lenguaje natural, con citas verificables al PDF y página. Modelos 100% locales (Ollama + GPU), sin dependencias cloud.

**Stack:** FastAPI · Postgres 16 · Qdrant · PyMuPDF · Surya OCR (GPU) · Ollama (`gpt-oss:20b` chat + `qwen3-embedding:4b`) · React 19 · Vite · Tailwind v4

---

## 1. Despliegue en producción

Modo prod: una sola imagen Docker corre el backend y sirve la SPA en el mismo origen (`/api/*` para API, `/` para UI). Sin nginx, sin frontend container separado.

### 1.1 Pre-requisitos en el host

| Requisito | Versión mínima | Comando de verificación |
|---|---|---|
| Linux con GPU NVIDIA | driver ≥ 535 | `nvidia-smi` |
| Docker Engine | 24+ | `docker --version` |
| Docker Compose v2 | v2.20+ | `docker compose version` |
| **NVIDIA Container Toolkit** | actual | `docker info \| grep -i nvidia` (debe aparecer en `Runtimes`) |
| **Ollama** instalado en el host | 0.6+ | `ollama --version` |
| Modelos Ollama descargados | — | `ollama list` |

Instalación de NVIDIA Container Toolkit (Ubuntu/Debian):

```bash
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Instalación de Ollama y descarga de modelos:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gpt-oss:20b           # ~14 GB VRAM cargado
ollama pull qwen3-embedding:4b    # ~3 GB VRAM cargado
```

VRAM requerido (como referencia con la configuración actual):
- gpt-oss:20b: 14.5 GB
- qwen3-embedding:4b: 3.4 GB
- Surya OCR (cuando procesa): 2-3 GB
- **Total**: ~21 GB. RTX 4090 (24 GB), RTX 5090 (32 GB), L40S (48 GB) cómodos. RTX 3090/4080 (16 GB) requiere ajustar (gpt-oss más pequeño o context length menor).

### 1.2 Puertos que mapea el stack

| Puerto host | Servicio | Configurable en |
|---|---|---|
| 8000 | Backend prod (UI + API) | `docker-compose.yml` |
| 5435 | Postgres (interno: 5432) | `docker-compose.yml` |
| 6335 | Qdrant HTTP (interno: 6333) | `docker-compose.yml` |
| 6336 | Qdrant gRPC (interno: 6334) | `docker-compose.yml` |
| 11434 | Ollama (host nativo) | systemd unit del Ollama |

Si alguno está ocupado, edita `docker-compose.yml` antes del primer `up`.

### 1.3 Despliegue paso a paso

```bash
# 1. Clonar
git clone git@github.com:ebrjose/rag-documents.git rag-da
cd rag-da

# 2. Configuración del backend
cp backend/.env.example backend/.env
# Los defaults funcionan para deploy estándar. Edita si necesitas:
#  - cambiar el modelo LLM (OLLAMA_LLM_MODEL)
#  - ajustar concurrencia (INGEST_CONCURRENCY, EMBED_CONCURRENCY)
#  - cambiar contextos (OLLAMA_CONTEXT_LENGTH, OLLAMA_EMBED_CONTEXT_LENGTH)

# 3. Verificar Ollama y modelos
curl -s http://localhost:11434/api/tags | grep -E "gpt-oss|qwen3-embedding"

# 4. Build + up del perfil prod
docker compose --profile prod build       # 5-15 min la primera vez (torch + cuda + Surya)
docker compose --profile prod up -d        # postgres + qdrant + backend-prod

# 5. Verificación
curl -s http://localhost:8000/api/health | python3 -m json.tool
# Esperado: {"status":"ok","ollama":true,"qdrant":true,"postgres":true,...}
```

Acceso:
- LAN: `http://<ip-del-host>:8000` (ej: `http://192.168.100.110:8000`)
- UI en `/`, API en `/api/*`, OpenAPI en `/api/docs`

### 1.4 Importación masiva del corpus

Si tienes un directorio con todas las DAs en PDF:

```bash
# Coloca los PDFs (no van al repo — están gitignored)
mkdir -p administrative_regulations
cp /ruta/a/tus/pdfs/*.pdf administrative_regulations/

# Importar
uv run python scripts/import_das.py --yes --wait
```

El script:
- Sube en lotes (default 15 por POST, máx 20)
- Skipea duplicados por SHA-256 (idempotente)
- Muestra progreso con tasa y ETA
- Con `--wait` bloquea hasta que el backend termine de procesar

Para 2,300 DAs (~30% escaneadas) en una RTX 5090 esperás ~1-1.5 horas.

---

## 2. Operación

### Comandos básicos

```bash
# Ver estado
docker compose ps

# Logs en vivo
docker compose logs -f backend-prod

# Reiniciar backend (tras cambiar config)
docker compose --profile prod up -d --force-recreate backend-prod

# Apagar todo (datos persisten en volumes/)
docker compose --profile prod down

# Apagar incluyendo Postgres + Qdrant
docker compose down
```

### Cambiar configuración runtime

La mayoría de cambios viven en `backend/.env`. Tras editar:

```bash
docker compose --profile prod up -d --force-recreate backend-prod
```

Cambios que requieren rebuild de imagen (no solo restart):
- Cambios en código (`backend/`, `frontend/`)
- Nuevas dependencias (`pyproject.toml`, `frontend/package.json`)

```bash
docker compose --profile prod build backend-prod
docker compose --profile prod up -d --force-recreate backend-prod
```

### Healthcheck y diagnóstico

```bash
# Salud completa
curl -s http://localhost:8000/api/health

# Estado del corpus
curl -s http://localhost:8000/api/documents | python3 -c "
import json, sys
from collections import Counter
docs = json.load(sys.stdin)
c = Counter(d['status'] for d in docs)
print(f'Total: {len(docs)}'); [print(f'  {s}: {n}') for s, n in c.items()]"

# VRAM en uso
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

# Estado Qdrant
curl -s http://localhost:6335/collections/disposiciones | python3 -m json.tool
```

---

## 3. Persistencia y backup

Todos los datos viven en `./volumes/` (gitignored):

| Carpeta | Tamaño típico | Qué guarda | ¿Backup? |
|---|---|---|---|
| `volumes/postgres/` | <50 MB | Catálogo (filas de `documents`, estados, `used_ocr`) | **Sí** |
| `volumes/qdrant/` | ~150 MB / 2.3K docs | Vectores densos + sparse + payload de chunks | **Sí** |
| `volumes/uploads/` | varía | PDFs originales (necesarios para citas) | **Sí** |
| `volumes/surya/` | 1.5 GB | Cache de modelos Surya | No (se redescarga) |
| `volumes/huggingface/`, `volumes/torch/` | 0 | Caches opcionales | No |

### Backup

```bash
# Detener para snapshot consistente (recomendado)
docker compose --profile prod down

# Snapshot
tar -czf rag-da-backup-$(date +%Y%m%d).tar.gz \
  volumes/postgres volumes/qdrant volumes/uploads

# Re-arrancar
docker compose --profile prod up -d
```

Para Postgres alternativamente puedes usar `pg_dump` (más portable entre arquitecturas):

```bash
docker exec rag-da-postgres pg_dump -U rag rag_da > catalog.sql
```

### Restore en otra máquina

```bash
# 1. Pre-requisitos del host nuevo (GPU, Docker, NVIDIA Toolkit, Ollama, modelos)
# 2. Clonar repo y configurar
git clone git@github.com:ebrjose/rag-documents.git rag-da
cd rag-da
cp backend/.env.example backend/.env

# 3. Restaurar volúmenes
tar -xzf rag-da-backup-YYYYMMDD.tar.gz   # crea volumes/postgres, qdrant, uploads

# 4. Levantar
docker compose --profile prod up -d
```

**Restricciones de portabilidad:**
- Postgres y Qdrant son sensibles a arquitectura: Linux x86_64 → Linux x86_64 funciona; cruzar a ARM o macOS puede romper. En ese caso usa `pg_dump` para Postgres y la API de snapshots de Qdrant (`POST /collections/<name>/snapshots`).
- Permisos: si Postgres se queja al arrancar, `sudo chown -R 999:999 volumes/postgres` (UID interno de la imagen alpine).

---

## 4. Modos alternativos (desarrollo)

El proyecto soporta dos modos de dev además del prod descrito arriba.

### 4.1 Modo host (HMR nativo, iteración rápida)

Backend y frontend corren fuera de Docker. Solo Postgres y Qdrant en containers.

```bash
docker compose up -d                       # solo postgres + qdrant
uv sync                                    # backend deps
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
cd frontend && npm install && npm run dev  # http://localhost:5173 con HMR
```

### 4.2 Modo Docker dev (todo en containers, con HMR)

```bash
docker compose --profile app up -d
# UI: http://localhost:5173 (Vite dev server)
# API: http://localhost:8000
```

### 4.3 Cambiar entre modos

```bash
# De cualquier modo a prod
docker compose --profile app down 2>/dev/null
pkill -f "uvicorn backend" 2>/dev/null
pkill -f "vite" 2>/dev/null
docker compose --profile prod up -d
```

---

## 5. Especificaciones y arquitectura

La fuente de verdad del proyecto vive en `specs/`:

- **`specs/requirements.md`** — qué hace y por qué (formato EARS).
- **`specs/design.md`** — stack, ADRs, contrato API, modelo de datos.
- **`specs/production.md`** — perfil productivo (hardware L40S, reranker).
- **`specs/tasks.md`** — plan incremental del MVP (Fases 0-4).
- **`specs/roadmap.md`** — backlog post-MVP priorizado contra estado del arte 2026.
- **`specs/rag-2026.md`** — referencia del estado del arte de RAG.

### Configuración (resumen `backend/.env`)

| Variable | Default | Notas |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Override en compose para Docker → `host.docker.internal:11434` |
| `OLLAMA_LLM_MODEL` | `gpt-oss:20b` | Alternativa: `gemma4:31b` (mejor calidad, +6 GB VRAM) |
| `OLLAMA_EMBED_MODEL` | `qwen3-embedding:4b` | Cambiar requiere reindexar todo |
| `OLLAMA_CONTEXT_LENGTH` | `16384` | num_ctx para chat |
| `OLLAMA_EMBED_CONTEXT_LENGTH` | `2048` | num_ctx para embeddings |
| `OLLAMA_MAX_TOKENS` | `4096` | Tope de output |
| `INGEST_CONCURRENCY` | `2` | Documentos en pipeline simultáneos |
| `EMBED_CONCURRENCY` | `4` | Embeddings concurrentes por doc |
| `OCR_ENABLED` | `true` | Si false, escaneados van a `requires_ocr` |
| `OCR_DPI` | `200` | Bajar a 150 para OCR ~30% más rápido |
| `QUERY_REWRITING_ENABLED` | `true` | Reformula follow-ups antes del retrieval |
| `TOP_K` | `8` | Chunks pasados al LLM |

### Flujo de una pregunta

```
Usuario → POST /api/chat (history)
       ↓
[1] Query rewrite (si hay history)        ← LLM auxiliar, ~500ms
[2] Embedding query (Ollama)
[3] BM25 query (FastEmbed)
[4] Hybrid search en Qdrant (RRF)         ← top 8 chunks
[5] Build prompt: system + history + contexto + pregunta
[6] LLM streaming (Ollama gpt-oss:20b)    ← SSE tokens
[7] Citations event (filename + página)
[8] Done event
```

### Estados de un documento

```
upload → pending → processing
                       ↓ (no hay texto)
                   ocr_processing → indexed
                       ↓ (OCR falla o sigue sin texto)
                   requires_ocr
                       ↓ (excepción)
                   error
```

Si el backend cae a mitad de ingesta, al reiniciar `_resume_orphan_ingests()` reencola todo lo que quedó en `pending`/`processing`/`ocr_processing`.

---

## 6. Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `health` muestra `ollama: false` | Ollama no está corriendo en host | `systemctl start ollama` |
| `health` muestra `qdrant: false` | Qdrant container caído | `docker compose up -d qdrant` |
| Qdrant: "Too many open files" | ulimit del container | Ya configurado en compose: `nofile=65536`. Si vuelve, subir más |
| Errores CUDA al arrancar backend | NVIDIA Container Toolkit no instalado | Ver §1.1 |
| Respuestas en chat sin sentido | Caché del navegador con JS antigua | Hard refresh (Ctrl+Shift+R) |
| Ingesta lenta | Default `OLLAMA_NUM_PARALLEL=1` en Ollama | `sudo systemctl edit ollama` y agregar `Environment=OLLAMA_NUM_PARALLEL=4` |
| OOM de VRAM al cargar gpt-oss | Otro modelo cargado | `curl -X POST http://localhost:11434/api/generate -d '{"model":"X","keep_alive":0}'` para descargar |

---

## 7. Licencia y uso

Sistema interno. Modelos open weights (`gpt-oss`, `qwen3-embedding`, Surya) bajo sus respectivas licencias. Código del proyecto sin licencia explícita — uso interno organizacional.
