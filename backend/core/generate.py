"""Prompt building + chat streaming with conversation history."""
from __future__ import annotations

from typing import AsyncIterator

from backend.core import ollama_client
from backend.schemas import ChatMessage

SYSTEM_PROMPT = """Eres un asistente que responde preguntas sobre disposiciones administrativas
basándote ÚNICAMENTE en los fragmentos de documentos que se te proporcionan
como contexto.

Reglas:
1. Si la información no está en el contexto, responde exactamente:
   "No encuentro información sobre eso en las disposiciones cargadas."
2. No inventes datos, números, fechas ni referencias.
3. Cita la fuente al final de cada afirmación, en formato [archivo.pdf, pág. N].
4. Responde en español, tono formal y preciso.
5. Si la pregunta es ambigua, pide aclaración.
6. Mantén coherencia con los turnos previos de la conversación cuando responda
   un follow-up — pero las afirmaciones nuevas deben seguir basándose en el
   contexto recuperado."""

_NO_INFO_FALLBACK = "No encuentro información sobre eso en las disposiciones cargadas."


def format_context(chunks: list[dict]) -> str:
    parts: list[str] = []
    for i, ch in enumerate(chunks, 1):
        p = ch["payload"]
        page_str = (
            f"pág. {p['page_start']}"
            if p["page_end"] == p["page_start"]
            else f"págs. {p['page_start']}-{p['page_end']}"
        )
        parts.append(
            f"[Fragmento {i} — {p['filename']}, {page_str}]\n{p['text']}"
        )
    return "\n\n---\n\n".join(parts)


async def generate(
    messages: list[ChatMessage], chunks: list[dict]
) -> AsyncIterator[str]:
    """Stream response. Pasa todo el historial al LLM. La última pregunta del
    usuario lleva el contexto recuperado como prefijo para que el modelo
    cite las fuentes."""
    if not chunks:
        yield _NO_INFO_FALLBACK
        return

    payload_messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    last_idx = len(messages) - 1
    context = format_context(chunks)

    for i, m in enumerate(messages):
        if i == last_idx and m.role == "user":
            payload_messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Contexto recuperado:\n\n{context}\n\n"
                        f"Pregunta: {m.content}\n\n"
                        f"Responde basándote sólo en el contexto. Cita fuentes."
                    ),
                }
            )
        else:
            payload_messages.append({"role": m.role, "content": m.content})

    async for tok in ollama_client.chat_stream_messages(payload_messages):
        yield tok
