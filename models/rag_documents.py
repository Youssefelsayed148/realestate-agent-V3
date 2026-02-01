from typing import Any, Dict

from sqlalchemy import BigInteger, Integer, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)

    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 🔴 FIX: rename Python attribute, keep DB column name
    meta_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",          # DB column name
        JSONB,
        nullable=False,
        server_default="{}",
    )

    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
