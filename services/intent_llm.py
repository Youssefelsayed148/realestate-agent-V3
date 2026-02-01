# services/intent_llm.py
from __future__ import annotations
from typing import Any

from .intents import Intent

def llm_detect_intent(message: str, current_state: dict[str, Any]) -> dict[str, Any]:
    # Placeholder until you wire OpenAI
    return {
        "intent": Intent.UNKNOWN.value,
        "state_patch": {},
        "missing_questions": [
            "Which location do you prefer?",
            "What is your maximum budget in EGP?"
        ],
    }
