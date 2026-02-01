from typing import Any, Dict, List, Optional, Tuple


def _min_max(nums: List[Optional[float]]) -> Tuple[Optional[float], Optional[float]]:
    vals = [x for x in nums if isinstance(x, (int, float))]
    if not vals:
        return None, None
    return min(vals), max(vals)


def _compact_text(text: str, max_lines: int = 4) -> str:
    """
    Make long descriptions chat-friendly:
    - strip
    - split lines
    - take up to max_lines non-empty lines
    """
    if not text:
        return ""
    lines = [ln.strip() for ln in text.replace("\r", "").split("\n")]
    lines = [ln for ln in lines if ln]  # remove empty lines
    return "\n".join(lines[:max_lines])


def format_project_details(project: Dict[str, Any], max_lines: int = 4) -> str:
    name = project.get("project_name") or f"Project #{project.get('id')}"
    area = project.get("area") or "Unknown location"

    desc = _compact_text(project.get("description") or "", max_lines=max_lines)

    units = project.get("unit_types") or []
    prices = [u.get("price") for u in units]
    areas = [u.get("area") for u in units]

    min_p, max_p = _min_max(prices)
    min_a, max_a = _min_max(areas)

    parts = [f"{name} — {area}"]
    if desc:
        parts.append(desc)

    line_bits = []
    if min_p is not None:
        if max_p is not None and max_p != min_p:
            line_bits.append(f"Price range: {min_p:,.0f} – {max_p:,.0f} EGP")
        else:
            line_bits.append(f"From {min_p:,.0f} EGP")

    if min_a is not None:
        if max_a is not None and max_a != min_a:
            line_bits.append(f"Sizes: {min_a:,.0f} – {max_a:,.0f} m²")
        else:
            line_bits.append(f"Size: {min_a:,.0f} m²")

    line_bits.append(f"Unit options: {len(units)}")
    parts.append(" | ".join(line_bits))

    return "\n\n".join(parts)


def format_compare_summary(result: Dict[str, Any]) -> str:
    summary = result.get("summary", "Comparison")
    diffs = result.get("differences", {})

    bullets = []
    if diffs.get("price"):
        bullets.append(f"- Price: {diffs['price']}")
    if diffs.get("unit_sizes"):
        bullets.append(f"- Unit sizes: {diffs['unit_sizes']}")
    if diffs.get("variety"):
        bullets.append(f"- Variety: {diffs['variety']}")

    return summary + ("\n\n" + "\n".join(bullets) if bullets else "")


# -----------------------
# UI-friendly compact objects (for compare response)
# -----------------------
def compact_project_for_ui(project: Dict[str, Any], max_lines: int = 4) -> Dict[str, Any]:
    units = project.get("unit_types") or []
    prices = [u.get("price") for u in units]
    areas = [u.get("area") for u in units]

    min_p, max_p = _min_max(prices)
    min_a, max_a = _min_max(areas)

    return {
        "id": project.get("id"),
        "project_name": project.get("project_name"),
        "area": project.get("area"),
        "description": _compact_text(project.get("description") or "", max_lines=max_lines),
        "unit_count": len(units),
        "min_price": min_p,
        "max_price": max_p,
        "min_area": min_a,
        "max_area": max_a,
    }


def compact_projects_for_ui(projects: List[Dict[str, Any]], max_lines: int = 4) -> List[Dict[str, Any]]:
    return [compact_project_for_ui(p, max_lines=max_lines) for p in projects]
