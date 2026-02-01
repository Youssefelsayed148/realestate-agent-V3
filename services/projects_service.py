from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.projects import Project
from models.project_unit_types import ProjectUnitType


def get_project_with_units(db: Session, project_id: int) -> Optional[Dict[str, Any]]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None

    units = (
        db.query(ProjectUnitType)
        .filter(ProjectUnitType.project_id == project_id)
        .order_by(ProjectUnitType.price.asc().nullslast())
        .all()
    )

    return {
        "id": int(project.id),
        "project_name": project.project_name,
        "area": project.area,
        "description": project.description,

        # Useful fields from your projects table
        "apartment_type_price": project.apartment_type_price,
        "summary_format": project.summary_format,
        "summary_path": project.summary_path,
        "html_summary": project.html_summary,

        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,

        "unit_types": [
            {
                "id": int(u.id),
                "unit_type": u.unit_type,
                "area": float(u.area) if u.area is not None else None,
                "price": float(u.price) if u.price is not None else None,
            }
            for u in units
        ],
    }


def get_projects_with_units(db: Session, project_ids: List[int]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for pid in project_ids:
        item = get_project_with_units(db, pid)
        if item:
            results.append(item)
    return results
