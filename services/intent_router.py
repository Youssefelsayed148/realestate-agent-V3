# services/intent_router.py
from __future__ import annotations
from typing import Any

from .intent_rules import detect_intent_rules
from .intent_llm import llm_detect_intent
from .intents import Intent
from .preference_parser import extract_state_patch


def detect_intent(message: str, current_state: dict[str, Any]) -> dict[str, Any]:
    # Always extract deterministic patch first
    deterministic_patch = extract_state_patch(message) or {}

    # 1) Rule-based intent
    rule_intent = detect_intent_rules(message)
    if rule_intent:
        return {
            "intent": rule_intent.value,
            "state_patch": deterministic_patch,
            "missing_questions": [],
        }

    # 2) Ollama fallback
    llm_result = llm_detect_intent(message, current_state)

    llm_patch = llm_result.get("state_patch") or {}
    merged_patch = dict(llm_patch)
    merged_patch.update(deterministic_patch)  # deterministic wins

    return {
        "intent": llm_result.get("intent", Intent.UNKNOWN.value),
        "state_patch": merged_patch,
        "missing_questions": llm_result.get("missing_questions", []),
        "confidence": llm_result.get("confidence", 0.5),
        "raw_intent": llm_result.get("raw_intent"),
    }
