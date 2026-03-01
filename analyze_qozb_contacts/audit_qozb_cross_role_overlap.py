"""
audit_qozb_cross_role_overlap.py

On a single property row, does the same phone number appear in >1 role column?
E.g., Owner Contact Phone == Manager Contact Phone

This indicates one physical person holds two roles on the same property.
In the new schema: 1 people record, 2 person_properties entries (role='owner' + role='manager').

Also checks: does the same (first, last) name appear across multiple roles on the same row?
"""
import pandas as pd
import os
from collections import defaultdict

CSV_PATH = "/Users/aryanjain/Documents/OZL/UsefulDocs/QOZB-Contacts/All QOZB Development Projects USA - 20260126.xlsx - Results.csv"

ROLE_PHONE_COLS = {
    "Owner":            "Owner Contact Phone Number",
    "Manager":          "Manager Contact Phone Number",
    "Trustee":          "Trustee Contact Phone Number",
    "Special Servicer": "Special Servicer Contact Phone Number",
}
ROLE_NAME_COLS = {
    "Owner":            ("Owner Contact First Name",           "Owner Contact Last Name"),
    "Manager":          ("Manager Contact First Name",         "Manager Contact Last Name"),
    "Trustee":          ("Trustee Contact First Name",         "Trustee Contact Last Name"),
    "Special Servicer": ("Special Servicer Contact First Name","Special Servicer Contact Last Name"),
}

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

    # Per-row: find roles that share a phone or share a name
    rows_with_phone_overlap = 0
    rows_with_name_overlap  = 0
    phone_overlap_examples  = []
    name_overlap_examples   = []

    # Count by role-pair
    phone_pair_counts = defaultdict(int)
    name_pair_counts  = defaultdict(int)

    roles = list(ROLE_PHONE_COLS.keys())

    for idx, row in df.iterrows():
        # Build phone → roles mapping for this row
        phone_roles = defaultdict(list)
        for role, col in ROLE_PHONE_COLS.items():
            p = clean_phone(row.get(col))
            if p:
                phone_roles[p].append(role)

        # Build name → roles mapping for this row
        name_roles = defaultdict(list)
        for role, (col_f, col_l) in ROLE_NAME_COLS.items():
            n = clean_name(row.get(col_f), row.get(col_l))
            if n:
                name_roles[n].append(role)

        # Check for overlaps
        row_has_phone_overlap = False
        for phone, overlapping_roles in phone_roles.items():
            if len(overlapping_roles) > 1:
                row_has_phone_overlap = True
                pair_key = tuple(sorted(overlapping_roles))
                phone_pair_counts[pair_key] += 1
                if len(phone_overlap_examples) < 5:
                    prop_name = str(row.get('Property Name', f'Row {idx}'))
                    phone_overlap_examples.append({
                        'property': prop_name,
                        'phone': phone,
                        'roles': overlapping_roles,
                    })

        row_has_name_overlap = False
        for name, overlapping_roles in name_roles.items():
            if len(overlapping_roles) > 1:
                row_has_name_overlap = True
                pair_key = tuple(sorted(overlapping_roles))
                name_pair_counts[pair_key] += 1
                if len(name_overlap_examples) < 5:
                    prop_name = str(row.get('Property Name', f'Row {idx}'))
                    name_overlap_examples.append({
                        'property': prop_name,
                        'name': name,
                        'roles': overlapping_roles,
                    })

        if row_has_phone_overlap:
            rows_with_phone_overlap += 1
        if row_has_name_overlap:
            rows_with_name_overlap += 1

    md = f"""# QOZB Cross-Role Overlap Analysis

**Dataset**: {total:,} property rows
**Dedup implication**: If the same phone OR name appears in multiple role columns on the same row,
that should be ONE `people` record with multiple `person_properties` entries (different roles),
NOT two separate people.

---

## Phone Overlap (Same Phone in Multiple Role Columns, Same Property)

**Rows with at least one phone shared across roles**: {rows_with_phone_overlap:,} ({rows_with_phone_overlap/total*100:.1f}%)

### Which Role Pairs Share Phones Most?

| Role Pair | # of Properties |
|---|---|
"""
    for pair, count in sorted(phone_pair_counts.items(), key=lambda x: x[1], reverse=True):
        md += f"| {' + '.join(pair)} | {count:,} |\n"

    md += "\n### Examples\n\n"
    for ex in phone_overlap_examples:
        md += f"- **{ex['property']}**: phone `{ex['phone']}` → roles: {ex['roles']}\n"

    md += f"""
---

## Name Overlap (Same Full Name in Multiple Role Columns, Same Property)

**Rows with at least one name shared across roles**: {rows_with_name_overlap:,} ({rows_with_name_overlap/total*100:.1f}%)

### Which Role Pairs Share Names Most?

| Role Pair | # of Properties |
|---|---|
"""
    for pair, count in sorted(name_pair_counts.items(), key=lambda x: x[1], reverse=True):
        md += f"| {' + '.join(pair)} | {count:,} |\n"

    md += "\n### Examples\n\n"
    for ex in name_overlap_examples:
        md += f"- **{ex['property']}**: name `{ex['name']}` → roles: {ex['roles']}\n"

    md += f"""
---

## Import Script Implication

For rows where the same phone appears across multiple roles:
- Create **one** `people` record (deduped on phone + name)
- Create **multiple** `person_properties` entries (one per role)
- The `phones` row is shared; `person_phones` has one entry pointing to it

Scale of this: **{rows_with_phone_overlap:,} properties** ({rows_with_phone_overlap/total*100:.1f}%) will collapse
at least one role-pair into a single person, saving duplicate records.
"""

    out = os.path.join(os.path.dirname(__file__), "cross_role_overlap_report.md")
    with open(out, "w") as f:
        f.write(md)
    print(f"Written: {out}")

if __name__ == "__main__":
    main()
