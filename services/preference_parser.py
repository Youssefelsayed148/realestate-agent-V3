# services/preference_parser.py
from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Any


# ----------------------------
# Digit normalization (Arabic -> Latin)
# ----------------------------
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _to_latin_digits(s: str) -> str:
    return (s or "").translate(_ARABIC_DIGITS)


# ----------------------------
# Unit keywords (EN + AR + typos)
# Canonical names here can be used in your DB filtering/pattern matching later.
# ----------------------------
UNIT_KEYWORDS = {
    "Apartment": [
        "apartment", "apartments", "apt", "flat", "appartment", "appartments",
        "شقة", "شقه", "شقق",
    ],
    "Chalet": [
        "chalet", "chalets", "shalet", "shaleet",
        "شاليه", "شاليهات",
    ],
    "Villa": [
        "villa", "villas", "vila",
        "separate villa", "garden villa", "sky villa", "twin villa",
        "فيلا", "فلل",
    ],
    "Town House": [
        "town house", "townhouse", "town-home",
        "تاون", "تاون هاوس", "تاونهاوس",
    ],
    "Twin House": [
        "twin house", "twinhouse",
        "توين", "توين هاوس", "توينهاوس",
    ],
    "Duplex": [
        "duplex", "duplx", "duplexes",
        "دوبلكس", "دوبليكس",
    ],
    "Studio": [
        "studio", "studios",
        "استوديو",
    ],
    "Penthouse": [
        "penthouse", "penthous", "pent house",
        "بنتهاوس", "بنت هاوس",
    ],
    "Lofts": [
        "loft", "lofts",
        "لوفت", "لوفتس",
    ],
    "Cabins": [
        "cabin", "cabins",
        "كابينة", "كابينه", "كابينات",
    ],
    "Offices": [
        "office", "offices",
        "مكتب", "مكاتب",
    ],
}


# ----------------------------
# Locations
# (kept from your version; we just normalize better + Arabic digit support)
# ----------------------------
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
    "the estates",
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

DIRECTIONAL_PHRASES = [
    r"(?:in|at|near|close to|by|next to|beside|around)\s+(.+?)(?:\s+(?:area|compound|project|district|zone))?",
    r"(?:located in|situated in|based in)\s+(.+?)(?:\s|$)",
    r"(?:prefer|preferably|looking for|want)\s+(?:something|place|apartment|villa)\s+(?:in|at|near)\s+(.+?)(?:\s|$|\.)",
    # Arabic-ish
    r"(?:في|بـ|ب|جنب|قريب من|حول)\s+(.+?)(?:\s|$|\.)",
]


# ----------------------------
# Normalization helpers
# ----------------------------
def _title_case_location(s: str) -> str:
    s = (s or "").strip()
    return " ".join(w.capitalize() for w in s.split())


