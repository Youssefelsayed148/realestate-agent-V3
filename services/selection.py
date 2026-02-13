# services/selection.py
from __future__ import annotations
import re
from typing import Any, Optional

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

_ORDINAL_MAP = {
    # english
    "first": 1, "1st": 1,
    "second": 2, "2nd": 2,
    "third": 3, "3rd": 3,
    "fourth": 4, "4th": 4,
    "fifth": 5, "5th": 5,
    # arabic common
    "اول": 1, "الأول": 1, "الاول": 1,
    "تاني": 2, "ثاني": 2, "الثاني": 2, "التاني": 2,
    "تالت": 3, "ثالث": 3, "الثالث": 3, "التالت": 3,
    "رابع": 4, "الرابع": 4,
    "خامس": 5, "الخامس": 5,
}

def _norm(text: str) -> str:
    t = (text or "").strip().lower().translate(_ARABIC_DIGITS)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def extract_option_index(message: str) -> int | None:
    """
    Supports:
      - "option 2"
      - "2"
      - "#3"
      - "show 4"
      - "i choose 1"
      - "second", "2nd"
      - "تاني", "الثاني"
      - Arabic digits "٢", "#٣"
    Returns 0-based index.
    """
    t = _norm(message)

    # 1) Ordinals / words
    for k, one_based in _ORDINAL_MAP.items():
        if re.search(rf"\b{k}\b", t):
            return one_based - 1

    # 2) "option 2" / "choose 2" / "اختار 2" / "وريني 3"
    m = re.search(r"\b(option|choose|pick|select|show|اختار|اختيار|وريني|اعرض|اظهر)\s*#?\s*(\d+)\b", t)
    if not m:
        # 3) message is just "2" or "#2"
        m = re.search(r"^#?\s*(\d+)\s*$", t)

    if not m:
        return None

    idx = int(m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)) - 1
    return idx if idx >= 0 else None

def format_selected(result: dict[str, Any], idx_1_based: int) -> str:
    return (
        f"Option {idx_1_based} details:\n"
        f"- Project: {result.get('project_name')}\n"
        f"- Location: {result.get('location')}\n"
        f"- Unit type: {result.get('unit_type')}\n"
        f"- Area: {result.get('area')} m²\n"
        f"- Price: {result.get('price'):,} EGP"
    )
