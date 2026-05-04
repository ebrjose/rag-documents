# Requirements — RAG de Disposiciones Administrativas (MVP)

## 1. Contexto y propósito

La organización mantiene un acervo histórico de **disposiciones administrativas (DAs)** en formato PDF, acumulado desde 1997 hasta la fecha. Hoy, consultar una DA específica o encontrar qué disposiciones tratan sobre un tema requiere abrir archivos uno por uno o depender de la memoria institucional.

Este sistema busca **permitir que los usuarios pregunten en lenguaje natural sobre el contenido de las disposiciones y obtengan respuestas con citas verificables al PDF y página de origen**, usando exclusivamente modelos locales (sin APIs externas).

## 2. Objetivo del MVP

Validar que un pipeline RAG construido sobre modelos locales puede responder con calidad aceptable preguntas sobre disposiciones administrativas, antes de invertir en una solución completa con frontend en React, ingesta automatizada e integración con el catálogo oficial.

El MVP **no busca** reemplazar el sistema de archivo actual ni indexar el corpus completo (~2,300 DAs). Busca validar el flujo end-to-end con un subconjunto de archivos cargados manualmente.

## 3. Alcance

### Dentro del MVP

- Aplicación web con **dos pantallas dedicadas**, navegables entre sí:
  - **Pantalla "Documentos"**: gestión de documentos (uploader + tabla con estados).
  - **Pantalla "Chat"**: consulta en lenguaje natural sobre el corpus indexado.
- Carga manual de uno o varios PDFs por el usuario a través de la pantalla "Documentos".
- Procesamiento automático de cada archivo: extracción de texto, segmentación, generación de vectores e indexación.
- Búsqueda semántica + por palabras clave sobre el corpus indexado.
- Chat en lenguaje natural que responde con citas al documento y página.
- Tabla de documentos indexados con estado en vivo, ordenamiento y opción de eliminar.
- Visualización del PDF original al hacer clic en una cita.
- Estética minimalista inspirada en apple.com (referencia explícita).
- Operación 100% local: modelos de embeddings y LLM corren en hardware propio (RTX 5090).

### Fuera del MVP

- Autenticación y multi-tenant.
- Importación masiva del corpus completo o sincronización con el sistema origen.
- Importación de metadata desde el catálogo CSV existente.
- Reranking, adjacent chunks, múltiples extractores PDF (ver `design.md` → Roadmap).
- OCR para PDFs escaneados (se rechazarán o marcarán; ver R-7).
- Despliegue productivo, observabilidad, métricas.

## 4. Usuarios

**Usuario único — administrador / analista** (en el MVP).
Persona técnica o semi-técnica de la organización que conoce el contenido de las disposiciones y valida que las respuestas del sistema sean correctas.

## 5. Requisitos funcionales

> Formato EARS — *"The system shall…"* en español.

### R-1. Carga de documentos

- **R-1.1.** El sistema **debe** permitir al usuario cargar uno o más archivos PDF a través de un componente de subida (drag-and-drop o selector de archivos).
- **R-1.2.** El sistema **debe** aceptar archivos con extensión `.pdf` y `.PDF`. Los `.docx` y otros formatos quedan fuera del MVP.
- **R-1.3.** El sistema **debe** rechazar archivos que no tengan cabecera PDF válida (`%PDF-`) y mostrar un mensaje claro de error.
- **R-1.4.** El sistema **debe** procesar las cargas de forma asíncrona y mostrar al usuario el estado de cada archivo: `pendiente`, `procesando`, `indexado`, `error`.
- **R-1.5.** El sistema **debe** soportar la carga simultánea de hasta 20 archivos por operación.

### R-2. Procesamiento e indexación

- **R-2.1.** El sistema **debe** extraer el texto de cada PDF, preservando información de número de página.
- **R-2.2.** El sistema **debe** segmentar el texto en *chunks* aptos para búsqueda semántica (parámetros en `design.md`).
- **R-2.3.** El sistema **debe** generar vectores densos (embeddings) y vectores sparse (BM25) por cada chunk.
- **R-2.4.** El sistema **debe** persistir los chunks con su metadata (nombre del archivo, número de página, índice del chunk, total de chunks del documento) en el almacén vectorial.
- **R-2.5.** El sistema **debe** evitar la duplicación: si el usuario sube un archivo con el mismo contenido (hash) que uno ya indexado, **debe** rechazarlo o reemplazarlo según política definida (TBD en `design.md`).

### R-3. Pantalla "Documentos" (gestión)

- **R-3.1.** El sistema **debe** mostrar al usuario una **tabla** de documentos con las columnas: nombre del archivo, estado, número de páginas, número de chunks generados, fecha de carga, acciones.
- **R-3.2.** La tabla **debe** soportar ordenamiento por al menos: nombre, fecha de carga y estado.
- **R-3.3.** El sistema **debe** refrescar el estado de los documentos automáticamente mientras existan documentos en estado `pending` o `processing` (polling, ver `design.md`).
- **R-3.4.** El sistema **debe** permitir eliminar un documento desde la tabla, removiendo el archivo del disco y todos sus chunks del almacén vectorial. La eliminación **debe** requerir confirmación.
- **R-3.5.** El uploader **debe** convivir en la misma pantalla que la tabla, ubicado de forma prominente.

### R-4. Pantalla "Chat" (consulta en lenguaje natural)

