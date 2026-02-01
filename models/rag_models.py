from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


# =========================
# Conversations
# =========================
class RagConversation(Base):
    __tablename__ = "rag_conversation"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    channel: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_identifier: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    messages: Mapped[List["RagMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    state: Mapped[Optional["RagConversationState"]] = relationship(
        back_populates="conversation",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    leads: Mapped[List["RagLead"]] = relationship(
        back_populates="conversation",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_rag_conversation_user_identifier", "user_identifier"),
        Index("idx_rag_conversation_created_at", "created_at"),
    )


# =========================
# Messages
# =========================
class RagMessage(Base):
    __tablename__ = "rag_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rag_conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(Text, nullable=False)  # user/assistant/system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    intent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    entities_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    conversation: Mapped["RagConversation"] = relationship(back_populates="messages")

    __table_args__ = (
        CheckConstraint("role in ('user','assistant','system')", name="ck_rag_messages_role"),
        Index("idx_rag_messages_conversation_created", "conversation_id", "created_at"),
        Index("idx_rag_messages_intent", "intent"),
    )


# =========================
# Conversation State (Memory)
# =========================
class RagConversationState(Base):
    __tablename__ = "rag_conversation_state"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rag_conversation.id", ondelete="CASCADE"),
        primary_key=True,
    )

    budget_min: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    budget_max: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)

    location_area: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    delivery_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payment_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    last_intent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ✅ NOW Pylance knows this is a List[int]
    last_project_ids: Mapped[List[int]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped["RagConversation"] = relationship(back_populates="state")

    __table_args__ = (
        Index("idx_rag_state_location", "location_area"),
        Index("idx_rag_state_budget_max", "budget_max"),
        Index("idx_rag_state_unit_type", "unit_type"),
    )


# =========================
# Leads
# =========================
class RagLead(Base):
    __tablename__ = "rag_leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rag_conversation.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferred_contact_time: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    interest_project_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
    )

    interest_area: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped[Optional["RagConversation"]] = relationship(back_populates="leads")

    __table_args__ = (
        Index("idx_rag_leads_phone", "phone"),
    )