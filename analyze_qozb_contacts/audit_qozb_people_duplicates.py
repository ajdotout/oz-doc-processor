"""
audit_qozb_people_duplicates.py

Given that phone number is our person dedup key:
  - Same phone + same name  → 1 person, multiple person_properties rows
  - Same phone + diff name  → different people, same phones row (junction)
  - No phone                → always new person (phone is not the only path)

This script answers:
  1. How many unique (phone, normalized_name) pairs exist? → upper bound on `people` records
  2. For phones that appear under multiple names: how many names per phone? (shared phone situation)
  3. Name collision distribution: how often does the same full name appear with DIFFERENT phones?
     (John Smith problem)
  4. How many people-slots have no phone at all? → will create person record without phone dedup
"""
import pandas as pd
import os
from collections import defaultdict

CSV_PATH = "/Users/aryanjain/Documents/OZL/UsefulDocs/QOZB-Contacts/All QOZB Development Projects USA - 20260126.xlsx - Results.csv"

ROLE_COLS = [
    ("Owner",           "Owner Contact First Name",          "Owner Contact Last Name",          "Owner Contact Phone Number"),
    ("Manager",         "Manager Contact First Name",        "Manager Contact Last Name",        "Manager Contact Phone Number"),
    ("Trustee",         "Trustee Contact First Name",        "Trustee Contact Last Name",        "Trustee Contact Phone Number"),
    ("Special Servicer","Special Servicer Contact First Name","Special Servicer Contact Last Name","Special Servicer Contact Phone Number"),
]

def clean_phone(val):
    if pd.isna(val): return None
    s = str(val).strip().split('.')[0].strip()
    digits = ''.join(c for c in s if c.isdigit())
    return digits if len(digits) >= 7 else None

def clean_name(first, last):
    f = str(first).strip() if not pd.isna(first) else ''
    l = str(last).strip() if not pd.isna(last) else ''
    if f.lower() == 'nan': f = ''
    if l.lower() == 'nan': l = ''
    full = (f + ' ' + l).strip()
    return full.lower() if full else None

