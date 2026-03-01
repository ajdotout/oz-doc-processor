"""
audit_family_office_for_crm_import.py

Comprehensive analysis of the Family Office Club CSV against:
  1. The existing QOZB data already in the CRM (via Supabase queries)
  2. Its own internal structure for import planning

Produces a report covering:
  - Column completeness (fill rates)
  - Overlap with existing DB: shared phones, shared emails, shared org names
  - Internal deduplication: LinkedIn URL dupes, name+firm dupes
  - Mapping to the new CRM schema
  - Recommendations for the import script

Usage:
  uv run contact_merge_scripts/audit_family_office_for_crm_import.py
  uv run contact_merge_scripts/audit_family_office_for_crm_import.py --db   # also check DB overlaps

Environment variables (only needed with --db):
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
"""

import os
import re
import sys
import argparse
from collections import defaultdict, Counter

import pandas as pd
from dotenv import load_dotenv

CSV_PATH = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists/USA_Family_Office_Consolidated.csv"

def clean_str(val):
    if pd.isna(val): return None
    s = str(val).strip()
    return s if s and s.lower() != 'nan' else None

def normalize_phone(val):
    s = clean_str(val)
    if not s: return None
    s = s.split('.')[0].strip()
    digits = re.sub(r'\D', '', s)
    return digits if len(digits) >= 7 else None

def normalize_email(val):
    s = clean_str(val)
    if not s or '@' not in s: return None
    return s.lower().strip()

