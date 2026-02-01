import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from rag.intent_router import OllamaIntentRouter

router = OllamaIntentRouter(model="llama3.1:8b")

state = {"budget_max": None, "location_area": None, "bedrooms": None, "unit_type": None}
res = router.route("I want a 3 bedroom in New Cairo under 3M", state, [])
print(res)
