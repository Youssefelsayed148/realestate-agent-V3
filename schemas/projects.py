from pydantic import BaseModel
from typing import Dict, List, Optional


class UnitTypeOut(BaseModel):
    id: int
    unit_type: Optional[str] = None
    area: Optional[float] = None
    price: Optional[float] = None


class ProjectOut(BaseModel):
    id: int
    project_name: Optional[str] = None
    area: Optional[str] = None
    description: Optional[str] = None

    apartment_type_price: Optional[str] = None
    summary_format: Optional[str] = None
    summary_path: Optional[str] = None
    html_summary: Optional[str] = None

    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    unit_types: List[UnitTypeOut] = []


class CompareRequest(BaseModel):
    project_ids: List[int]


class CompareOut(BaseModel):
    projects: List[ProjectOut]
    summary: str
    differences: Dict[str, str]
