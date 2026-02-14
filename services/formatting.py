# services/formatting.py
from __future__ import annotations
from typing import Any, Optional


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> Optional[int]:
    if v is None or isinstance(v, bool):
        return None
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return None


def format_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return (
            "I couldn’t find matches with the current filters. "
            "Want to relax the budget or change the location/unit type?"
        )

    lines: list[str] = ["Here are the best matches I found:"]

    seen_project_ids: set[int] = set()
    shown_idx = 0

    for r in results:
        project = str(r.get("project_name") or "Unknown Project")
        location = str(r.get("location") or "Unknown Location")
        unit_type = str(r.get("unit_type") or "Unknown Unit")

        area_val = _to_float(r.get("unit_area"))
        price_val = _to_int(r.get("unit_price"))

        area_txt = f"{area_val:.0f} m²" if area_val is not None else "N/A m²"
        price_txt = f"{price_val:,} EGP" if price_val is not None else "N/A EGP"

        project_id = _safe_int(r.get("project_id"))

        # Prevent duplicate projects in display (only if project_id exists)
        if project_id is not None:
            if project_id in seen_project_ids:
                continue
            seen_project_ids.add(project_id)

        shown_idx += 1
        pid_txt = f" (Project ID: {project_id})" if project_id is not None else ""

        # ✅ Explicitly label list position as "Option X"
        lines.append(
            f"Option {shown_idx}: {project} — {location} — {unit_type} — {area_txt} — {price_txt}{pid_txt}"
        )

    lines.append("")
    lines.append("To select: reply with **Option 1–{n}** (example: `option 4`) or **Project ID** (example: `project 22`).".format(n=shown_idx))

    return "\n".join(lines)


def slim_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Keep payload small and stable for UI.
    """
    out: list[dict[str, Any]] = []
    for r in results:
        out.append(
            {
                "project_id": _safe_int(r.get("project_id")),
                "project_name": r.get("project_name"),
                "location": r.get("location"),
                "unit_type": r.get("unit_type"),
                "area": _to_float(r.get("unit_area")),
                "price": _to_int(r.get("unit_price")),
            }
        )
    return out
