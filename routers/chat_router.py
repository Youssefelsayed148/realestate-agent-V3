# routers/chat.py
from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from services.chat_flow import handle_chat_message

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("")
def chat(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    return handle_chat_message(db=db, payload=payload)
