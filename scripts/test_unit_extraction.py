#!/usr/bin/env python3
"""
Test script for enhanced unit type extraction.
Run: python scripts/test_unit_extraction.py
"""

import sys
sys.path.insert(0, '/mnt/d/The Osiris Labs/realestate-agent-backend')

from services.preference_parser import extract_state_patch, _parse_unit_type, _parse_bedrooms, _parse_floor_type, _parse_unit_features

test_cases = [
    # Basic unit types (should still work)
    ("apartment", {"unit_type": "Apartment"}),
    ("villa", {"unit_type": "Villa"}),
    ("studio", {"unit_type": "Studio"}),
    ("duplex", {"unit_type": "Duplex"}),
    ("penthouse", {"unit_type": "Penthouse"}),
    ("chalet", {"unit_type": "Chalet"}),
    
    # With bedroom counts
    ("2 bedroom apartment", {"unit_type": "Apartment", "bedrooms": 2}),
    ("3 bedroom villa", {"unit_type": "Villa", "bedrooms": 3}),
    ("1 bedroom studio", {"unit_type": "Studio", "bedrooms": 1}),
    ("4 bedroom penthouse", {"unit_type": "Penthouse", "bedrooms": 4}),
    ("2-bed apartment", {"unit_type": "Apartment", "bedrooms": 2}),
    ("3-bed villa", {"unit_type": "Villa", "bedrooms": 3}),
    ("2 bed apartment", {"unit_type": "Apartment", "bedrooms": 2}),
    ("3br apartment", {"unit_type": "Apartment", "bedrooms": 3}),
    ("4br villa", {"unit_type": "Villa", "bedrooms": 4}),
    
    # Floor types
    ("ground floor apartment", {"unit_type": "Apartment", "floor_type": "ground_floor"}),
    ("first floor unit", {"floor_type": "first_floor"}),
    ("2nd floor apartment", {"unit_type": "Apartment", "floor_type": "second_floor"}),
    ("high floor penthouse", {"unit_type": "Penthouse", "floor_type": "high_floor"}),
    ("top floor apartment", {"unit_type": "Apartment", "floor_type": "top_floor"}),
    
    # Features - Garden/Outdoor
    ("apartment with garden", {"unit_type": "Apartment", "features": {"has_garden": True}}),
    ("villa with roof", {"unit_type": "Villa", "features": {"has_roof": True}}),
    ("penthouse with terrace", {"unit_type": "Penthouse", "features": {"has_terrace": True}}),
    ("apartment with balcony", {"unit_type": "Apartment", "features": {"has_balcony": True}}),
    ("garden villa", {"unit_type": "Villa", "features": {"has_garden": True}}),
    
    # Features - Views
    ("apartment with sea view", {"unit_type": "Apartment", "features": {"view_type": "sea"}}),
    ("villa with garden view", {"unit_type": "Villa", "features": {"view_type": "garden"}}),
    ("apartment with pool view", {"unit_type": "Apartment", "features": {"view_type": "pool"}}),
    
    # Features - Position
    ("corner apartment", {"unit_type": "Apartment", "features": {"is_corner_unit": True}}),
    ("corner unit", {"features": {"is_corner_unit": True}}),
    ("end unit", {"features": {"is_end_unit": True}}),
    
    # Features - Furnishing
    ("furnished apartment", {"unit_type": "Apartment", "features": {"furnishing": "furnished"}}),
    ("semi-furnished villa", {"unit_type": "Villa", "features": {"furnishing": "semi"}}),
    ("unfurnished apartment", {"unit_type": "Apartment", "features": {"furnishing": "unfurnished"}}),
    
    # Features - Size
    ("small studio", {"unit_type": "Studio", "features": {"size_preference": "small"}}),
    ("large villa", {"unit_type": "Villa", "features": {"size_preference": "large"}}),
    ("big apartment", {"unit_type": "Apartment", "features": {"size_preference": "large"}}),
    ("spacious villa", {"unit_type": "Villa", "features": {"size_preference": "spacious"}}),
    
    # Combined patterns
    ("3 bedroom apartment with garden in New Cairo", {
        "unit_type": "Apartment", 
        "bedrooms": 3, 
        "location": "New Cairo",
        "features": {"has_garden": True}
    }),
    ("2 bedroom furnished villa with sea view", {
        "unit_type": "Villa",
        "bedrooms": 2,
        "features": {"furnishing": "furnished", "view_type": "sea"}
    }),
    ("small studio in Tagamo3", {
        "unit_type": "Studio",
        "location": "Tagamo3",
        "features": {"size_preference": "small"}
    }),
    ("ground floor apartment with garden", {
        "unit_type": "Apartment",
        "floor_type": "ground_floor",
        "features": {"has_garden": True}
    }),
    ("large 4 bedroom villa", {
        "unit_type": "Villa",
        "bedrooms": 4,
        "features": {"size_preference": "large"}
    }),
    ("penthouse with roof terrace", {
        "unit_type": "Penthouse",
        "features": {"has_roof": True, "has_terrace": True}
    }),
]

def check_features_match(expected_features, actual_features):
    """Check if features dict matches expected"""
    if not expected_features:
        return actual_features == {} or actual_features is None
    
    if not actual_features:
        return False
    
    for key, val in expected_features.items():
        if actual_features.get(key) != val:
            return False
    
    return True

def run_tests():
    print("=" * 80)
    print("ENHANCED UNIT TYPE EXTRACTION TEST")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for input_text, expected in test_cases:
        result = extract_state_patch(input_text)
        
        # Check all expected fields
        all_match = True
        mismatches = []
        
        for key, expected_val in expected.items():
            result_val = result.get(key)
            
            if key == "features":
                if not check_features_match(expected_val, result_val):
                    all_match = False
                    mismatches.append(f"{key}: expected={expected_val}, got={result_val}")
            elif result_val != expected_val:
                all_match = False
                mismatches.append(f"{key}: expected={expected_val}, got={result_val}")
        
        status = "✅ PASS" if all_match else "❌ FAIL"
        
        print(f"\n{status} Input: \"{input_text}\"")
        print(f"   Unit:      '{result.get('unit_type')}'")
        print(f"   Bedrooms:  {result.get('bedrooms')}")
        print(f"   Floor:     {result.get('floor_type')}")
        print(f"   Features:  {result.get('features')}")
        
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
