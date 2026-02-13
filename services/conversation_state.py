# services/conversation_state.py
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from models.conversation import Conversation


DEFAULT_STATE: dict[str, Any] = {
    "location": None,
    "budget_min": None,
    "budget_max": None,
    "unit_type": None,
    "area_min": None,
    "area_max": None,
    "confirmed": False,
    "chosen_option": None,
    "last_results": [],
    # ✅ NEW: memory for compare/details/cheapest/largest follow-ups
    "last_project_ids": [],
}


def merge_state(old: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """
    Merge patch into old state.

    IMPORTANT:
    - If a key exists in patch, we apply it even if the value is None.
      This enables explicit "reset" / clearing fields.
    - If patch doesn't include a key, we keep the old value.
    """
    if old is None:
        old = {}
    if patch is None:
        patch = {}

    new_state = dict(old)

    # Apply all keys present in patch (including None)
    for k, v in patch.items():
        # internal flags are allowed but should not be stored
        if k.startswith("__") and k.endswith("__"):
            continue
        new_state[k] = v

    return new_state


def get_or_create_conversation(
    db: Session,
    conversation_id: str | None = None,
    user_id: str | None = None
) -> Conversation:
    conv: Conversation | None = None

    if conversation_id:
        try:
            conv_uuid = uuid.UUID(conversation_id)
            conv = db.query(Conversation).filter(Conversation.id == conv_uuid).first()
        except ValueError:
            conv = None

    if conv is None:
        conv = Conversation(user_id=user_id, state=dict(DEFAULT_STATE))
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv

    # Ensure state always has required keys
    if conv.state is None:
        conv.state = dict(DEFAULT_STATE)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv

    # Backfill missing keys
    changed = False
    for k, v in DEFAULT_STATE.items():
        if k not in conv.state:
            conv.state[k] = v
            changed = True

    if changed:
        db.add(conv)
        db.commit()
        db.refresh(conv)

    return conv


def update_conversation_state(db: Session, conv: Conversation, patch: dict[str, Any]) -> Conversation:
    old_state = conv.state or {}
    conv.state = merge_state(old_state, patch)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv
