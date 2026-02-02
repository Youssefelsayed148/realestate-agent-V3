# routers/chat_router.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db
from services.chat_flow import handle_chat_message

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    conversation_id: str | None = Field(default=None, description="Conversation UUID for continuity")
    message: str = Field(..., min_length=1, description="User message text")

class ChatResponse(BaseModel):
    conversation_id: str
    reply: str

@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    # We keep your existing service API that expects a dict payload
    result = handle_chat_message(
        db=db,
        payload=payload.model_dump()
    )

    # Expecting your service to return {"conversation_id": "...", "reply": "..."}
    # If it already does, perfect. If not, we normalize below to avoid frontend breakage.
    conv_id = result.get("conversation_id") or payload.conversation_id
    reply = result.get("reply") or result.get("message") or str(result)

    if not conv_id:
        # last resort: avoid returning null conversation_id to frontend
        conv_id = "unknown"

    return ChatResponse(conversation_id=conv_id, reply=reply)
