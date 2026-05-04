import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.core import generate, retrieve
from backend.schemas import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("")
async def chat(req: ChatRequest):
    async def event_stream():
        try:
            chunks = await retrieve.retrieve(req.question, req.top_k)
            citations: list[dict] = []
            seen: set[tuple[str, int]] = set()
            for c in chunks:
                p = c["payload"]
                key = (p["filename"], p["page_start"])
                if key in seen:
                    continue
                seen.add(key)
                citations.append(
                    {
                        "document_id": p["document_id"],
                        "filename": p["filename"],
                        "page": p["page_start"],
                    }
                )

            async for tok in generate.generate(req.question, chunks):
                yield _sse("token", {"text": tok})

            yield _sse("citations", {"citations": citations})
            yield _sse("done", {})
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
