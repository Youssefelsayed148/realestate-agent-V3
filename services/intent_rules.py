# services/intent_rules.py
from __future__ import annotations
import re

from .intents import Intent

def detect_intent_rules(text: str) -> Intent | None:
    t = (text or "").strip().lower()

    if any(x in t for x in ["restart", "start over", "reset", "new search", "from scratch"]):
        return Intent.RESTART

    if any(x in t for x in ["show results", "show me", "list options", "options", "what do you have"]):
        return Intent.SHOW_RESULTS

    if any(x in t for x in ["i choose", "i pick", "confirm", "book", "reserve", "send details", "contact"]):
        return Intent.CONFIRM_CHOICE

    if any(x in t for x in ["bigger", "smaller", "cheaper", "more expensive", "increase", "decrease", "change budget"]):
        return Intent.REFINE_SEARCH

    has_money = bool(re.search(r"\b(\d{1,3}(,\d{3})+|\d+)\b", t)) and any(
        x in t for x in ["egp", "million", "m", "budget", "price"]
    )
    has_area = any(x in t for x in ["m2", "sqm", "meter", "metre", "متر"]) or "m²" in t
    has_unit = any(x in t for x in ["apartment", "villa", "townhouse", "duplex", "studio", "chalet"])
    has_location = any(x in t for x in ["new cairo", "mostakbal", "zayed", "north coast", "ain sokhna", "tagamoa"])

    if has_money or has_area or has_unit or has_location:
        return Intent.PROVIDE_PREFERENCES

    return None
