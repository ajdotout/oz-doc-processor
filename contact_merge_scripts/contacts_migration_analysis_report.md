# Contacts → CRM Migration Analysis
**Source**: Live `contacts` table (32,584 rows)
**Target**: New CRM schema (people, emails, phones, organizations + junctions)

## Migration Impact Summary

| Action | Count | Notes |
|--------|------:|-------|
| **People to ENRICH** (email match) | 727 | Existing person gets new tags, lead_status, org links |
| **People to CREATE** (new email) | 31,857 | New person + email entity + junctions |
| Emails to create | 31,857 | |
| Emails already existing | 727 | |
| Phones to create | 2,048 | |
| Phones already existing | 1,629 | |
| Organizations to create | 6,333 | |
| Organizations to link (existing) | 6,431 | Exact name match |
| Bounce status to set | 2,630 | emails.status = 'bounced' |
| Suppression status to set | 272 | emails.status = 'suppressed' |
| user_id links to set | 210 | |

## Post-Migration Totals (estimated)

| Entity | Current | + New | = Total |
|--------|--------:|------:|--------:|
| People | 16,604 | 31,857 | ~48,461 |
| Emails | 4,056 | 31,857 | ~35,913 |
| Phones | 26,438 | 2,048 | ~28,486 |
| Organizations | 13,046 | 6,333 | ~19,379 |

## Source Distribution

| Source | Count |
|--------|------:|
| DEVELOPERS.xlsx | 7,974 |
| US INVESTMENT BANKING FIRMS.xlsx | 3,004 |
| GLOBAL FAMILY OFFICES.xlsx | 2,557 |
| pension_funds.xlsx | 2,462 |
| ozl_sdb.csv | 2,356 |
| real_estate_firms.xlsx | 1,790 |
| NON-BANK LENDERS & INTERMEDIARIES.xlsx | 1,750 |
| OZL-Chris-n8n-leads.csv | 1,488 |
| REAL ESTATE INVESTMENT FIRMS.xlsx | 1,356 |
| oz_development_list.xlsx | 1,315 |
| INDUSTRIAL INVESTORS.xlsx | 1,223 |
| TRIPLE NET LEASE INVESTORS.xlsx | 1,157 |
| GLOBAL MULTI-FAMILY OFFICE.xlsx | 1,094 |
| OFFICE INVESTORS.xlsx | 711 |
| HOTEL, HOSPITALITY INVESTORS.xlsx | 706 |
| RETAIL INVESTORS.xlsx | 355 |
| MIXED-USE INVESTORS.xlsx | 341 |
| opportunity-funds-listing | 141 |
| webinar_eventbritewebinars | 130 |
| MEDICAL INVESTORS.xlsx | 119 |
| EXP Multifamily database 3-11-2024.xlsx | 99 |
| authenticated_user | 94 |
| website_signup | 58 |
| webinar_legal101 | 52 |
| SELF-STORAGE INVESTORS.xlsx | 47 |
| webinar_recap | 40 |
| DEVELOPMENT,  REDEVELOPMENT FIRMS.xlsx | 38 |
| webinar_ozunlocked | 35 |
| eventbrite_opportunity_zone_marketing_-_for_sponsors_raising_capital_[webinar] | 27 |
| webinar_familyoffices | 23 |
| eventbrite_oz_listings_"office_hours"_-_q&a_with_opportunity_zone_experts | 17 |
| eventbrite_exclusive_opportunity_zone_investments_in_ma_[accredited_investors_only] | 15 |
| webinar_taxcliff | 10 |

## Contact Types Distribution

| Type | Count |
|------|------:|
| investor | 23,314 |
| developer | 10,857 |
| fund | 152 |

## Lead Status Distribution

| Status | Count |
|--------|------:|
| (none) | 32,046 |
| warm | 538 |
