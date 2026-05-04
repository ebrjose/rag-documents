import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.core import generate, retrieve
from backend.schemas import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("")
async def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(400, "Se requiere al menos un mensaje.")
    if req.messages[-1].role != "user":
        raise HTTPException(400, "El último mensaje debe ser del usuario.")

    async def event_stream():
        try:
            chunks, query = await retrieve.retrieve(req.messages, req.top_k)
            citations = _unique_citations(chunks)

            async for tok in generate.generate(req.messages, chunks):
                yield _sse("token", {"text": tok})

            yield _sse("citations", {"citations": citations})
            yield _sse("done", {"query": query})
        except Exception as e:
            yield _sse("error", {"message": f"{type(e).__name__}: {e}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _unique_citations(chunks: list[dict]) -> list[dict]:
    seen: set[tuple[str, int]] = set()
    out: list[dict] = []
    for c in chunks:
        p = c["payload"]
        key = (p["filename"], p["page_start"])
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "document_id": p["document_id"],
                "filename": p["filename"],
                "page": p["page_start"],
            }
        )
    return out
