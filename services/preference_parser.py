# services/preference_parser.py
from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Any

UNIT_KEYWORDS = {
    "Apartment": ["apartment", "apartments", "apt", "flat"],
    "Chalet": ["chalet", "chalets"],
    "Villa": ["villa", "villas", "separate villa", "garden villa", "sky villa", "twin villa"],
    "Town House": ["town house", "townhouse"],
    "Twin House": ["twin house"],
    "Duplex": ["duplex"],
    "Studio": ["studio"],
    "Penthouse": ["penthouse"],
    "Lofts": ["loft", "lofts"],
    "Cabins": ["cabin", "cabins"],
    "Offices": ["office", "offices"],
}

# Locations seen in your DB (including common variants/typos)
# ✅ Added: "zayed"
KNOWN_LOCATIONS = [
    "new cairo",
    "mostakbal city - new cairo",
    "mostakbal city",
    "el shorouk - new cairo",
    "el shorouk",
    "fifth settelments",   # DB typo
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

def _title_case_location(s: str) -> str:
    s = (s or "").strip()
    return " ".join(w.capitalize() for w in s.split())

def _normalize_text(s: str) -> str:
    """
    Normalize for fuzzy matching:
    - lowercase
    - remove punctuation
    - collapse spaces
    """
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)  # keep letters/digits/spaces/dashes
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _normalize_location(loc: str) -> str:
    """
    Canonical nice output for UI/state.
    """
    if loc.strip().lower() == "zayed":
        return "Zayed"
    return _title_case_location(loc)

def _best_location_match(user_text: str) -> str | None:
    """
    Finds the best match from KNOWN_LOCATIONS even with typos.
    Strategy:
      1) direct contains
      2) fuzzy match full string
      3) fuzzy match single words (helps short inputs like 'zayed')
    """
    t = _normalize_text(user_text)

    # 1) direct contains
    for loc in KNOWN_LOCATIONS:
        if loc in t:
            return loc

    # 2) fuzzy match full
    # cutoff tuned to accept small typos but avoid wild matches
    candidates = get_close_matches(t, KNOWN_LOCATIONS, n=1, cutoff=0.78)
    if candidates:
        return candidates[0]

    # 3) fuzzy match per word
    words = t.split()
    for w in words:
        c2 = get_close_matches(w, KNOWN_LOCATIONS, n=1, cutoff=0.80)
        if c2:
            return c2[0]

    return None

def _parse_budget_egp(text: str) -> int | None:
    t = text.lower().replace(",", " ").strip()

    # 10m / 10 million
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(million|m)\b", t)
    if m:
        return int(float(m.group(1)) * 1_000_000)

    # 10000000 or 10 000 000
    m2 = re.search(r"\b(\d{1,3}(?:\s\d{3})+|\d{6,})\b", t)
    if m2:
        digits = int(m2.group(1).replace(" ", ""))
        if digits >= 100_000:
            return digits

    return None

def _parse_area_m2(text: str) -> float | None:
    t = text.lower()

    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(m2|sqm|m²)\b", t)
    if m:
        return float(m.group(1))

    m2 = re.search(r"\b(\d+(?:\.\d+)?)\s*(meter|meters|metre|metres|متر)\b", t)
    if m2:
        return float(m2.group(1))

    return None

def _parse_unit_type(text: str) -> str | None:
    t = text.lower()
    for canonical, variants in UNIT_KEYWORDS.items():
        for v in variants:
            if re.search(rf"\b{re.escape(v)}\b", t):
                return canonical
    return None

def _parse_location(text: str) -> str | None:
    raw = (text or "").strip()
    t = _normalize_text(raw)

    # ✅ handle: "change location to X" / "set location to X"
    m = re.search(r"\b(change|set)\s+(the\s+)?location\s+(to|as)\s+(.+)$", t)
    if m:
        candidate = m.group(4).strip()
        best = _best_location_match(candidate)
        if best:
            return _normalize_location(best)
        return _normalize_location(candidate)

    # normal best-match on the whole message
    best = _best_location_match(t)
    if best:
        return _normalize_location(best)

    # fallback: common keyword
    if "new cairo" in t:
        return "New Cairo"

    return None

def extract_state_patch(message: str) -> dict[str, Any]:
    patch: dict[str, Any] = {}

    loc = _parse_location(message)
    if loc:
        patch["location"] = loc

    unit = _parse_unit_type(message)
    if unit:
        patch["unit_type"] = unit

    budget = _parse_budget_egp(message)
    if budget is not None:
        if re.search(r"\b(min|from|starting)\b", message.lower()):
            patch["budget_min"] = budget
        else:
            patch["budget_max"] = budget

    area = _parse_area_m2(message)
    if area is not None:
        if re.search(r"\b(max|under|below|less than)\b", message.lower()):
            patch["area_max"] = area
        else:
            patch["area_min"] = area

    return patch
