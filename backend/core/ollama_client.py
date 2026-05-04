import json
from typing import AsyncIterator

import httpx

from backend.settings import settings


async def embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
        )
        r.raise_for_status()
        return r.json()["embedding"]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    async with httpx.AsyncClient(timeout=300.0) as client:
        for t in texts:
            r = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": settings.ollama_embed_model, "prompt": t},
            )
            r.raise_for_status()
            out.append(r.json()["embedding"])
    return out


async def chat_stream(
    system: str, user: str, *, temperature: float | None = None
) -> AsyncIterator[str]:
    payload = {
        "model": settings.ollama_llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": True,
        "options": {
            "temperature": temperature if temperature is not None else settings.ollama_temperature,
            "num_ctx": settings.ollama_context_length,
        },
    }
    async with httpx.AsyncClient(timeout=None) as client:
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
                msg = obj.get("message") or {}
                content = msg.get("content") or ""
                if content:
                    yield content
                if obj.get("done"):
                    break


async def ping() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            return r.status_code == 200
    except Exception:
        return False
