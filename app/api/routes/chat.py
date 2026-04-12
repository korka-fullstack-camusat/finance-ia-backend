"""Route chat — streaming SSE async."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from app.agent.orchestrator import stream_chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("")
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message vide")

    async def generator():
        try:
            async for token in stream_chat(body.message, db):
                escaped = token.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)[:200]}\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
