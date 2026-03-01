"""
audit_qozb_contact_completeness.py

For each of the 4 roles (Owner, Manager, Trustee, Special Servicer),
report the fill rate (% of rows with a value) for each contact column.

This tells us exactly:
  - How many real person-records we'll create (have at least a first name)
  - How many are phone-only (no name, but still actionable as property_phones)
  - How many slots are completely empty
"""
import pandas as pd
import os

CSV_PATH = "/Users/aryanjain/Documents/OZL/UsefulDocs/QOZB-Contacts/All QOZB Development Projects USA - 20260126.xlsx - Results.csv"

ROLES = {
    "Owner": {
        "entity":     "Owner",
        "first_name": "Owner Contact First Name",
        "last_name":  "Owner Contact Last Name",
        "email":      "Owner Contact Email",        # Only Owner has email
        "phone":      "Owner Contact Phone Number",
        "address":    "Owner Address",
        "website":    "Owner Website",
    },
    "Manager": {
        "entity":     "Manager",
        "first_name": "Manager Contact First Name",
        "last_name":  "Manager Contact Last Name",
        "email":      None,
        "phone":      "Manager Contact Phone Number",
        "address":    "Manager Address",
        "website":    "Manager Website",
    },
    "Trustee": {
        "entity":     "Trustee",
        "first_name": "Trustee Contact First Name",
        "last_name":  "Trustee Contact Last Name",
        "email":      None,
        "phone":      "Trustee Contact Phone Number",
        "address":    "Trustee Address",
        "website":    "Trustee Website",
    },
    "Special Servicer": {
        "entity":              "Special Servicer",
        "first_name":          "Special Servicer Contact First Name",
        "last_name":           "Special Servicer Contact Last Name",
        "email":               None,
        "phone":               "Special Servicer Contact Phone Number",
        "address":             "Special Servicer Address",
        "website":             "Special Servicer Website",
    },
}

def is_present(val):
    if pd.isna(val):
        return False
    s = str(val).strip()
    return s != '' and s.lower() != 'nan'

def main():
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig', low_memory=False)
    total = len(df)

    md = f"""# QOZB Contact Column Completeness Report

**Dataset**: QOZB Development Projects CSV
**Total Property Rows**: {total:,}

This report shows fill rates for each contact column per role, and classifies
rows into actionability tiers:
- **Full person**: has First Name (can create a `people` record)
- **Phone-only**: has phone but no first name (→ `property_phones`, no `people` record)
- **Entity-only**: has entity name but no phone and no first name (→ `organizations` record only)
- **Empty**: no entity, no phone, no name (slot is completely blank)

---

"""

    summary_rows = []

    for role, cols in ROLES.items():
        col_entity = cols["entity"]
        col_first  = cols["first_name"]
        col_last   = cols["last_name"]
        col_email  = cols["email"]
        col_phone  = cols["phone"]
        col_addr   = cols["address"]
        col_website= cols["website"]

        has_entity  = df[col_entity].apply(is_present)  if col_entity  in df.columns else pd.Series([False]*total)
        has_first   = df[col_first].apply(is_present)   if col_first   in df.columns else pd.Series([False]*total)
        has_last    = df[col_last].apply(is_present)    if col_last    in df.columns else pd.Series([False]*total)
        has_phone   = df[col_phone].apply(is_present)   if col_phone   in df.columns else pd.Series([False]*total)
        has_addr    = df[col_addr].apply(is_present)    if col_addr    in df.columns else pd.Series([False]*total)
        has_website = df[col_website].apply(is_present) if col_website in df.columns else pd.Series([False]*total)

        # Email only for Owner
        if col_email and col_email in df.columns:
            has_email = df[col_email].apply(is_present)
        else:
            has_email = pd.Series([False]*total)

        # Tiers
        full_person   = has_first.sum()
        phone_only    = (~has_first & has_phone).sum()
        entity_only   = (~has_first & ~has_phone & has_entity).sum()
        empty_slot    = (~has_first & ~has_phone & ~has_entity).sum()

        pct = lambda n: f"{n:,} ({n/total*100:.1f}%)"

        md += f"## {role}\n\n"
        md += f"| Field | Rows with Value | Fill Rate |\n"
        md += f"|---|---|---|\n"
        md += f"| **Entity / Company name** | {has_entity.sum():,} | {has_entity.mean()*100:.1f}% |\n"
        md += f"| **First Name** | {has_first.sum():,} | {has_first.mean()*100:.1f}% |\n"
        md += f"| **Last Name** | {has_last.sum():,} | {has_last.mean()*100:.1f}% |\n"
        md += f"| **Phone** | {has_phone.sum():,} | {has_phone.mean()*100:.1f}% |\n"
        if col_email:
            md += f"| **Email** | {has_email.sum():,} | {has_email.mean()*100:.1f}% |\n"
        md += f"| **Address** | {has_addr.sum():,} | {has_addr.mean()*100:.1f}% |\n"
        md += f"| **Website** | {has_website.sum():,} | {has_website.mean()*100:.1f}% |\n"

        md += f"\n### Actionability Tiers\n\n"
        md += f"| Tier | Count | % of rows | Action |\n"
        md += f"|---|---|---|---|\n"
        md += f"| **Full person** (has First Name) | {pct(full_person)} | Create `people` record |\n"
        md += f"| **Phone-only** (phone, no name) | {pct(phone_only)} | Create `property_phones` entry |\n"
        md += f"| **Entity-only** (company, no phone, no name) | {pct(entity_only)} | Create `organizations` only |\n"
        md += f"| **Empty slot** | {pct(empty_slot)} | Skip |\n"
        md += "\n---\n\n"

        summary_rows.append((role, full_person, phone_only, entity_only, empty_slot))

    md += "## Summary Across All Roles\n\n"
    md += "| Role | Full People | Phone-Only | Entity-Only | Empty |\n"
    md += "|---|---|---|---|---|\n"
    total_people = total_phone_only = total_entity_only = total_empty = 0
    for role, fp, po, eo, em in summary_rows:
        md += f"| {role} | {fp:,} | {po:,} | {eo:,} | {em:,} |\n"
        total_people    += fp
        total_phone_only+= po
        total_entity_only+=eo
        total_empty     += em
    md += f"| **Total** | **{total_people:,}** | **{total_phone_only:,}** | **{total_entity_only:,}** | **{total_empty:,}** |\n"

    md += f"""
> Note: totals are per-role-slot counts, not unique people. The same person can
> appear across multiple roles on different properties.
> Maximum possible `people` records = {total_people:,} (before deduplication by phone number).
"""

    out = os.path.join(os.path.dirname(__file__), "contact_completeness_report.md")
    with open(out, "w") as f:
        f.write(md)
    print(f"Written: {out}")

if __name__ == "__main__":
    main()
