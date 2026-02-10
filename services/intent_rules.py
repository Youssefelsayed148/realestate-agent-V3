# services/intent_rules.py
from __future__ import annotations
import re

from .intents import Intent

def detect_intent_rules(text: str) -> Intent | None:
    t = (text or "").strip().lower()

    # 1) RESTART intents
    if any(x in t for x in ["restart", "start over", "reset", "new search", "from scratch", "begin again"]):
        return Intent.RESTART

    # 2) COMPARISON intents
    if _is_comparison_intent(t):
        return Intent.COMPARE

    # 3) CONFIRM / BOOK / CHOOSE (check early for contact/booking intents)
    if _is_confirm_intent(t):
        return Intent.CONFIRM_CHOICE
    
    # Check standalone confirm
    if t in ["confirm", "yes", "ok", "okay"]:
        return Intent.CONFIRM_CHOICE

    # 4) DETAILS / MORE INFO (check before SHOW_RESULTS to catch "show me the details")
    if _is_details_intent(t):
        return Intent.SHOW_DETAILS

    # 5) FILTER / REFINE (check before SHOW_RESULTS)
    if _is_filter_intent(t):
        return Intent.FILTER_RESULTS

    # 6) SORT
    if _is_sort_intent(t):
        return Intent.SORT_RESULTS

    # 7) NAVIGATION (next/previous/page)
    if _is_navigation_intent(t):
        return Intent.NAVIGATE

    # 8) REFINE SEARCH (adjustments) - check before SHOW_RESULTS to catch words like "cheaper"
    if any(x in t for x in ["bigger", "smaller", "cheaper", "more expensive", "increase", "decrease", "change budget", "adjust"]):
        return Intent.REFINE_SEARCH
    
    # Check for refine patterns with "options" suffix
    if re.search(r"\b(cheaper|lower price|reduce|better price|less expensive)\s*(?:options?)?\b", t):
        return Intent.REFINE_SEARCH

    # 9) SHOW RESULTS / LIST (but not if it contains location/unit/bedroom info)
    if any(x in t for x in ["show results", "list options", "what do you have", "what's available"]):
        return Intent.SHOW_RESULTS
    
    # Check for standalone "options"
    if t == "options" or t == "show options":
        return Intent.SHOW_RESULTS
    
    # Check for "show me" but exclude if it's a search query with parameters
    if "show me" in t:
        # If it has location, unit, or bedroom info, treat as search not show_results
        has_unit = any(x in t for x in ["apartment", "villa", "townhouse", "duplex", "studio", "chalet"])
        has_bedroom = bool(re.search(r"\b\d+\s*(?:bedroom|bed)", t))
        has_location = any(x in t for x in ["new cairo", "mostakbal", "zayed", "north coast", "ain sokhna", "tagamoa", "marassi", "rehab", "katameya"])
        
        if not (has_unit or has_bedroom or has_location):
            return Intent.SHOW_RESULTS

    # 10) PROVIDE PREFERENCES (default search)
    has_money = bool(re.search(r"\b(\d{1,3}(,\d{3})+|\d+)(?:\s*m|million|m\b)?", t)) and any(
        x in t for x in ["egp", "million", "m ", "budget", "price", "m$"]
    )
    # Also check for budget patterns like "5M budget" or "5 million"
    has_budget_phrase = bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:m|million)\b", t)) and "budget" in t
    has_area = any(x in t for x in ["m2", "sqm", "meter", "metre", "متر"]) or "m²" in t
    has_unit = any(x in t for x in ["apartment", "villa", "townhouse", "duplex", "studio", "chalet"])
    has_location = any(x in t for x in ["new cairo", "mostakbal", "zayed", "north coast", "ain sokhna", "tagamoa"])

    if has_money or has_budget_phrase or has_area or has_unit or has_location:
        return Intent.PROVIDE_PREFERENCES

    return None


def _is_comparison_intent(text: str) -> bool:
    """Detect comparison patterns like 'compare 1 and 2', 'difference between first and second'"""
    comparison_patterns = [
        r"\bcompare\b.*\b(option|choice|#)?\s*(\d+|first|second|third|1st|2nd|3rd)",
        r"\bdifference\b.*\b(between|among)",
        r"\bvs\b|\bversus\b",
        r"\bwhich\s+(?:is\s+)?(?:better|best|cheaper|more expensive|bigger|smaller)",
        r"\b(option|choice|#)?\s*(\d+|first|second|third)\s+(?:and|or|vs)\s+(option|choice|#)?\s*(\d+|first|second|third)",
        r"\bwhich\s+one\s+(?:is\s+)?best\b",
    ]
    return any(re.search(pattern, text) for pattern in comparison_patterns)


def _is_details_intent(text: str) -> bool:
    """Detect detail request patterns like 'tell me more', 'what are amenities'"""
    details_patterns = [
        r"\btell\s+me\s+more\b",
        r"\bmore\s+(?:info|information|details)\b",
        r"\bdetails\s+(?:about|for|on)\b",
        r"\bwhat\s+(?:are|is)\s+(?:the\s+)?(?:amenities|features|specs|specifications)",
        r"\bshow\s+(?:me\s+)?(?:the\s+)?details\b",
        r"\bdescribe\b",
        r"\babout\s+(?:the\s+)?(?:option|choice|#)?\s*(\d+|first|second|third)",
        r"\b(option|choice|#)?\s*(\d+|first|second|third)\s+details\b",
    ]
    return any(re.search(pattern, text) for pattern in details_patterns)


