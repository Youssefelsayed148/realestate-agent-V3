from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, DateTime, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.project_unit_types import ProjectUnitType


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    project_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    area: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    apartment_type_price: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.now(),
    )

    # summary_format is USER-DEFINED in DB.
    # Safest mapping: Text (unless you tell me what the enum/type name is).
    summary_format: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    summary_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    html_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    unit_types: Mapped[List["ProjectUnitType"]] = relationship(
        "ProjectUnitType",
        back_populates="project",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_projects_project_name", "project_name"),
        Index("idx_projects_area", "area"),
    )
