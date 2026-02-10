# Enhanced Pattern Extraction Documentation

## Overview

This document describes all the enhanced pattern extraction capabilities added to the Real Estate Chatbot across 5 phases. The system now supports comprehensive extraction of budget, area, location, unit types, and intents from natural language user messages.

**Total Test Coverage: 269 tests**
- Budget extraction: 30 tests
- Area extraction: 37 tests
- Location extraction: 53 tests
- Unit type extraction: 44 tests
- Intent detection: 85 tests
- Integration tests: 20 scenarios

---

## Phase 1: Enhanced Budget Extraction

### Simple Budget Amounts

**Patterns Detected:**
- Direct amounts: `5M`, `5 million`, `5000000`, `3.5M`
- Approximate: `around 6M`, `about 4.5 million`, `~7M`, `approximately 10M`
- Budget phrases: `budget is 8M`, `my budget 12M`, `budget 8 million`

**Examples:**
```
"I want an apartment for 5M"                    → budget_max: 5,000,000
"around 6M"                                    → budget_max: 6,000,000  
"my budget is 12M"                             → budget_max: 12,000,000
```

### Budget Ranges

**Patterns Detected:**
- Between: `between 3M and 5M`, `between 3 million and 5 million`
- From-to: `from 4 million to 7 million`, `from 2M to 4M`
- To format: `3M to 6M`, `3 million to 5 million`
- Dash format: `4-8M`, `5M-10M`, `100-150`

**Examples:**
```
"between 3M and 5M"                           → budget_min: 3,000,000, budget_max: 5,000,000
"from 4M to 7M"                               → budget_min: 4,000,000, budget_max: 7,000,000
"3-5M"                                        → budget_min: 3,000,000, budget_max: 5,000,000
```

### Maximum Budget Indicators

**Triggers:** `up to`, `not more than`, `no more than`, `at most`, `maximum`, `max`, `less than`, `below`, `under`

**Examples:**
```
"up to 5M"                                    → budget_max: 5,000,000
"not more than 6 million"                     → budget_max: 6,000,000
"at most 8M"                                  → budget_max: 8,000,000
```

### Minimum Budget Indicators

**Triggers:** `starting from`, `from`, `at least`, `minimum`, `min`, `more than`, `above`, `over`

**Examples:**
```
"starting from 3M"                            → budget_min: 3,000,000
"at least 5M"                                 → budget_min: 5,000,000
"minimum 6M"                                  → budget_min: 6,000,000
```

---

## Phase 2: Enhanced Area Extraction

### Simple Area Amounts

**Units Supported:** `sqm`, `m2`, `m²`, `square meters`, `square metres`, `meters`, `metres`

**Patterns:**
- Direct: `120 sqm`, `150 m2`, `200 square meters`
- Approximate: `around 130 sqm`, `about 140 m2`, `~150 sqm`
- Area phrases: `area is 120 sqm`, `size is 150 m2`
- Just meters: `180 meters`, `200 metres` (when in area context)

**Examples:**
```
"120 sqm"                                     → area_min: 120.0
"around 130 sqm"                              → area_min: 130.0
"area is 120 sqm"                             → area_min: 120.0
```

### Area Ranges

**Patterns:**
- Between: `between 100 and 150 sqm`
- From-to: `from 120 to 180 m2`, `100 to 150 sqm`
- Dash format: `130-170 m2`, `100-150 square meters`

**Examples:**
```
"between 100 and 150 sqm"                     → area_min: 100.0, area_max: 150.0
"120 to 160 sqm"                              → area_min: 120.0, area_max: 160.0
"130-170 m2"                                  → area_min: 130.0, area_max: 170.0
```

### Maximum Area Indicators

**Triggers:** `up to`, `not more than`, `no more than`, `at most`, `maximum`, `max`, `less than`, `below`, `under`

**Examples:**
```
"up to 150 sqm"                               → area_max: 150.0
"max 140 sqm"                                 → area_max: 140.0
"less than 150 sqm"                           → area_max: 150.0
```

### Minimum Area Indicators

