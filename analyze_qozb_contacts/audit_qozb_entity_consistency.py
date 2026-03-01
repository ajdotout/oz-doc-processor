"""
audit_qozb_entity_consistency.py

For entity names that appear across multiple properties (potential `organizations` records),
how consistent are their associated address, city, state, zip, website fields?

Consistent data → we can build a reliable `organizations` record.
Inconsistent data → store only the most common value, or leave fields blank.

Also: categorize entity strings that are clearly not real organizations
(e.g., "Owner Managed", "N/A", etc.) so we can special-case them in the import script.
"""
import pandas as pd
import os
from collections import defaultdict, Counter

CSV_PATH = "/Users/aryanjain/Documents/OZL/UsefulDocs/QOZB-Contacts/All QOZB Development Projects USA - 20260126.xlsx - Results.csv"

ROLE_ENTITY_COLS = {
    "Owner": {
        "entity":  "Owner",
        "address": "Owner Address",
        "city":    "Owner City",
        "state":   "Owner State",
        "zip":     "Owner ZIP",
        "country": "Owner Country",
        "website": "Owner Website",
    },
    "Manager": {
        "entity":  "Manager",
        "address": "Manager Address",
        "city":    "Manager City",
        "state":   "Manager State",
        "zip":     "Manager ZIP",
        "country": "Manager Country",
        "website": "Manager Website",
    },
    "Trustee": {
        "entity":  "Trustee",
        "address": "Trustee Address",
        "city":    "Trustee City",
        "state":   "Trustee State",
        "zip":     "Trustee ZIP",
        "country": "Trustee Country",
        "website": "Trustee Website",
    },
    "Special Servicer": {
        "entity":  "Special Servicer",
        "address": "Special Servicer Address",
        "city":    "Special Servicer City",
        "state":   "Special Servicer State",
        "zip":     "Special Servicer ZIP",
        "country": "Special Servicer Country",
        "website": "Special Servicer Website",
    },
}

# Strings that are clearly NOT real organizations — skip creating an org record
FAKE_ENTITIES = {
    "owner managed", "owner-managed", "self managed", "self-managed",
    "n/a", "na", "none", "unknown", "tbd", "pending", "not available",
    "", "nan",
}

def clean(val):
    if pd.isna(val): return None
    s = str(val).strip()
    return s if s and s.lower() not in FAKE_ENTITIES else None

