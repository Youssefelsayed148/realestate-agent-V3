import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.rag_models import RagConversation, RagMessage

from services.projects_service import get_project_with_units, get_projects_with_units
from services.compare_service import compare_projects
from services.rag_state_service import get_last_project_ids, set_last_project_ids
from services.project_search_service import search_projects_ranked
from services.response_templates import (
    format_project_details,
    format_compare_summary,
    compact_projects_for_ui,
)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatIn(BaseModel):
    message: str
    conversation_id: Optional[str] = None


# -----------------------
# Helpers
# -----------------------
def _extract_ids(text: str) -> List[int]:
    return [int(x) for x in re.findall(r"\b\d+\b", text)]


def _is_compare(text: str) -> bool:
    t = text.lower()
    return ("compare" in t) or (" vs " in t) or ("difference" in t) or ("versus" in t)


def _split_compare_names(text: str) -> List[str]:
    """
    Very cheap parser:
    - "Compare A vs B"
    - "A versus B"
    - "difference between A and B"
    """
    t = text.strip()

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


def _ensure_conversation(db: Session, conversation_id: Optional[str]) -> uuid.UUID:
    if conversation_id:
        cid = uuid.UUID(conversation_id)
        conv = db.query(RagConversation).filter(RagConversation.id == cid).first()
        if conv:
            return cid

    conv = RagConversation(channel="api", user_identifier=None)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv.id


# -----------------------
# Unit-intent detection
# -----------------------
def _unit_intent(text: str) -> Optional[str]:
    t = text.strip().lower()

    if any(k in t for k in ["largest unit", "biggest unit", "max area", "largest option"]):
        return "largest_unit"

    if any(k in t for k in ["cheapest", "lowest price", "min price", "cheapest unit", "cheapest option"]):
        return "cheapest_unit"

    return None


def _pick_unit(units: List[Dict[str, Any]], mode: str) -> Optional[Dict[str, Any]]:
    # Improvement:
    # - largest_unit: require area only
    # - cheapest_unit: require price only
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
    return f"{int(x):,} EGP"


