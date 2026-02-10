#!/usr/bin/env python3
"""
Test script for enhanced budget extraction.
Run: python scripts/test_budget_extraction.py
"""

import sys
sys.path.insert(0, '/mnt/d/The Osiris Labs/realestate-agent-backend')

from services.preference_parser import extract_state_patch, _parse_budget_egp, _parse_budget_range

test_cases = [
    # Simple amounts (should work)
    ("I want an apartment for 5M", {"budget_max": 5_000_000}),
    ("budget is 8 million", {"budget_max": 8_000_000}),
    ("3500000 EGP", {"budget_max": 3_500_000}),
    
    # Approximate amounts
    ("around 6M", {"budget_max": 6_000_000}),
    ("about 4.5 million", {"budget_max": 4_500_000}),
    ("~7M", {"budget_max": 7_000_000}),
    ("approximately 10M", {"budget_max": 10_000_000}),
    
    # Budget phrases
    ("my budget is 12M", {"budget_max": 12_000_000}),
    ("budget 8 million", {"budget_max": 8_000_000}),
    
    # Ranges
    ("between 3M and 5M", {"budget_min": 3_000_000, "budget_max": 5_000_000}),
    ("from 4 million to 7 million", {"budget_min": 4_000_000, "budget_max": 7_000_000}),
    ("3M to 6M", {"budget_min": 3_000_000, "budget_max": 6_000_000}),
    ("4-8M", {"budget_min": 4_000_000, "budget_max": 8_000_000}),
    ("5M-10M", {"budget_min": 5_000_000, "budget_max": 10_000_000}),
    
    # Maximum indicators
    ("up to 5M", {"budget_max": 5_000_000}),
    ("not more than 6 million", {"budget_max": 6_000_000}),
    ("no more than 4M", {"budget_max": 4_000_000}),
    ("at most 8M", {"budget_max": 8_000_000}),
    ("less than 10M", {"budget_max": 10_000_000}),
    ("below 7M", {"budget_max": 7_000_000}),
    ("under 5 million", {"budget_max": 5_000_000}),
    
    # Minimum indicators
    ("starting from 3M", {"budget_min": 3_000_000}),
    ("from 4 million", {"budget_min": 4_000_000}),
    ("at least 5M", {"budget_min": 5_000_000}),
    ("minimum 6M", {"budget_min": 6_000_000}),
    ("more than 2M", {"budget_min": 2_000_000}),
    ("above 3 million", {"budget_min": 3_000_000}),
    ("over 4M", {"budget_min": 4_000_000}),
    
    # Combined with other info
    ("apartment in New Cairo around 8M", {"location": "New Cairo", "unit_type": "Apartment", "budget_max": 8_000_000}),
    ("villa between 10M and 15M in Zayed", {"location": "Zayed", "unit_type": "Villa", "budget_min": 10_000_000, "budget_max": 15_000_000}),
]

def format_currency(value):
    if value is None:
        return "None"
    return f"{value:,} EGP"

def run_tests():
    print("=" * 80)
    print("ENHANCED BUDGET EXTRACTION TEST")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for input_text, expected in test_cases:
        result = extract_state_patch(input_text)
        
        # Only check fields that are explicitly expected
        all_match = True
        mismatches = []
        
        for key, expected_val in expected.items():
            result_val = result.get(key)
            if result_val != expected_val:
                all_match = False
                mismatches.append(f"{key}: expected={expected_val}, got={result_val}")
        
        status = "✅ PASS" if all_match else "❌ FAIL"
        
        print(f"\n{status} Input: \"{input_text}\"")
        print(f"   Expected: max={format_currency(expected.get('budget_max'))}, min={format_currency(expected.get('budget_min'))}")
        print(f"   Got:      max={format_currency(result.get('budget_max'))}, min={format_currency(result.get('budget_min'))}")
        
        if expected.get("location"):
            print(f"   Location: expected='{expected.get('location')}', got='{result.get('location')}'")
        if expected.get("unit_type"):
            print(f"   Unit:     expected='{expected.get('unit_type')}', got='{result.get('unit_type')}'")
        
        if not all_match:
            for mismatch in mismatches:
                print(f"   ❌ {mismatch}")
            failed += 1
        else:
            passed += 1
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