def main():
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig', low_memory=False)
    total = len(df)

    # entity_name → {field: Counter of values seen}
    entity_data = defaultdict(lambda: defaultdict(Counter))
    entity_mention_count = Counter()
    fake_entity_counts   = Counter()

    for role, cols in ROLE_ENTITY_COLS.items():
        for _, row in df.iterrows():
            raw_entity = str(row.get(cols["entity"], '')).strip()
            if not raw_entity or raw_entity.lower() in FAKE_ENTITIES or raw_entity.lower() == 'nan':
                fake_entity_counts[raw_entity.lower()] += 1
                continue

            entity_mention_count[raw_entity] += 1

            for field in ["address", "city", "state", "zip", "website"]:
                col = cols.get(field)
                if col and col in df.columns:
                    val = clean(row.get(col))
                    if val:
                        entity_data[raw_entity][field][val] += 1

    # Entities that appear multiple times: analyze consistency
    multi_mention = {e: cnt for e, cnt in entity_mention_count.items() if cnt >= 3}

    # For each multi-mention entity, compute consistency score
    # Consistency = (most common value count) / total mentions for that field
    consistent_entities   = []  # >80% agreement on city+state
    inconsistent_entities = []  # <50% on any key field

    for entity, cnt in sorted(multi_mention.items(), key=lambda x: x[1], reverse=True):
        fields = entity_data[entity]
        city_top = fields["city"].most_common(1)
        state_top = fields["state"].most_common(1)
        city_pct  = city_top[0][1]/cnt*100  if city_top  else 0
        state_pct = state_top[0][1]/cnt*100 if state_top else 0
        website_top = fields["website"].most_common(1)
        website_pct = website_top[0][1]/cnt*100 if website_top else 0

        row_data = {
            "entity": entity,
            "mentions": cnt,
            "city": city_top[0][0] if city_top else None,
            "city_pct": city_pct,
            "state": state_top[0][0] if state_top else None,
            "state_pct": state_pct,
            "website": website_top[0][0] if website_top else None,
            "website_pct": website_pct,
        }

        if city_pct >= 80 and state_pct >= 80:
            consistent_entities.append(row_data)
        elif city_pct < 50 or state_pct < 50:
            inconsistent_entities.append(row_data)

    # Total unique real entities vs fake
    total_unique_real = len(entity_mention_count)
    total_fake        = sum(fake_entity_counts.values())

    md = f"""# QOZB Entity (Organization) Consistency Report

**Dataset**: {total:,} property rows × 4 roles = {total*4:,} entity slots

---

## Overview

| Metric | Count |
|---|---|
| Total entity slots | {total*4:,} |
| Fake / placeholder entity strings | {total_fake:,} |
| Real entity names (total) | {sum(entity_mention_count.values()):,} |
| **Unique real entity names** | {total_unique_real:,} |
| Entities appearing ≥3 times | {len(multi_mention):,} |

These {total_unique_real:,} unique real entity names will become `organizations` records
(exact name dedup only — "Greystar" and "Greystar Management" stay as separate records).

---

## Fake / Placeholder Entity Strings (Skip List)

These strings must be excluded from `organizations` import:

| String | Occurrences |
|---|---|
"""
    for s, count in fake_entity_counts.most_common(20):
        if count > 0:
            md += f"| `{s}` | {count:,} |\n"

    md += f"""
---

## Address Data Consistency (Entities Appearing ≥3 Times)

For the **{len(multi_mention):,}** entities seen 3+ times, we measure how consistent
their city/state/website fields are across all their property appearances.

**Consistent** (≥80% agreement on city+state): {len(consistent_entities):,} entities
→ Will produce clean `organizations` records with high-confidence location data.

**Inconsistent** (<50% agreement on city or state): {len(inconsistent_entities):,} entities
→ Multi-location firms (e.g., national property managers). Store the most common value,
  accept it may be wrong. Or store only `name` and leave location blank.

---

## Top 30 Entities by Mention Count (with Consistency)

| Entity | Mentions | City (top) | City % | State (top) | State % | Website % |
|---|---|---|---|---|---|---|
"""
    top_multi = sorted(multi_mention.items(), key=lambda x: x[1], reverse=True)[:30]
    for entity, cnt in top_multi:
        fields = entity_data[entity]
        city_top    = fields["city"].most_common(1)
        state_top   = fields["state"].most_common(1)
        website_top = fields["website"].most_common(1)
        city_val    = city_top[0][0]    if city_top    else "—"
        city_pct    = city_top[0][1]/cnt*100    if city_top    else 0
        state_val   = state_top[0][0]   if state_top   else "—"
        state_pct   = state_top[0][1]/cnt*100   if state_top   else 0
        web_pct     = website_top[0][1]/cnt*100 if website_top else 0
        md += f"| {entity[:40]} | {cnt} | {city_val[:20]} | {city_pct:.0f}% | {state_val} | {state_pct:.0f}% | {web_pct:.0f}% |\n"

    md += f"""
---

## Most Inconsistent Entities (Spread Across Many Locations)

These are likely national/multi-city firms. Storing location data for them will be unreliable.

| Entity | Mentions | City Consistency | State Consistency |
|---|---|---|---|
"""
    for r in sorted(inconsistent_entities, key=lambda x: x["mentions"], reverse=True)[:20]:
        md += f"| {r['entity'][:40]} | {r['mentions']} | {r['city_pct']:.0f}% | {r['state_pct']:.0f}% |\n"

    md += f"""
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
"""

    out = os.path.join(os.path.dirname(__file__), "entity_consistency_report.md")
    with open(out, "w") as f:
        f.write(md)
    print(f"Written: {out}")

if __name__ == "__main__":
    main()
