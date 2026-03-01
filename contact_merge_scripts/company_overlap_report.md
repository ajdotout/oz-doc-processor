# Company / Organization Overlap Audit
**Total unique outreach companies**: 9,659 (raw), 9,080 (normalized)
**QOZB entities**: 11,848
**Family Office firms**: 1,202
**Combined new-schema orgs**: 13,046 (raw), 12,851 (normalized)

## Overlap Summary
| Match Type | ∩ QOZB | ∩ FO | ∩ Either | Only Outreach |
|------------|-------:|-----:|---------:|--------------:|
| Exact match | 1,470 | 100 | 1,567 | 8,092 |
| Normalized match | 2,001 | 190 | 2,184 | 6,896 |

## Per-List Breakdown (Normalized Match)
| List | Companies | ∩ QOZB | ∩ FO | ∩ Either | New |
|------|----------:|-------:|-----:|---------:|----:|
| InvestorsData (Oct 2025) | 3,940 | 390 | 114 | 501 | 3,394 |
| Investor List (Jan 2026) | 4,826 | 442 | 126 | 565 | 4,196 |
| Developers (short) | 3,504 | 1,694 | 5 | 1,696 | 1,742 |
| Developers Rows (extended) | 3,473 | 1,504 | 6 | 1,507 | 1,907 |
| Funds | 237 | 3 | 0 | 3 | 234 |
| CapMatch Funds | 152 | 2 | 0 | 2 | 150 |
| GHL Chris Dump | 0 | 0 | 0 | 0 | 0 |
| n8n Extracted | 674 | 11 | 15 | 25 | 643 |
| n8n Leads | 2,027 | 51 | 111 | 158 | 1,845 |
| Overlapping Contacts | 481 | 138 | 1 | 139 | 339 |

## Sample Overlapping Companies (first 30)
| Outreach Name | Matched To | Source |
|---------------|------------|--------|
| 13th Floor Investments | 13th Floor Investments | QOZB |
| 1820 Ventures | 1820 Ventures | QOZB |
| 1911 Office | 1911 Office, LLC | Family Office |
| 1st Lake Properties | 1st Lake Properties | QOZB |
| 21 Alpha Group | 21 Alpha Group | QOZB |
| 29Th Street Capital | 29th Street Capital | QOZB |
| 2Life Communities | 2Life Communities | QOZB |
| 2m Companies | 2M Companies LLC | Family Office |
| 33 Realty Management | 33 Realty Management | QOZB |
| 3650 REIT | 3650 REIT | QOZB |
| 3H Group | 3H Group | QOZB |
| 3l Real Estate | 3L Real Estate | QOZB |
| 400 Monroe Associates | 400 Monroe Associates | QOZB |
| 4Creeks | 4Creeks | QOZB |
| 548 Development | 548 Development | QOZB |
| 8Th Street Investment Group | 8th Street Investment Group | QOZB |
| 908 Group | 908 Group | QOZB |
| A.F. Jonna Development | A.F. Jonna Development | QOZB |
| A.W. Perry | A.W. Perry | QOZB |
| A9 Family Office | A9 Family Office | Family Office |
| Aardex Real Estate Services | Aardex Real Estate Services | QOZB |
| Abacus Capital | Abacus Capital | QOZB |
| Abacus Capital Group | Abacus Capital Group | QOZB |
| Abbey Road Advisors | Abbey Road | QOZB |
| Abbhi Capital | Abbhi Capital | QOZB |
| Abby Development & Construction | Abby Development & Construction | QOZB |
| Abebe Ventures | Abebe Ventures | QOZB |
| Abunasra, Sami | Abunasra, Sami | QOZB |
| Acabay | Acabay | QOZB |
| ACACIA PARTNERS | Acacia Capital | QOZB |

## Migration Impact

- **2,184 companies** from outreach lists match existing organizations in the new schema.
  These will be **linked** to existing `organizations` records (not duplicated).

- **6,896 companies** are unique to outreach lists.
  These will create **new `organizations` records**.

- Total organizations after import: ~19,747 (normalized).
