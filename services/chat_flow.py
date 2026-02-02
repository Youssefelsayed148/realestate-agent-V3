# services/chat_flow.py
from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session

from services.conversation_state import get_or_create_conversation, update_conversation_state
from services.intent_router import detect_intent

from services.preference_parser import extract_state_patch
from services.refine import build_refine_patch

from services.search import search_db
from services.formatting import format_results, slim_results
from services.selection import extract_option_index, format_selected


def compute_missing_questions(state: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not state.get("location"):
        missing.append("Which location do you prefer (e.g., New Cairo, Zayed, North Coast)?")
    if not state.get("budget_max"):
        missing.append("What is your maximum budget in EGP?")
    if not state.get("unit_type"):
        missing.append("Which unit type do you prefer (Apartment, Villa, Townhouse, Chalet)?")
    return missing


def _respond_missing(conv, state: dict[str, Any]) -> dict[str, Any]:
    missing = compute_missing_questions(state)
    question = missing[0] if missing else "What would you like to search for?"
    return {
        "conversation_id": str(conv.id),
        "intent": "ask_question",
        "reply": question,
        "state": state,
    }


def _search_and_respond(db: Session, conv, state: dict[str, Any]) -> dict[str, Any]:
    try:
        results = search_db(db, state, limit=10)
    except Exception:
        # Don't crash demo; keep conversation_id stable
        return {
            "conversation_id": str(conv.id),
            "intent": "error",
            "reply": "Something went wrong while searching. Please try again or change your filters.",
            "state": state,
        }

    slim = slim_results(results)
    conv = update_conversation_state(db, conv, {"last_results": slim})

    return {
        "conversation_id": str(conv.id),
        "intent": "show_results",
        "reply": format_results(results),
        "results": slim,
        "state": conv.state,
    }


def handle_chat_message(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    conversation_id = payload.get("conversation_id")
    user_id = payload.get("user_id")

    user_message_raw = payload.get("message", "")
    user_message = str(user_message_raw).strip()

    conv = get_or_create_conversation(db, conversation_id=conversation_id, user_id=user_id)

    # conv.state should be dict; be defensive
    state = conv.state or {}

    # 0) Option selection
    idx = extract_option_index(user_message)
    if idx is not None:
        last_results = state.get("last_results") or []
        if 0 <= idx < len(last_results):
            chosen = last_results[idx]
            conv = update_conversation_state(db, conv, {"confirmed": True, "chosen_option": chosen})
            return {
                "conversation_id": str(conv.id),
                "intent": "confirm_choice",
                "reply": format_selected(chosen, idx + 1),
                "selected": chosen,
                "state": conv.state,
            }

        return {
            "conversation_id": str(conv.id),
            "intent": "ask_question",
            "reply": f"I couldn’t find option {idx+1}. Please choose between 1 and {len(last_results)}.",
            "state": state,
        }

    # 1) Refinement patch
    refine_patch = build_refine_patch(user_message, state)
    if refine_patch:
        did_reset = bool(refine_patch.pop("__did_reset__", False))
        conv = update_conversation_state(db, conv, refine_patch)
        state = conv.state or {}

        if did_reset:
            return _respond_missing(conv, state)

        if compute_missing_questions(state):
            return _respond_missing(conv, state)

        # user refined constraints => clear confirmation
        conv = update_conversation_state(db, conv, {"confirmed": False, "chosen_option": None})
        return _search_and_respond(db, conv, conv.state or {})

    # 2) Always extract preferences (so "Sheikh Zayed" works)
    extracted_patch = extract_state_patch(user_message)

    # 3) Intent detection
    intent_bundle = detect_intent(user_message, state)

    merged_patch: dict[str, Any] = {}
    merged_patch.update(intent_bundle.get("state_patch", {}) or {})
    merged_patch.update(extracted_patch or {})

    if merged_patch:
        merged_patch.setdefault("confirmed", False)
        merged_patch.setdefault("chosen_option", None)

    conv = update_conversation_state(db, conv, merged_patch)
    state = conv.state or {}

    # 4) missing info?
    if compute_missing_questions(state):
        return _respond_missing(conv, state)

    # 5) search
    return _search_and_respond(db, conv, state)
