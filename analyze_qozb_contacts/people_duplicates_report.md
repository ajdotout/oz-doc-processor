# QOZB People Deduplication Analysis

**Deduplication strategy**: Phone number is the primary person dedup key.
- Same phone + same name → 1 `people` record, multiple `person_properties`
- Same phone + different name → different `people` records, both linked to same `phones` row
- No phone → create `people` record anyway (no phone-based merge possible)

**Dataset**: 21,287 property rows × 4 roles = 85,148 total contact slots

---

## High-Level People Record Estimates

| Metric | Count |
|---|---|
| Total contact slots | 85,148 |
| Slots with at least a name (will create person) | 38,241 |
| Named slots WITH a phone | 36,643 |
| Named slots WITHOUT a phone | 1,598 |
| Slots with no name at all (skip or phone-only) | 46,907 |
| Unique phones in dataset | 10,449 |
| Unique (phone, name) pairs | 12,241 |
| Unique names that have any phone | 12,003 |

**Estimated `people` records post-dedup** (upper bound):
- `12,241` from phone-keyed dedup
- Plus nameless slots that end up as phone/property-only entries

---

## Phone Sharing: Multiple Names Per Phone

1,717 phones are shared across **multiple distinct named people**.
8,732 phones have exactly one name attached.

### Distribution: Names Per Phone

| Names sharing a phone | # of phones |
|---|---|
| 1 | 8,732 |
| 2 | 1,655 |
| 3 | 52 |
| 4 | 7 |
| 5 | 3 |

### Top 15 Most-Shared Phones (Most Names Attached)

| Phone | # Distinct Names | Sample Names |
|---|---|---|
| 9094832444 | 5 | john seymour, daniel w. lorraine, jeffrey burum, tony mize |
| 2103524764 | 5 | olivia loudis, annalisa lavoie, melissa steed, nadia hepner |
| 2124007000 | 5 | patricia wadley, beverly johnson, claire sheedy, samantha conlan |
| 2406830300 | 4 | cindy martin, donald nuzzio jr., judy sarhan, debra new |
| 5173511544 | 4 | abigail diller, tammy patrick, traci rogers, steve van riper |
| 7632858808 | 4 | jamie luehrs, shane lafave, jessica correll, conyunn west |
| 3606947888 | 4 | jennifer pendersen, ryan trainor, clyde p. holland jr., sarah early |
| 7139744292 | 4 | sal thomas, rick wilson, todd witmer, anthony tarantino |
| 3176847305 | 4 | russ seiler, eric bryan, bobby bridge, bruce mills |
| 5126466700 | 4 | dally ward, matthew c. lutz, april royal, kelly scott |
| 9143473333 | 3 | debra reid, robert h. wilder jr., james r. wendling |
| 8059632884 | 3 | sara brown, michael r. schell, kimberly board |
| 2158878400 | 3 | john schonborn, jessica scully, james conway |
| 6177424500 | 3 | patrick m. appleby, terri benskin, tim mustacato |
| 4349774181 | 3 | steve houchens, dean wenger, diane caton |

---

## Name Collisions: Same Full Name, Different Phones

236 distinct names appear with **multiple different phone numbers**.
This means the same name (e.g., "john smith") has appeared on rows with different phone numbers —
these each become separate `people` records (different phone = different person, per our dedup rule).

### Distribution: How Often Does Each Full Name Appear?

| Times name appears in dataset | # of unique names |
|---|---|
| 1x | 7,094 |
| 2x | 2,693 |
| 3x | 926 |
| 4x | 733 |
| 5x | 352 |
| 6x | 301 |
| 7x | 174 |
| 8x | 144 |
| 9x | 103 |
| 10x | 104 |
| 11x | 73 |
| 12x | 60 |
| 13x | 42 |
| 14x | 42 |
| 15x | 37 |
| 16x | 26 |
| 17x | 25 |
| 18x | 21 |
| 19x | 11 |
| 20x | 15 |

### Top 20 Most Common Names (High Collision Risk)

These names appear most frequently. Each is a candidate for being one person (same phone → merged)
or many people (different phones → separate records).

| Name | Total Appearances | Distinct Phones |
|---|---|---|
| dan olsen | 341 | 1 |
| brian hanson | 263 | 1 |
| stephanie nascimento | 205 | 1 |
| david divine | 154 | 1 |
| david m. brickman | 137 | 1 |
| terri benskin | 129 | 1 |
| daniel e. bober | 122 | 1 |
| brandon rich | 97 | 1 |
| kevin sheehan | 97 | 1 |
| steve davis | 86 | 1 |
| kenneth p. wong | 85 | 1 |
| kimberlee schreiber | 82 | 1 |
| brenda barrett | 80 | 1 |
| steve mcelroy | 79 | 1 |
| michael flanagan | 77 | 1 |
| sherry freitas | 73 | 1 |
| bradley johnson | 71 | 1 |
| charlie adams | 70 | 2 |
| allina boohoff | 69 | 1 |
| gregory raap | 69 | 1 |

---

## Key Takeaways for Import Script

1. **Phone is a reliable dedup key**: If the same name appears N times but always with the same phone,
   those collapse to 1 `people` record with N `person_properties` entries.

2. **Shared phones are structural, not a problem**: 1,717 phones link to multiple
   people — this is exactly what the `person_phones` junction table handles.

3. **1,598 named contacts have no phone** — these will each create their own `people` record
   (no dedup possible). They won't be in the calling queue but will be in the CRM.

4. **46,907 slots are completely nameless** — handled via `property_phones` junction table,
   not as `people` records.
