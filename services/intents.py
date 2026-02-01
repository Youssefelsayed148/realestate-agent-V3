# services/intents.py
from enum import Enum

class Intent(str, Enum):
    RESTART = "restart"
    SHOW_RESULTS = "show_results"
    PROVIDE_PREFERENCES = "provide_preferences"
    REFINE_SEARCH = "refine_search"
    CONFIRM_CHOICE = "confirm_choice"
    UNKNOWN = "unknown"