def _normalize_text(s: str) -> str:
    """
    Normalize for matching:
    - lowercase
    - convert Arabic digits
    - keep Arabic letters + english letters + digits + spaces + dashes
    - collapse spaces
    """
    s = _to_latin_digits((s or "").lower().strip())
    s = re.sub(r"[^0-9a-z\u0600-\u06FF\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalize_location(loc: str) -> str:
    """
    Canonical nice output for UI/state.
    - Keep Arabic as-is
    - Title Case English
    """
    loc = (loc or "").strip()
    if not loc:
        return loc
    if re.search(r"[\u0600-\u06FF]", loc):
        return loc  # Arabic: don't Title Case
    if loc.lower() == "zayed":
        return "Zayed"
    return _title_case_location(loc)


def _best_location_match(user_text: str) -> str | None:
    t = _normalize_text(user_text)

    # 1) direct contains (longest first)
    for loc in sorted(KNOWN_LOCATIONS, key=len, reverse=True):
        if loc in t:
            return loc

    # 2) fuzzy full string
    candidates = get_close_matches(t, KNOWN_LOCATIONS, n=1, cutoff=0.75)
    if candidates:
        return candidates[0]

    # 3) fuzzy per word and small phrases
    words = t.split()
    for i, w in enumerate(words):
        c1 = get_close_matches(w, KNOWN_LOCATIONS, n=1, cutoff=0.80)
        if c1:
            return c1[0]

        if i < len(words) - 1:
            phrase2 = f"{w} {words[i+1]}"
            c2 = get_close_matches(phrase2, KNOWN_LOCATIONS, n=1, cutoff=0.75)
            if c2:
                return c2[0]

        if i < len(words) - 2:
            phrase3 = f"{w} {words[i+1]} {words[i+2]}"
            c3 = get_close_matches(phrase3, KNOWN_LOCATIONS, n=1, cutoff=0.72)
            if c3:
                return c3[0]

    return None


def _extract_location_from_phrases(text: str) -> str | None:
    t = _normalize_text(text)

    for pattern in DIRECTIONAL_PHRASES:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            candidate = (m.group(1) or "").strip()
            best = _best_location_match(candidate)
            if best:
                return best

            full_match = _best_location_match(t)
            if full_match:
                return full_match

    return None


def _extract_primary_location(text: str) -> str | None:
    t = _normalize_text(text)

    # Split by preference indicators (EN + AR)
    preference_splits = re.split(r"\s*(?:or|but|preferably|prefer|mainly|mostly|ideally|if possible|او|لكن|يفضل|ممكن)\s+", t)

    for segment in preference_splits:
        segment = segment.strip()
        if not segment:
            continue
        loc = _best_location_match(segment)
        if loc:
            return loc

    return None


# ----------------------------
# Budget parsing (EN + AR + digits)
# ----------------------------
def _parse_budget_egp(text: str) -> int | None:
    """
    Handles:
    - 5M, 5 million, 5.5m
    - 5000000, 5,000,000, 5 000 000
    - Arabic: ٥ مليون, ٣.٥م, ٥م
    - "around/about/~" noise
    """
    t = _to_latin_digits((text or "").lower().replace(",", " ").strip())
    t = re.sub(r"\s+", " ", t)

    # Accept Arabic million markers too: مليون / م
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(million|m|مليون|م)\b", t)
    if m:
        return int(float(m.group(1)) * 1_000_000)

    # Also accept "k/thousand" in case users type 750k
    mk = re.search(r"\b(\d+(?:\.\d+)?)\s*(k|thousand|الف)\b", t)
    if mk:
        return int(float(mk.group(1)) * 1_000)

    # Raw number with spaces 10 000 000 OR 5000000
    m2 = re.search(r"\b(\d{1,3}(?:\s\d{3})+|\d{6,})\b", t)
    if m2:
        digits = int(m2.group(1).replace(" ", ""))
        if digits >= 100_000:
            return digits

    return None


def _parse_budget_range(text: str) -> dict[str, int] | None:
    """
    Handles:
    - between 3M and 5M
    - from 2M to 4M
    - 3 to 5 million
    - 3-5M
    - Arabic: من ٣م ل ٥م / بين ٣ و ٥ مليون
    """
    t = _to_latin_digits((text or "").lower().replace(",", " ").strip())
    t = re.sub(r"\s+", " ", t)

    # Support English & Arabic connectors
    patterns = [
        r"(?:between|بين)\s+(\d+(?:\.\d+)?)\s*(million|m|مليون|م)?\s+(?:and|و)\s+(\d+(?:\.\d+)?)\s*(million|m|مليون|م)?",
        r"(?:from|من)\s+(\d+(?:\.\d+)?)\s*(million|m|مليون|م)?\s+(?:to|ل|الى|إلى)\s+(\d+(?:\.\d+)?)\s*(million|m|مليون|م)?",
        r"(\d+(?:\.\d+)?)\s*(million|m|مليون|م)?\s+(?:to|ل|الى|إلى)\s+(\d+(?:\.\d+)?)\s*(million|m|مليون|م)?",
        r"(\d+(?:\.\d+)?)\s*(million|m|مليون|م)?\s*-\s*(\d+(?:\.\d+)?)\s*(million|m|مليون|م)?",
    ]

    for pattern in patterns:
        m = re.search(pattern, t)
        if not m:
            continue

        v1 = float(m.group(1))
        u1 = (m.group(2) or "").strip()
        v2 = float(m.group(3))
        u2 = (m.group(4) or "").strip()

        # inherit unit if missing
        if not u1 and u2:
            u1 = u2
        if not u2 and u1:
            u2 = u1

        mult1 = 1_000_000 if u1 in ("million", "m", "مليون", "م") else 1
        mult2 = 1_000_000 if u2 in ("million", "m", "مليون", "م") else 1

        b1 = int(v1 * mult1)
        b2 = int(v2 * mult2)

        return {"budget_min": min(b1, b2), "budget_max": max(b1, b2)}

    return None


def _is_budget_max_indicator(text: str) -> bool:
    t = _normalize_text(text)
    max_indicators = [
        "up to", "not more than", "no more than", "at most", "maximum",
        "less than", "below", "under", "max",
        # Arabic
        "بحد اقصى", "بحد أقصى", "حد اقصى", "حد أقصى", "اقل من", "أقل من", "تحت", "ماكس",
    ]
    return any(x in t for x in max_indicators)


def _is_budget_min_indicator(text: str) -> bool:
    t = _normalize_text(text)
    min_indicators = [
        "starting from", "from", "at least", "minimum", "more than", "above",
        "over", "min",
        # Arabic
        "ابتداء من", "ابتداءً من", "من", "حد ادنى", "حد أدنى", "على الاقل", "على الأقل", "اكتر من", "أكثر من",
    ]
    return any(x in t for x in min_indicators)


# ----------------------------
# Area parsing (EN + AR + digits)
# ----------------------------
def _parse_area_m2(text: str) -> float | None:
    """
    Handles:
    - 120 sqm, 120 m2, 120 m²
    - 120 square meters
    - Arabic: ١٢٠ متر, 120 متر مربع, 120 م2
    """
    t = _to_latin_digits((text or "").lower().replace(",", " ").strip())
    t = re.sub(r"\s+", " ", t)

    # m2/sqm
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(sqm|m2|m²|م2|م²)\b", t)
    if m:
        return float(m.group(1))

    # square meters/metres
    m2 = re.search(r"\b(\d+(?:\.\d+)?)\s*square\s+(?:meters?|metres?)\b", t)
    if m2:
        return float(m2.group(1))

    # Arabic meters
    m3 = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:متر\s+مربع|متر)\b", t)
    if m3:
        return float(m3.group(1))

    return None


