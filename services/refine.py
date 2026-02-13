# services/refine.py
from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Any

KNOWN_LOCATIONS = [
    "new cairo",
    "mostakbal city - new cairo",
    "mostakbal city",
    "el shorouk - new cairo",
    "el shorouk",
    "fifth settelments",
    "fifth settlement",

    "sheikh zayed",
    "zayed",
    "desert road- sheikh zayed",
    "green belt - sheikh zayed",

    "north coast",
    "ras al hekma",
    "ras el hekma",
    "sidi abdelrahman",
    "ain sokhna",
    "6 october",
    "6th of october",
]

def _normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _title_case_location(s: str) -> str:
    s = (s or "").strip()
    return " ".join(w.capitalize() for w in s.split())



def _best_location_match(user_text: str) -> str | None:
    t = _normalize_text(user_text)

    for loc in KNOWN_LOCATIONS:
        if loc in t:
            return loc

    candidates = get_close_matches(t, KNOWN_LOCATIONS, n=1, cutoff=0.78)
    if candidates:
        return candidates[0]

    for w in t.split():
        c2 = get_close_matches(w, KNOWN_LOCATIONS, n=1, cutoff=0.80)
        if c2:
            return c2[0]

    return None

def _parse_number_egp(text: str) -> int | None:
    t = text.lower().replace(",", " ").strip()

    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(million|m)\b", t)
    if m:
        return int(float(m.group(1)) * 1_000_000)

    m2 = re.search(r"\b(\d{1,3}(?:\s\d{3})+|\d{6,})\b", t)
    if m2:
        n = int(m2.group(1).replace(" ", ""))
        if n >= 100_000:
            return n

    return None

def build_refine_patch(message: str, state: dict[str, Any]) -> dict[str, Any]:
    t_raw = (message or "").strip()
    t = _normalize_text(t_raw)
    patch: dict[str, Any] = {}

    # Reset
    if any(x in t for x in ["reset", "restart", "start over", "new search", "from scratch"]):
        return {
            "location": None,
            "budget_min": None,
            "budget_max": None,
            "unit_type": None,
            "area_min": None,
            "area_max": None,
            "confirmed": False,
            "chosen_option": None,
            "last_results": [],
            # ✅ NEW: reset memory used by compare/details/cheapest/largest
            "last_project_ids": [],
            "__did_reset__": True,
        }

    # Change location phrases
    m = re.search(r"\b(change|set)\s+(the\s+)?location\s+(to|as)\s+(.+)$", t)
    if m:
        candidate = m.group(4).strip()
        best = _best_location_match(candidate)
        return {
            "location": _normalize_location(best or candidate),
            "confirmed": False,
            "chosen_option": None,
        }

    # Set budget explicitly when number exists
    if any(x in t for x in ["budget", "max", "under", "less than", "up to", "increase", "raise", "set", "to"]):
        n = _parse_number_egp(t)
        if n is not None and (any(x in t for x in ["budget", "max", "under", "up to", "egp", "million", "m"]) or n >= 500_000):
            return {"budget_max": n, "confirmed": False, "chosen_option": None}

    # Cheaper
    if any(x in t for x in ["cheaper", "lower", "decrease budget", "reduce budget"]):
        bm = state.get("budget_max")
        if isinstance(bm, (int, float)) and bm:
            return {
                "budget_max": int(max(bm - max(int(bm * 0.10), 250_000), 0)),
                "confirmed": False,
                "chosen_option": None,
            }
        return {}

    # Increase budget (no number) => +10%
    if any(x in t for x in ["more expensive", "increase budget", "raise budget", "higher budget"]):
        bm = state.get("budget_max")
        if isinstance(bm, (int, float)) and bm:
            return {
                "budget_max": int(bm + max(int(bm * 0.10), 250_000)),
                "confirmed": False,
                "chosen_option": None,
            }
        return {}

    # Bigger
    if any(x in t for x in ["bigger", "larger", "more space", "bigger area"]):
        am = state.get("area_min")
        new_am = (float(am) + max(float(am) * 0.10, 10.0)) if isinstance(am, (int, float)) and am else 100.0
        return {"area_min": new_am, "confirmed": False, "chosen_option": None}

    # Smaller
    if any(x in t for x in ["smaller", "less space", "smaller area"]):
        am = state.get("area_min")
        if isinstance(am, (int, float)) and am:
            new_am = float(am) - 10.0
            return {"area_min": new_am if new_am >= 30 else None, "confirmed": False, "chosen_option": None}
        return {}

    return {}
def _normalize_location(loc: str) -> str:
    loc = (loc or "").strip()
    # If contains Arabic letters, keep as-is (don’t Title Case Arabic)
    if re.search(r"[\u0600-\u06FF]", loc):
        return loc
    if loc.lower() == "zayed":
        return "Zayed"
    return _title_case_location(loc)