**Triggers:** `starting from`, `from`, `at least`, `minimum`, `min`, `more than`, `above`, `over`

**Examples:**
```
"starting from 120 sqm"                       → area_min: 120.0
"at least 160 sqm"                            → area_min: 160.0
"minimum 180 m²"                              → area_min: 180.0
```

---

## Phase 3: Enhanced Location Extraction

### Supported Locations (75+ Total)

**Main Areas:**
- New Cairo
- Mostakbal City / Mostakbal City - New Cairo
- El Shorouk / El Shorouk - New Cairo
- Fifth Settlement / Fifth District
- Sheikh Zayed / Zayed
- North Coast
- Ras Al Hekma / Ras El Hekma
- Sidi Abdelrahman
- Ain Sokhna
- 6 October / 6th of October
- New Capital / New Administrative Capital

**Districts & Neighborhoods (25+):**
- Tagamo3 / Tagamo 3 / El Tagamo3
- Rehab / Al Rehab
- Madinet Nasr / Nasr City
- Heliopolis / Masr El Gedida
- Maadi, Giza, Dokki, Mohandessin, Agouza
- Zamalek, Garden City, Downtown, Ramses
- Haram, Faysal, Imbaba, Shubra
- Matarya, Ain Shams, Marg, Waili
- Sawah, Mokattam, Katameya, Wadi Degla

**Compounds (35+):**
- Marassi, Hacienda, Mountain View, Palm Hills
- Katameya Heights, Madinaty, Rehab City
- Hyde Park, Taj City, Eastown, Waterway
- Village Gate, Uptown Cairo, Creek Town
- Sodic, Sodic East, Sodic West, East Cairo, West Cairo
- Il Bosco, The Butterfly, The Estates
- Badya, Orkidia, Zavani, Al Maqsed
- Al Burouj, La Verde, Capital Prime, De Joya, Al Manara

**Specific Areas:**
- Golf Extension, Golf Area, Golden Square, Petrified Forest
- First/Second/Third/Fourth Settlement
- Narges, Lotus/Lotus District, Yasmin/Yasmin District
- Banafseg/Banafseg District, El Banafseg

### Directional Phrases

**Patterns:** `in X`, `at X`, `near X`, `close to X`, `by X`, `next to X`, `located in X`, `situated in X`

**Examples:**
```
"in New Cairo"                                → location: "New Cairo"
"near Marassi"                                → location: "marassi"
"close to Mountain View"                      → location: "mountain view"
"located in Rehab"                            → location: "rehab"
```

### Multi-Location Preferences

Extracts first mentioned location from multi-location expressions:

**Examples:**
```
"New Cairo or Zayed"                          → location: "New Cairo"
"preferably North Coast but open to Ain Sokhna" → location: "North Coast"
"Tagamo3 or Rehab"                            → location: "tagamo3"
```

### Change Location Commands

**Patterns:** `change location to X`, `set location to X`, `change the location to X`

**Examples:**
```
"change location to New Cairo"                → location: "New Cairo"
"set location to Sheikh Zayed"                → location: "Sheikh Zayed"
```

### Fuzzy Matching (Typos)

**Examples of typo tolerance:**
```
"New Caior"                                   → location: "New Cairo"
"Zayad"                                       → location: "Zayed"
"Marasi"                                      → location: "Marassi"
"Rehad"                                       → location: "Rehab"
```

---

## Phase 4: Enhanced Unit Type Extraction

### Basic Unit Types

**Supported Types:**
- Apartment (`apartment`, `apt`, `flat`)
- Villa (`villa`, `villas`)
- Studio (`studio`)
- Duplex (`duplex`)
- Penthouse (`penthouse`)
- Chalet (`chalet`, `chalets`)
- Town House (`town house`, `townhouse`)
- Twin House (`twin house`)
- Lofts (`loft`, `lofts`)
- Cabins (`cabin`, `cabins`)
- Offices (`office`, `offices`)

### Bedroom Counts

**Patterns:**
- Full word: `2 bedroom`, `3 bedrooms`
- Hyphenated: `2-bed`, `3-bed`
- Abbreviated: `2 bed`, `3br`, `4br`

