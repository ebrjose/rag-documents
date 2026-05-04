"""Ollama HTTP client. Sólo cliente; no construye prompts ni decide modelos."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import httpx

from backend.settings import settings


def _embed_payload(text: str) -> dict:
    """Single source of truth for the embedding request body. `num_ctx` evita
    que Ollama asigne KV cache para 32K cuando el embedding sólo procesa
    chunks cortos."""
    return {
        "model": settings.ollama_embed_model,
        "prompt": text,
        "options": {"num_ctx": settings.ollama_embed_context_length},
    }


async def embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=settings.ollama_embed_timeout_seconds) as client:
        r = await client.post(
            f"{settings.ollama_base_url}/api/embeddings", json=_embed_payload(text)
        )
        r.raise_for_status()
        return r.json()["embedding"]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Concurrent batching. Ollama serializa internamente, pero el solape de
    TCP/HTTP da una mejora real. Un semáforo limita la fan-out para no
    saturar al servidor con cientos de requests simultáneas."""
    if not texts:
        return []
    sem = asyncio.Semaphore(settings.embed_concurrency)

    async def _one(client: httpx.AsyncClient, text: str) -> list[float]:
        async with sem:
            r = await client.post(
                f"{settings.ollama_base_url}/api/embeddings", json=_embed_payload(text)
            )
            r.raise_for_status()
            return r.json()["embedding"]

    async with httpx.AsyncClient(timeout=settings.ollama_embed_batch_timeout_seconds) as client:
        return await asyncio.gather(*(_one(client, t) for t in texts))


def _chat_payload(
    messages: list[dict], *, temperature: float | None, stream: bool
) -> dict:
    return {
        "model": settings.ollama_llm_model,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": temperature if temperature is not None else settings.ollama_temperature,
            "num_ctx": settings.ollama_context_length,
            "num_predict": settings.ollama_max_tokens,
        },
    }


async def chat_stream_messages(
    messages: list[dict], *, temperature: float | None = None
) -> AsyncIterator[str]:
    """Stream chat completion para una conversación completa (system + history)."""
    payload = _chat_payload(messages, temperature=temperature, stream=True)
    async with httpx.AsyncClient(timeout=settings.ollama_chat_timeout_seconds) as client:
        async with client.stream(
            "POST", f"{settings.ollama_base_url}/api/chat", json=payload
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = (obj.get("message") or {}).get("content") or ""
                if content:
                    yield content
                if obj.get("done"):
                    break


async def chat_stream(
    system: str, user: str, *, temperature: float | None = None
) -> AsyncIterator[str]:
    """Conveniencia para el patrón system + single user (one-shot)."""
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    async for tok in chat_stream_messages(msgs, temperature=temperature):
        yield tok


async def chat_complete(
    system: str, user: str, *, temperature: float | None = None
) -> str:
    """Versión no-streaming, devuelve el texto completo. Útil para tareas
    auxiliares como query rewriting, no para respuestas al usuario."""
    payload = _chat_payload(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        stream=False,
    )
    async with httpx.AsyncClient(timeout=settings.ollama_chat_timeout_seconds) as client:
        r = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        r.raise_for_status()
        return ((r.json().get("message") or {}).get("content") or "").strip()


async def ping() -> bool:
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_ping_timeout_seconds) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            return r.status_code == 200
    except Exception:
        return False
