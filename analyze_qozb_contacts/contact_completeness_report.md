# QOZB Contact Column Completeness Report

**Dataset**: QOZB Development Projects CSV
**Total Property Rows**: 21,287

This report shows fill rates for each contact column per role, and classifies
rows into actionability tiers:
- **Full person**: has First Name (can create a `people` record)
- **Phone-only**: has phone but no first name (→ `property_phones`, no `people` record)
- **Entity-only**: has entity name but no phone and no first name (→ `organizations` record only)
- **Empty**: no entity, no phone, no name (slot is completely blank)

---

## Owner

| Field | Rows with Value | Fill Rate |
|---|---|---|
| **Entity / Company name** | 21,273 | 99.9% |
| **First Name** | 21,273 | 99.9% |
| **Last Name** | 21,271 | 99.9% |
| **Phone** | 21,272 | 99.9% |
| **Email** | 2,638 | 12.4% |
| **Address** | 21,270 | 99.9% |
| **Website** | 17,079 | 80.2% |

### Actionability Tiers

| Tier | Count | % of rows | Action |
|---|---|---|---|
| **Full person** (has First Name) | 21,273 (99.9%) | Create `people` record |
| **Phone-only** (phone, no name) | 0 (0.0%) | Create `property_phones` entry |
| **Entity-only** (company, no phone, no name) | 0 (0.0%) | Create `organizations` only |
| **Empty slot** | 14 (0.1%) | Skip |

---

## Manager

| Field | Rows with Value | Fill Rate |
|---|---|---|
| **Entity / Company name** | 16,650 | 78.2% |
| **First Name** | 15,813 | 74.3% |
| **Last Name** | 15,814 | 74.3% |
| **Phone** | 15,814 | 74.3% |
| **Address** | 15,814 | 74.3% |
| **Website** | 14,679 | 69.0% |

### Actionability Tiers

| Tier | Count | % of rows | Action |
|---|---|---|---|
| **Full person** (has First Name) | 15,813 (74.3%) | Create `people` record |
| **Phone-only** (phone, no name) | 1 (0.0%) | Create `property_phones` entry |
| **Entity-only** (company, no phone, no name) | 836 (3.9%) | Create `organizations` only |
| **Empty slot** | 4,637 (21.8%) | Skip |

---

## Trustee

| Field | Rows with Value | Fill Rate |
|---|---|---|
| **Entity / Company name** | 6 | 0.0% |
| **First Name** | 6 | 0.0% |
| **Last Name** | 6 | 0.0% |
| **Phone** | 6 | 0.0% |
| **Address** | 6 | 0.0% |
| **Website** | 6 | 0.0% |

### Actionability Tiers

| Tier | Count | % of rows | Action |
|---|---|---|---|
| **Full person** (has First Name) | 6 (0.0%) | Create `people` record |
| **Phone-only** (phone, no name) | 0 (0.0%) | Create `property_phones` entry |
| **Entity-only** (company, no phone, no name) | 0 (0.0%) | Create `organizations` only |
| **Empty slot** | 21,281 (100.0%) | Skip |

---

## Special Servicer

| Field | Rows with Value | Fill Rate |
|---|---|---|
| **Entity / Company name** | 1,148 | 5.4% |
| **First Name** | 1,148 | 5.4% |
| **Last Name** | 1,148 | 5.4% |
| **Phone** | 1,148 | 5.4% |
| **Address** | 1,148 | 5.4% |
| **Website** | 1,101 | 5.2% |

### Actionability Tiers

| Tier | Count | % of rows | Action |
|---|---|---|---|
| **Full person** (has First Name) | 1,148 (5.4%) | Create `people` record |
| **Phone-only** (phone, no name) | 0 (0.0%) | Create `property_phones` entry |
| **Entity-only** (company, no phone, no name) | 0 (0.0%) | Create `organizations` only |
| **Empty slot** | 20,139 (94.6%) | Skip |

---

## Summary Across All Roles

| Role | Full People | Phone-Only | Entity-Only | Empty |
|---|---|---|---|---|
| Owner | 21,273 | 0 | 0 | 14 |
| Manager | 15,813 | 1 | 836 | 4,637 |
| Trustee | 6 | 0 | 0 | 21,281 |
| Special Servicer | 1,148 | 0 | 0 | 20,139 |
| **Total** | **38,240** | **1** | **836** | **46,071** |

> Note: totals are per-role-slot counts, not unique people. The same person can
> appear across multiple roles on different properties.
> Maximum possible `people` records = 38,240 (before deduplication by phone number).