**Examples:**
```
"2 bedroom apartment"                         → unit_type: "Apartment", bedrooms: 2
"3-bed villa"                                 → unit_type: "Villa", bedrooms: 3
"4br apartment"                               → unit_type: "Apartment", bedrooms: 4
```

### Floor Types

**Supported Types:**
- `ground_floor`
- `first_floor`, `1st floor`
- `second_floor`, `2nd floor`
- `high_floor`
- `low_floor`
- `middle_floor`
- `top_floor`, `upper_floor`

**Examples:**
```
"ground floor apartment"                      → unit_type: "Apartment", floor_type: "ground_floor"
"high floor penthouse"                        → unit_type: "Penthouse", floor_type: "high_floor"
```

### Unit Features

#### Outdoor Features
```
"with garden" / "garden unit" / "garden villa"   → features.has_garden: true
"with roof" / "roof terrace" / "rooftop"         → features.has_roof: true
"with terrace" / "terrace"                       → features.has_terrace: true
"with balcony" / "balcony"                       → features.has_balcony: true
```

#### Views
```
"sea view" / "ocean view" / "beach view"         → features.view_type: "sea"
"garden view" / "green view"                     → features.view_type: "garden"
"pool view"                                      → features.view_type: "pool"
"street view"                                    → features.view_type: "street"
```

#### Unit Position
```
"corner unit" / "corner apartment" / "corner villa" → features.is_corner_unit: true
"end unit"                                       → features.is_end_unit: true
```

#### Furnishing
```
"furnished"                                      → features.furnishing: "furnished"
"semi-furnished" / "partly furnished"            → features.furnishing: "semi"
"unfurnished" / "not furnished"                  → features.furnishing: "unfurnished"
```

#### Size Modifiers
```
"small studio" / "small apartment"               → features.size_preference: "small"
"large villa" / "big apartment"                  → features.size_preference: "large"
"spacious"                                       → features.size_preference: "spacious"
"compact" / "cozy"                               → features.size_preference: "compact"
```

---

## Phase 5: Enhanced Intent Detection

### Intent Types

1. **RESTART** - Reset conversation
2. **SHOW_RESULTS** - Display search results
3. **PROVIDE_PREFERENCES** - User provides search criteria
4. **REFINE_SEARCH** - Adjust current search
5. **CONFIRM_CHOICE** - Select/book an option
6. **UNKNOWN** - Default fallback
7. **COMPARE** - Compare options (NEW)
8. **SHOW_DETAILS** - Request more information (NEW)
9. **FILTER_RESULTS** - Filter current results (NEW)
10. **SORT_RESULTS** - Sort results (NEW)
11. **NAVIGATE** - Navigate pages (NEW)

### Comparison Intent

**Triggers:**
```
"compare option 1 and 3"
"compare 1 and 2"
"compare first and second"
"difference between option 1 and 2"
"option 1 vs option 2"
"which is better"
"which is cheaper"
"which one is best"
```

### Show Details Intent

**Triggers:**
```
"tell me more"
"more info" / "more information"
"details about option 2"
"show me the details"
"what are the amenities"
"what are the features"
"describe option 1"
"about the first option"
"option 2 details"
```

### Filter Results Intent

**Triggers:**
```
"only show apartments"
"show only villas"
"only apartments"
"remove villas"
"exclude apartments"
"filter by price"
"just show me studios"
"show me only chalets"
```

### Sort Results Intent

**Triggers:**
```
"sort by price" / "sort by area" / "sort by date"
"cheapest first"
"most expensive first"
"lowest price" / "highest price"
"smallest first" / "largest first"
"newest first" / "latest first"
"show the cheapest"
"by price"
"order by date"
"sorted by budget"
```

### Navigate Intent

**Triggers:**
```
"next" / "next page"
"previous" / "prev" / "previous page"
"show more" / "load more"
"more results"
"go back" / "go forward"
"page 2" / "page two"
"first page" / "last page"
```

### Confirm/Book Intent

