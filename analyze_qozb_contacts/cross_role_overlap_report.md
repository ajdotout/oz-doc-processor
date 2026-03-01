# QOZB Cross-Role Overlap Analysis

**Dataset**: 21,287 property rows
**Dedup implication**: If the same phone OR name appears in multiple role columns on the same row,
that should be ONE `people` record with multiple `person_properties` entries (different roles),
NOT two separate people.

---

## Phone Overlap (Same Phone in Multiple Role Columns, Same Property)

**Rows with at least one phone shared across roles**: 6,919 (32.5%)

### Which Role Pairs Share Phones Most?

| Role Pair | # of Properties |
|---|---|
| Manager + Owner | 6,917 |
| Manager + Trustee | 1 |
| Manager + Owner + Trustee | 1 |

### Examples

- **760 Broadway**: phone `5185123693` → roles: ['Owner', 'Manager']
- **Arcade Building, The**: phone `5185123693` → roles: ['Owner', 'Manager']
- **Gallery on Holland, The**: phone `5187867100` → roles: ['Owner', 'Manager']
- **Industrie**: phone `5182505732` → roles: ['Owner', 'Manager']
- **Park South**: phone `5188626600` → roles: ['Owner', 'Manager']

---

## Name Overlap (Same Full Name in Multiple Role Columns, Same Property)

**Rows with at least one name shared across roles**: 2,605 (12.2%)

### Which Role Pairs Share Names Most?

| Role Pair | # of Properties |
|---|---|
| Manager + Owner | 2,604 |
| Owner + Trustee | 1 |

### Examples

- **760 Broadway**: name `david sarraf` → roles: ['Owner', 'Manager']
- **Arcade Building, The**: name `david sarraf` → roles: ['Owner', 'Manager']
- **Gallery on Holland, The**: name `toby milde` → roles: ['Owner', 'Manager']
- **Industrie**: name `seth rosenblum` → roles: ['Owner', 'Manager']
- **Schuyler**: name `asaf elkayam` → roles: ['Owner', 'Manager']

---

## Import Script Implication

For rows where the same phone appears across multiple roles:
- Create **one** `people` record (deduped on phone + name)
- Create **multiple** `person_properties` entries (one per role)
- The `phones` row is shared; `person_phones` has one entry pointing to it

Scale of this: **6,919 properties** (32.5%) will collapse
at least one role-pair into a single person, saving duplicate records.
