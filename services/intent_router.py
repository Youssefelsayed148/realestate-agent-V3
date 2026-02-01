# services/intent_router.py
from __future__ import annotations
from typing import Any

from .intent_rules import detect_intent_rules
from .intent_llm import llm_detect_intent
from .intents import Intent

def detect_intent(message: str, current_state: dict[str, Any]) -> dict[str, Any]:
    rule_intent = detect_intent_rules(message)
    if rule_intent:
        return {"intent": rule_intent.value, "state_patch": {}, "missing_questions": []}

    result = llm_detect_intent(message, current_state)
    result.setdefault("intent", Intent.UNKNOWN.value)
    result.setdefault("state_patch", {})
    result.setdefault("missing_questions", [])
    return result
