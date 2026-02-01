from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.projects import Project


class ProjectUnitType(Base):
    __tablename__ = "project_unit_types"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    project_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    unit_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    area: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)

    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="unit_types",
    )

    __table_args__ = (
        Index("idx_project_unit_types_project_id", "project_id"),
        Index("idx_project_unit_types_unit_type", "unit_type"),
    )
