import re
from typing import List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.projects import Project


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def search_projects_ranked(db: Session, query: str, limit: int = 8) -> List[Tuple[Project, int]]:
    """
    Simple ranking:
    3 = exact contains
    2 = startswith
    1 = partial
    """
    q = (query or "").strip()
    if not q:
        return []

    ql = q.lower()

    rows = (
        db.query(Project)
        .filter(Project.project_name.isnot(None))
        .filter(func.lower(Project.project_name).contains(ql))
        .limit(limit)
        .all()
    )

    scored: List[Tuple[Project, int]] = []
    for p in rows:
        name = (p.project_name or "").lower()
        if name == ql:
            score = 3
        elif name.startswith(ql):
            score = 2
        else:
            score = 1
        scored.append((p, score))

    scored.sort(key=lambda x: (-x[1], _norm(x[0].project_name or "")))
    return scored
