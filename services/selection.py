# services/selection.py
from __future__ import annotations
import re
from typing import Any

def extract_option_index(message: str) -> int | None:
    """
    Supports:
      - "option 2"
      - "2"
      - "#3"
      - "show 4"
      - "i choose 1"
    Returns 0-based index.
    """
    t = (message or "").strip().lower()

    m = re.search(r"\b(option|choose|pick|select|show)\s*#?\s*(\d+)\b", t)
    if not m:
        m = re.search(r"^#?\s*(\d+)\s*$", t)  # message is just "2"
    if not m:
        return None

    idx = int(m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)) - 1
    if idx < 0:
        return None
    return idx

def format_selected(result: dict[str, Any], idx_1_based: int) -> str:
    return (
        f"Option {idx_1_based} details:\n"
        f"- Project: {result.get('project_name')}\n"
        f"- Location: {result.get('location')}\n"
        f"- Unit type: {result.get('unit_type')}\n"
        f"- Area: {result.get('area')} m²\n"
        f"- Price: {result.get('price'):,} EGP"
    )
