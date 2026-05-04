# Roadmap post-MVP — alineación con estado del arte (mayo 2026)

> Documento de **siguientes pasos** después de validar el MVP. Acompaña a:
> - `requirements.md` (qué hace y por qué)
> - `design.md` (cómo está construido)
> - `tasks.md` (plan incremental del MVP, Fases 0-4)
> - `production.md` (perfil de hardware dedicado L40S)
> - `rag-2026.md` (estado del arte de referencia)
>
> Este archivo registra el *gap analysis* contra `rag-2026.md` y la priorización
> de mejoras posteriores al MVP. Es un backlog vivo: cada cambio significativo
> que se incorpore debe quedar reflejado moviendo su entrada de "pendiente" a
> "hecho" y enlazando al ADR correspondiente en `design.md`.

## 1. Cobertura actual frente a `rag-2026.md`

Estado al cierre del MVP:

| # | Recomendación rag-2026 | Estado | Notas |
|---|---|---|---|
| 1 | Ingesta inteligente (chunks semánticos + metadatos ricos) | 🟡 Parcial | Splitter párrafo→oración→char. Metadata: `document_id`, `filename`, `page_start/end`, `chunk_index`, `source_type`, `used_ocr`. Falta: secciones, títulos, tablas, fecha, área, tipo doc temático. |
| 2 | Hybrid search (BM25 + vector + RRF) | ✅ Completo | Qdrant nativo. Pesos 70/30 configurables (`settings.dense_weight` / `sparse_weight`). |
| 3 | Reranking | ❌ Pendiente | `ADR-006` lo difiere a Fase 2. `production.md` planifica `Qwen3-Reranker-4B` (default) o `bge-reranker-v2-m3` (fallback). |
| 4 | Query rewriting | ❌ Pendiente | Pregunta del usuario se pasa tal cual al embedding y al LLM. |
| 5 | Metadata filtering | 🟡 Mínimo | Solo filtramos por `document_id IN (indexed)`. Falta: fecha, tipo, área, versión, permisos. |
| 6 | Citations obligatorias | ✅ Completo | Evento SSE `citations` con `{document_id, filename, page}`. Click abre PDF inline. Prompt obliga a citar. |
| 7 | Evaluación + trazas | ❌ Pendiente | Sin métricas, sin tabla de traces, sin feedback del usuario. |
| 8 | Agentic RAG | ❌ Fuera de alcance | One-shot retrieval. Solo se evalúa si aparece un caso de uso que lo justifique. |
| 9 | GraphRAG | ❌ Fuera de alcance | Para corpus de DAs no aplica claramente. Reconsiderar si llega un dataset con relaciones fuertes (expedientes, normas que se modifican, etc.). |

## 2. Stack comparado

| Capa | Recomendado por rag-2026 | Implementado | Match |
|---|---|---|---|
| Vector store | Qdrant / Milvus / Elastic | Qdrant (Docker) | ✅ |
| Catálogo / metadata | PostgreSQL | Postgres 16 (Docker) | ✅ |
| Documentos originales | MinIO | Filesystem (`./volumes/uploads/`) | 🟡 funciona en single-host; migrar a MinIO si se vuelve multi-host |
| Backend | FastAPI + Celery + Redis | FastAPI + `BackgroundTasks` | 🟡 BackgroundTasks no escala; Celery cuando se ingesten miles de DAs |
| Tracing | OpenTelemetry | `logging` stdlib | ❌ |
| Embeddings | bge-m3 / Qwen / e5-mistral / jina-v3 | `qwen3-embedding:4b` (Ollama) | ✅ |
| Reranker | bge-reranker-v2-m3 / Qwen / jina | ninguno | ❌ |
| LLM | Qwen3 / Llama 3.x / Gemma 3 | `gemma4:31b` (Ollama) | ✅ |
| OCR | (no menciona explícito) | Surya OCR (GPU, abstracción `OCRProvider`) | ✅ + |

## 3. Diagnóstico