**Triggers:**
```
"I want option 1"
"I choose the first one"
"pick option 2"
"select the third option"
"book option 2"
"reserve this one"
"proceed with option 1"
"confirm the booking"
"I'll take this one"
"contact me about option 2"
"call me regarding the first option"
"send me details about option 1"
"I'm interested in option 2"
"this one is good"
"this one is perfect"
```

### Refine Search Intent

**Triggers:**
```
"cheaper" / "cheaper options"
"bigger" / "smaller"
"more expensive"
"increase budget" / "decrease budget"
"change budget"
"adjust"
```

---

## Combined Examples

### Complex Search Queries

```
"3 bedroom apartment with garden in New Cairo around 8M"
→ unit_type: "Apartment"
→ bedrooms: 3
→ location: "New Cairo"
→ budget_max: 8,000,000
→ features: {has_garden: true}
→ intent: PROVIDE_PREFERENCES
```

```
"large 5 bedroom villa between 10M and 15M in Sheikh Zayed with pool view"
→ unit_type: "Villa"
→ bedrooms: 5
→ location: "Sheikh Zayed"
→ budget_min: 10,000,000
→ budget_max: 15,000,000
→ features: {size_preference: "large", view_type: "pool"}
→ intent: PROVIDE_PREFERENCES
```

```
"penthouse with roof terrace 200-250 sqm in Marassi around 12M"
→ unit_type: "Penthouse"
→ location: "marassi"
→ area_min: 200.0
→ area_max: 250.0
→ budget_max: 12,000,000
→ features: {has_roof: true, has_terrace: true}
→ intent: PROVIDE_PREFERENCES
```

```
"ground floor 2 bedroom apartment at least 5M in Rehab"
→ unit_type: "Apartment"
→ bedrooms: 2
→ location: "Rehab"
→ budget_min: 5,000,000
→ floor_type: "ground_floor"
→ intent: PROVIDE_PREFERENCES
```

---

## File Structure

### Modified Files

1. **services/preference_parser.py**
   - Enhanced budget parsing functions
   - Enhanced area parsing functions
   - Enhanced location parsing with 75+ locations
   - Enhanced unit type parsing with bedrooms and features

2. **services/intent_rules.py**
   - Added comparison detection
   - Added details detection
   - Added filter detection
   - Added sort detection
   - Added navigation detection
   - Added enhanced confirm detection

3. **services/intents.py**
   - Added 5 new intent types: COMPARE, SHOW_DETAILS, FILTER_RESULTS, SORT_RESULTS, NAVIGATE

### Test Files

1. **scripts/test_budget_extraction.py** - 30 budget tests
2. **scripts/test_area_extraction.py** - 37 area tests
3. **scripts/test_location_extraction.py** - 53 location tests
4. **scripts/test_unit_extraction.py** - 44 unit type tests
5. **scripts/test_intent_extraction.py** - 85 intent tests
6. **scripts/test_integration.py** - 20 complex scenario tests

### Documentation Files

1. **TEST_SCENARIOS.txt** - 171 manual test scenarios
2. **EXTRACTION_PATTERNS.md** - This documentation

---

## Usage Notes

1. **Order Matters**: The extraction system processes patterns in a specific order to avoid conflicts (e.g., area indicators take precedence over budget when both numbers are present)

2. **Fuzzy Matching**: Location extraction uses fuzzy matching with 75-80% similarity threshold to handle typos

3. **Multi-Pattern Support**: Single messages can trigger multiple extractions simultaneously

4. **Intent Priority**: Intent detection follows priority order: RESTART > COMPARE > CONFIRM > DETAILS > FILTER > SORT > NAVIGATE > SHOW_RESULTS > REFINE > PROVIDE_PREFERENCES

5. **State Management**: All extracted values are merged into conversation state for multi-turn conversations

---

## Future Enhancements

Potential additions for future phases:
- Arabic language support
- Voice input processing
- More compound names
- Amenity extraction (parking, pool, security, gym)
- Date/time extraction for delivery year
- Payment plan preferences
- Developer name extraction
