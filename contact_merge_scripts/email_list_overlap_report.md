# Email List Overlap Audit
**Total unique emails across all outreach lists**: 32,761
**QOZB unique emails**: 920
**Family Office unique emails**: 3,676  (personal: 2,700, company: 561, secondary: 443)
**Combined new-schema emails**: 4,596

## Overall Overlap Summary
| Metric | Count | % of Outreach |
|--------|------:|:--------------:|
| Total outreach emails | 32,761 | 100% |
| Overlap with QOZB | 263 | 0.8% |
| Overlap with Family Office | 493 | 1.5% |
| Overlap with either (QOZB ∪ FO) | 756 | 2.3% |
| **Unique to outreach only** | **32,005** | **97.7%** |

## Per-List Overlap Breakdown
| List | Unique Emails | ∩ QOZB | ∩ FO | ∩ Either | Only in This List |
|------|-------------:|-------:|-----:|---------:|------------------:|
| InvestorsData (Oct 2025, cleaned) | 20,011 | 29 | 465 | 494 | 19,517 |
| Investor List (Jan 2026) | 23,253 | 43 | 478 | 521 | 22,732 |
| Developers (short) | 9,970 | 234 | 16 | 250 | 9,720 |
| Developers Rows (extended) | 9,893 | 215 | 16 | 231 | 9,662 |
| Funds | 201 | 3 | 1 | 4 | 197 |
| CapMatch Funds | 150 | 3 | 1 | 4 | 146 |
| GHL Chris Dump | 4,653 | 0 | 354 | 354 | 4,299 |
| n8n Extracted | 1,488 | 0 | 8 | 8 | 1,480 |
| n8n Leads | 3,782 | 0 | 161 | 161 | 3,621 |
| Overlapping Contacts | 1,699 | 14 | 5 | 19 | 1,680 |
| Warm Contacts (merged) | 414 | 2 | 2 | 4 | 410 |
| EventBrite Webinars | 148 | 0 | 2 | 2 | 146 |

## Cross-List Duplication
| # of Lists Containing Email | # of Emails |
|:---------------------------:|------------:|
| 1 | 1,643 |
| 2 | 23,423 |
| 3 | 3,650 |
| 4 | 4,016 |
| 5 | 15 |
| 6 | 14 |

## Sample Overlapping Emails (first 20)
These emails exist in both outreach lists AND QOZB/Family Office data:

| Email | In QOZB? | In FO? | Outreach Lists |
|-------|:--------:|:------:|----------------|
| a.johnson@adifo.net | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026), GHL Chris Dump |
| a.kesete@akdevmke.com | ✅ | — | Developers (short), Developers Rows (extended) |
| aagarwal@whitelotusgroup.com | ✅ | — | Developers (short) |
| aaron.cozart@navoak.com | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026), GHL Chris Dump |
| aaron@bywaterdevelopment.com | ✅ | — | Developers (short), Developers Rows (extended) |
| abe@legacyknight.com | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026), GHL Chris Dump |
| abismonte@raviniagroup.com | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026) |
| abudinoff@cattrail.com | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026), GHL Chris Dump, n8n Leads |
| acolvin@crnstn.com | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026), GHL Chris Dump |
| adam@civiccompanies.com | ✅ | — | Developers (short), Developers Rows (extended) |
| adam@commonground.net | ✅ | — | Developers (short) |
| adam@horowitzgroup.com | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026), GHL Chris Dump, n8n Leads |
| adosen@gardnercapital.com | ✅ | — | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026) |
| afishman@fairmountproperties.com | ✅ | — | Developers (short), Developers Rows (extended) |
| afletcher@maxusprop.com | ✅ | — | Developers (short), Developers Rows (extended) |
| afocapital@gmail.com | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026), GHL Chris Dump, n8n Leads |
| afried@thekfund.com | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026), GHL Chris Dump |
| agerrits@hildredpartners.com | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026), GHL Chris Dump, n8n Leads |
| aglomski@agassetadvisory.com | — | ✅ | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026), GHL Chris Dump, n8n Leads |
| ahancock@raintreepartners.com | ✅ | — | InvestorsData (Oct 2025, cleaned), Investor List (Jan 2026) |

## Migration Impact Summary

After importing the email lists into the new CRM schema:

- **756 emails** will match existing `people` records (from QOZB/FO imports).
  These people will be **enriched** (tags, lead_status, organization links added) — NOT duplicated.

- **32,005 emails** are unique to the outreach lists.
  These will create **new `people` records** + `emails` entities + junctions.

- **32,761 total unique emails** → will produce at most **32,005 new people** 
  (assuming perfect dedup; actual count depends on name variations across lists).
