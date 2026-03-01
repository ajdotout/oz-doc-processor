# USA Family Office Consolidated CSV Data Analysis & Investigations

This document summarizes the tests and investigations performed on the `USA_Family_Office_Consolidated.csv` dataset to inform our data modeling and import strategy for the LinkedIn Outreach feature.

## 1. Company Email Consistency (`check_company_email.py`)
**Goal:** Determine if `company_email` should reside at the contact level (`family_office_contacts`) or the firm level (`family_office_firms`).
**Method:** Grouped the data by `Firm Name` and checked if contacts within the same firm used different company emails.
**Results:**
- Out of 367 firms containing multiple contacts with valid emails, 362 (98.6%) shared the exact same company email across all contacts.
- Only 5 firms had conflicting emails (typically variations like `info@` vs an individual's email, or `directinvestments@` vs `realestate@`).
**Conclusion:** It is highly viable and optimal to store `company_email` at the `family_office_firms` level to normalize the data. For the 5 conflicts, the import script can simply select the mode (most frequent) or use a generic fallback.

## 2. Fuzzy Duplicate Firm Name Detection (`find_fuzzy_duplicate_firms.py`)
**Goal:** Identify firms that appear multiple times under slightly varied names.
**Method:** Stripped corporate suffixes (LLC, Inc, Capital, Group, etc.) and punctuation to extract "naked" base names.
**Results:**
- Found 16 potential duplicate groups.
- Discovered true duplicates (e.g., `Legacy Wealth Advisors` vs `Legacy Wealth Advisors, LLC`; `Pathstone` vs `Pathstone Family Office, LLC`).
- Identified false positives/overlapping entities (e.g., `Acadia Family Office` [MD] vs `Acadia Management Co. Inc.` [MA]).
**Conclusion:** Blind regex-based deduplication is risky due to false positives. To prevent merging unrelated firms, more robust strategies would be required (e.g., matching Domain + Cleaned Name), or we can simply treat exact `Firm Name` strings as distinct firms for simplicity.

## 3. Contact Overlap Across Duplicate Firms (`check_duplicate_contacts.py`)
**Goal:** Determine if these "fuzzy duplicate" firms contained the exact same list of individuals.
**Method:** Grouped by the fuzzy base name and compared the contact lists for each original firm spelling.
**Results:**
- The duplicate firm listings contained completely different individuals (e.g., Matthew at `Pathstone Family Office, LLC` and John at `Pathstone`).
**Conclusion:** Because they hold different people, merging them into a single `firm_id` would allow our 14-day rotational logic to space out outreach flawlessly. However, as these are generic LinkedIn outreach requests, relying on exact firm name matches as distinct firms is an acceptable tradeoff for a simpler import script.

## 4. Duplicate Individual & LinkedIn URL Analysis (`check_duplicate_linkedin.py`)
**Goal:** Verify if every row in the CSV represents a completely unique individual with a unique LinkedIn profile.
**Method:** Checked for duplicates across the `LinkedIn Profile` column and `(First Name + Last Name + Firm Name)` combinations.
**Results:**
- Found 76 instances of duplicate LinkedIn URLs.
  - Example: Individuals like 'Erik Averill' appear multiple times across variations of his firm name.
  - Example: Generic company LinkedIn pages were used for multiple people instead of personal profiles (e.g., `Kevin Gerson` and `Ford Austin` both sharing the generic `.../in/the-private-office-of-anderson-family-investments...` LinkedIn URL).
- Found 39 instances of exact duplicate `First Name` + `Last Name` + `Firm Name` combinations.
**Conclusion:** The CSV undeniably contains duplicate individuals and overlapping generic LinkedIn URLs. The data import process MUST deduplicate contacts at the `linkedin_url` level to prevent messaging the same person (or a generic company page) multiple times under the guise of different rows.
