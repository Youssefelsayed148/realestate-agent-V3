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
# ✅ Enhanced with compounds, districts, and directional phrases
KNOWN_LOCATIONS = [
    # Main areas
    "new cairo",
    "mostakbal city - new cairo",
    "mostakbal city",
    "el shorouk - new cairo",
    "el shorouk",
    "fifth settelments",   # DB typo
    "fifth settlement",
    "fifth district",
    
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
    "new capital",
    "new administrative capital",
    
    # Districts & neighborhoods
    "tagamo3",
    "tagamo 3",
    "el tagamo3",
    "rehab",
    "al rehab",
    "madinet nasr",
    "nasr city",
    "heliopolis",
    "masr el gedida",
    "maadi",
    "giza",
    "dokki",
    "mohandessin",
    "agouza",
    "zamalek",
    "garden city",
    "downtown",
    "ramses",
    "haram",
    "faysal",
    "imbaba",
    "shubra",
    "matarya",
    "ain shams",
    "marg",
    "waili",
    "sawah",
    "mokattam",
    "katameya",
    "wadi degla",
    
    # Compounds (popular ones)
    "marassi",
    "hacienda",
    "mountain view",
    "palm hills",
    "al palm hills",
    "katameya heights",
    "madinaty",
    "rehab city",
    "al rehab city",
    "hyde park",
    "taj city",
    "eastown",
    "waterway",
    "village gate",
    "uptown cairo",
    "creek town",
    "sodic",
    "sodic east",
    "sodic west",
    "east cairo",
    "west cairo",
    "il bosco",
    "the butterfly",
    "the Estates",
    "badya",
    "orkidia",
    "zavani",
    "al maqsed",
    "al burouj",
    "la verde",
    "capital prime",
    "de joya",
    "al manara",
    
    # Specific areas within main locations
    "golf extension",
    "golf area",
    "golden square",
    "petrified forest",
    "first settlement",
    "second settlement",
    "third settlement",
    "fourth settlement",
    "narges",
    "lotus",
    "lotus district",
    "yasmin",
    "yasmin district",
    "banafseg",
    "banafseg district",
    "el banafseg",
]