def main():
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig', low_memory=False)
    total = len(df)

    # phone → set of normalized names
    phone_to_names = defaultdict(set)
    # normalized_name → set of phones
    name_to_phones = defaultdict(set)

    no_phone_with_name = 0
    no_phone_no_name   = 0
    total_slots        = 0
    person_slots       = 0  # has at least a name

    # Collect all (phone, name) pairs
    for role, col_first, col_last, col_phone in ROLE_COLS:
        for _, row in df.iterrows():
            phone = clean_phone(row.get(col_phone))
            name  = clean_name(row.get(col_first), row.get(col_last))
            total_slots += 1

            if not name:
                no_phone_no_name += 1
                continue

            person_slots += 1

            if phone:
                phone_to_names[phone].add(name)
                name_to_phones[name].add(phone)
            else:
                no_phone_with_name += 1

    # Unique (phone, name) pairs → how many people records will be created (phone-deduped)
    unique_phone_name_pairs = set()
    for phone, names in phone_to_names.items():
        for name in names:
            unique_phone_name_pairs.add((phone, name))

    # People without phone: each unique name+no-phone → separate person
    # But since we can't merge them (no phone key), they each become a person
    names_without_phone = name_to_phones.keys() - {
        name for _, names in phone_to_names.items() for name in names
    }
    # Actually count differently: names that have NO phone associated
    # Walk again
    names_with_phone_only = set()
    names_with_no_phone   = set()
    for name, phones in name_to_phones.items():
        if phones:
            names_with_phone_only.add(name)
        else:
            names_with_no_phone.add(name)

    # Phones with multiple names: shared phone scenario
    phones_multi_name = {p: names for p, names in phone_to_names.items() if len(names) > 1}
    phones_single_name = {p: names for p, names in phone_to_names.items() if len(names) == 1}

    # Names with multiple phones: same person, different phones??
    names_multi_phone = {n: phones for n, phones in name_to_phones.items() if len(phones) > 1}

    # Distribution: how many names per phone
    names_per_phone_dist = defaultdict(int)
    for p, names in phone_to_names.items():
        names_per_phone_dist[len(names)] += 1

    # Distribution: how many times does the same full name appear (collision rate)
    name_appearance_count = defaultdict(int)
    for role, col_first, col_last, col_phone in ROLE_COLS:
        for _, row in df.iterrows():
            name = clean_name(row.get(col_first), row.get(col_last))
            if name:
                name_appearance_count[name] += 1

    collision_dist = defaultdict(int)
    for name, count in name_appearance_count.items():
        collision_dist[count] += 1

    # Top names by appearance count
    top_names = sorted(name_appearance_count.items(), key=lambda x: x[1], reverse=True)[:20]

    # Top phones by # distinct names attached
    top_shared_phones = sorted(phones_multi_name.items(), key=lambda x: len(x[1]), reverse=True)[:15]

    md = f"""# QOZB People Deduplication Analysis

**Deduplication strategy**: Phone number is the primary person dedup key.
- Same phone + same name → 1 `people` record, multiple `person_properties`
- Same phone + different name → different `people` records, both linked to same `phones` row
- No phone → create `people` record anyway (no phone-based merge possible)

**Dataset**: {total:,} property rows × 4 roles = {total_slots:,} total contact slots

---

## High-Level People Record Estimates

| Metric | Count |
|---|---|
| Total contact slots | {total_slots:,} |
| Slots with at least a name (will create person) | {person_slots:,} |
| Named slots WITH a phone | {person_slots - no_phone_with_name:,} |
| Named slots WITHOUT a phone | {no_phone_with_name:,} |
| Slots with no name at all (skip or phone-only) | {no_phone_no_name:,} |
| Unique phones in dataset | {len(phone_to_names):,} |
| Unique (phone, name) pairs | {len(unique_phone_name_pairs):,} |
| Unique names that have any phone | {len(names_with_phone_only):,} |

**Estimated `people` records post-dedup** (upper bound):
- `{len(unique_phone_name_pairs):,}` from phone-keyed dedup
- Plus nameless slots that end up as phone/property-only entries

---

## Phone Sharing: Multiple Names Per Phone

{len(phones_multi_name):,} phones are shared across **multiple distinct named people**.
{len(phones_single_name):,} phones have exactly one name attached.

### Distribution: Names Per Phone

| Names sharing a phone | # of phones |
|---|---|
"""
    for count in sorted(names_per_phone_dist.keys()):
        md += f"| {count} | {names_per_phone_dist[count]:,} |\n"

    md += f"""
### Top 15 Most-Shared Phones (Most Names Attached)

| Phone | # Distinct Names | Sample Names |
|---|---|---|
"""
    for phone, names in top_shared_phones:
        sample = ', '.join(list(names)[:4])
        md += f"| {phone} | {len(names)} | {sample} |\n"

    md += f"""
---

## Name Collisions: Same Full Name, Different Phones

{len(names_multi_phone):,} distinct names appear with **multiple different phone numbers**.
This means the same name (e.g., "john smith") has appeared on rows with different phone numbers —
these each become separate `people` records (different phone = different person, per our dedup rule).

### Distribution: How Often Does Each Full Name Appear?

| Times name appears in dataset | # of unique names |
|---|---|
"""
    for count in sorted(collision_dist.keys())[:20]:
        md += f"| {count}x | {collision_dist[count]:,} |\n"

    md += f"""
### Top 20 Most Common Names (High Collision Risk)

These names appear most frequently. Each is a candidate for being one person (same phone → merged)
or many people (different phones → separate records).

| Name | Total Appearances | Distinct Phones |
|---|---|---|
"""
    for name, count in top_names:
        phones = name_to_phones.get(name, set())
        md += f"| {name} | {count} | {len(phones)} |\n"

    md += f"""
---

## Key Takeaways for Import Script

1. **Phone is a reliable dedup key**: If the same name appears N times but always with the same phone,
   those collapse to 1 `people` record with N `person_properties` entries.

2. **Shared phones are structural, not a problem**: {len(phones_multi_name):,} phones link to multiple
   people — this is exactly what the `person_phones` junction table handles.

3. **{no_phone_with_name:,} named contacts have no phone** — these will each create their own `people` record
   (no dedup possible). They won't be in the calling queue but will be in the CRM.

4. **{no_phone_no_name:,} slots are completely nameless** — handled via `property_phones` junction table,
   not as `people` records.
"""

    out = os.path.join(os.path.dirname(__file__), "people_duplicates_report.md")
    with open(out, "w") as f:
        f.write(md)
    print(f"Written: {out}")

if __name__ == "__main__":
    main()
