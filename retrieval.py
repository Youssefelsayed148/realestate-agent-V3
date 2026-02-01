import re
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from collections import defaultdict

from sqlalchemy import text
from sentence_transformers import SentenceTransformer


# ----------------------------
# Types
# ----------------------------
class PaymentTerms(TypedDict):
    down_payment: Optional[str]
    years: Optional[str]


# ----------------------------
# Embedding helper
# ----------------------------
def to_pgvector_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"


# ----------------------------
# Parsing (cheap heuristics)
# ----------------------------
def parse_budget_egp(q: str) -> Optional[float]:
    ql = (q or "").lower().replace(",", "").strip()

    # Match:
    #   under 10m
    #   under 10 m
    #   under 10mn
    #   under 10 mil
    #   under 10 million
    #   under 10000000
    m = re.search(r"(under|below|max)\s+(\d+(?:\.\d+)?)([a-z]+)?", ql)
    if not m:
        return None

    val = float(m.group(2))
    suffix = (m.group(3) or "").strip()

    # normalize common "million" variants
    million_suffixes = {"m", "mn", "mil", "mill", "million", "millions"}

    if suffix in million_suffixes:
        return val * 1_000_000

    # If suffix is empty, treat as raw EGP number
    if suffix == "":
        return val

    # If we captured some other letters (like "in"), ignore suffix and treat as raw
    # (this prevents false positives)
    return val




def parse_area(q: str) -> Optional[float]:
    ql = (q or "").lower()
    # Only accept sqm formats (avoids confusing "10m" million with meters)
    m = re.search(r"(\d{2,4})\s*(sqm|m2|m²)\b", ql)
    return float(m.group(1)) if m else None



def parse_bucket(q: str) -> Optional[str]:
    ql = q.lower()
    if "villa" in ql:
        return "villa"
    if "townhouse" in ql or "town house" in ql:
        return "townhouse"
    if any(k in ql for k in ["apartment", "studio", "penthouse", "duplex", "loft"]):
        return "apartment"
    if any(k in ql for k in ["chalet", "cabin"]):
        return "chalet"
    return None


def is_approx_query(q: str) -> bool:
    ql = q.lower()
    return any(w in ql for w in ["around", "approx", "approximately", "about"])


# ----------------------------
# Location normalization
# ----------------------------
_LOCATION_SYNONYMS: List[Tuple[List[str], str]] = [
    (["fifth settlement", "the 5th settlement", "5th settlement", "tagamoa", "tagamo3", "new cairo"], "New Cairo"),
    (["mostakbal city"], "Mostakbal City"),
    (["sheikh zayed", "zayed", "el sheikh zayed"], "Sheikh Zayed"),
    (["green belt"], "Green Belt"),
    (["north coast", "sahel", "al sahel"], "North Coast"),
    (["ras el hikma", "ras elhekma", "ras el hemka", "ras elhemka"], "Ras El Hikma"),
    (["sidi abdelrahman", "sidi abd el rahman"], "Sidi Abdelrahman"),
    (["el shorouk", "shorouk"], "El Shorouk"),
    (["6th of october", "6 october", "october"], "6th of October"),
]


def extract_location_hint(q: str) -> Optional[str]:
    ql = q.lower()
    for keys, canonical in _LOCATION_SYNONYMS:
        if any(k in ql for k in keys):
            return canonical
    return None


def location_to_db_filter(location_hint: Optional[str]) -> Optional[str]:
    # Your DB stores "Mostakbal City - New Cairo", etc. Using substring works well.
    return location_hint


# ----------------------------
# Query gating (avoid junk queries like "test")
# ----------------------------
def needs_clarification(user_query: str) -> bool:
    q = (user_query or "").strip().lower()
    if len(q) < 6:
        return True

    has_bucket = parse_bucket(q) is not None
    has_location = extract_location_hint(q) is not None
    has_area = parse_area(q) is not None
    has_budget = parse_budget_egp(q) is not None

    return not (has_bucket or has_location or has_area or has_budget)


