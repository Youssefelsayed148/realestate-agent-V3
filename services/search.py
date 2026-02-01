# services/search.py
from __future__ import annotations
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

DEFAULT_LIMIT = 10

def search_db(db: Session, state: dict[str, Any], limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    """
    Robust DB search:
    - location: contains match on projects.area (ILIKE)
    - unit_type: contains match on project_unit_types.unit_type (ILIKE)
      so "Apartment" matches "Apartments" + "Apartment with Garden"
    - budgets/areas: numeric comparisons
    """

    location = (state.get("location") or "").strip()
    unit_type = (state.get("unit_type") or "").strip() or None

    budget_min = state.get("budget_min")
    budget_max = state.get("budget_max")
    area_min = state.get("area_min")
    area_max = state.get("area_max")

    sql = text("""
        SELECT
            p.id AS project_id,
            p.project_name,
            p.area AS location,
            p.description,
            put.unit_type,
            put.area AS unit_area,
            put.price AS unit_price
        FROM project_unit_types put
        JOIN projects p ON p.id = put.project_id
        WHERE
            (:location = '' OR p.area ILIKE '%' || :location || '%')
            AND (:unit_type IS NULL OR put.unit_type ILIKE '%' || :unit_type || '%')
            AND (:budget_min IS NULL OR put.price >= :budget_min)
            AND (:budget_max IS NULL OR put.price <= :budget_max)
            AND (:area_min IS NULL OR put.area >= :area_min)
            AND (:area_max IS NULL OR put.area <= :area_max)
        ORDER BY
            CASE
              WHEN :budget_max IS NOT NULL THEN ABS(put.price - :budget_max)
              ELSE put.price
            END ASC,
            put.area DESC
        LIMIT :limit
    """)

    rows = db.execute(sql, {
        "location": location,
        "unit_type": unit_type,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "area_min": area_min,
        "area_max": area_max,
        "limit": limit,
    }).mappings().all()

    return [dict(r) for r in rows]
