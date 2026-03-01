# QOZB Entity (Organization) Consistency Report

**Dataset**: 21,287 property rows × 4 roles = 85,148 entity slots

---

## Overview

| Metric | Count |
|---|---|
| Total entity slots | 85,148 |
| Fake / placeholder entity strings | 46,907 |
| Real entity names (total) | 38,241 |
| **Unique real entity names** | 11,848 |
| Entities appearing ≥3 times | 3,196 |

These 11,848 unique real entity names will become `organizations` records
(exact name dedup only — "Greystar" and "Greystar Management" stay as separate records).

---

## Fake / Placeholder Entity Strings (Skip List)

These strings must be excluded from `organizations` import:

| String | Occurrences |
|---|---|
| `nan` | 46,071 |
| `owner managed` | 836 |

---

## Address Data Consistency (Entities Appearing ≥3 Times)

For the **3,196** entities seen 3+ times, we measure how consistent
their city/state/website fields are across all their property appearances.

**Consistent** (≥80% agreement on city+state): 3,091 entities
→ Will produce clean `organizations` records with high-confidence location data.

**Inconsistent** (<50% agreement on city or state): 5 entities
→ Multi-location firms (e.g., national property managers). Store the most common value,
  accept it may be wrong. Or store only `name` and leave location blank.

---

## Top 30 Entities by Mention Count (with Consistency)

| Entity | Mentions | City (top) | City % | State (top) | State % | Website % |
|---|---|---|---|---|---|---|
| Greystar Management | 450 | Charleston | 100% | SC | 100% | 100% |
| KeyCorp Real Estate Capital Markets | 341 | Dallas | 100% | TX | 100% | 100% |
| CWCapital Asset Management | 263 | Bethesda | 100% | MD | 100% | 100% |
| Asset Living | 205 | Houston | 100% | TX | 100% | 100% |
| WinnResidential | 169 | Boston | 100% | MA | 100% | 100% |
| Michaels Organization, The | 159 | Camden | 100% | NJ | 100% | 100% |
| FPI Management | 154 | Folsom | 100% | CA | 100% | 100% |
| Freddie Mac | 137 | McLean | 100% | VA | 100% | 100% |
| Wells Fargo | 122 | Birmingham | 100% | MI | 100% | 100% |
| New York City Housing Authority | 121 | New York | 100% | NY | 100% | 51% |
| Mercy Housing | 91 | Denver | 57% | CO | 57% | 100% |
| John Stewart Company, The | 86 | San Francisco | 100% | CA | 100% | 100% |
| Related Companies | 85 | New York | 100% | NY | 100% | 100% |
| Avenue5 Residential | 85 | Seattle | 100% | WA | 100% | 100% |
| Community Builders, The | 84 | Boston | 98% | MA | 98% | 100% |
| AMC | 83 | Salt Lake City | 100% | UT | 100% | 100% |
| Dominium | 79 | Plymouth | 100% | MN | 100% | 100% |
| Weidner Apartment Homes | 79 | Kirkland | 100% | WA | 100% | 100% |
| Cushman & Wakefield | 73 | Chicago | 100% | IL | 100% | 100% |
| Pennrose Properties | 70 | Philadelphia | 100% | PA | 100% | 100% |
| Scion Group, The | 70 | Chicago | 100% | IL | 100% | 100% |
| LivCor | 69 | Chicago | 100% | IL | 100% | 100% |
| ConAm Management | 69 | San Diego | 100% | CA | 100% | 100% |
| NRP Group | 68 | Cleveland | 57% | OH | 57% | 100% |
| National Church Residences | 68 | Columbus | 100% | OH | 100% | 100% |
| RPM Living | 62 | Austin | 100% | TX | 100% | 100% |
| Willow Bridge | 60 | Lake Mary | 47% | FL | 47% | 100% |
| McCormack Baron Salazar | 59 | St. Louis | 100% | MO | 100% | 100% |
| Capital Realty Group | 58 | Spring Valley | 100% | NY | 100% | 100% |
| Woda Cooper Companies | 58 | Columbus | 100% | OH | 100% | 100% |

---

## Most Inconsistent Entities (Spread Across Many Locations)

These are likely national/multi-city firms. Storing location data for them will be unreliable.

| Entity | Mentions | City Consistency | State Consistency |
|---|---|---|---|
| Willow Bridge | 60 | 47% | 47% |
| Highmark Residential | 45 | 27% | 47% |
| Mission Rock Residential | 24 | 38% | 38% |
| Invesco Real Estate | 5 | 40% | 80% |
| Cypress Management | 4 | 25% | 50% |

---

## Import Recommendations for `organizations`

1. **Skip these fake entity strings** (use the list above as the import script exclusion set).
2. **Exact name dedup**: `INSERT INTO organizations (name, ...) ON CONFLICT (name) DO NOTHING`
   — but `organizations` does NOT yet have a UNIQUE constraint on `name`.
   **Schema addition needed**: `UNIQUE(name)` on `organizations.name` (or handle in script).
3. **For location data**: Store the most common city/state/website for each entity,
   regardless of consistency. It's directional, not authoritative.
4. **Inconsistent entities** (national firms) will have location data that's at best
   their HQ city. That's fine — the data isn't trying to be a firm directory.
