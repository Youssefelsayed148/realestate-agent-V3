#!/usr/bin/env python3
"""
Test script for enhanced area extraction.
Run: python scripts/test_area_extraction.py
"""

import sys
sys.path.insert(0, '/mnt/d/The Osiris Labs/realestate-agent-backend')

from services.preference_parser import extract_state_patch, _parse_area_m2, _parse_area_range

test_cases = [
    # Simple amounts (should work)
    ("120 sqm", {"area_min": 120.0}),
    ("150 m2", {"area_min": 150.0}),
    ("180 m²", {"area_min": 180.0}),
    ("200 square meters", {"area_min": 200.0}),
    ("140 square metres", {"area_min": 140.0}),
    
    # Approximate amounts
    ("around 130 sqm", {"area_min": 130.0}),
    ("about 140 m2", {"area_min": 140.0}),
    ("approximately 160 m²", {"area_min": 160.0}),
    ("~150 square meters", {"area_min": 150.0}),
    
    # Area phrases
    ("area is 120 sqm", {"area_min": 120.0}),
    ("size is 150 m2", {"area_min": 150.0}),
    
    # Just meters (area context)
    ("180 meters", {"area_min": 180.0}),
    ("200 metres", {"area_min": 200.0}),
    
    # Ranges
    ("between 100 and 150 sqm", {"area_min": 100.0, "area_max": 150.0}),
    ("from 120 to 180 m2", {"area_min": 120.0, "area_max": 180.0}),
    ("120 to 160 sqm", {"area_min": 120.0, "area_max": 160.0}),
    ("130-170 m2", {"area_min": 130.0, "area_max": 170.0}),
    ("100-150 square meters", {"area_min": 100.0, "area_max": 150.0}),
    
    # Maximum indicators
    ("up to 150 sqm", {"area_max": 150.0}),
    ("not more than 180 m2", {"area_max": 180.0}),
    ("no more than 200 sqm", {"area_max": 200.0}),
    ("at most 160 m²", {"area_max": 160.0}),
    ("max 140 sqm", {"area_max": 140.0}),
    ("maximum area 170 m2", {"area_max": 170.0}),
    ("less than 150 sqm", {"area_max": 150.0}),
    ("below 180 m2", {"area_max": 180.0}),
    ("under 200 sqm", {"area_max": 200.0}),
    
    # Minimum indicators
    ("starting from 120 sqm", {"area_min": 120.0}),
    ("from 140 m2", {"area_min": 140.0}),
    ("at least 160 sqm", {"area_min": 160.0}),
    ("minimum 180 m²", {"area_min": 180.0}),
    ("min area 150 sqm", {"area_min": 150.0}),
    ("more than 130 m2", {"area_min": 130.0}),
    ("above 170 sqm", {"area_min": 170.0}),
    ("over 140 m2", {"area_min": 140.0}),
    
    # Combined with other info
    ("apartment 120 sqm in New Cairo", {"unit_type": "Apartment", "area_min": 120.0, "location": "New Cairo"}),
    ("villa between 200 and 300 sqm in Zayed", {"unit_type": "Villa", "area_min": 200.0, "area_max": 300.0, "location": "Zayed"}),
]

def format_area(value):
    if value is None:
        return "None"
    return f"{value} m²"

def run_tests():
    print("=" * 80)
    print("ENHANCED AREA EXTRACTION TEST")
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
            # Handle float comparison with small tolerance
            if isinstance(expected_val, float) and isinstance(result_val, float):
                if abs(expected_val - result_val) > 0.01:
                    all_match = False
                    mismatches.append(f"{key}: expected={expected_val}, got={result_val}")
            elif result_val != expected_val:
                all_match = False
                mismatches.append(f"{key}: expected={expected_val}, got={result_val}")
        
        status = "✅ PASS" if all_match else "❌ FAIL"
        
        print(f"\n{status} Input: \"{input_text}\"")
        print(f"   Expected: min={format_area(expected.get('area_min'))}, max={format_area(expected.get('area_max'))}")
        print(f"   Got:      min={format_area(result.get('area_min'))}, max={format_area(result.get('area_max'))}")
        
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
