import os
import sys
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from db import SessionLocal
from rag.orchestrator import ChatOrchestrator


def main():
    print("✅ test_orchestrator.py started")
    print("PROJECT_ROOT =", PROJECT_ROOT)

    db = SessionLocal()
    try:
        orch = ChatOrchestrator(db, model="llama3.1:8b")
        print("✅ Orchestrator created")

        # Turn 1
        res1 = orch.handle_user_message("I want a 3 bedroom in New Cairo under 6M")
        print("\nTURN 1 RESULT:\n", res1)

        conv_id = res1["conversation_id"]

        # Turn 2: answer follow-up if any
        if res1.get("missing_slots"):
            res2 = orch.handle_user_message("Apartment", conversation_id=conv_id)
            print("\nTURN 2 RESULT:\n", res2)

        # Turn 3
        res3 = orch.handle_user_message("Installments are fine", conversation_id=conv_id)
        print("\nTURN 3 RESULT:\n", res3)

        print("\n✅ Orchestrator test finished OK")

    except Exception as e:
        print("\n❌ Orchestrator test FAILED:", repr(e))
        traceback.print_exc()
    finally:
        db.close()
        print("✅ DB session closed")


if __name__ == "__main__":
    main()
