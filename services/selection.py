# services/selection.py
from __future__ import annotations

import re
from typing import Any, Optional, Tuple

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

_ORDINAL_MAP = {
    # English
    "first": 1, "1st": 1,
    "second": 2, "2nd": 2,
    "third": 3, "3rd": 3,
    "fourth": 4, "4th": 4,
    "fifth": 5, "5th": 5,
    # Arabic (kept)
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


def _safe_int(x: Any) -> Optional[int]:
    if x is None or isinstance(x, bool):
        return None
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return None


def extract_project_id(message: str) -> Optional[int]:
    """
    Explicit project id selection:
      - "project 22"
      - "project id 22"
      - "id 22"
    """
    t = _norm(message)
    m = re.search(r"\b(project\s*id|project|id)\s*[:#]?\s*(\d+)\b", t)
    if not m:
        return None
    return _safe_int(m.group(2))


def extract_option_index(message: str) -> Optional[int]:
    """
    Option index selection (0-based):
      - "option 2"
      - "choose 2"
      - "pick 2"
      - "show 2"
      - "2"
      - "#2"
      - ordinals: "second", "2nd", "fourth"
    """
    t = _norm(message)

    # Ordinals / words
    for k, one_based in _ORDINAL_MAP.items():
        if re.search(rf"\b{k}\b", t):
            return one_based - 1

    # "option 2" / "choose 2" / ...
    m = re.search(r"\b(option|choose|pick|select|show)\s*#?\s*(\d+)\b", t)
    if not m:
        # Just "2" or "#2"
        m = re.search(r"^#?\s*(\d+)\s*$", t)

    if not m:
        return None

    n = _safe_int(m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1))
    if n is None:
        return None

    idx = n - 1
    return idx if idx >= 0 else None


def resolve_choice(
    message: str,
    last_results: list[dict[str, Any]],
) -> Tuple[Optional[dict[str, Any]], Optional[int], Optional[int]]:
    """
    Returns:
      (chosen_result, chosen_index_0based, mentioned_project_id)

    Rules:
      A) If explicit "id/project" keyword -> match by project_id
      B) Else if looks like option selection and within 1..N -> match by index
      C) Else if message is just a number:
         - If within 1..N -> option index
         - Else try match by project_id
    """
    t = _norm(message)

    # A) Explicit project id
    pid = extract_project_id(t)
    if pid is not None:
        for i, r in enumerate(last_results):
            rpid = _safe_int(r.get("project_id"))
            if rpid is not None and rpid == pid:
                return r, i, pid
        return None, None, pid  # mentioned pid but not found

    # B) Option index
    idx = extract_option_index(t)
    if idx is not None and 0 <= idx < len(last_results):
        chosen = last_results[idx]
        return chosen, idx, _safe_int(chosen.get("project_id"))

    # C) Plain number disambiguation
    m = re.search(r"^#?\s*(\d+)\s*$", t)
    if m:
        n = _safe_int(m.group(1))
        if n is None:
            return None, None, None

        # If it's a valid option number, treat as option
        if 1 <= n <= len(last_results):
            idx2 = n - 1
            chosen = last_results[idx2]
            return chosen, idx2, _safe_int(chosen.get("project_id"))

        # Otherwise try project_id
        for i, r in enumerate(last_results):
            rpid = _safe_int(r.get("project_id"))
            if rpid is not None and rpid == n:
                return r, i, n

    return None, None, None


def format_selected(result: dict[str, Any], idx_1_based: int) -> str:
    price = result.get("price")
    try:
        price_txt = f"{int(price):,} EGP" if price is not None else "N/A"
    except Exception:
        price_txt = str(price) if price is not None else "N/A"

    return (
        f"Option {idx_1_based} details:\n"
        f"- Project: {result.get('project_name')}\n"
        f"- Location: {result.get('location')}\n"
        f"- Unit type: {result.get('unit_type')}\n"
        f"- Area: {result.get('area')} m²\n"
        f"- Price: {price_txt}\n\n"
        "If you want, I can arrange a viewing. Tell me if you prefer an **office visit** or a **unit visit**, "
        "and I’ll collect your name, phone, and email."
    )
