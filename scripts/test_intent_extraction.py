#!/usr/bin/env python3
"""
Test script for enhanced intent detection.
Run: python scripts/test_intent_extraction.py
"""

import sys
sys.path.insert(0, '/mnt/d/The Osiris Labs/realestate-agent-backend')

from services.intent_rules import detect_intent_rules
from services.intents import Intent

test_cases = [
    # Original intents (should still work)
    ("restart", Intent.RESTART),
    ("start over", Intent.RESTART),
    ("reset", Intent.RESTART),
    ("new search", Intent.RESTART),
    ("show results", Intent.SHOW_RESULTS),
    ("show me options", Intent.SHOW_RESULTS),
    ("what do you have", Intent.SHOW_RESULTS),
    ("I choose option 2", Intent.CONFIRM_CHOICE),
    ("confirm", Intent.CONFIRM_CHOICE),
    ("book it", Intent.CONFIRM_CHOICE),
    ("cheaper", Intent.REFINE_SEARCH),
    ("bigger", Intent.REFINE_SEARCH),
    ("change budget", Intent.REFINE_SEARCH),
    ("apartment in New Cairo", Intent.PROVIDE_PREFERENCES),
    ("5M budget", Intent.PROVIDE_PREFERENCES),
    
    # COMPARISON intents
    ("compare option 1 and 3", Intent.COMPARE),
    ("compare 1 and 2", Intent.COMPARE),
    ("compare first and second", Intent.COMPARE),
    ("what's the difference between option 1 and 2", Intent.COMPARE),
    ("difference between first and second", Intent.COMPARE),
    ("option 1 vs option 2", Intent.COMPARE),
    ("1 vs 2", Intent.COMPARE),
    ("which is better", Intent.COMPARE),
    ("which is cheaper", Intent.COMPARE),
    ("which one is best", Intent.COMPARE),
    
    # DETAILS intents
    ("tell me more", Intent.SHOW_DETAILS),
    ("more info", Intent.SHOW_DETAILS),
    ("more information", Intent.SHOW_DETAILS),
    ("details about option 2", Intent.SHOW_DETAILS),
    ("show me the details", Intent.SHOW_DETAILS),
    ("what are the amenities", Intent.SHOW_DETAILS),
    ("what are the features", Intent.SHOW_DETAILS),
    ("describe option 1", Intent.SHOW_DETAILS),
    ("about the first option", Intent.SHOW_DETAILS),
    ("option 2 details", Intent.SHOW_DETAILS),
    
    # FILTER intents
    ("only show apartments", Intent.FILTER_RESULTS),
    ("show only villas", Intent.FILTER_RESULTS),
    ("only apartments", Intent.FILTER_RESULTS),
    ("remove villas", Intent.FILTER_RESULTS),
    ("exclude apartments", Intent.FILTER_RESULTS),
    ("filter by price", Intent.FILTER_RESULTS),
    ("just show me studios", Intent.FILTER_RESULTS),
    ("show me only chalets", Intent.FILTER_RESULTS),
    
    # SORT intents
    ("sort by price", Intent.SORT_RESULTS),
    ("sort by area", Intent.SORT_RESULTS),
    ("cheapest first", Intent.SORT_RESULTS),
    ("most expensive first", Intent.SORT_RESULTS),
    ("lowest price", Intent.SORT_RESULTS),
    ("highest price", Intent.SORT_RESULTS),
    ("smallest first", Intent.SORT_RESULTS),
    ("largest first", Intent.SORT_RESULTS),
    ("newest first", Intent.SORT_RESULTS),
    ("show the cheapest", Intent.SORT_RESULTS),
    ("by price", Intent.SORT_RESULTS),
    ("order by date", Intent.SORT_RESULTS),
    ("sorted by budget", Intent.SORT_RESULTS),
    
    # NAVIGATION intents
    ("next", Intent.NAVIGATE),
    ("next page", Intent.NAVIGATE),
    ("previous", Intent.NAVIGATE),
    ("prev", Intent.NAVIGATE),
    ("previous page", Intent.NAVIGATE),
    ("show more", Intent.NAVIGATE),
    ("load more", Intent.NAVIGATE),
    ("more results", Intent.NAVIGATE),
    ("go back", Intent.NAVIGATE),
    ("go forward", Intent.NAVIGATE),
    ("page 2", Intent.NAVIGATE),
    ("first page", Intent.NAVIGATE),
    ("last page", Intent.NAVIGATE),
    
    # CONFIRM/BOOK intents (enhanced)
    ("I want option 1", Intent.CONFIRM_CHOICE),
    ("I choose the first one", Intent.CONFIRM_CHOICE),
    ("pick option 2", Intent.CONFIRM_CHOICE),
    ("select the third option", Intent.CONFIRM_CHOICE),
    ("book option 2", Intent.CONFIRM_CHOICE),
    ("reserve this one", Intent.CONFIRM_CHOICE),
    ("proceed with option 1", Intent.CONFIRM_CHOICE),
    ("confirm the booking", Intent.CONFIRM_CHOICE),
    ("I'll take this one", Intent.CONFIRM_CHOICE),
    ("I will take option 3", Intent.CONFIRM_CHOICE),
    ("contact me about option 2", Intent.CONFIRM_CHOICE),
    ("call me regarding the first option", Intent.CONFIRM_CHOICE),
    ("send me details about option 1", Intent.CONFIRM_CHOICE),
    ("I'm interested in option 2", Intent.CONFIRM_CHOICE),
    ("this one is good", Intent.CONFIRM_CHOICE),
    ("this one is perfect", Intent.CONFIRM_CHOICE),
]

def run_tests():
    print("=" * 80)
    print("ENHANCED INTENT DETECTION TEST")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for input_text, expected_intent in test_cases:
        result = detect_intent_rules(input_text)
        
        # Handle None result
        if result is None:
            result_intent = "None"
        else:
            result_intent = result.value
        
        expected_value = expected_intent.value
        
        status = "✅ PASS" if result_intent == expected_value else "❌ FAIL"
        
        print(f"\n{status} Input: \"{input_text}\"")
        print(f"   Expected: {expected_value}")
        print(f"   Got:      {result_intent}")
        
        if result_intent == expected_value:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
