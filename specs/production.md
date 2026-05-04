# Production — RAG de Disposiciones Administrativas

> Documento de arquitectura posterior al MVP. El MVP sigue definido por `requirements.md`, `design.md` y `tasks.md`; este documento describe el perfil de produccion para corpus completo y hardware dedicado.

## 1. Objetivo

Pasar del MVP con 20-30 PDFs cargados manualmente a un despliegue productivo capaz de operar sobre el corpus completo de disposiciones administrativas, manteniendo operacion 100% local, respuestas en espanol y citas verificables al documento y pagina de origen.

Produccion no debe cambiar los criterios basicos del sistema:

- Las respuestas deben estar fundamentadas en chunks recuperados.
- Toda respuesta afirmativa debe conservar citas a documento y pagina.
- Si el corpus no contiene informacion suficiente, el sistema debe decirlo explicitamente.
- Ningun contenido de las disposiciones debe salir de la red local.

## 2. Hardware y modelos

### Hardware objetivo

- Servidor con NVIDIA L40S de 48 GB VRAM.
- Ollama o runtime equivalente accesible por LAN desde el backend.
- Almacenamiento persistente para Qdrant, catalogo SQLite/PostgreSQL futuro, PDFs originales y artefactos de indexacion.

### Modelos recomendados

| Funcion | Modelo default | Alternativa / fallback | Nota |
|---|---|---|---|
| Chat / generacion | `gemma4:31b` | Modelo local equivalente si falla latencia/calidad | Priorizar espanol, citas y baja alucinacion |
| Embeddings | `qwen3-embedding:4b` | `qwen3-embedding:8b` si mejora validacion real | No cambiar dimensiones sin reindexar |
| Reranker | `Qwen3-Reranker-4B` | `BAAI/bge-reranker-v2-m3` | Qwen es default productivo; BGE es fallback liviano |

`qwen3-embedding:8b` queda como mejora condicionada: solo debe adoptarse si las pruebas sobre preguntas reales muestran mejor recuperacion/citas y el costo de reindexar queda aceptado.

## 3. Pipeline productivo

### Indexacion

1. Extraer texto por pagina desde PDF.
2. Detectar PDFs sin texto extraible y marcarlos como `requires_ocr`.
3. Segmentar texto en chunks con metadata completa: documento, pagina, indice de chunk y hash de contenido.
4. Generar embeddings con `qwen3-embedding:4b`.
5. Persistir vectores densos y sparse/BM25 en Qdrant.
6. Persistir estado documental y metadata operacional en catalogo.

### Consulta

1. Recibir pregunta en espanol.
2. Ejecutar busqueda hibrida en Qdrant.
3. Recuperar `RERANK_TOP_N` candidatos, default `50`.
4. Reordenar candidatos con `Qwen3-Reranker-4B`.
5. Seleccionar `FINAL_CONTEXT_CHUNKS`, default `8`.
6. Construir prompt estricto para `gemma4:31b` con chunks y metadata de cita.
7. Transmitir respuesta por SSE.
8. Devolver citas normalizadas a documento y pagina.

El reranker nunca debe inventar metadata ni reemplazar el filtro de citas. Solo decide relevancia relativa entre pregunta y chunk candidato.

## 4. Serving y configuracion

Ollama puede servir chat y embeddings. El reranker debe servirse con runtime dedicado o wrapper Python; no asumir que Ollama provee un endpoint nativo de reranking compatible con el contrato del backend.

Providers aceptados para reranking:

- `vllm`: preferido si se estandariza serving GPU para modelos Qwen.
- `tei`: aceptable si facilita scoring por pares y despliegue estable.
- `flagembedding`: fallback simple en Python, especialmente para `BAAI/bge-reranker-v2-m3`.
- `none`: desactiva reranking para diagnostico o fallback operativo.

Variables de entorno productivas:

```env
OLLAMA_BASE_URL=http://<host-modelos>:11434
OLLAMA_CHAT_MODEL=gemma4:31b
OLLAMA_EMBED_MODEL=qwen3-embedding:4b

RERANKER_ENABLED=true
RERANKER_PROVIDER=vllm
RERANKER_BASE_URL=http://<host-reranker>:8000
RERANKER_MODEL=Qwen3-Reranker-4B
RERANK_TOP_N=50
FINAL_CONTEXT_CHUNKS=8
```

Configuracion de fallback:

```env
RERANKER_ENABLED=true
RERANKER_PROVIDER=flagembedding
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RERANK_TOP_N=30
FINAL_CONTEXT_CHUNKS=8
```

## 5. Validacion productiva

Antes de activar reranking en produccion, comparar tres variantes sobre el mismo set de preguntas:

1. Sin reranker: Qdrant hybrid search directo a contexto final.
2. `BAAI/bge-reranker-v2-m3`: baseline liviano.
3. `Qwen3-Reranker-4B`: candidato productivo.

Medir como minimo:

- acierto de respuesta;
- precision de citas;
- casos correctos de "no encuentro informacion";
- latencia total;
- latencia de reranking;
- cantidad de chunks enviados al LLM;
- errores de serving o timeouts.

El criterio de adopcion de `Qwen3-Reranker-4B` es que mejore precision de respuesta o citas frente al baseline sin romper la latencia aceptable de chat. Si no mejora de forma clara, mantener `bge-reranker-v2-m3` o desactivar reranking temporalmente.

## 6. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Reranker aumenta demasiado la latencia | Reducir `RERANK_TOP_N`, usar batching, evaluar fallback BGE |
| Cambio de embedding requiere reindexar | Versionar nombre/dimension del modelo en la coleccion Qdrant |
| Reranker descarta chunk con cita correcta | Mantener logs de candidatos antes/despues de rerank para auditoria |
| LLM responde sin apoyo suficiente | Prompt estricto + umbral minimo de relevancia + respuesta "no encuentro informacion" |
| Serving de modelos compite por VRAM | Separar procesos/modelos, limitar concurrencia y monitorear memoria |

## 7. Relacion con el MVP

Este documento no cambia el alcance del MVP. Para el MVP:

- el reranker no es obligatorio;
- el hardware base sigue siendo la RTX 5090 definida en `requirements.md`;
- la validacion sigue siendo sobre 20-30 disposiciones y 10 preguntas representativas.

Produccion debe retomarse despues de validar el MVP y contar con resultados en `specs/validation.md`.