- **R-4.1.** El sistema **debe** ofrecer una pantalla dedicada de chat donde el usuario pueda escribir preguntas en español.
- **R-4.2.** El sistema **debe** ejecutar una búsqueda híbrida (densa + sparse) sobre el corpus indexado y recuperar los chunks más relevantes.
- **R-4.3.** El sistema **debe** generar una respuesta usando el LLM local, alimentándolo con los chunks recuperados como contexto.
- **R-4.4.** El sistema **debe** transmitir la respuesta en streaming (token a token) para mejorar la experiencia.
- **R-4.5.** El sistema **debe** incluir, junto con la respuesta, las citas a los documentos y páginas de origen utilizados.
- **R-4.6.** El sistema **debe** indicar explícitamente si no encuentra información relevante para la pregunta, en lugar de inventar.
- **R-4.7.** El sistema **debe** mantener el historial de la conversación visible mientras dure la sesión (no se requiere persistencia entre sesiones en el MVP).
- **R-4.8.** Si no hay ningún documento con estado `indexed`, la pantalla de chat **debe** mostrar un mensaje guiando al usuario a la pantalla "Documentos" para subir archivos.

### R-5. Visualización de citas

- **R-5.1.** El sistema **debe** permitir al usuario hacer clic en una cita y abrir el PDF correspondiente.
- **R-5.2.** El sistema **debería** abrir el PDF posicionado en la página citada (no obligatorio para MVP).

### R-6. Operación local

- **R-6.1.** El sistema **debe** funcionar sin depender de APIs externas de pago. Todos los modelos (embeddings y LLM) se ejecutan localmente.
- **R-6.2.** El backend **debe** poder consumir un servicio Ollama remoto a través de su URL configurable (para usar la RTX 5090 desde la máquina del usuario).

### R-7. Manejo de PDFs escaneados

- **R-7.1.** El sistema **debe** detectar PDFs sin texto extraíble (probablemente escaneados) y marcarlos con estado `requiere_ocr`, sin indexarlos.
- **R-7.2.** El sistema **no debe** intentar OCR en el MVP.
- **R-7.3.** El usuario **debe** poder ver claramente cuáles documentos requieren OCR para tomar acción manual.

## 6. Requisitos no funcionales

### NF-1. Rendimiento (objetivos, no SLA)

- **NF-1.1.** Indexación de un PDF de hasta 10 páginas en menos de 30 segundos (corriendo en RTX 5090).
- **NF-1.2.** Primer token de respuesta en chat en menos de 5 segundos desde que el usuario envía la pregunta.
- **NF-1.3.** Latencia total de respuesta para una pregunta típica: menos de 30 segundos.

### NF-2. Calidad de respuesta

- **NF-2.1.** Las respuestas **deben** estar fundamentadas en chunks recuperados; no se aceptan alucinaciones sin cita.
- **NF-2.2.** El sistema **debe** preferir responder *"no encuentro información sobre eso en las disposiciones cargadas"* antes que improvisar.

### NF-3. Mantenibilidad

- **NF-3.1.** El backend **debe** exponer una API HTTP independiente. El frontend (React) la consume; ningún acoplamiento más allá del contrato HTTP/JSON+SSE.
- **NF-3.2.** Los parámetros clave (modelo de embeddings, modelo LLM, tamaño de chunk, top-k, etc.) **deben** estar configurables vía variables de entorno o archivo de configuración, no hardcodeados.

### NF-4. Privacidad

- **NF-4.1.** Ningún contenido de las disposiciones **debe** salir de la red local. El requisito de modelos locales es absoluto.

## 7. Criterios de aceptación del MVP

El MVP se considera **validado** cuando, con un conjunto de **20–30 disposiciones cargadas manualmente**, el usuario puede:

1. Subir esos archivos en una sola operación y verlos indexados sin errores.
2. Hacer al menos **10 preguntas** representativas (tanto de búsqueda específica — "¿qué dice la DA 1503?" — como temáticas — "¿qué disposiciones hablan sobre contratación de consultores?") y obtener:
   - Respuestas correctas o claramente justificadas en al menos 7 de 10 casos (juicio del usuario).
   - Citas correctas (documento + página) en todos los casos donde haya respuesta.
   - Reconocimiento explícito de "no encuentro información" cuando no haya datos relevantes.
3. Hacer clic en una cita y abrir el PDF original.
4. Eliminar un documento y verificar que ya no aparece en respuestas posteriores.

## 8. Restricciones y supuestos

- **Hardware disponible**: máquina con RTX 5090 (32 GB VRAM) accesible por red local.
- **Idioma del corpus**: principalmente español.
- **Idioma de la interfaz y respuestas**: español.
- **Volumen del MVP**: decenas de documentos, no miles. El corpus completo (~2,300 DAs) se indexará en una fase posterior.
- **Sin OCR en MVP**: los PDFs escaneados quedan fuera; se manejan con un estado especial (R-7).
- **Sin metadata externa**: no se importa el catálogo CSV. La única metadata disponible es la que se extrae del PDF más el nombre de archivo.

## 9. Roadmap posterior al MVP (referencia, no compromiso)

Una vez validado el MVP, los siguientes pasos previstos son:

1. Reranking con cross-encoder. Para el perfil de producción con L40S, ver `production.md`.
2. Adjacent chunks en retrieval para mejorar contexto.
3. Múltiples extractores PDF (bookmarks, layout-based) para PDFs estructurados.
4. OCR para escaneados (Tesseract o PaddleOCR).
5. Importación masiva desde el catálogo CSV con su metadata estructurada.
6. Autenticación y multi-usuario.
7. Despliegue en servidor con la RTX 5090 como backend permanente.