def _parse_area_range(text: str) -> dict[str, float] | None:
    """
    Handles:
    - between 100 and 150 sqm
    - 100-150 sqm / 100 to 150 sqm
    - Arabic: بين ١٠٠ و ١٥٠ متر / من ١٢٠ ل ١٨٠ م٢
    """
    t = _to_latin_digits((text or "").lower().replace(",", " ").strip())
    t = re.sub(r"\s+", " ", t)

    unit_pattern = r"(?:sqm|m2|m²|م2|م²|square\s+(?:meters?|metres?)|meters?|metres?|متر\s+مربع|متر)?"

    patterns = [
        rf"(?:between|بين)\s+(\d+(?:\.\d+)?)\s*{unit_pattern}\s+(?:and|و)\s+(\d+(?:\.\d+)?)\s*{unit_pattern}",
        rf"(?:from|من)\s+(\d+(?:\.\d+)?)\s*{unit_pattern}\s+(?:to|ل|الى|إلى)\s+(\d+(?:\.\d+)?)\s*{unit_pattern}",
        rf"(\d+(?:\.\d+)?)\s*{unit_pattern}\s+(?:to|ل|الى|إلى)\s+(\d+(?:\.\d+)?)\s*{unit_pattern}",
        rf"(\d+(?:\.\d+)?)\s*{unit_pattern}\s*-\s*(\d+(?:\.\d+)?)\s*{unit_pattern}",
    ]

    for pattern in patterns:
        m = re.search(pattern, t)
        if m:
            v1 = float(m.group(1))
            v2 = float(m.group(2))
            return {"area_min": min(v1, v2), "area_max": max(v1, v2)}

    return None


def _is_area_max_indicator(text: str) -> bool:
    t = _normalize_text(text)
    max_indicators = [
        "up to", "not more than", "no more than", "at most", "maximum", "max",
        "less than", "below", "under",
        # Arabic
        "بحد اقصى", "بحد أقصى", "حد اقصى", "حد أقصى", "اقل من", "أقل من", "تحت", "ماكس",
    ]
    return any(x in t for x in max_indicators)


def _is_area_min_indicator(text: str) -> bool:
    t = _normalize_text(text)
    min_indicators = [
        "starting from", "from", "at least", "minimum", "min", "more than", "above", "over",
        # Arabic
        "ابتداء من", "ابتداءً من", "من", "حد ادنى", "حد أدنى", "على الاقل", "على الأقل", "اكتر من", "أكثر من",
    ]
    return any(x in t for x in min_indicators)


# ----------------------------
# Unit type / bedrooms / features
# (kept mostly as-is, with Arabic digit support + better matching)
# ----------------------------
def _parse_unit_type(text: str) -> str | None:
    t = _normalize_text(text)

    # Bedroom + unit pattern
    m = re.search(
        r"\b(\d+)\s*(?:bedroom|bed|beds|br|غرفة|غرف)?\s*(?:-| )?\s*(apartment|apt|flat|villa|chalet|townhouse|duplex|penthouse|studio|شقة|شقه|فيلا|شاليه|تاون|دوبلكس|استوديو|بنتهاوس)\b",
        t
    )
    if m:
        unit_word = m.group(2)
        for canonical, variants in UNIT_KEYWORDS.items():
            for v in variants:
                if re.search(rf"\b{re.escape(_normalize_text(v))}\b", unit_word):
                    return canonical

    # Standard unit matching
    for canonical, variants in UNIT_KEYWORDS.items():
        for v in variants:
            if re.search(rf"\b{re.escape(_normalize_text(v))}\b", t):
                return canonical

    return None


