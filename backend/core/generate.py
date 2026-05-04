from typing import AsyncIterator

from backend.core import ollama_client

SYSTEM_PROMPT = """Eres un asistente que responde preguntas sobre disposiciones administrativas
basándote ÚNICAMENTE en los fragmentos de documentos que se te proporcionan
como contexto.

Reglas:
1. Si la información no está en el contexto, responde exactamente:
   "No encuentro información sobre eso en las disposiciones cargadas."
2. No inventes datos, números, fechas ni referencias.
3. Cita la fuente al final de cada afirmación, en formato [archivo.pdf, pág. N].
4. Responde en español, tono formal y preciso.
5. Si la pregunta es ambigua, pide aclaración."""


def format_context(chunks: list[dict]) -> str:
    parts: list[str] = []
    for i, ch in enumerate(chunks, 1):
        p = ch["payload"]
        page = p["page_start"]
        if p["page_end"] != p["page_start"]:
            page_str = f"págs. {p['page_start']}-{p['page_end']}"
        else:
            page_str = f"pág. {page}"
        parts.append(
            f"[Fragmento {i} — {p['filename']}, {page_str}]\n{p['text']}"
        )
    return "\n\n---\n\n".join(parts)


async def generate(question: str, chunks: list[dict]) -> AsyncIterator[str]:
    if not chunks:
        yield "No encuentro información sobre eso en las disposiciones cargadas."
        return
    context = format_context(chunks)
    user = (
        f"Contexto disponible:\n\n{context}\n\n"
        f"Pregunta: {question}\n\n"
        f"Responde basándote sólo en el contexto. Cita fuentes al final de cada afirmación."
    )
    async for tok in ollama_client.chat_stream(SYSTEM_PROMPT, user):
        yield tok