def normalize_linkedin(val):
    s = clean_str(val)
    if not s: return None
    # Normalize to just the path portion
    s = s.strip().rstrip('/')
    # Remove query params
    s = s.split('?')[0]
    return s.lower()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', action='store_true', help='Check overlaps against Supabase DB')
    args = parser.parse_args()

    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig', low_memory=False)
    total = len(df)

    # ─── Column Completeness ───────────────────────────────────────────────────
    cols_to_check = {
        'Firm Name':                         'firm_name',
        'Contact First Name':                'first_name',
        'Contact Last Name':                 'last_name',
        'Contact Title/Position':            'title',
        'Phone Number':                      'phone',
        'Personal Email Address':            'personal_email',
        'Company Email Address':             'company_email',
        'Company Street Address':            'address',
        'City':                              'city',
        'State/ Province':                   'state',
        'Postal/Zip Code':                   'zip',
        'Country':                           'country',
        'Alma Mater':                        'alma_mater',
        'LinkedIn Profile':                  'linkedin',
        "Company's Areas of Investments/Interest": 'investment_prefs',
        'Year Founded':                      'year_founded',
        'AUM':                               'aum',
        'Secondary Email':                   'secondary_email',
        'Website':                           'website',
        'About Company':                     'about',
        'Category':                          'category',
    }

    fill_rates = {}
    for csv_col, label in cols_to_check.items():
        if csv_col in df.columns:
            filled = df[csv_col].apply(lambda v: clean_str(v) is not None).sum()
            fill_rates[label] = (filled, filled / total * 100)
        else:
            fill_rates[label] = (0, 0)

    # ─── Extract all contact identifiers ───────────────────────────────────────
    all_phones       = set()
    all_personal_emails = set()
    all_company_emails  = set()
    all_secondary_emails= set()
    all_linkedins    = set()
    all_firm_names   = set()

    # Per-row data for dedup analysis
    person_records = []

    for _, row in df.iterrows():
        phone = normalize_phone(row.get('Phone Number'))
        personal_email = normalize_email(row.get('Personal Email Address'))
        company_email  = normalize_email(row.get('Company Email Address'))
        secondary_email= normalize_email(row.get('Secondary Email'))
        linkedin       = normalize_linkedin(row.get('LinkedIn Profile'))
        firm_name      = clean_str(row.get('Firm Name'))
        first_name     = clean_str(row.get('Contact First Name'))
        last_name      = clean_str(row.get('Contact Last Name'))
        title          = clean_str(row.get('Contact Title/Position'))
        category       = clean_str(row.get('Category'))

        if phone:            all_phones.add(phone)
        if personal_email:   all_personal_emails.add(personal_email)
        if company_email:    all_company_emails.add(company_email)
        if secondary_email:  all_secondary_emails.add(secondary_email)
        if linkedin:         all_linkedins.add(linkedin)
        if firm_name:        all_firm_names.add(firm_name)

        person_records.append({
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'personal_email': personal_email,
            'company_email': company_email,
            'secondary_email': secondary_email,
            'linkedin': linkedin,
            'firm_name': firm_name,
            'title': title,
            'category': category,
        })

    all_emails = all_personal_emails | all_company_emails | all_secondary_emails

    # ─── Internal Dedup: LinkedIn URLs ────────────────────────────────────────
    linkedin_counter = Counter()
    for r in person_records:
        if r['linkedin']:
            linkedin_counter[r['linkedin']] += 1
    dup_linkedins = {url: cnt for url, cnt in linkedin_counter.items() if cnt > 1}

    # ─── Internal Dedup: (first, last, firm) ──────────────────────────────────
    name_firm_counter = Counter()
    for r in person_records:
        if r['first_name'] and r['last_name'] and r['firm_name']:
            key = (r['first_name'].lower(), r['last_name'].lower(), r['firm_name'].lower())
            name_firm_counter[key] += 1
    dup_name_firm = {k: v for k, v in name_firm_counter.items() if v > 1}

    # ─── Category distribution ────────────────────────────────────────────────
    categories = Counter(r['category'] for r in person_records if r['category'])

    # ─── DB Overlap Check ─────────────────────────────────────────────────────
    db_overlap = None
    if args.db:
        load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        if not url or not key:
            print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required with --db")
            sys.exit(1)
        from supabase import create_client
        sb = create_client(url, key)

        # Fetch all existing phones
        db_phones = set()
        offset = 0
        while True:
            resp = sb.table('phones').select('number').range(offset, offset + 999).execute()
            if not resp.data: break
            for r in resp.data: db_phones.add(r['number'])
            if len(resp.data) < 1000: break
            offset += 1000

        # Fetch all existing emails
        db_emails = set()
        offset = 0
        while True:
            resp = sb.table('emails').select('address').range(offset, offset + 999).execute()
            if not resp.data: break
            for r in resp.data: db_emails.add(r['address'])
            if len(resp.data) < 1000: break
            offset += 1000

        # Fetch all existing org names
        db_orgs = set()
        offset = 0
        while True:
            resp = sb.table('organizations').select('name').range(offset, offset + 999).execute()
            if not resp.data: break
            for r in resp.data: db_orgs.add(r['name'])
            if len(resp.data) < 1000: break
            offset += 1000

        # Fetch all existing LinkedIn URLs
        db_linkedins = set()
        offset = 0
        while True:
            resp = sb.table('linkedin_profiles').select('url').range(offset, offset + 999).execute()
            if not resp.data: break
            for r in resp.data: db_linkedins.add(r['url'])
            if len(resp.data) < 1000: break
            offset += 1000

        shared_phones    = all_phones & db_phones
        shared_emails    = all_emails & db_emails
        shared_orgs      = all_firm_names & db_orgs
        shared_linkedins = all_linkedins & db_linkedins

        db_overlap = {
            'db_phones': len(db_phones),
            'db_emails': len(db_emails),
            'db_orgs':   len(db_orgs),
            'db_linkedins': len(db_linkedins),
            'shared_phones': shared_phones,
            'shared_emails': shared_emails,
            'shared_orgs': shared_orgs,
            'shared_linkedins': shared_linkedins,
        }

    # ─── Build Report ─────────────────────────────────────────────────────────
    md = f"""# Family Office CSV → CRM Import Analysis

**Source**: `USA_Family_Office_Consolidated.csv`
**Total Rows**: {total:,}
**DB overlap check**: {'Yes' if args.db else 'Not run (use --db flag)'}

---

## 1. Column Completeness

| Field | Filled | Fill Rate |
|---|---|---|
"""
    for label, (filled, pct) in fill_rates.items():
        md += f"| {label} | {filled:,} | {pct:.1f}% |\n"

    md += f"""
---

## 2. Unique Identifiers Summary

| Identifier | Unique Count | Notes |
|---|---|---|
| Firm names | {len(all_firm_names):,} | → `organizations` table |
| Phones | {len(all_phones):,} | → `phones` table |
| Personal emails | {len(all_personal_emails):,} | → `emails` table (label='personal') |
| Company emails | {len(all_company_emails):,} | → `organizations.company_email` (firm-level) |
| Secondary emails | {len(all_secondary_emails):,} | → `emails` table (label='secondary') |
| **All unique emails** | **{len(all_emails):,}** | union of all email columns |
| LinkedIn profiles | {len(all_linkedins):,} | → `linkedin_profiles` table |

---

## 3. Internal Deduplication

### Duplicate LinkedIn URLs
**{len(dup_linkedins)} LinkedIn URLs** appear on multiple rows (same URL used by different contacts, or true dupes).

"""
    if dup_linkedins:
        md += "| LinkedIn URL | Times Used |\n|---|---|\n"
        for url, cnt in sorted(dup_linkedins.items(), key=lambda x: x[1], reverse=True)[:15]:
            md += f"| {url[:80]}... | {cnt} |\n"

    md += f"""
### Duplicate (First, Last, Firm) Combos
**{len(dup_name_firm)} name+firm combos** appear more than once (exact same person listed twice).

"""
    if dup_name_firm:
        md += "| First | Last | Firm | Times |\n|---|---|---|---|\n"
        for (f, l, firm), cnt in sorted(dup_name_firm.items(), key=lambda x: x[1], reverse=True)[:15]:
            md += f"| {f} | {l} | {firm[:40]} | {cnt} |\n"

    md += f"""
---

## 4. Category Distribution

The `Category` column classifies the family office type.

| Category | Count |
|---|---|
"""
    for cat, cnt in categories.most_common():
        md += f"| {cat} | {cnt:,} |\n"

    if db_overlap:
        md += f"""
---

## 5. Overlap with Existing CRM (QOZB Data)

Data already in the database from the QOZB import:
- **{db_overlap['db_phones']:,}** phones
- **{db_overlap['db_emails']:,}** emails
- **{db_overlap['db_orgs']:,}** organizations
- **{db_overlap['db_linkedins']:,}** LinkedIn profiles

### Shared Identifiers (Family Office CSV ∩ Existing DB)

| Identifier | FO CSV | In DB Already | **Shared** | Net New |
|---|---|---|---|---|
| Phones | {len(all_phones):,} | {db_overlap['db_phones']:,} | **{len(db_overlap['shared_phones']):,}** | {len(all_phones) - len(db_overlap['shared_phones']):,} |
| Emails (all) | {len(all_emails):,} | {db_overlap['db_emails']:,} | **{len(db_overlap['shared_emails']):,}** | {len(all_emails) - len(db_overlap['shared_emails']):,} |
| Org names | {len(all_firm_names):,} | {db_overlap['db_orgs']:,} | **{len(db_overlap['shared_orgs']):,}** | {len(all_firm_names) - len(db_overlap['shared_orgs']):,} |
| LinkedIn | {len(all_linkedins):,} | {db_overlap['db_linkedins']:,} | **{len(db_overlap['shared_linkedins']):,}** | {len(all_linkedins) - len(db_overlap['shared_linkedins']):,} |

"""
        if db_overlap['shared_phones']:
            md += "### Sample Shared Phones (Family Office contacts already in DB)\n\n"
            md += "| Phone |\n|---|\n"
            for p in list(db_overlap['shared_phones'])[:10]:
                md += f"| {p} |\n"

        if db_overlap['shared_orgs']:
            md += "\n### Sample Shared Organization Names\n\n"
            md += "| Organization |\n|---|\n"
            for o in sorted(list(db_overlap['shared_orgs']))[:20]:
                md += f"| {o} |\n"

        if db_overlap['shared_emails']:
            md += f"\n### Shared Emails: {len(db_overlap['shared_emails'])} matches\n\n"
            md += "| Email |\n|---|\n"
            for e in list(db_overlap['shared_emails'])[:10]:
                md += f"| {e} |\n"

    md += f"""
---

## 6. Schema Mapping: Family Office CSV → CRM Tables

### Row Decomposition

Each CSV row maps to:

```
CSV Row → {{
  organizations (firm_name → name, company_email, address, city, state, zip,
                 website, category → org.category,
                 details JSONB: {{ aum, year_founded, investment_prefs, about }})
                 org_type = 'family_office'

  people (first_name, last_name,
          tags = ['family_office'], lead_status = 'new',
          details JSONB: {{ alma_mater }})

  person_organizations (person_id, org_id, title = Contact Title/Position)

  phones (Phone Number → normalized) + person_phones

  emails:
    Personal Email → emails + person_emails (label='personal')
    Secondary Email → emails + person_emails (label='secondary')
    Company Email  → organizations.company_email (firm-level, NOT person_emails)

  linkedin_profiles (LinkedIn Profile → url, profile_name from CSV name)
    + person_linkedin
}}
```

### Dedup Keys for Import

- **People**: LinkedIn URL is the primary dedup key (per existing analysis — 76 dup URLs).
  If no LinkedIn, fall back to (personal_email) then (phone + name).
- **Organizations**: Exact firm name match (same as QOZB strategy).
- **Phones/Emails**: Structural UNIQUE constraints handle dedup.

### What's NEW vs. QOZB Import

| Entity | New for Family Office | Already Existed |
|---|---|---|
| `linkedin_profiles` | ✅ First time populating | Empty table from QOZB |
| `person_linkedin` | ✅ First time | Empty |
| `organizations.category` | 'SF' / 'MF' values | QOZB had no category |
| `organizations.details` | aum, year_founded, etc. | QOZB had no business details |
| `people.tags` | `['family_office']` | QOZB used `['qozb_property_contact']` |
| Personal emails | ✅ Many | QOZB had very few emails |
| Company emails | Goes to org level | QOZB had no company emails |

### Tags / Classification Strategy

**No schema change needed.** Using `people.tags TEXT[]`:
- Family Office contacts: `tags = ['family_office']`
- If a person already exists (matched by phone/email/linkedin): just append `'family_office'` to their existing tags
- Query: `WHERE 'family_office' = ANY(tags)`

For organization-level classification:
- `organizations.org_type = 'family_office'` (distinct from QOZB's `'qozb_entity'`)
- `organizations.category = 'SF'` or `'MF'` (single-family vs multi-family)
- Business details (AUM, investment preferences, about) → `organizations.details` JSONB

Both `org_type` and `category` columns already exist in the schema. No new columns needed.
"""

    # Write report
    output_path = os.path.join(os.path.dirname(__file__), "family_office_crm_import_analysis.md")
    with open(output_path, 'w') as f:
        f.write(md)
    print(f"Written: {output_path}")


if __name__ == '__main__':
    main()