def _is_filter_intent(text: str) -> bool:
    """Detect filter patterns like 'only show apartments', 'remove villas'"""
    filter_patterns = [
        r"\bonly\s+(?:show\s+)?(?:me\s+)?(?:apartments|villas|studios|duplexes|chalets|townhouses)\b",
        r"\b(show\s+)?only\s+(?:the\s+)?(?:apartments|villas|studios|duplexes|chalets|townhouses)\b",
        r"\bremove\s+(?:the\s+)?(?:apartments|villas|studios|duplexes|chalets|townhouses)\b",
        r"\bexclude\s+(?:the\s+)?(?:apartments|villas|studios|duplexes|chalets|townhouses)\b",
        r"\bfilter\s+(?:by|for)\b",
        r"\bjust\s+(?:show\s+)?(?:me\s+)?(?:apartments|villas|studios|duplexes|chalets|townhouses)\b",
        r"\bshow\s+me\s+only\s+(?:the\s+)?(?:apartments|villas|studios|duplexes|chalets|townhouses)\b",
    ]
    return any(re.search(pattern, text) for pattern in filter_patterns)


def _is_sort_intent(text: str) -> bool:
    """Detect sort patterns like 'sort by price', 'cheapest first'"""
    sort_patterns = [
        r"\bsort\s+(?:by\s+)?(?:price|budget|area|size|date|newest|oldest|location)\b",
        r"\bsorted\s+(?:by\s+)?(?:price|budget|area|size|date|newest|oldest|location)\b",
        r"\bcheapest\s+(?:first|to|one)\b",
        r"\bmost\s+expensive\s+(?:first|to|one)\b",
        r"\blowest\s+(?:price|budget)\b",
        r"\bhighest\s+(?:price|budget)\b",
        r"\b(smallest|largest|biggest)\s+(?:first|to|one)\b",
        r"\bnewest\s+(?:first|to|one)\b",
        r"\blatest\s+(?:first|to|one)\b",
        r"\bshow\s+(?:the\s+)?(?:cheapest|most expensive|smallest|largest|newest)\b",
        r"\bby\s+(?:price|area|budget|size|date|location)\b",
        r"\border\s+(?:by\s+)?(?:price|area|budget|size|date|location)\b",
    ]
    return any(re.search(pattern, text) for pattern in sort_patterns)


def _is_navigation_intent(text: str) -> bool:
    """Detect navigation patterns like 'next', 'previous', 'show more'"""
    nav_patterns = [
        r"\bnext\s*(?:page|results?)?\b",
        r"\bprevious\s*(?:page|results?)?\b|\bprev\b",
        r"\bshow\s+more\b|\bload\s+more\b",
        r"\b(more\s+)?results?\b",
        r"\bgo\s+(?:back|forward)\b",
        r"\bpage\s*(\d+|one|two|three)\b",
        r"\bfirst\s+page\b|\blast\s+page\b",
    ]
    return any(re.search(pattern, text) for pattern in nav_patterns)


def _is_confirm_intent(text: str) -> bool:
    """Detect confirmation patterns like 'book option 2', 'I want the first one'"""
    confirm_patterns = [
        r"\b(?:i\s+)?(?:want|choose|pick|select|like|prefer)\s+(?:the\s+)?(?:option|choice|#)?\s*(\d+|first|second|third|1st|2nd|3rd|this|that)\b",
        r"\b(?:book|reserve|schedule|arrange)\s+(?:the\s+)?(?:option|choice|#)?\s*(\d+|first|second|third|1st|2nd|3rd|this|that)?\b",
        r"\b(?:proceed\s+with|confirm|finalize)\s+(?:the\s+)?(?:option|choice|#)?\s*(\d+|first|second|third|1st|2nd|3rd|this|that)?\b",
        r"\b(?:i'll\s+take|i\s+will\s+take)\s+(?:the\s+)?(?:option|choice|#)?\s*(\d+|first|second|third|1st|2nd|3rd|this|that)?\b",
        r"\b(?:contact|call|reach|talk\s+to)\s+(?:me\s+about|regarding)?\s*(?:the\s+)?(?:option|choice|#)?\s*(\d+|first|second|third|1st|2nd|3rd|this|that)?\b",
        r"\bsend\s+(?:me\s+)?(?:details|info|information)\s+(?:about|for|on|regarding)\s+(?:the\s+)?(?:option|choice|#)?\s*(\d+|first|second|third|1st|2nd|3rd)\b",
        r"\bi'm\s+interested\s+(?:in\s+)?(?:the\s+)?(?:option|choice|#)?\s*(\d+|first|second|third|1st|2nd|3rd|this|that)\b",
        r"\bthis\s+one\s+(?:is\s+)?(?:good|fine|ok|okay|perfect|great)\b",
    ]
    return any(re.search(pattern, text) for pattern in confirm_patterns)
