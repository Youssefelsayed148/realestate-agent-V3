# services/chat_flow.py
from __future__ import annotations
import os
import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from services.conversation_state import get_or_create_conversation, update_conversation_state
from services.intent_router import detect_intent

from services.preference_parser import extract_state_patch
from services.refine import build_refine_patch

from services.search import search_db
from services.formatting import format_results, slim_results
from services.selection import extract_option_index, format_selected

# ---- "chat.py" features (moved into services) ----
from services.projects_service import get_project_with_units, get_projects_with_units
from services.compare_service import compare_projects
from services.project_search_service import search_projects_ranked
from services.response_templates import (
    format_project_details,
    format_compare_summary,
    compact_projects_for_ui,
)


# ----------------------------
# Slot questions (existing)
# ----------------------------
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


# ----------------------------
# Helpers migrated from chat.py
# ----------------------------
def _extract_ids(text: str) -> List[int]:
    return [int(x) for x in re.findall(r"\b\d+\b", text or "")]


def _is_compare(text: str) -> bool:
    t = (text or "").lower()

    # existing triggers
    if ("compare" in t) or (" vs " in t) or ("difference" in t) or ("versus" in t):
        return True

    # NEW: "between X and Y" pattern (numbers)
    # examples: "between 1 and 2", "between 3 and 5"
    if "between" in t and re.search(r"\bbetween\b.*\b\d+\b.*\band\b.*\b\d+\b", t):
        return True

    # OPTIONAL (still cheap): "between A and B" (names)
    # This helps: "between Bloomfields and Village West"
    if "between" in t and " and " in t:
        return True

    return False


def _split_compare_names(text: str) -> List[str]:
    """
    Very cheap parser:
    - "Compare A vs B"
    - "A versus B"
    - "difference between A and B"
    """
    t = (text or "").strip()

    if " vs " in t.lower() or " versus " in t.lower():
        parts = re.split(r"\b(vs|versus)\b", t, flags=re.IGNORECASE)
        cleaned: List[str] = []
        for p in parts:
            p = p.strip(" -,\n\t")
            if not p:
                continue
            if p.lower() in ("vs", "versus"):
                continue
            cleaned.append(p)

        if cleaned:
            cleaned[0] = re.sub(r"^\s*compare\s+", "", cleaned[0], flags=re.IGNORECASE).strip()

        return cleaned

    m = re.search(r"^(compare|difference between)\s+(.*)$", t, flags=re.IGNORECASE)
    if m:
        rest = m.group(2)
        parts = re.split(r"\band\b|&", rest, flags=re.IGNORECASE)
        return [p.strip(" -,\n\t") for p in parts if p.strip()]

    return []


def _unit_intent(text: str) -> Optional[str]:
    t = (text or "").strip().lower()

    if any(k in t for k in ["largest unit", "biggest unit", "max area", "largest option"]):
        return "largest_unit"

    if any(k in t for k in ["cheapest", "lowest price", "min price", "cheapest unit", "cheapest option"]):
        return "cheapest_unit"

    return None


def _pick_unit(units: List[Dict[str, Any]], mode: str) -> Optional[Dict[str, Any]]:
    if mode == "largest_unit":
        filtered = [u for u in units if u.get("area") is not None]
        if not filtered:
            return None
        return max(filtered, key=lambda u: float(u["area"]))

    if mode == "cheapest_unit":
        filtered = [u for u in units if u.get("price") is not None]
        if not filtered:
            return None
        return min(filtered, key=lambda u: float(u["price"]))

    return None