# ----------------------------
# Retrieval
# ----------------------------
def retrieve_inventory_options(
    db,
    embed_model: SentenceTransformer,
    user_query: str,
    k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Uses SQL-side filtered vector search over project_unit_types via search_put_filtered.
    """
    bucket = parse_bucket(user_query)
    target_area = parse_area(user_query)
    max_price = parse_budget_egp(user_query)

    loc_hint = extract_location_hint(user_query)
    loc_filter = location_to_db_filter(loc_hint)

    min_area = max_area = None
    if target_area is not None:
        tol = 0.35 if is_approx_query(user_query) else 0.25
        min_area = target_area * (1 - tol)
        max_area = target_area * (1 + tol)

    vec = embed_model.encode([user_query], normalize_embeddings=True)[0].tolist()
    vec_lit = to_pgvector_literal(vec)

    sql = text("""
        SELECT source_id, similarity, unit_type, area_sqm, price_egp, location, content
        FROM public.search_put_filtered(
            (:qvec)::vector(384),
            :k,
            :bucket,
            :min_area,
            :max_area,
            :max_price,
            :location
        )
    """)

    rows = db.execute(sql, {
        "qvec": vec_lit,
        "k": k,
        "bucket": bucket,
        "min_area": min_area,
        "max_area": max_area,
        "max_price": max_price,
        "location": loc_filter,
    }).mappings().all()

    return [dict(r) for r in rows]


def retrieve_project_context(
    db,
    embed_model: SentenceTransformer,
    user_query: str,
    k: int = 8,
) -> List[Dict[str, Any]]:
    """
    Semantic search over projects docs for payment plans, developer, etc.
    """
    vec = embed_model.encode([user_query], normalize_embeddings=True)[0].tolist()
    vec_lit = to_pgvector_literal(vec)

    sql = text("""
        SELECT source_id, chunk_index, similarity, content, metadata
        FROM public.search_vector((:qvec)::vector(384), :k, :src)
    """)

    rows = db.execute(sql, {"qvec": vec_lit, "k": k, "src": "projects"}).mappings().all()
    return [dict(r) for r in rows]


# ----------------------------
# Formatting helpers
# ----------------------------
def _extract_project_name_from_put_content(content: str) -> Optional[str]:
    # "Unit type option in project X. Location/Area: ..."
    m = re.search(r"in project\s+(.+?)\.", content, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def _project_name_from_project_chunk(text_block: str) -> Optional[str]:
    # project chunks typically contain "Project: NAME."
    m = re.search(r"Project:\s*(.+?)\.", text_block)
    return m.group(1).strip() if m else None


def _extract_payment_terms(text_block: str) -> PaymentTerms:
    out: PaymentTerms = {"down_payment": None, "years": None}

    m = re.search(r"(\d{1,2})\s*%\s*(down payment|downpayment)", text_block, flags=re.IGNORECASE)
    if m:
        out["down_payment"] = f"{m.group(1)}%"

    m = re.search(r"(\d{1,2})\s*(years|year)", text_block, flags=re.IGNORECASE)
    if m:
        out["years"] = f"{m.group(1)} years"

    return out


# ----------------------------
# Final answer formatter
# ----------------------------
def format_answer(
    user_query: str,
    inventory_rows: List[Dict[str, Any]],
    project_rows: List[Dict[str, Any]],
    max_projects: int = 3,
    max_options_per_project: int = 2,
) -> str:
    if needs_clarification(user_query):
        return (
            "Tell me what you’re looking for, for example:\n"
            "- Unit type (apartment / chalet / villa / townhouse)\n"
            "- Location (New Cairo / Sheikh Zayed / North Coast / etc.)\n"
            "- Budget (e.g., under 10 million)\n"
            "- Area (e.g., 160 sqm)\n\n"
            "Example: 'Chalet 160 sqm under 20 million in North Coast'"
        )

    if not inventory_rows:
        return (
            "I couldn't find matching unit-type options with the current filters.\n"
            "Try relaxing the area/budget or changing the location keywords."
        )

    bucket = parse_bucket(user_query) or "units"
    target_area = parse_area(user_query)
    max_price = parse_budget_egp(user_query)
    loc_hint = extract_location_hint(user_query)

    summary_bits: List[str] = [bucket]
    if target_area is not None:
        summary_bits.append(f"~{int(target_area)} sqm")
    if max_price is not None:
        summary_bits.append(f"≤ {int(max_price):,} EGP")
    if loc_hint:
        summary_bits.append(f"in/near {loc_hint}")

    # Payment hints per project (best-effort)
    payment_by_project: Dict[str, PaymentTerms] = {}
    for pr in project_rows:
        txt = pr.get("content") or ""
        pname = _project_name_from_project_chunk(txt)
        if not pname:
            continue

        terms = _extract_payment_terms(txt)
        existing: PaymentTerms = payment_by_project.get(pname, {"down_payment": None, "years": None})

        if existing["down_payment"] is None and terms["down_payment"] is not None:
            existing["down_payment"] = terms["down_payment"]
        if existing["years"] is None and terms["years"] is not None:
            existing["years"] = terms["years"]

        payment_by_project[pname] = existing

    # Group inventory by project name
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in inventory_rows:
        pname = _extract_project_name_from_put_content(r.get("content") or "") or "Unknown Project"
        grouped[pname].append(r)

    # Sort options within each project by:
    # 1) closest to target area (if any)
    # 2) lowest price
    # 3) highest similarity
    def option_key(x: Dict[str, Any]) -> Tuple[float, float, float]:
        area = x.get("area_sqm")
        if target_area is not None and area is not None:
            area_dist = abs(float(area) - float(target_area))
        else:
            area_dist = 1e18

        price = x.get("price_egp")
        price_key = float(price) if price is not None else 1e18

        sim_key = -float(x.get("similarity") or 0.0)
        return (area_dist, price_key, sim_key)

    for pname in grouped:
        grouped[pname].sort(key=option_key)

    # Rank projects by best similarity among their options
    project_rank = sorted(
        grouped.keys(),
        key=lambda pn: max(float(x.get("similarity") or 0.0) for x in grouped[pn]),
        reverse=True
    )[:max_projects]

    lines: List[str] = []
    lines.append(f"Query: {user_query}")
    lines.append("")
    lines.append("Looking for: " + ", ".join(summary_bits))
    lines.append("")
    lines.append("Top matches (grouped by project):")
    lines.append("")

    for pname in project_rank:
        options = grouped[pname][:max_options_per_project]
        pay = payment_by_project.get(pname, {"down_payment": None, "years": None})

        header = pname
        if pay["down_payment"] or pay["years"]:
            extra_parts: List[str] = []
            if pay["down_payment"]:
                extra_parts.append(f"Down payment: {pay['down_payment']}")
            if pay["years"]:
                extra_parts.append(f"Installments: {pay['years']}")
            header += f" ({' • '.join(extra_parts)})"

        lines.append(f"- {header}")

        for opt in options:
            ut = opt.get("unit_type") or ""
            area = opt.get("area_sqm")
            price = opt.get("price_egp")
            loc = opt.get("location") or ""
            sid = opt.get("source_id") or ""

            area_str = f"{float(area):g} sqm" if area is not None else "N/A"
            price_str = f"{int(float(price)):,} EGP" if price is not None else "N/A"

            lines.append(f"  • {ut} — {area_str} — {price_str} — {loc}  [{sid}]")

        lines.append("")

    return "\n".join(lines).strip()
