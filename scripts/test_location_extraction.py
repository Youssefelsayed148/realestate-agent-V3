#!/usr/bin/env python3
"""
Test script for enhanced location extraction.
Run: python scripts/test_location_extraction.py
"""

import sys
sys.path.insert(0, '/mnt/d/The Osiris Labs/realestate-agent-backend')

from services.preference_parser import extract_state_patch, _parse_location, _best_location_match

test_cases = [
    # Original locations (should still work)
    ("New Cairo", {"location": "New Cairo"}),
    ("Sheikh Zayed", {"location": "Sheikh Zayed"}),
    ("Zayed", {"location": "Zayed"}),
    ("North Coast", {"location": "North Coast"}),
    ("6th of October", {"location": "6th Of October"}),
    
    # Directional phrases
    ("in New Cairo", {"location": "New Cairo"}),
    ("at Sheikh Zayed", {"location": "Sheikh Zayed"}),
    ("near Marassi", {"location": "marassi"}),
    ("close to Mountain View", {"location": "mountain view"}),
    ("by Palm Hills", {"location": "palm hills"}),
    ("located in Rehab", {"location": "rehab"}),
    ("situated in Tagamo3", {"location": "tagamo3"}),
    ("prefer something in Madinet Nasr", {"location": "madinet nasr"}),
    ("looking for place in Hacienda", {"location": "hacienda"}),
    
    # Compounds
    ("Marassi", {"location": "marassi"}),
    ("Hacienda", {"location": "hacienda"}),
    ("Mountain View", {"location": "mountain view"}),
    ("Palm Hills", {"location": "palm hills"}),
    ("Katameya Heights", {"location": "katameya heights"}),
    ("Madinaty", {"location": "madinaty"}),
    ("Rehab City", {"location": "rehab city"}),
    ("Hyde Park", {"location": "hyde park"}),
    ("Taj City", {"location": "taj city"}),
    ("Eastown", {"location": "eastown"}),
    ("Waterway", {"location": "waterway"}),
    ("Uptown Cairo", {"location": "uptown cairo"}),
    
    # Districts
    ("Tagamo3", {"location": "tagamo3"}),
    ("Tagamo 3", {"location": "tagamo 3"}),
    ("Rehab", {"location": "rehab"}),
    ("Madinet Nasr", {"location": "madinet nasr"}),
    ("Nasr City", {"location": "nasr city"}),
    ("Heliopolis", {"location": "heliopolis"}),
    ("Maadi", {"location": "maadi"}),
    ("Mokattam", {"location": "mokattam"}),
    ("Katameya", {"location": "katameya"}),
    
    # Multi-location preferences (should extract first)
    ("New Cairo or Zayed", {"location": "new cairo"}),
    ("preferably North Coast but open to Ain Sokhna", {"location": "north coast"}),
    ("Sheikh Zayed or 6 October", {"location": "sheikh zayed"}),
    ("Tagamo3 or Rehab", {"location": "tagamo3"}),
    ("Marassi or Hacienda", {"location": "marassi"}),
    
    # Change location
    ("change location to New Cairo", {"location": "New Cairo"}),
    ("set location to Sheikh Zayed", {"location": "Sheikh Zayed"}),
    ("change the location to Marassi", {"location": "marassi"}),
    
    # Combined with other info
    ("apartment in New Cairo for 5M", {"location": "New Cairo", "unit_type": "Apartment", "budget_max": 5_000_000}),
    ("villa at Marassi around 10M", {"location": "marassi", "unit_type": "Villa", "budget_max": 10_000_000}),
    ("120 sqm in Tagamo3", {"location": "tagamo3", "area_min": 120.0}),
    
    # New Capital
    ("New Capital", {"location": "new capital"}),
    ("New Administrative Capital", {"location": "new administrative capital"}),
    ("in New Capital", {"location": "new capital"}),
    
    # Edge cases with typos
    ("New Caior", {"location": "new cairo"}),
    ("Zayad", {"location": "zayed"}),
    ("Marasi", {"location": "marassi"}),
    ("Rehad", {"location": "rehab"}),
]

def run_tests():
    print("=" * 80)
    print("ENHANCED LOCATION EXTRACTION TEST")
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
            # Case-insensitive comparison for location
            if key == "location" and isinstance(expected_val, str) and isinstance(result_val, str):
                if expected_val.lower() != result_val.lower():
                    all_match = False
                    mismatches.append(f"{key}: expected='{expected_val}', got='{result_val}'")
            elif result_val != expected_val:
                all_match = False
                mismatches.append(f"{key}: expected={expected_val}, got={result_val}")
        
        status = "✅ PASS" if all_match else "❌ FAIL"
        
        print(f"\n{status} Input: \"{input_text}\"")
        print(f"   Expected location: '{expected.get('location')}'")
        print(f"   Got location:      '{result.get('location')}'")
        
        if expected.get("unit_type"):
            print(f"   Unit: expected='{expected.get('unit_type')}', got='{result.get('unit_type')}'")
        if expected.get("budget_max"):
            print(f"   Budget: expected={expected.get('budget_max'):,}, got={result.get('budget_max'):,}")
        if expected.get("area_min"):
            print(f"   Area: expected={expected.get('area_min')}, got={result.get('area_min')}")
        
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