def _short_money(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{int(float(x)):,} EGP"


def _norm_name(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _looks_like_details_request(text: str) -> bool:
    """
    Prevent accidental "project name" matches:
    Only treat as details if user asks for details explicitly.
    """
    t = (text or "").strip().lower()
    triggers = [
        "details",
        "tell me about",
        "about ",
        "describe",
        "more info",
        "more information",
        "amenities",
        "payment plan",
        "down payment",
        "installments",
        "developer",
    ]
    return any(x in t for x in triggers)


def _maybe_map_option_indexes(user_text: str, ids: List[int], remembered: List[int]) -> List[int]:
    """
    If user says 'compare 1 and 2' and we have remembered IDs in display order,
    treat numbers as option indexes (1-based) when they fit.
    """
    if not remembered or len(ids) < 2:
        return ids

    t = (user_text or "").lower()
    looks_like_option_compare = ("compare" in t) or ("between" in t) or (" vs " in t) or ("versus" in t)

    # If all numbers are within 1..len(remembered), map them as indexes
    if looks_like_option_compare and all(1 <= x <= len(remembered) for x in ids[:4]):
        return [int(remembered[x - 1]) for x in ids[:4]]

    return ids


# ----------------------------
# Search response (existing)
# ----------------------------
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

    # --- store last_project_ids for "compare 1 and 2" / "compare them" / "cheapest" follow-ups ---
    seen: set[int] = set()
    last_project_ids: list[int] = []
    for r in slim:
        pid = r.get("project_id")
        if pid is None:
            continue
        try:
            pid_int = int(pid)
        except Exception:
            continue
        if pid_int not in seen:
            seen.add(pid_int)
            last_project_ids.append(pid_int)

    conv = update_conversation_state(
        db,
        conv,
        {
            "last_results": slim,
            "last_project_ids": last_project_ids,
        },
    )

    return {
        "conversation_id": str(conv.id),
        "intent": "show_results",
        "reply": format_results(results),
        "results": slim,
        "state": conv.state,
    }


# ----------------------------
# Main entry
# ----------------------------
def handle_chat_message(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    conversation_id = payload.get("conversation_id")
    user_id = payload.get("user_id")

    user_message_raw = payload.get("message", "")
    user_message = str(user_message_raw).strip()

    conv = get_or_create_conversation(db, conversation_id=conversation_id, user_id=user_id)

    # conv.state should be dict; be defensive
    state = conv.state or {}

    # Ensure new key exists even if old conversations existed before DEFAULT_STATE update
    if "last_project_ids" not in state:
        conv = update_conversation_state(db, conv, {"last_project_ids": []})
        state = conv.state or {}

    # ✅ EARLY deterministic parse BEFORE refine/missing-slot checks
    early_patch = extract_state_patch(user_message) or {}
    if early_patch:
        early_patch.setdefault("confirmed", False)
        early_patch.setdefault("chosen_option", None)
        conv = update_conversation_state(db, conv, early_patch)
        state = conv.state or {}

    # =========================================================
    # ✅ 0.5) EARLY deterministic parse (BEFORE refine + missing checks)
    # =========================================================
    early_patch = extract_state_patch(user_message) or {}
    if early_patch:
        early_patch.setdefault("confirmed", False)
        early_patch.setdefault("chosen_option", None)
        conv = update_conversation_state(db, conv, early_patch)
        state = conv.state or {}

    # 0) Option selection ("2", "option 2", etc.)
    idx = extract_option_index(user_message)
    if idx is not None:
        last_results = state.get("last_results") or []
        if 0 <= idx < len(last_results):
            chosen = last_results[idx]
            chosen_pid = chosen.get("project_id")

            # bump chosen project to the front of last_project_ids
            last_pids = [
                int(x)
                for x in (state.get("last_project_ids") or [])
                if isinstance(x, int) or str(x).isdigit()
            ]
            if chosen_pid is not None:
                try:
                    pid_int = int(chosen_pid)
                    last_pids = [pid_int] + [x for x in last_pids if x != pid_int]
                except Exception:
                    pass

            conv = update_conversation_state(
                db,
                conv,
                {
                    "confirmed": True,
                    "chosen_option": chosen,
                    "last_project_ids": last_pids,
                },
            )

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

    # 1) Refinement patch (reset / cheaper / bigger / change location, etc.)
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

    # ---------------------------------------------------------
    # 1.5) "chat.py" features: cheapest/largest, compare, details
    # ---------------------------------------------------------
    # A) Cheapest / Largest unit
    u_intent = _unit_intent(user_message)
    if u_intent:
        ids = _extract_ids(user_message)
        project_id: Optional[int] = ids[0] if ids else None

        if project_id is None:
            remembered = state.get("last_project_ids") or []
            if remembered:
                try:
                    project_id = int(remembered[0])
                except Exception:
                    project_id = None

        if project_id is None:
            reply = "Which project? Send the project name (or ID) first, then ask “cheapest” or “largest unit”."
            return {"conversation_id": str(conv.id), "reply": reply, "intent": "unit_query", "state": state}

        project = get_project_with_units(db, project_id)
        if not project:
            reply = "I couldn’t find that project. Please send a valid project ID or name."
            return {"conversation_id": str(conv.id), "reply": reply, "intent": "unit_query", "state": state}

        # update memory
        conv = update_conversation_state(db, conv, {"last_project_ids": [int(project["id"])]})
        state = conv.state or {}

        chosen_unit = _pick_unit(project.get("unit_types", []), u_intent)
        if not chosen_unit:
            reply = f"I found {project.get('project_name')} but there isn’t enough unit data to answer that yet."
            return {"conversation_id": str(conv.id), "reply": reply, "intent": "unit_query", "state": state}

        pname = project.get("project_name") or "This project"
        label = "largest" if u_intent == "largest_unit" else "cheapest"
        reply = (
            f"{pname}: {label} option is **{chosen_unit.get('unit_type')}**\n"
            f"- Size: {chosen_unit.get('area')} m²\n"
            f"- Price: {_short_money(chosen_unit.get('price'))}"
        )
        return {"conversation_id": str(conv.id), "reply": reply, "intent": "unit_query", "state": state}

    # B) Compare (UPDATED)
            # ---------------------------------------------------------
    # ✅ EARLY COMPARE (before parsing/refine/search)
    # This prevents "between 1 and 3" from being treated as filters.
    # ---------------------------------------------------------
    if _is_compare(user_message):
        ids: List[int] = _extract_ids(user_message)

        remembered_raw = state.get("last_project_ids") or []
        remembered: List[int] = []
        for x in remembered_raw:
            if isinstance(x, int) or str(x).isdigit():
                remembered.append(int(x))

        ids = _maybe_map_option_indexes(user_message, ids, remembered)

        if len(ids) < 2:
            name_parts = _split_compare_names(user_message)

            # support "between A and B"
            if not name_parts:
                m = re.search(r"\bbetween\b\s+(.*)\s+\band\b\s+(.*)$", user_message, flags=re.IGNORECASE)
                if m:
                    a = m.group(1).strip(" -,\n\t")
                    b = m.group(2).strip(" -,\n\t")
                    if a and b:
                        name_parts = [a, b]

            if not name_parts:
                if len(remembered) >= 2:
                    ids = remembered[:]
                else:
                    reply = (
                        "Tell me the two project names (or pick from the last results).\n"
                        "Examples: 'Compare 1 and 3' or 'Between Bloomfields and Village West'."
                    )
                    return {"conversation_id": str(conv.id), "reply": reply, "intent": "compare", "state": state}

            if name_parts and len(ids) < 2:
                resolved: List[int] = []
                for name in name_parts[:2]:
                    ranked = search_projects_ranked(db, name, limit=8)
                    if ranked:
                        resolved.append(int(ranked[0][0].id))
                ids = resolved

        if len(ids) < 2:
            reply = (
                "I couldn’t resolve two projects. "
                "Try: 'Compare <project A> vs <project B>' or 'Compare 1 and 3'."
            )
            return {"conversation_id": str(conv.id), "reply": reply, "intent": "compare", "state": state}

        projects = get_projects_with_units(db, ids[:4])
        if len(projects) < 2:
            reply = "I couldn't find enough projects to compare from what you provided."
            return {"conversation_id": str(conv.id), "reply": reply, "intent": "compare", "state": state}

        result = compare_projects(projects)
        reply = format_compare_summary(result)
        projects_ui = compact_projects_for_ui(projects, max_lines=4)

        conv = update_conversation_state(db, conv, {"last_project_ids": [int(p["id"]) for p in projects]})
        state = conv.state or {}

        return {
            "conversation_id": str(conv.id),
            "reply": reply,
            "intent": "compare",
            "differences": result.get("differences", {}),
            "projects": projects_ui,
            "state": state,
        }


    # C) Details (only if user explicitly asks for details)
    if _looks_like_details_request(user_message):
        ids = _extract_ids(user_message)
        project = None

        if ids:
            project = get_project_with_units(db, ids[0])
        else:
            ranked = search_projects_ranked(db, user_message, limit=8)
            if ranked:
                top_name = _norm_name(ranked[0][0].project_name or "")
                same_name = [r for r in ranked if _norm_name(r[0].project_name or "") == top_name]

                if len(same_name) >= 2:
                    lines = ["I found multiple matching projects. Which one do you mean?\n"]
                    for p, _score in same_name[:6]:
                        area = (p.area or "").strip()
                        area_part = f" — {area}" if area else ""
                        lines.append(f"- {p.project_name}{area_part} (id: {p.id})")

                    reply = "\n".join(lines)
                    return {"conversation_id": str(conv.id), "reply": reply, "intent": "disambiguate", "state": state}

                project = get_project_with_units(db, int(ranked[0][0].id))

        if not project:
            reply = "Tell me the project name (or ID) and I’ll show details."
            return {"conversation_id": str(conv.id), "reply": reply, "intent": "details", "state": state}

        # memory
        conv = update_conversation_state(db, conv, {"last_project_ids": [int(project["id"])]})
        state = conv.state or {}

        reply = format_project_details(project, max_lines=4)
        return {
            "conversation_id": str(conv.id),
            "reply": reply,
            "intent": "details",
            "project": project,
            "state": state,
        }

    # 2) Intent detection (rules + Ollama fallback)
    intent_bundle = detect_intent(user_message, state)

    # Don't let intent patch clear keys with None
    raw_intent_patch = (intent_bundle.get("state_patch") or {})
    intent_patch = {k: v for k, v in raw_intent_patch.items() if v is not None}

    if intent_patch:
        intent_patch.setdefault("confirmed", False)
        intent_patch.setdefault("chosen_option", None)
        conv = update_conversation_state(db, conv, intent_patch)
        state = conv.state or {}

    # 3) missing info?
    if compute_missing_questions(state):
        return _respond_missing(conv, state)

    # 4) search
    return _search_and_respond(db, conv, state)
