# Orphan Property Phones Analysis

Based on the [Consolidated CRM Planning Doc](oz-dev-dash/docs/consolidated-crm-planning.md), we need to analyze how to handle property-level phone numbers during migration.

**Dataset**: QOZB Development Projects CSV
**Total Properties (Rows)**: 21287

## Questions & Answers

**1. How many rows have a property-level `Phone Number` that does NOT match any Owner/Manager/Trustee Contact Phone Number?**
- Answer: **15097** rows

**2. Of those orphan phones, how many have at least one entity name (Owner/Manager/Trustee company)?**
- Answer: **15085** rows (These can potentially be linked to an Organization)

**3. Of those orphans, how many have NO entity at all?**
- Answer: **12** rows (These might require a synthetic person or organization, or might just remain unlinked data)

---

### Sample Orphans
- **Property**: 20 Park Residences
  - Property Phone: 5184340726
  - Contact Phones Present: ['7184932866']
  - Has Entity Context: True

- **Property**: 930 on Broadway
  - Property Phone: 5187279786
  - Contact Phones Present: ['5183444543', '7818994002']
  - Has Entity Context: True

- **Property**: Abraxas at 90 State
  - Property Phone: 5186212177
  - Contact Phones Present: ['7038341900', '5184633281']
  - Has Entity Context: True

- **Property**: Gallery on Holland, The
  - Property Phone: 5188070127
  - Contact Phones Present: ['5187867100']
  - Has Entity Context: True

- **Property**: Industrie
  - Property Phone: 5189003780
  - Contact Phones Present: ['5182505732']
  - Has Entity Context: True