Estamos en el **piso aceptable** del estado del arte: hybrid search + citas verificables + streaming + OCR sobre GPU. Por encima del "RAG básico" que `rag-2026.md` descalifica (solo vector search, chunks fijos sin metadatos, sin citas).

No estamos todavía en perfil productivo de mayo 2026 porque faltan tres cosas que pesan:

1. **Reranking** — sin esto la respuesta depende mucho del orden inicial del retrieval. Es la mejora individual de mayor impacto.
2. **Metadata estructurada + filtering** — habilita preguntas tipo *"qué DA del 2018 trata sobre contratación de consultores"*. El catálogo `documents_administrative_regulation.csv` que existe en el repo no se está importando.
3. **Trazabilidad y evaluación** — sin esto cualquier mejora es subjetiva. No podemos comparar variantes con datos.

Las técnicas avanzadas (Agentic RAG, GraphRAG, query rewriting agresivo) son post-MVP justificadas. **No las necesitamos hasta validar lo básico con usuarios reales**.

## 4. Backlog priorizado (post-MVP)

Orden recomendado por relación impacto/esfuerzo, asumiendo que el MVP ya está validado contra usuarios.

### Sprint 1 — Reranking
- **Esfuerzo**: 2-3 días.
- **Implementación**: añadir `RerankerProvider` (siguiendo el patrón de `OCRProvider` en `backend/core/ocr/`). Implementaciones: `BgeRerankerProvider` (fallback liviano) y `QwenRerankerProvider` (default productivo según `production.md`).
- **Cambios**: `retrieve.py` recupera `RERANK_TOP_N=50`, pasa al reranker, devuelve `FINAL_CONTEXT_CHUNKS=8`. Config: `RERANKER_ENABLED`, `RERANKER_PROVIDER`, `RERANKER_MODEL`, `RERANK_TOP_N`.
- **Impacto**: alto. Mejora precisión de citas y reduce ruido en el contexto.
- **Decisión asociada**: revisar `ADR-006` (que difería el reranker) y agregar nuevo ADR.

### Sprint 2 — Metadata estructurada desde el catálogo CSV
- **Esfuerzo**: 3-5 días.
- **Implementación**: importar `documents_administrative_regulation.csv` con metadata por DA (número, año, fecha, área, tema, estado vigencia). Agregar columnas a Postgres: `da_number`, `published_at`, `subject`, `area`, `is_repealed`. Indexar también en payload de Qdrant para filtering.
- **Cambios**: nueva ruta `POST /api/catalog/import`, ampliar `DocumentOut`, agregar filtros opcionales en `/api/chat` (`filters`).
- **Impacto**: alto. Habilita búsqueda por número de DA, año, área. Habilita preguntas que hoy fallan.
- **Riesgo**: el CSV puede no estar 1-a-1 con los PDFs subidos — necesita matching por número o nombre de archivo.

### Sprint 3 — Trazabilidad básica
- **Esfuerzo**: 2 días.
- **Implementación**: nueva tabla `query_traces` en Postgres con: `id`, `created_at`, `question`, `top_chunks` (JSONB), `scores` (JSONB), `response`, `citations` (JSONB), `latency_ms`, `feedback` (nullable).
- **Cambios**: middleware en `routers/chat.py` que persiste cada query. Endpoint `POST /api/feedback` para 👍/👎 desde la UI.
- **Impacto**: medio inmediato, alto a futuro (habilita evaluación).

### Sprint 4 — Eval suite
- **Esfuerzo**: 3 días.
- **Implementación**: 30 preguntas curadas en `specs/evaluation.md` (mezcla específicas + temáticas + casos negativos esperados). Script `scripts/run_eval.py` que ejecuta cada pregunta contra el sistema y compara contra respuesta y citas esperadas. Métricas: precision@k de citas, faithfulness manual o LLM-as-judge, latencia.
- **Cambios**: ningún cambio runtime, todo offline.
- **Impacto**: alto. Convierte cambios en datos y permite comparar variantes de chunking, reranker, prompt.

