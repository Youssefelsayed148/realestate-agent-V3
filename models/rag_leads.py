# models/rag_lead.py
from __future__ import annotations

import uuid
from typing import Any, Optional, Dict, List
from datetime import datetime

from sqlalchemy import Text, DateTime, func, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class RagLead(Base):
    __tablename__ = "rag_leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    preferred_contact_time: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    selection_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 'project'|'unit'
    interest_project_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    interest_unit_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)

    interest_area: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    selection_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    visit_mode: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 'office'|'unit'
    preferred_visit_times: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    visit_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="new")

    email_user_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    email_office_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    assigned_to: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    email_provider_message_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
