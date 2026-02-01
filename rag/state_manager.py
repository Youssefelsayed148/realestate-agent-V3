# rag/state_manager.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models.rag_models import RagConversation, RagConversationState, RagLead, RagMessage


@dataclass
class StateUpdate:
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    location_area: Optional[str] = None
    unit_type: Optional[str] = None
    bedrooms: Optional[int] = None
    delivery_year: Optional[int] = None
    payment_plan: Optional[str] = None
    last_intent: Optional[str] = None
    last_project_ids: Optional[List[int]] = None


class StateManager:
    def __init__(self, db: Session):
        self.db = db

    # Exposed so orchestrator can sanitize returns too
    def json_safe(self, obj: Any) -> Any:
        if obj is None:
            return None
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {str(k): self.json_safe(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.json_safe(x) for x in obj]
        if isinstance(obj, tuple):
            return [self.json_safe(x) for x in obj]
        return obj

    def get_or_create_conversation(
        self,
        conversation_id: Optional[UUID] = None,
        channel: Optional[str] = None,
        user_identifier: Optional[str] = None,
    ) -> RagConversation:
        if conversation_id:
            conv = self.db.get(RagConversation, conversation_id)
            if conv:
                return conv

        conv = RagConversation(channel=channel, user_identifier=user_identifier)
        self.db.add(conv)
        self.db.flush()  # generate UUID
        self.get_or_create_state(conv.id)
        return conv

    def get_or_create_state(self, conversation_id: UUID) -> RagConversationState:
        st = self.db.get(RagConversationState, conversation_id)
        if st:
            return st
        st = RagConversationState(conversation_id=conversation_id)
        self.db.add(st)
        self.db.flush()
        return st

    def get_state(self, conversation_id: UUID) -> RagConversationState:
        st = self.db.get(RagConversationState, conversation_id)
        if not st:
            st = self.get_or_create_state(conversation_id)
        return st

    def merge_state(self, state: RagConversationState, upd: StateUpdate) -> RagConversationState:
        for field, val in upd.__dict__.items():
            if val is None:
                continue
            setattr(state, field, val)
        return state

    def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        intent: Optional[str] = None,
        entities_json: Optional[Dict[str, Any]] = None,
    ) -> RagMessage:
        entities_json = self.json_safe(entities_json)

        msg = RagMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            intent=intent,
            entities_json=entities_json,
        )
        self.db.add(msg)
        self.db.flush()
        return msg

    def get_last_messages(self, conversation_id: UUID, limit: int = 6) -> List[RagMessage]:
        return (
            self.db.query(RagMessage)
            .filter(RagMessage.conversation_id == conversation_id)
            .order_by(RagMessage.created_at.asc())
            .limit(limit)
            .all()
        )

    def add_lead(
        self,
        conversation_id: Optional[UUID],
        name: Optional[str] = None,
        phone: Optional[str] = None,
        preferred_contact_time: Optional[str] = None,
        interest_project_id: Optional[int] = None,
        interest_area: Optional[str] = None,
    ) -> RagLead:
        lead = RagLead(
            conversation_id=conversation_id,
            name=name,
            phone=phone,
            preferred_contact_time=preferred_contact_time,
            interest_project_id=interest_project_id,
            interest_area=interest_area,
        )
        self.db.add(lead)
        self.db.flush()
        return lead

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
