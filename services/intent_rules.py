# services/intent_rules.py
from __future__ import annotations

import re
from .intents import Intent


# -----------------------------
# Shared normalization
# -----------------------------
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def _norm(text: str) -> str:
    t = (text or "").strip().lower()
    t = t.translate(_ARABIC_DIGITS)
    t = re.sub(r"[^\w\s#\-]", " ", t, flags=re.UNICODE)  # keep words/#/-
    t = re.sub(r"\s+", " ", t).strip()
    return t


def detect_intent_rules(text: str) -> Intent | None:
    t = _norm(text)

    # 1) RESTART
    if _contains_any(t, [
        "restart", "reset", "start over", "new search", "from scratch", "begin again",
        "clear all", "clear filters", "wipe",
        # typos
        "reastart", "restar", "restert", "re set", "re-set",
        # arabic
        "ابدأ من جديد", "ابدء من جديد", "ابدا من جديد",
        "اعادة", "إعادة", "اعاده", "إعاده",
        "امسح", "امسح الكل", "امسح الفلاتر",
        "ريست", "ريستارت",
    ]):
        return Intent.RESTART

    # 2) COMPARE
    if _is_comparison_intent(t):
        return Intent.COMPARE

    # 3) CONFIRM / BOOK / CHOOSE
    if _is_confirm_intent(t):
        return Intent.CONFIRM_CHOICE

    # Standalone confirm (English + Arabic)
    if t in ["confirm", "yes", "ok", "okay", "تمام", "موافق", "اوكي", "أوكي", "ايوه", "نعم"]:
        return Intent.CONFIRM_CHOICE

    # 4) DETAILS
    if _is_details_intent(t):
        return Intent.SHOW_DETAILS

    # 5) FILTER
    if _is_filter_intent(t):
        return Intent.FILTER_RESULTS

    # 6) SORT
    if _is_sort_intent(t):
        return Intent.SORT_RESULTS

    # 7) NAVIGATION
    if _is_navigation_intent(t):
        return Intent.NAVIGATE

    # 8) REFINE SEARCH (cheap heuristics)
    if _contains_any(t, [
        "bigger", "larger", "more space", "bigger area",
        "smaller", "less space", "smaller area",
        "cheaper", "lower", "reduce", "decrease",
        "more expensive", "increase", "raise", "higher budget",
        "change budget", "adjust", "modify",
        # arabic
        "اكبر", "أكبر", "مساحة اكبر", "مساحة أكبر", "اوسع",
        "اصغر", "أصغر", "مساحة اصغر", "مساحة أصغر",
        "ارخص", "أرخص", "اقل", "أقل", "خفض", "قلل",
        "اغلى", "أغلى", "زود", "زوّد", "ارفع",
    ]):
        return Intent.REFINE_SEARCH

    # 9) SHOW RESULTS / LIST
    if _contains_any(t, [
        "show results", "list options", "show options", "options",
        "what do you have", "what's available", "available",
        "show me options", "show me results", "give me options", "results",
        # arabic
        "النتايج", "النتائج", "عرض", "وريني", "وريني الاوبشنز", "وريني الخيارات",
        "ايه المتاح", "ايه الموجود", "هات الخيارات", "الخيارات",
    ]):
        return Intent.SHOW_RESULTS

    # 10) PROVIDE PREFERENCES (default search)
    # Detect any signal of search constraints: money/area/unit/location/bedrooms
    if _has_search_signals(t):
        return Intent.PROVIDE_PREFERENCES

    return None


# -----------------------------
# Helpers
# -----------------------------
def _contains_any(t: str, phrases: list[str]) -> bool:
    for p in phrases:
        if p and p in t:
            return True
    return False


def _has_search_signals(t: str) -> bool:
    # money
    has_money = bool(re.search(r"\b(\d{1,3}(?:,\d{3})+|\d{5,9}|\d+(?:\.\d+)?)\b", t)) and _contains_any(
        t,
        ["egp", "budget", "price", "m", "million", "k", "thousand", "مليون", "م", "جنيه", "ميزانية", "سعر"]
    )

    # "5m budget" / "5 million"
    has_million_word = bool(re.search(r"\b\d+(?:\.\d+)?\s*(m|million|مليون|م)\b", t))

    # area/sqm
    has_area = _contains_any(t, ["m2", "sqm", "meter", "metre", "متر", "م²", "مساحة"]) or bool(re.search(r"\b\d+\s*(m2|sqm|متر)\b", t))

    # unit types (EN + AR + common typos)
    has_unit = _contains_any(t, [
        "apartment", "apt", "appartment", "flat",
        "villa", "vila",
        "townhouse", "town house",
        "duplex", "duplx",
        "studio",
        "chalet", "shalet",
        # arabic
        "شقة", "شقه", "فيلا", "توين", "تاون", "دوبلكس", "استوديو", "شاليه",
    ])

    # bedrooms
    has_bedroom = bool(re.search(r"\b\d+\s*(bed|beds|bedroom|bedrooms|غرفة|غرف)\b", t))

    # location hint (keep broad; preference_parser/refine will normalize)
    has_location = _contains_any(t, [
        "new cairo", "tagamo", "tagamo3", "fifth settlement", "rehab", "katameya", "mostakbal", "shorouk",
        "sheikh zayed", "zayed", "6 october", "october",
        "north coast", "sahel", "ain sokhna", "sokhna", "ras el hekma", "sidi abdelrahman",
        # arabic
        "القاهرة الجديدة", "التجمع", "الرحاب", "مدينتي", "الشروق", "المستقبل",
        "الشيخ زايد", "زايد", "اكتوبر", "٦ اكتوبر", "الساحل", "السخنة", "راس الحكمة", "سيدي عبدالرحمن",
    ])

    return has_money or has_million_word or has_area or has_unit or has_bedroom or has_location


