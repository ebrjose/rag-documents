"""Query rewriting para conversaciones multi-turno.

Convierte preguntas de seguimiento (`¿y para Europa?`, `explícame más`) en
queries autocontenidas que el retrieval puede embebir y buscar bien.

Si la conversación tiene un solo turno, no hace nada y devuelve la pregunta
original. Si el rewriter falla por cualquier razón, también degrada a la
pregunta original (mejor algo que nada).
"""
from __future__ import annotations

import logging

from backend.core import ollama_client
from backend.schemas import ChatMessage
from backend.settings import settings

log = logging.getLogger(__name__)

_REWRITE_SYSTEM_PROMPT = """Eres un asistente que reescribe preguntas de seguimiento.

Te paso un historial de conversación y la última pregunta del usuario. Devuelve
SOLO la pregunta reformulada en una sola frase, en español, autocontenida — es
decir, que pueda buscarse en una base de documentos sin necesidad del historial.

Reglas estrictas:
1. Devuelve SOLO la pregunta reformulada, sin preámbulos, sin "Aquí está:", sin
   comillas, sin formato. Una sola línea de texto plano.
2. Si la pregunta ya es autocontenida (no es follow-up), devuélvela tal cual.
3. Si la pregunta es ambigua incluso con el historial, devuélvela tal cual.
4. Nunca inventes datos que no estén en el historial."""


async def rewrite_if_followup(messages: list[ChatMessage]) -> str:
    """Returns the (possibly rewritten) query that should be used for retrieval.

    Si `query_rewriting_enabled` está apagado o sólo hay un mensaje, devuelve
    la última pregunta tal cual.
    """
    if not messages:
        return ""
    current = messages[-1].content.strip()
    if not settings.query_rewriting_enabled or len(messages) <= 1:
        return current

    history = messages[-(settings.rewrite_history_limit + 1) : -1]
    history_text = "\n".join(f"{m.role}: {m.content}" for m in history)
    user_prompt = (
        f"Historial:\n{history_text}\n\nPregunta a reformular: {current}"
    )

    try:
        rewritten = await ollama_client.chat_complete(
            _REWRITE_SYSTEM_PROMPT, user_prompt, temperature=0.0
        )
    except Exception:
        log.exception("Query rewriting falló; uso pregunta original.")
        return current

    rewritten = rewritten.strip().strip('"').strip("'")
    if not rewritten:
        return current
    if rewritten != current:
        log.info("Rewrite: %r → %r", current, rewritten)
    return rewritten