def _parse_bedrooms(text: str) -> int | None:
    t = _to_latin_digits((text or "").lower())

    patterns = [
        r"\b(\d+)\s*(?:bedroom|bed|beds)\b",
        r"\b(\d+)\s*br\b",
        r"\b(\d+)\s*(?:غرفة|غرف)\b",
        r"\b(\d+)\s*(?:bedroom|bed|beds)?\s+(?:apartment|apt|flat|villa|chalet|townhouse|duplex|penthouse|studio|unit|شقة|شقه|فيلا|شاليه|تاون|دوبلكس|استوديو|بنتهاوس)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, t)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
    return None


def _parse_floor_type(text: str) -> str | None:
    t = _normalize_text(text)

    floor_patterns = [
        ("ground_floor", r"\bground\s+floor\b|أرضي|ارضي"),
        ("first_floor", r"\bfirst\s+floor\b|\b1st\s+floor\b|أول|اول"),
        ("second_floor", r"\bsecond\s+floor\b|\b2nd\s+floor\b|ثاني|تاني"),
        ("high_floor", r"\bhigh\s+floor\b|دور عالي"),
        ("low_floor", r"\blow\s+floor\b|دور واطي|دور منخفض"),
        ("middle_floor", r"\bmiddle\s+floor\b|دور متوسط"),
        ("top_floor", r"\btop\s+floor\b|\bupper\s+floor\b|آخر دور|اخر دور"),
    ]
    for floor_type, pattern in floor_patterns:
        if re.search(pattern, t):
            return floor_type
    return None


def _parse_unit_features(text: str) -> dict[str, Any]:
    t = _normalize_text(text)
    features: dict[str, Any] = {}

    # Garden/Outdoor features (EN + AR)
    if re.search(r"\bwith\s+garden\b|\bgarden\s+unit\b|\bgarden\s+villa\b|بحديقة|حديقة", t):
        features["has_garden"] = True

    if re.search(r"\bwith\s+roof\b|\broof\s+terrace\b|\brooftop\b|روف", t):
        features["has_roof"] = True

    if re.search(r"\bwith\s+terrace\b|\bterrace\b|تراس", t):
        features["has_terrace"] = True

    if re.search(r"\bwith\s+balcony\b|\bbalcony\b|بلكونة|بلكون", t):
        features["has_balcony"] = True

    # Views
    if re.search(r"\bsea\s+view\b|\bocean\s+view\b|\bbeach\s+view\b|إطلالة بحر|اطلالة بحر|بحر", t):
        features["view_type"] = "sea"
    elif re.search(r"\bgarden\s+view\b|\bgreen\s+view\b|إطلالة حديقة|اطلالة حديقة|حديقة", t):
        features["view_type"] = "garden"
    elif re.search(r"\bpool\s+view\b|حمام سباحة|بيسين", t):
        features["view_type"] = "pool"

    # Furnishing
    if re.search(r"\bunfurnished\b|\bnot\s+furnished\b|غير مفروش", t):
        features["furnishing"] = "unfurnished"
    elif re.search(r"\bsemi[-\s]?furnished\b|\bpartly\s+furnished\b|نصف مفروش|نص مفروش", t):
        features["furnishing"] = "semi"
    elif re.search(r"\bfurnished\b|مفروش", t):
        features["furnishing"] = "furnished"

    return features


def _parse_location(text: str) -> str | None:
    if not text:
        return None

    raw = text.strip()
    t = _normalize_text(raw)

    # explicit override
    m = re.search(r"\b(change|set)\s+(the\s+)?location\s+(to|as)\s+(.+)$", t)
    if m:
        candidate = (m.group(4) or "").strip()
        candidate = re.sub(r"[.!?]+$", "", candidate)
        best = _best_location_match(candidate)
        return _normalize_location(best or candidate)

    # try primary preference
    primary = _extract_primary_location(raw)
    if primary:
        return _normalize_location(primary)

    # directional phrases
    phrase_loc = _extract_location_from_phrases(raw)
    if phrase_loc:
        return _normalize_location(phrase_loc)

    # full message best match
    best = _best_location_match(t)
    if best:
        return _normalize_location(best)

    # fallback
    if "new cairo" in t:
        return "New Cairo"

    return None


# ----------------------------
# Main entry: extract_state_patch
# ----------------------------
def extract_state_patch(message: str) -> dict[str, Any]:
    patch: dict[str, Any] = {}

    loc = _parse_location(message)
    if loc:
        patch["location"] = loc

    unit = _parse_unit_type(message)
    if unit:
        patch["unit_type"] = unit

    # Budget / area: handle ranges first
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
                # default to max budget for safety
                patch["budget_max"] = budget

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

    bedrooms = _parse_bedrooms(message)
    if bedrooms is not None:
        patch["bedrooms"] = bedrooms

    floor_type = _parse_floor_type(message)
    if floor_type:
        patch["floor_type"] = floor_type

    features = _parse_unit_features(message)
    if features:
        patch["features"] = features

    return patch
