import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from models.rag_models import RagConversationState  # adjust filename if needed


def get_or_create_state(db: Session, conversation_id: uuid.UUID) -> RagConversationState:
    state = db.query(RagConversationState).filter(
        RagConversationState.conversation_id == conversation_id
    ).first()

    if state:
        return state

    state = RagConversationState(conversation_id=conversation_id, last_project_ids=[])
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def set_last_project_ids(db: Session, conversation_id: uuid.UUID, project_ids: List[int]) -> None:
    state = get_or_create_state(db, conversation_id)
    state.last_project_ids = [int(x) for x in project_ids]
    db.add(state)
    db.commit()


def get_last_project_ids(db: Session, conversation_id: uuid.UUID) -> List[int]:
    state = get_or_create_state(db, conversation_id)
    return [int(x) for x in (state.last_project_ids or [])]
