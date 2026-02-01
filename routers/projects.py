from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from schemas.projects import ProjectOut, CompareRequest, CompareOut
from services.projects_service import get_project_with_units, get_projects_with_units
from services.compare_service import compare_projects

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/{project_id}", response_model=ProjectOut)
def project_details(project_id: int, db: Session = Depends(get_db)):
    data = get_project_with_units(db, project_id)
    if not data:
        raise HTTPException(status_code=404, detail="Project not found")
    return data


@router.post("/compare", response_model=CompareOut)
def compare(req: CompareRequest, db: Session = Depends(get_db)):
    if len(req.project_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 project_ids")

    projects = get_projects_with_units(db, req.project_ids)
    if len(projects) < 2:
        raise HTTPException(status_code=404, detail="Not enough projects found to compare")

    result = compare_projects(projects)
    return {
        "projects": projects,
        "summary": result["summary"],
        "differences": result["differences"],
    }