def _norm_name(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _maybe_map_option_indexes(user_text: str, ids: List[int], remembered: List[int]) -> List[int]:
    """
    If user says 'compare 1 and 2' and we have remembered IDs,
    treat numbers as option indexes (1-based) when they fit.
    """
    if not remembered or len(ids) < 2:
        return ids

    t = user_text.lower()
    looks_like_option_compare = ("compare" in t) or ("between" in t) or (" vs " in t) or ("versus" in t)

    # If all numbers are within 1..len(remembered), map them as indexes
    if looks_like_option_compare and all(1 <= x <= len(remembered) for x in ids[:4]):
        return [remembered[x - 1] for x in ids[:4]]

    return ids


# -----------------------
# Main endpoint
# -----------------------
@router.post("/")
def chat(payload: ChatIn, db: Session = Depends(get_db)):
    cid = _ensure_conversation(db, payload.conversation_id)
    user_text = payload.message.strip()

    # store user message
    db.add(RagMessage(conversation_id=cid, role="user", content=user_text))
    db.commit()

    # -----------------------
    # UNIT INTENTS (cheapest/largest) with memory fallback
    # -----------------------
    u_intent = _unit_intent(user_text)
    if u_intent:
        ids = _extract_ids(user_text)
        project_id: Optional[int] = ids[0] if ids else None

        if project_id is None:
            remembered = get_last_project_ids(db, cid)
            if remembered:
                project_id = int(remembered[0])

        if project_id is None:
            reply = "Which project? Send the project name (or ID) first, then ask “cheapest” or “largest unit”."
            db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="unit_query"))
            db.commit()
            return {"conversation_id": str(cid), "reply": reply}

        project = get_project_with_units(db, project_id)
        if not project:
            reply = "I couldn’t find that project. Please send a valid project ID or name."
            db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="unit_query"))
            db.commit()
            return {"conversation_id": str(cid), "reply": reply}

        set_last_project_ids(db, cid, [project["id"]])

        chosen = _pick_unit(project.get("unit_types", []), u_intent)
        if not chosen:
            reply = f"I found {project.get('project_name')} but there isn’t enough unit data to answer that yet."
            db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="unit_query"))
            db.commit()
            return {"conversation_id": str(cid), "reply": reply}

        pname = project.get("project_name") or "This project"
        label = "largest" if u_intent == "largest_unit" else "cheapest"
        reply = (
            f"{pname}: {label} option is **{chosen.get('unit_type')}**\n"
            f"- Size: {chosen.get('area')} m²\n"
            f"- Price: {_short_money(chosen.get('price'))}"
        )

        db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="unit_query"))
        db.commit()
        return {"conversation_id": str(cid), "reply": reply}

    # -----------------------
    # COMPARE
    # -----------------------
    if _is_compare(user_text):
        ids: List[int] = _extract_ids(user_text)

        remembered = get_last_project_ids(db, cid)
        ids = _maybe_map_option_indexes(user_text, ids, remembered)

        if len(ids) < 2:
            name_parts = _split_compare_names(user_text)

            if not name_parts:
                if len(remembered) >= 2:
                    ids = remembered[:]
                else:
                    reply = (
                        "Tell me the two project names (or pick from the last results). "
                        "Example: 'Compare Bloomfields vs Village West' or 'Compare 1 and 2'."
                    )
                    db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="compare"))
                    db.commit()
                    return {"conversation_id": str(cid), "reply": reply}

            if name_parts and len(ids) < 2:
                resolved: List[int] = []
                for name in name_parts[:3]:
                    ranked = search_projects_ranked(db, name, limit=8)
                    if ranked:
                        resolved.append(int(ranked[0][0].id))
                ids = resolved

        # safety net: map again if they were indexes
        if len(ids) >= 2 and len(remembered) >= 2:
            ids = _maybe_map_option_indexes(user_text, ids, remembered)

        if len(ids) < 2:
            reply = (
                "I couldn’t resolve two projects. "
                "Try: 'Compare <project A> vs <project B>' or 'Compare 1 and 2' from the last results."
            )
            db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="compare"))
            db.commit()
            return {"conversation_id": str(cid), "reply": reply}

        projects = get_projects_with_units(db, ids[:4])
        if len(projects) < 2:
            reply = "I couldn't find enough projects to compare from what you provided."
            db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="compare"))
            db.commit()
            return {"conversation_id": str(cid), "reply": reply}

        result = compare_projects(projects)
        set_last_project_ids(db, cid, [p["id"] for p in projects])

        reply = format_compare_summary(result)
        db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="compare"))
        db.commit()

        projects_ui = compact_projects_for_ui(projects, max_lines=4)

        return {
            "conversation_id": str(cid),
            "reply": reply,
            "differences": result["differences"],
            "projects": projects_ui,
        }

    # -----------------------
    # DETAILS
    # -----------------------
    ids = _extract_ids(user_text)
    project = None

    if ids:
        project = get_project_with_units(db, ids[0])
    else:
        ranked = search_projects_ranked(db, user_text, limit=8)

        if ranked:
            # Detect duplicates by same normalized name
            top_name = _norm_name(ranked[0][0].project_name or "")
            same_name = [r for r in ranked if _norm_name(r[0].project_name or "") == top_name]

            if len(same_name) >= 2:
                lines = ["I found multiple matching projects. Which one do you mean?\n"]
                for p, _score in same_name[:6]:
                    area = (p.area or "").strip()
                    area_part = f" — {area}" if area else ""
                    lines.append(f"- {p.project_name}{area_part} (id: {p.id})")

                reply = "\n".join(lines)
                db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="disambiguate"))
                db.commit()
                return {"conversation_id": str(cid), "reply": reply}

            # safe to pick top
            project = get_project_with_units(db, int(ranked[0][0].id))

    if not project:
        reply = "Tell me the project name (or ID) and I’ll show details."
        db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="details"))
        db.commit()
        return {"conversation_id": str(cid), "reply": reply}

    set_last_project_ids(db, cid, [project["id"]])

    reply = format_project_details(project, max_lines=4)
    db.add(RagMessage(conversation_id=cid, role="assistant", content=reply, intent="details"))
    db.commit()

    return {"conversation_id": str(cid), "reply": reply, "project": project}
