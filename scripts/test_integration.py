#!/usr/bin/env python3
"""
FINAL INTEGRATION TEST - All Phases Combined
Run: python scripts/test_integration.py
"""

import sys
sys.path.insert(0, '/mnt/d/The Osiris Labs/realestate-agent-backend')

from services.preference_parser import extract_state_patch
from services.intent_rules import detect_intent_rules
from services.intents import Intent

# Complex real-world scenarios combining all extraction features
integration_tests = [
    # Scenario 1: Complete search query
    {
        "input": "I want a 3 bedroom apartment with garden in New Cairo around 8M",
        "expected": {
            "unit_type": "Apartment",
            "bedrooms": 3,
            "location": "New Cairo",
            "budget_max": 8_000_000,
            "features": {"has_garden": True}
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 2: Villa search with all filters
    {
        "input": "large 5 bedroom villa between 10M and 15M in Sheikh Zayed with pool view",
        "expected": {
            "unit_type": "Villa",
            "bedrooms": 5,
            "location": "Sheikh Zayed",
            "budget_min": 10_000_000,
            "budget_max": 15_000_000,
            "features": {"size_preference": "large", "view_type": "pool"}
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 3: Studio with specific requirements
    {
        "input": "small furnished studio up to 3M in Tagamo3 with balcony",
        "expected": {
            "unit_type": "Studio",
            "location": "Tagamo3",
            "budget_max": 3_000_000,
            "features": {"size_preference": "small", "furnishing": "furnished", "has_balcony": True}
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 4: Penthouse with range area
    {
        "input": "penthouse with roof terrace 200-250 sqm in Marassi around 12M",
        "expected": {
            "unit_type": "Penthouse",
            "location": "marassi",
            "area_min": 200.0,
            "area_max": 250.0,
            "budget_max": 12_000_000,
            "features": {"has_roof": True, "has_terrace": True}
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 5: Ground floor apartment
    {
        "input": "ground floor 2 bedroom apartment at least 5M in Rehab",
        "expected": {
            "unit_type": "Apartment",
            "bedrooms": 2,
            "location": "Rehab",
            "budget_min": 5_000_000,
            "floor_type": "ground_floor"
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 6: Duplex with multiple features
    {
        "input": "spacious duplex with garden view unfurnished between 7M-9M in Madinaty",
        "expected": {
            "unit_type": "Duplex",
            "location": "madinaty",
            "budget_min": 7_000_000,
            "budget_max": 9_000_000,
            "features": {"size_preference": "spacious", "view_type": "garden", "furnishing": "unfurnished"}
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 7: Chalet on North Coast
    {
        "input": "chalet with sea view up to 4M in North Coast or Ras El Hekma",
        "expected": {
            "unit_type": "Chalet",
            "location": "North Coast",
            "budget_max": 4_000_000,
            "features": {"view_type": "sea"}
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 8: Townhouse with minimum area
    {
        "input": "3 bedroom townhouse minimum 180 sqm starting from 6M in Palm Hills",
        "expected": {
            "unit_type": "Town House",
            "bedrooms": 3,
            "location": "palm hills",
            "area_min": 180.0,
            "budget_min": 6_000_000
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 9: Compare options
    {
        "input": "compare option 1 and 3",
        "expected": {},
        "intent": Intent.COMPARE
    },
    
    # Scenario 10: Show details
    {
        "input": "tell me more about the second option",
        "expected": {},
        "intent": Intent.SHOW_DETAILS
    },
    
    # Scenario 11: Filter results
    {
        "input": "only show me apartments",
        "expected": {},
        "intent": Intent.FILTER_RESULTS
    },
    
    # Scenario 12: Sort results
    {
        "input": "sort by price cheapest first",
        "expected": {},
        "intent": Intent.SORT_RESULTS
    },
    
    # Scenario 13: Navigation
    {
        "input": "show more results",
        "expected": {},
        "intent": Intent.NAVIGATE
    },
    
    # Scenario 14: Confirm choice
    {
        "input": "I want to book option 2",
        "expected": {},
        "intent": Intent.CONFIRM_CHOICE
    },
    
    # Scenario 15: Restart
    {
        "input": "start over",
        "expected": {},
        "intent": Intent.RESTART
    },
    
    # Scenario 16: Refine search
    {
        "input": "cheaper options",
        "expected": {},
        "intent": Intent.REFINE_SEARCH
    },
    
    # Scenario 17: Complex with location change
    {
        "input": "change location to Katameya Heights and show me 4 bedroom villas",
        "expected": {
            "location": "Katameya Heights",
            "unit_type": "Villa",
            "bedrooms": 4
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 18: Budget range with unit type
    {
        "input": "2 bedroom apartment from 5M to 7M in Hyde Park",
        "expected": {
            "unit_type": "Apartment",
            "bedrooms": 2,
            "location": "hyde park",
            "budget_min": 5_000_000,
            "budget_max": 7_000_000
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 19: Corner unit with features
    {
        "input": "corner apartment with 2 bedrooms and balcony in Eastown around 6M",
        "expected": {
            "unit_type": "Apartment",
            "bedrooms": 2,
            "location": "eastown",
            "budget_max": 6_000_000,
            "features": {"is_corner_unit": True, "has_balcony": True}
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
    
    # Scenario 20: High floor penthouse
    {
        "input": "high floor penthouse with roof not more than 15M in Uptown Cairo",
        "expected": {
            "unit_type": "Penthouse",
            "location": "uptown cairo",
            "budget_max": 15_000_000,
            "floor_type": "high_floor",
            "features": {"has_roof": True}
        },
        "intent": Intent.PROVIDE_PREFERENCES
    },
]

def check_dict_match(expected, actual):
    """Check if all expected keys match in actual dict"""
    if not expected:
        return True
    
    for key, expected_val in expected.items():
        actual_val = actual.get(key)
        
        if key == "features":
            if expected_val and not actual_val:
                return False
            if expected_val and actual_val:
                for fkey, fval in expected_val.items():
                    if actual_val.get(fkey) != fval:
                        return False
        elif key == "location":
            # Case-insensitive comparison
            if expected_val and actual_val:
                if expected_val.lower() != actual_val.lower():
                    return False
        elif actual_val != expected_val:
            return False
    
    return True

def run_integration_tests():
    print("=" * 90)
    print("FINAL INTEGRATION TEST - All Phases Combined")
    print("=" * 90)
    print(f"\nTesting {len(integration_tests)} complex real-world scenarios...\n")
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(integration_tests, 1):
        input_text = test["input"]
        expected = test["expected"]
        expected_intent = test["intent"]
        
        # Get extraction results
        result = extract_state_patch(input_text)
        
        # Get intent
        intent_result = detect_intent_rules(input_text)
        intent_value = intent_result.value if intent_result else "None"
        
        # Check extraction match
        extraction_match = check_dict_match(expected, result)
        intent_match = intent_value == expected_intent.value
        
        all_match = extraction_match and intent_match
        status = "✅ PASS" if all_match else "❌ FAIL"
        
        print(f"{status} Scenario {i}: \"{input_text}\"")
        
        if not extraction_match:
            print(f"   Expected extraction: {expected}")
            print(f"   Got extraction:      {result}")
        
        if not intent_match:
            print(f"   Expected intent: {expected_intent.value}")
            print(f"   Got intent:      {intent_value}")
        
        if all_match:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 90)
    print(f"INTEGRATION TEST RESULTS: {passed} passed, {failed} failed out of {len(integration_tests)} scenarios")
    print("=" * 90)
    
    if failed == 0:
        print("\n🎉 ALL INTEGRATION TESTS PASSED! 🎉")
        print(f"\nTotal test coverage:")
        print(f"  - Budget extraction: 30 tests")
        print(f"  - Area extraction: 37 tests")
        print(f"  - Location extraction: 53 tests")
        print(f"  - Unit type extraction: 44 tests")
        print(f"  - Intent detection: 85 tests")
        print(f"  - Integration tests: 20 scenarios")
        print(f"  - TOTAL: 269 tests")
    
    return failed == 0

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
