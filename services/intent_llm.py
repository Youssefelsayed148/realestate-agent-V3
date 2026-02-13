# services/intent_llm.py
from __future__ import annotations

import os
from typing import Any, Dict

from services.intents import Intent
from services.preference_parser import extract_state_patch
from services.ollama_intent_router import OllamaIntentRouter


_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
_OLLAMA_TIMEOUT_S = int(os.getenv("OLLAMA_TIMEOUT_S", "30"))

_router = OllamaIntentRouter(
    model=_OLLAMA_MODEL,
    base_url=_OLLAMA_BASE_URL,
    timeout_s=_OLLAMA_TIMEOUT_S,
)


def llm_detect_intent(message: str, current_state: dict[str, Any]) -> dict[str, Any]:
    """
    World-1 compatible LLM fallback (local Ollama).
    Must return: {"intent": str, "state_patch": dict, "missing_questions": list}
    """

    state_for_llm: Dict[str, Any] = {
        "budget_min": current_state.get("budget_min"),
        "budget_max": current_state.get("budget_max"),
        # World-1 uses "location"; LLM expects "location_area"
        "location_area": current_state.get("location"),
        "unit_type": current_state.get("unit_type"),
        "bedrooms": current_state.get("bedrooms"),
        "delivery_year": current_state.get("delivery_year"),
        "payment_plan": current_state.get("payment_plan"),
    }

    res = _router.route(
        user_text=message,
        conversation_state=state_for_llm,
        last_messages=None,
    )

    intent_map = {
        "search_projects": Intent.PROVIDE_PREFERENCES.value,
        "filter_units": Intent.FILTER_RESULTS.value,
        "project_details": Intent.SHOW_DETAILS.value,
        "compare_projects": Intent.COMPARE.value,
        "schedule_visit": Intent.CONFIRM_CHOICE.value,
        "budget_check": Intent.REFINE_SEARCH.value,
        "general_question": Intent.UNKNOWN.value,
    }
    mapped_intent = intent_map.get(res.intent, Intent.UNKNOWN.value)

    # Patch: deterministic parser first, then LLM entities
    patch = extract_state_patch(message) or {}
    ent = res.entities or {}

    if isinstance(ent.get("budget_min"), (int, float)):
        patch["budget_min"] = int(ent["budget_min"])
    if isinstance(ent.get("budget_max"), (int, float)):
        patch["budget_max"] = int(ent["budget_max"])

    if isinstance(ent.get("location_area"), str) and ent["location_area"].strip():
        patch.setdefault("location", ent["location_area"].strip())

    if isinstance(ent.get("unit_type"), str) and ent["unit_type"].strip():
        ut = ent["unit_type"].strip()
        if ut != "any":
            patch.setdefault("unit_type", ut.title())

    if isinstance(ent.get("bedrooms"), int):
        patch["bedrooms"] = ent["bedrooms"]

    if isinstance(ent.get("payment_plan"), str) and ent["payment_plan"].strip():
        patch["payment_plan"] = ent["payment_plan"].strip()

    return {
        "intent": mapped_intent,
        "state_patch": patch,
        "missing_questions": [],
        "confidence": float(getattr(res, "confidence", 0.5)),
        "raw_intent": res.intent,  # optional debug
    }