def _is_comparison_intent(t: str) -> bool:
    # compare / vs / difference / Arabic equivalents
    if _contains_any(t, ["compare", "vs", "versus", "difference", "diff", "قارن", "مقارنة", "الفرق", "فرق"]):
        return True

    # patterns: "1 vs 2", "option 1 and 2"
    if re.search(r"\b(option|choice|#)?\s*\d+\s*(and|or|vs)\s*(option|choice|#)?\s*\d+\b", t):
        return True

    return False


def _is_details_intent(t: str) -> bool:
    return bool(re.search(
        r"(\btell me more\b|\bmore (info|information|details)\b|\bdetails\b|\bdescribe\b|\bamenities\b|"
        r"\bfeatures\b|\bpayment plan\b|\bdown payment\b|"
        r"تفاصيل|معلومات|احكي|قولي|قوللي|وصف|مميزات|خطة سداد|تقسيط|مقدم)",
        t
    ))


def _is_filter_intent(t: str) -> bool:
    # Filter-like patterns in EN + AR
    if _contains_any(t, ["only show", "just show", "remove", "exclude", "filter", "فلتر", "استبعد", "شيل", "اظهر بس", "بس"]):
        return True

    # explicit unit filters
    if re.search(r"\b(only|just)\s+(apartments|villas|studios|duplexes|chalets|townhouses)\b", t):
        return True

    if re.search(r"(شقق|شقة|فلل|فيلا|شاليهات|شاليه|تاون|توين|دوبلكس|استوديو)\b", t) and _contains_any(t, ["بس", "فقط", "اظهر", "وريني"]):
        return True

    return False


def _is_sort_intent(t: str) -> bool:
    if _contains_any(t, [
        "sort", "sorted", "order by", "cheapest", "most expensive",
        "lowest price", "highest price", "smallest", "largest", "newest", "latest",
        # arabic
        "رتب", "ترتيب", "اقل سعر", "أقل سعر", "اغلى", "أغلى", "ارخص", "أرخص",
        "من الاقل", "من الأرخص", "من الأغلى", "اكبر", "أكبر", "اصغر", "أصغر",
    ]):
        return True
    return False


def _is_navigation_intent(t: str) -> bool:
    if _contains_any(t, [
        "next", "next page", "more", "show more", "load more",
        "previous", "prev", "back", "forward", "page",
        # arabic
        "التالي", "اللي بعده", "بعد كده", "اكتر", "المزيد",
        "السابق", "قبل", "ارجع", "رجوع", "صفحة",
    ]):
        return True
    return False


def _is_confirm_intent(t: str) -> bool:
    # English
    patterns = [
        r"\b(i\s+)?(want|choose|pick|select|like|prefer)\s+(the\s+)?(option|choice|#)?\s*(\d+|first|second|third|1st|2nd|3rd|this|that)\b",
        r"\b(book|reserve|schedule|arrange)\s+(the\s+)?(option|choice|#)?\s*(\d+|first|second|third|1st|2nd|3rd|this|that)?\b",
        r"\b(proceed with|confirm|finalize)\b",
        r"\b(i'll take|i will take)\b",
        r"\b(this one)\s+(is\s+)?(good|fine|ok|okay|perfect|great)\b",
    ]
    if any(re.search(p, t) for p in patterns):
        return True

    # Arabic confirm-ish
    if _contains_any(t, [
        "اختار", "اختار ده", "عايز ده", "عايز دي", "انا عايز", "انا عاوز",
        "احجز", "حجز", "حجزلي", "احجزلي", "عايز احجز",
        "تمام كده", "ده مناسب", "دي مناسبة", "ده كويس", "دي كويسة",
        "أكد", "تأكيد", "موافق",
    ]):
        return True

    return False
