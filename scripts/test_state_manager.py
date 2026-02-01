import os
import sys
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

# Ensure project root is on sys.path when running: python scripts/test_state_manager.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from db import SessionLocal
from rag import StateManager, StateUpdate
from models.rag_models import RagConversation, RagMessage, RagConversationState, RagLead


def _num_to_float(x: Optional[Any]) -> Optional[float]:
    """Safely convert Decimal/Numeric/etc to float for printing."""
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main() -> None:
    db: Session = SessionLocal()
    sm = StateManager(db)

    try:
        # 1) Create conversation
        conv = sm.get_or_create_conversation(channel="web", user_identifier="test-user-001")
        print(f"✅ Conversation created: {conv.id}")

        # 2) Insert user message
        sm.add_message(
            conversation_id=conv.id,
            role="user",
            content="I want a 3 bedroom in New Cairo under 3M",
        )
        print("✅ User message inserted")

        # 3) Create/get state row
        state = sm.get_state(conv.id)
        print("✅ State row ready")

        # 4) Merge state update (simulate extracted entities)
        upd = StateUpdate(
            budget_max=3000000,
            location_area="New Cairo",
            bedrooms=3,
            last_intent="filter_units",
            last_project_ids=[101, 205],  # example IDs (int8). Can be [] too.
        )
        sm.merge_state(state, upd)
        print("✅ State merged")

        # 5) Insert assistant message
        sm.add_message(
            conversation_id=conv.id,
            role="assistant",
            content="Noted. Do you prefer apartment or villa?",
            intent="follow_up",
            entities_json={"missing_slots": ["unit_type"]},
        )
        print("✅ Assistant message inserted")

        # 6) Insert lead (safe even if interest_project_id=None)
        sm.create_lead(
            conversation_id=conv.id,
            name="Test Lead",
            phone="+201000000000",
            preferred_contact_time="Evening",
            interest_project_id=None,
            interest_area="New Cairo",
        )
        print("✅ Lead inserted")

        # 7) Commit
        sm.commit()
        print("✅ Commit successful")

        # -------------------------
        # Read back (SQLAlchemy 2.0)
        # -------------------------
        conv2 = db.get(RagConversation, conv.id)
        state2 = db.get(RagConversationState, conv.id)

        if conv2 is None:
            raise RuntimeError("Conversation not found after commit")
        if state2 is None:
            raise RuntimeError("State not found after commit")

        messages = db.execute(
            select(RagMessage)
            .where(RagMessage.conversation_id == conv.id)
            .order_by(RagMessage.created_at.asc())
        ).scalars().all()

        leads = db.execute(
            select(RagLead)
            .where(RagLead.conversation_id == conv.id)
            .order_by(RagLead.created_at.asc())
        ).scalars().all()

        print("\n--- READ BACK ---")
        print("Conversation:", conv2.id, conv2.channel, conv2.user_identifier)
        print("State:", {
            "budget_min": _num_to_float(state2.budget_min),
            "budget_max": _num_to_float(state2.budget_max),
            "location_area": state2.location_area,
            "unit_type": state2.unit_type,
            "bedrooms": state2.bedrooms,
            "delivery_year": state2.delivery_year,
            "payment_plan": state2.payment_plan,
            "last_intent": state2.last_intent,
            "last_project_ids": state2.last_project_ids,
        })

        print("Messages count:", len(messages))
        for m in messages:
            print(f"- [{m.role}] {m.content} (intent={m.intent})")

        print("Leads count:", len(leads))
        for l in leads:
            print(
                f"- Lead: name={l.name}, phone={l.phone}, "
                f"area={l.interest_area}, project_id={l.interest_project_id}"
            )

        print("\n✅ StateManager end-to-end test PASSED")

    except Exception as e:
        sm.rollback()
        print("\n❌ Test FAILED:", repr(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