# Directional phrases that indicate location proximity
DIRECTIONAL_PHRASES = [
    r"(?:in|at|near|close to|by|next to|beside|around)\s+(.+?)(?:\s+(?:area|compound|project|district|zone))?",
    r"(?:located in|situated in|based in)\s+(.+?)(?:\s|$)",
    r"(?:prefer|preferably|looking for|want)\s+(?:something|place|apartment|villa)\s+(?:in|at|near)\s+(.+?)(?:\s|$|\.)",
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
      1) Direct contains (longest match first for compounds)
      2) Fuzzy match full string
      3) Fuzzy match single words (helps short inputs like 'zayed')
      4) Multi-word location matching
    """
    t = _normalize_text(user_text)
    
    # 1) Direct contains - sort by length (longest first) to match compounds
    sorted_locations = sorted(KNOWN_LOCATIONS, key=len, reverse=True)
    for loc in sorted_locations:
        if loc in t:
            return loc
    
    # 2) Fuzzy match full string
    candidates = get_close_matches(t, KNOWN_LOCATIONS, n=1, cutoff=0.75)
    if candidates:
        return candidates[0]
    
    # 3) Fuzzy match per word (for multi-word locations)
    words = t.split()
    best_match = None
    best_score = 0.0
    
    for i, w in enumerate(words):
        # Try single word
        c2 = get_close_matches(w, KNOWN_LOCATIONS, n=1, cutoff=0.80)
        if c2:
            return c2[0]
        
        # Try 2-word phrases
        if i < len(words) - 1:
            phrase = f"{w} {words[i+1]}"
            c3 = get_close_matches(phrase, KNOWN_LOCATIONS, n=1, cutoff=0.75)
            if c3:
                return c3[0]
        
        # Try 3-word phrases
        if i < len(words) - 2:
            phrase3 = f"{w} {words[i+1]} {words[i+2]}"
            c4 = get_close_matches(phrase3, KNOWN_LOCATIONS, n=1, cutoff=0.72)
            if c4:
                return c4[0]
    
    return None


def _extract_location_from_phrases(text: str) -> str | None:
    """
    Extract location using directional phrases like 'in X', 'near Y', 'close to Z'.
    """
    t = text.lower()
    
    for pattern in DIRECTIONAL_PHRASES:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            # Try to match the extracted candidate
            best = _best_location_match(candidate)
            if best:
                return best
            
            # Also try matching the full text with this phrase context
            full_match = _best_location_match(t)
            if full_match:
                return full_match
    
    return None


def _extract_primary_location(text: str) -> str | None:
    """
    Extract primary location from multi-location expressions like:
    - 'New Cairo or Zayed' -> returns first mentioned
    - 'preferably North Coast but open to Ain Sokhna' -> returns 'North Coast'
    """
    t = _normalize_text(text)
    
    # Split by preference indicators
    preference_splits = re.split(r'\s*(?:or|but|preferably|prefer|mainly|mostly|ideally|if possible)\s+', t)
    
    for segment in preference_splits:
        segment = segment.strip()
        if not segment:
            continue
        
        # Try to find location in this segment
        loc = _best_location_match(segment)
        if loc:
            return loc
    
    return None

def _parse_budget_egp(text: str) -> int | None:
    """
    Parse budget from text. Handles:
    - Simple amounts: 5M, 5 million, 5000000
    - Approximate: around 5M, about 5 million, ~7M
    - Budget phrases: budget is 8M, my budget 8 million
    """
    t = text.lower().replace(",", " ").strip()
    
    # Remove budget indicators to get to the number
    # Pattern: "budget is X", "my budget X", "around X", "about X", "~X"
    budget_indicators = r"(?:budget\s+(?:is\s+)?|my\s+budget\s+|around\s+|about\s+|~\s*)"
    
    # Try with budget indicators first
    m = re.search(rf"{budget_indicators}(\d+(?:\.\d+)?)\s*(million|m)\b", t)
    if m:
        return int(float(m.group(1)) * 1_000_000)
    
    # Raw number with spaces (10 000 000)
    m2 = re.search(rf"{budget_indicators}?(\d{{1,3}}(?:\s\d{{3}})+|\d{{6,}})\b", t)
    if m2:
        digits = int(m2.group(1).replace(" ", ""))
        if digits >= 100_000:
            return digits
    
    # Fallback to original patterns without indicators
    m3 = re.search(r"\b(\d+(?:\.\d+)?)\s*(million|m)\b", t)
    if m3:
        return int(float(m3.group(1)) * 1_000_000)
    
    m4 = re.search(r"\b(\d{1,3}(?:\s\d{3})+|\d{6,})\b", t)
    if m4:
        digits = int(m4.group(1).replace(" ", ""))
        if digits >= 100_000:
            return digits
    
    return None


def _parse_budget_range(text: str) -> dict[str, int] | None:
    """
    Parse budget range expressions. Returns dict with budget_min and/or budget_max.
    Handles:
    - between 3M and 5M
    - 3M to 5M / 3-5M
    - from 2M to 4M
    """
    t = text.lower().replace(",", " ").strip()
    
    # Pattern: between X and Y / from X to Y / X to Y / X-Y
    range_patterns = [
        # "between 3M and 5M" or "between 3 million and 5 million"
        r"between\s+(\d+(?:\.\d+)?)\s*(million|m)?\s+and\s+(\d+(?:\.\d+)?)\s*(million|m)?",
        # "from 2M to 4M" or "from 2 million to 4 million"
        r"from\s+(\d+(?:\.\d+)?)\s*(million|m)?\s+to\s+(\d+(?:\.\d+)?)\s*(million|m)?",
        # "3M to 5M" or "3 million to 5 million"
        r"(\d+(?:\.\d+)?)\s*(million|m)?\s+to\s+(\d+(?:\.\d+)?)\s*(million|m)?",
        # "3-5M" or "3M-5M"
        r"(\d+(?:\.\d+)?)\s*(million|m)?\s*-\s*(\d+(?:\.\d+)?)\s*(million|m)?",
    ]
    
    for pattern in range_patterns:
        m = re.search(pattern, t)
        if m:
            val1 = float(m.group(1))
            unit1 = m.group(2) if m.group(2) else ""
            val2 = float(m.group(3))
            unit2 = m.group(4) if len(m.groups()) > 3 and m.group(4) else ""
            
            # If first number has no unit but second does, inherit the unit
            if not unit1 and unit2:
                unit1 = unit2
            
            # Convert to actual values
            mult1 = 1_000_000 if unit1 in ("million", "m") else 1
            mult2 = 1_000_000 if unit2 in ("million", "m") else 1
            
            budget1 = int(val1 * mult1)
            budget2 = int(val2 * mult2)
            
            # Ensure min is actually smaller
            return {
                "budget_min": min(budget1, budget2),
                "budget_max": max(budget1, budget2)
            }
    
    return None


def _is_budget_max_indicator(text: str) -> bool:
    """Check if text indicates a maximum budget constraint."""
    max_indicators = [
        "up to", "not more than", "no more than", "at most", "maximum",
        "less than", "below", "under", "max", "حد أقصى", "أقل من"
    ]
    t = text.lower()
    return any(indicator in t for indicator in max_indicators)


def _is_budget_min_indicator(text: str) -> bool:
    """Check if text indicates a minimum budget constraint."""
    min_indicators = [
        "starting from", "from", "at least", "minimum", "more than", "above",
        "over", "min", "حد أدنى", "أكثر من", "من"
    ]
    t = text.lower()
    return any(indicator in t for indicator in min_indicators)

def _parse_area_m2(text: str) -> float | None:
    """
    Parse area from text. Handles:
    - Simple amounts: 120 sqm, 120 m2, 120 m², 120 square meters
    - Approximate: around 130 sqm, about 140 m2, ~150 sqm
    - Arabic: ١٢٠ متر, 120 متر مربع
    """
    t = text.lower().replace(",", " ").strip()
    
    # Remove area indicators to get to the number
    # Pattern: "around X", "about X", "~X", "area is X", "size is X"
    area_indicators = r"(?:area\s+(?:is\s+)?|size\s+(?:is\s+)?|around\s+|about\s+|~\s*|approximately\s+)"
    
    # Try with area indicators first
    # sqm, m2, m², square meters, square metre
    m = re.search(rf"{area_indicators}(\d+(?:\.\d+)?)\s*(sqm|m2|m²)\b", t)
    if m:
        return float(m.group(1))
    
    # square meters/metres (need \b after the word)
    m_sq = re.search(rf"{area_indicators}(\d+(?:\.\d+)?)\s*square\s+(?:meters?|metres?)\b", t)
    if m_sq:
        return float(m_sq.group(1))
    
    # meters/metres (without square)
    m2 = re.search(rf"{area_indicators}?(\d+(?:\.\d+)?)\s*(meter|meters|metre|metres)\b", t)
    if m2:
        # Make sure it's not a length measurement (e.g., "10 meters from the beach")
        # Check if it's preceded by area-related words or followed by area units
        before = t[:m2.start()]
        after = t[m2.end():]
        area_context = any(word in before[-30:] for word in ["area", "size", "space", "sqm", "m2"])
        not_length = not any(word in after[:20] for word in ["from", "away", "distance", "long", "tall"])
        if area_context or not_length:
            return float(m2.group(1))
    
    # Arabic: 120 متر or 120 متر مربع
    m3 = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:متر\s+مربع|م²|متر)\b", t)
    if m3:
        return float(m3.group(1))
    
    # Fallback: standalone "square meters/metres" without indicators
    m_sq2 = re.search(r"(\d+(?:\.\d+)?)\s*square\s+(?:meters?|metres?)\b", t)
    if m_sq2:
        return float(m_sq2.group(1))
    
    # Fallback to original patterns
    m4 = re.search(r"\b(\d+(?:\.\d+)?)\s*(sqm|m2|m²)\b", t)
    if m4:
        return float(m4.group(1))
    
    return None


def _parse_area_range(text: str) -> dict[str, float] | None:
    """
    Parse area range expressions. Returns dict with area_min and/or area_max.
    Handles:
    - between 100 and 150 sqm
    - 100-150 sqm / 100 to 150 sqm
    - from 120 to 180 m2
    """
    t = text.lower().replace(",", " ").strip()
    
    # Pattern: between X and Y / from X to Y / X to Y / X-Y
    # Support various unit formats: sqm, m2, m², square meters, meters
    unit_pattern = r"(?:sqm|m2|m²|square\s+(?:meters?|metres?)|meters?|metres?)?"
    
    range_patterns = [
        # "between 100 sqm and 150 sqm" or "between 100 and 150 square meters"
        rf"between\s+(\d+(?:\.\d+)?)\s*{unit_pattern}\s+and\s+(\d+(?:\.\d+)?)\s*{unit_pattern}",
        # "from 120 m2 to 180 m2" or "from 120 to 180 sqm"
        rf"from\s+(\d+(?:\.\d+)?)\s*{unit_pattern}\s+to\s+(\d+(?:\.\d+)?)\s*{unit_pattern}",
        # "100 sqm to 150 sqm" or "100 to 150 m2"
        rf"(\d+(?:\.\d+)?)\s*{unit_pattern}\s+to\s+(\d+(?:\.\d+)?)\s*{unit_pattern}",
        # "100-150 sqm" or "120-180 m2"
        rf"(\d+(?:\.\d+)?)\s*{unit_pattern}\s*-\s*(\d+(?:\.\d+)?)\s*{unit_pattern}",
    ]
    
    for pattern in range_patterns:
        m = re.search(pattern, t)
        if m:
            val1 = float(m.group(1))
            val2 = float(m.group(2))
            
            # Ensure min is actually smaller
            return {
                "area_min": min(val1, val2),
                "area_max": max(val1, val2)
            }
    
    return None


def _is_area_max_indicator(text: str) -> bool:
    """Check if text indicates a maximum area constraint."""
    max_indicators = [
        "up to", "not more than", "no more than", "at most", "maximum", "max",
        "less than", "below", "under", "max area", "maximum area",
        "أقل من", "حد أقصى", "ماكس"
    ]
    t = text.lower()
    return any(indicator in t for indicator in max_indicators)


def _is_area_min_indicator(text: str) -> bool:
    """Check if text indicates a minimum area constraint."""
    min_indicators = [
        "starting from", "from", "at least", "minimum", "min", "more than", "above",
        "over", "min area", "minimum area",
        "على الأقل", "حد أدنى", "أكثر من"
    ]
    t = text.lower()
    return any(indicator in t for indicator in min_indicators)

def _parse_unit_type(text: str) -> str | None:
    """
    Parse unit type from text. Handles:
    - Direct unit mentions: apartment, villa, chalet
    - With bedroom counts: "2 bedroom apartment", "3-bed villa"
    - With descriptors: "duplex with garden", "corner unit"
    - Size modifiers: "small studio", "large villa"
    """
    t = text.lower()
    
    # First, try to match compound patterns with bedroom counts
    # Pattern: "X bedroom(s) UNIT" or "X-bed UNIT"
    bedroom_unit_pattern = r"\b(\d+)\s*(?:bedroom|bed)?s?\s+(?:apartment|apt|flat|villa|chalet|townhouse|duplex|penthouse|studio)\b"
    m = re.search(bedroom_unit_pattern, t)
    if m:
        # Extract just the unit type part after the bedroom count
        unit_part = re.search(r"\b(apartment|apt|flat|villa|chalet|townhouse|duplex|penthouse|studio)\b", m.group(0))
        if unit_part:
            unit_text = unit_part.group(1)
            for canonical, variants in UNIT_KEYWORDS.items():
                for v in variants:
                    if re.search(rf"\b{re.escape(v)}\b", unit_text):
                        return canonical
    
    # Try standard unit matching
    for canonical, variants in UNIT_KEYWORDS.items():
        for v in variants:
            if re.search(rf"\b{re.escape(v)}\b", t):
                return canonical
    
    return None


def _parse_bedrooms(text: str) -> int | None:
    """
    Parse bedroom count from text. Handles:
    - "2 bedroom", "3 bedrooms"
    - "2-bed", "3-bed"
    - "2 bed", "3 beds"
    - "2br", "3br"
    """
    t = text.lower()
    
    # Pattern: "X bedroom(s)" or "X bed(s)"
    patterns = [
        r"\b(\d+)\s*(?:bedroom|bed)?s?\s+(?:apartment|apt|flat|villa|chalet|townhouse|duplex|penthouse|studio|unit)\b",
        r"\b(\d+)\s*[-\s]?(?:bedroom|bed)s?\b",
        r"\b(\d+)\s*br\b",
    ]
    
    for pattern in patterns:
        m = re.search(pattern, t)
        if m:
            try:
                return int(m.group(1))
            except (ValueError, IndexError):
                continue
    
    return None


def _parse_floor_type(text: str) -> str | None:
    """
    Parse floor type preferences. Handles:
    - "ground floor", "first floor", "second floor"
    - "high floor", "low floor", "middle floor"
    - "top floor", "upper floor"
    """
    t = text.lower()
    
    floor_patterns = [
        ("ground_floor", r"\bground\s+floor\b"),
        ("first_floor", r"\bfirst\s+floor\b|\b1st\s+floor\b"),
        ("second_floor", r"\bsecond\s+floor\b|\b2nd\s+floor\b"),
        ("high_floor", r"\bhigh\s+floor\b"),
        ("low_floor", r"\blow\s+floor\b"),
        ("middle_floor", r"\bmiddle\s+floor\b"),
        ("top_floor", r"\btop\s+floor\b|\bupper\s+floor\b"),
    ]
    
    for floor_type, pattern in floor_patterns:
        if re.search(pattern, t):
            return floor_type
    
    return None


def _parse_unit_features(text: str) -> dict[str, Any]:
    """
    Parse unit features and descriptors. Returns dict with features found.
    Handles:
    - "with garden", "with roof", "with terrace"
    - "corner unit", "end unit"
    - "sea view", "garden view", "pool view"
    - "furnished", "semi-furnished", "unfurnished"
    """
    t = text.lower()
    features = {}
    
    # Garden/Outdoor features
    if re.search(r"\bwith\s+garden\b|\bgarden\s+unit\b|\bgarden\s+villa\b", t):
        features["has_garden"] = True
    
    if re.search(r"\bwith\s+roof\b|\broof\s+terrace\b|\brooftop\b", t):
        features["has_roof"] = True
    
    if re.search(r"\bwith\s+terrace\b|\bterrace\b", t):
        features["has_terrace"] = True
    
    if re.search(r"\bwith\s+balcony\b|\bbalcony\b", t):
        features["has_balcony"] = True
    
    # Unit position
    if re.search(r"\bcorner\s+(?:unit|apartment|villa)\b", t):
        features["is_corner_unit"] = True
    
    if re.search(r"\bend\s+unit\b", t):
        features["is_end_unit"] = True
    
    # Views
    if re.search(r"\bsea\s+view\b|\bocean\s+view\b|\bbeach\s+view\b", t):
        features["view_type"] = "sea"
    elif re.search(r"\bgarden\s+view\b|\bgreen\s+view\b", t):
        features["view_type"] = "garden"
    elif re.search(r"\bpool\s+view\b", t):
        features["view_type"] = "pool"
    elif re.search(r"\bstreet\s+view\b", t):
        features["view_type"] = "street"
    
    # Furnishing
    # Check unfurnished first to avoid matching "furnished" part
    if re.search(r"\bunfurnished\b|\bnot\s+furnished\b", t):
        features["furnishing"] = "unfurnished"
    elif re.search(r"\bsemi[-\s]?furnished\b|\bpartly\s+furnished\b", t):
        features["furnishing"] = "semi"
    elif re.search(r"\bfurnished\b", t):
        features["furnishing"] = "furnished"
    
    # Size modifiers - more flexible patterns
    if re.search(r"\bsmall\s+(?:(?:furnished|unfurnished|semi[-\s]?furnished)\s+)?(?:studio|apartment|unit|house)\b", t):
        features["size_preference"] = "small"
    elif re.search(r"\blarge\s+(?:(?:furnished|unfurnished|semi[-\s]?furnished)\s+)?(?:villa|apartment|unit|house)\b", t) or \
         re.search(r"\bbig\s+(?:(?:furnished|unfurnished|semi[-\s]?furnished)\s+)?(?:villa|apartment|unit|house)\b", t):
        features["size_preference"] = "large"
    elif re.search(r"\blarge\s+\d+\s*(?:bedroom|bed)?\s+(?:villa|apartment|unit|house)\b", t):
        features["size_preference"] = "large"
    elif re.search(r"\bspacious\b", t):
        features["size_preference"] = "spacious"
    elif re.search(r"\bcompact\b|\bcozy\b", t):
        features["size_preference"] = "compact"
    
    return features

def _parse_location(text: str) -> str | None:
    """
    Parse location from text. Handles:
    - Direct location mentions
    - Change/set location phrases
    - Directional phrases: 'in X', 'near Y', 'close to Z'
    - Multi-location preferences: 'New Cairo or Zayed'
    - Compounds: 'Marassi', 'Mountain View', 'Palm Hills'
    - Districts: 'Tagamo3', 'Rehab', 'Madinet Nasr'
    """
    if not text:
        return None
    
    raw = text.strip()
    t = _normalize_text(raw)
    
    # 1) Handle: "change location to X" / "set location to X" (explicit override)
    # Match everything after "to" until end of string or punctuation
    m = re.search(r"\b(change|set)\s+(the\s+)?location\s+(to|as)\s+(.+)$", t)
    if m:
        candidate = m.group(4).strip()
        # Remove trailing punctuation
        candidate = re.sub(r'[.!?]+$', '', candidate)
        best = _best_location_match(candidate)
        if best:
            return _normalize_location(best)
        return _normalize_location(candidate)
    
    # 2) Try multi-location extraction (gets first preference)
    primary = _extract_primary_location(text)
    if primary:
        return _normalize_location(primary)
    
    # 3) Try directional phrase extraction
    phrase_loc = _extract_location_from_phrases(text)
    if phrase_loc:
        return _normalize_location(phrase_loc)
    
    # 4) Normal best-match on the whole message
    best = _best_location_match(t)
    if best:
        return _normalize_location(best)
    
    # 5) Fallback: common keywords
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

    # Check if message contains area indicators (sqm, m2, etc.)
    has_area_indicators = bool(re.search(r'\b(?:sqm|m2|m²|square\s+meters?|square\s+metres?|meters?)\b', message.lower()))
    
    # If area indicators present, parse area first
    if has_area_indicators:
        # Enhanced area extraction with ranges
        area_range = _parse_area_range(message)
        if area_range:
            patch.update(area_range)
        else:
            area = _parse_area_m2(message)
            if area is not None:
                if _is_area_max_indicator(message):
                    patch["area_max"] = area
                elif _is_area_min_indicator(message):
                    patch["area_min"] = area
                else:
                    patch["area_min"] = area
        
        # Then parse budget (single value only, skip range to avoid conflict)
        budget = _parse_budget_egp(message)
        if budget is not None:
            if _is_budget_max_indicator(message):
                patch["budget_max"] = budget
            elif _is_budget_min_indicator(message):
                patch["budget_min"] = budget
            else:
                patch["budget_max"] = budget
    else:
        # No area indicators - parse budget first (with ranges)
        budget_range = _parse_budget_range(message)
        if budget_range:
            patch.update(budget_range)
        else:
            budget = _parse_budget_egp(message)
            if budget is not None:
                if _is_budget_max_indicator(message):
                    patch["budget_max"] = budget
                elif _is_budget_min_indicator(message):
                    patch["budget_min"] = budget
                else:
                    patch["budget_max"] = budget
        
        # Then parse area (without unit indicators, this might still work for simple numbers)
        area_range = _parse_area_range(message)
        if area_range:
            patch.update(area_range)
        else:
            area = _parse_area_m2(message)
            if area is not None:
                if _is_area_max_indicator(message):
                    patch["area_max"] = area
                elif _is_area_min_indicator(message):
                    patch["area_min"] = area
                else:
                    patch["area_min"] = area

    # Bedroom count extraction
    bedrooms = _parse_bedrooms(message)
    if bedrooms is not None:
        patch["bedrooms"] = bedrooms

    # Floor type extraction
    floor_type = _parse_floor_type(message)
    if floor_type:
        patch["floor_type"] = floor_type

    # Unit features extraction
    features = _parse_unit_features(message)
    if features is not None:
        patch["features"] = features

    return patch