### Sprint 5 — Query rewriting (single-rewrite)
- **Esfuerzo**: 1-2 días.
- **Implementación**: opcional, controlado por `QUERY_REWRITE_ENABLED`. Antes del retrieval, llamar al LLM para reformular la pregunta del usuario en una versión más explícita. Una sola reformulación, sin sub-queries.
- **Cambios**: `retrieve.py` añade paso de reformulación. Persistir tanto la pregunta original como la reformulada en `query_traces`.
- **Impacto**: medio. Útil para preguntas cortas o ambiguas. Latencia adicional ~500ms.

### Sprint 6 — Caching
- **Esfuerzo**: 1-2 días.
- **Implementación**: Redis para:
  - Cache de embeddings de query (clave: hash de la pregunta normalizada).
  - Cache de respuestas completas (clave: hash de pregunta + ids de docs activos).
- **Impacto**: medio. Solo aplica si hay preguntas repetidas o flujos demo donde se hacen las mismas queries varias veces.

### Sprint 7 (opcional) — Cola de ingesta con Celery
- **Esfuerzo**: 2-3 días.
- **Implementación**: reemplazar `FastAPI BackgroundTasks` con Celery + Redis. Permite paralelizar ingesta, reintentos automáticos, dashboards (Flower).
- **Cuándo activarlo**: cuando se vaya a ingestar el corpus completo (~2,300 DAs) o cuando varios usuarios suban en paralelo.
- **Impacto**: bajo hoy, alto cuando se llegue al corpus completo.

## 5. Lo que NO se va a hacer (y por qué)

| Item | Razón |
|---|---|
| Agentic RAG | Solo lo justifica un caso de uso concreto que requiera múltiples pasos de razonamiento. Hoy las preguntas son one-shot sobre el corpus. Latencia y costo adicionales no compensan. |
| GraphRAG | Las DAs no tienen relaciones explícitas estructuradas que un grafo capte mejor que metadata + reranker. Reevaluar si el catálogo CSV revela relaciones del tipo *"DA X modifica DA Y"*. |
| MinIO | Funcionamos single-host. Mover PDFs a MinIO solo se justifica si se vuelve multi-host o si el almacenamiento local se vuelve un cuello. |
| OpenTelemetry | Sobreingeniería para single-user MVP. Reconsiderar cuando haya >1 usuario o se quiera profilear flujos completos. |
| Otros formatos (DOCX, etc.) | El schema (`source_type` con CHECK) está preparado para DOCX. Implementar cuando aparezca un caso real — la mayoría del corpus son PDFs. |
| Permisos / multi-tenant | Fuera del alcance del MVP. Roadmap propio cuando se llegue a más de 1 usuario. |

## 6. Decisiones que cambia este roadmap

Si se adopta el Sprint 1 (reranking):
- Actualizar `ADR-006` en `design.md` (marcar como superseded por nuevo ADR-014 o similar).
- Modificar `retrieve.py` y `settings.py`.
- Agregar `RerankerProvider` en `backend/core/rerank/` siguiendo el mismo patrón de `OCRProvider`.

Si se adopta el Sprint 2 (CSV import):
- Migración Postgres: nuevas columnas en `documents`.
- Actualizar `init.sql` y agregar script de migración para DBs existentes.
- Endpoint nuevo + cambios en `DocumentOut` y la tabla del frontend.

Si se adopta el Sprint 3 (traces):
- Nueva tabla `query_traces`. Frontend gana botones de feedback en cada respuesta.

## 7. Observación crítica sobre el doc fuente

`rag-2026.md` presenta el estado del arte como un checklist. En la práctica:

> **Reranker + metadata estructurada del CSV** dan más ganancia neta que todas las técnicas avanzadas (agentic, graph, query rewriting agresivo) juntas para un corpus de documentos administrativos.

La sofisticación adicional cuesta complejidad que muchas veces no se compensa con calidad medible. Por eso este roadmap prioriza lo que mueve la aguja sobre lo que está de moda.
