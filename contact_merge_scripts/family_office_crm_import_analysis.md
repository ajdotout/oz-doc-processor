# Family Office CSV → CRM Import Analysis

**Source**: `USA_Family_Office_Consolidated.csv`
**Total Rows**: 2,864
**DB overlap check**: Yes

---

## 1. Column Completeness

| Field | Filled | Fill Rate |
|---|---|---|
| firm_name | 2,834 | 99.0% |
| first_name | 2,857 | 99.8% |
| last_name | 2,856 | 99.7% |
| title | 2,855 | 99.7% |
| phone | 2,527 | 88.2% |
| personal_email | 2,764 | 96.5% |
| company_email | 1,512 | 52.8% |
| address | 2,739 | 95.6% |
| city | 2,859 | 99.8% |
| state | 2,863 | 100.0% |
| zip | 2,773 | 96.8% |
| country | 2,864 | 100.0% |
| alma_mater | 2,186 | 76.3% |
| linkedin | 2,549 | 89.0% |
| investment_prefs | 2,245 | 78.4% |
| year_founded | 2,400 | 83.8% |
| aum | 1,135 | 39.6% |
| secondary_email | 479 | 16.7% |
| website | 2,627 | 91.7% |
| about | 2,863 | 100.0% |
| category | 2,759 | 96.3% |

---

## 2. Unique Identifiers Summary

| Identifier | Unique Count | Notes |
|---|---|---|
| Firm names | 1,202 | → `organizations` table |
| Phones | 1,530 | → `phones` table |
| Personal emails | 2,700 | → `emails` table (label='personal') |
| Company emails | 561 | → `organizations.company_email` (firm-level) |
| Secondary emails | 444 | → `emails` table (label='secondary') |
| **All unique emails** | **3,680** | union of all email columns |
| LinkedIn profiles | 2,470 | → `linkedin_profiles` table |

---

## 3. Internal Deduplication

### Duplicate LinkedIn URLs
**76 LinkedIn URLs** appear on multiple rows (same URL used by different contacts, or true dupes).

| LinkedIn URL | Times Used |
|---|---|
| https://www.linkedin.com/in/erikaverill... | 3 |
| https://www.linkedin.com/in/kurtleedy... | 3 |
| https://www.linkedin.com/in/brandonaverill... | 3 |
| https://www.linkedin.com/in/the-private-office-of-anderson-family-investments-aa... | 2 |
| https://www.linkedin.com/in/ledawalker... | 2 |
| https://www.linkedin.com/in/robert-robby-mcconchie-cpa-pfs-cka-2a60a23... | 2 |
| https://www.linkedin.com/in/stephen-collins-442a732b... | 2 |
| https://www.linkedin.com/in/greggorybrant... | 2 |
| https://www.linkedin.com/in/justin-berman-b55a453a... | 2 |
| https://www.linkedin.com/in/deborah-debbie-bingham-6b293062... | 2 |
| https://www.linkedin.com/in/michael-bingham-a939556... | 2 |
| https://www.linkedin.com/in/scott-calhoun-cfp-cpa-pfs-cima-cws-0913a47... | 2 |
| https://www.linkedin.com/in/skip-perkins-18b6266... | 2 |
| https://www.linkedin.com/in/ashley-dennig... | 2 |
| https://www.linkedin.com/in/eva-chen-6113ab41... | 2 |

### Duplicate (First, Last, Firm) Combos
**39 name+firm combos** appear more than once (exact same person listed twice).

| First | Last | Firm | Times |
|---|---|---|---|
| kurt | leedy | miramar holdings, lp | 3 |
| leda | walker | arthur m. blank family office, llc | 2 |
| erik | averill | awm capital | 2 |
| robert | mcconchie | awm capital | 2 |
| stephen | collins | ballast point capital, llc | 2 |
| drew | mcmorrow | ballentine partners, llc | 2 |
| deborah | bingham | blue diamond capital, llc | 2 |
| michael | bingham | blue diamond capital, llc | 2 |
| ashley | dennig | broad family office | 2 |
| eva | chen | broad family office | 2 |
| barney | corning | cove capital corp. | 2 |
| heidi | goodin | envision company | 2 |
| ron | inman | envision company | 2 |
| evan | roskos | f/b/o services, inc. | 2 |
| joanne | nolt | f/b/o services, inc. | 2 |

---

## 4. Category Distribution

The `Category` column classifies the family office type.

| Category | Count |
|---|---|
| MF | 1,519 |
| SF | 1,240 |

---

## 5. Overlap with Existing CRM (QOZB Data)

Data already in the database from the QOZB import:
- **24,918** phones
- **920** emails
- **11,848** organizations
- **0** LinkedIn profiles

### Shared Identifiers (Family Office CSV ∩ Existing DB)

| Identifier | FO CSV | In DB Already | **Shared** | Net New |
|---|---|---|---|---|
| Phones | 1,530 | 24,918 | **10** | 1,520 |
| Emails (all) | 3,680 | 920 | **0** | 3,680 |
| Org names | 1,202 | 11,848 | **4** | 1,198 |
| LinkedIn | 2,470 | 0 | **0** | 2,470 |

### Sample Shared Phones (Family Office contacts already in DB)

| Phone |
|---|
| 8178703117 |
| 2164470070 |
| 2038831944 |
| 6177903900 |
| 3039893900 |
| 7189775666 |
| 3129200500 |
| 3235566600 |
| 3102033800 |
| 9013468800 |

### Sample Shared Organization Names

| Organization |
|---|
| Beitel Group |
| Belpointe |
| Dakota Pacific |
| Kemmons Wilson Companies |

---

## 6. Schema Mapping: Family Office CSV → CRM Tables

### Row Decomposition

Each CSV row maps to:

```
CSV Row → {
  organizations (firm_name → name, company_email, address, city, state, zip,
                 website, category → org.category,
                 details JSONB: { aum, year_founded, investment_prefs, about })
                 org_type = 'family_office'

  people (first_name, last_name,
          tags = ['family_office'], lead_status = 'new',
          details JSONB: { alma_mater })

  person_organizations (person_id, org_id, title = Contact Title/Position)

  phones (Phone Number → normalized) + person_phones

  emails:
    Personal Email → emails + person_emails (label='personal')
    Secondary Email → emails + person_emails (label='secondary')
    Company Email  → organizations.company_email (firm-level, NOT person_emails)

  linkedin_profiles (LinkedIn Profile → url, profile_name from CSV name)
    + person_linkedin
}
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
