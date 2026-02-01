from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text


def _unit_type_pattern(unit_type: str) -> str:
    """
    Map normalized unit types to DB patterns.
    Your DB values are like:
    - Apartments
    - Apartment with Garden
    - Duplex with Garden
    - Separate Villa
    """
    u = (unit_type or "").strip().lower()
    if u in ("apartment", "apt", "flat"):
        return "%apart%"
    if u == "villa":
        return "%villa%"
    if u == "chalet":
        return "%chalet%"
    if u == "duplex":
        return "%duplex%"
    if u == "studio":
        return "%studio%"
    if u == "penthouse":
        return "%penthouse%"
    if u == "townhouse":
        return "%town%"
    return f"%{u}%" if u else "%"


def search_units(
    db: Session,
    location_area: str,
    unit_type: str,
    budget_max: float,
    bedrooms: Optional[int] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Minimal search using DB filtering.
    Note: bedrooms is not used here because your project_unit_types table likely
    doesn't store bedrooms per offer (can be added later if available).
    """
    unit_pat = _unit_type_pattern(unit_type)

    sql = """
    SELECT
      p.id as project_id,
      p.project_name,
      p.area as project_area,
      put.unit_type,
      put.area as unit_area_sqm,
      put.price as unit_price
    FROM projects p
    JOIN project_unit_types put ON put.project_id = p.id
    WHERE p.area ILIKE :loc
      AND put.unit_type ILIKE :unit_pat
      AND put.price <= :budget_max
    ORDER BY put.price ASC
    LIMIT :limit
    """

    rows = db.execute(
        text(sql),
        {
            "loc": f"%{location_area}%",
            "unit_pat": unit_pat,
            "budget_max": budget_max,
            "limit": limit,
        },
    ).mappings().all()

    return [dict(r) for r in rows]


def min_price_for_filters(
    db: Session,
    location_area: str,
    unit_type: str,
) -> Optional[float]:
    """
    Used when there are no results: gives the user a helpful minimum price.
    """
    unit_pat = _unit_type_pattern(unit_type)

    sql = """
    SELECT MIN(put.price) AS min_price
    FROM projects p
    JOIN project_unit_types put ON put.project_id = p.id
    WHERE p.area ILIKE :loc
      AND put.unit_type ILIKE :unit_pat
    """

    val = db.execute(
        text(sql),
        {"loc": f"%{location_area}%", "unit_pat": unit_pat},
    ).scalar()

    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None
