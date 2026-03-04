---
name: listing-verify
description: Use this skill to verify if the generated JSON output accurately reflects the data from the source documents (PDFs, Excel, Markdown). The goal is to cross-check extracted metrics to ensure they represent the original files without hallucinations.
---

# Listing Document Verification Skill

This skill outlines the process for auditing and verifying the structured JSON data extracted from property listing documents in the `oz-doc-processor` repository. It is essential for ensuring that every data point presented is grounded in the source materials and free of AI hallucinations.

## Context

The processing pipeline (described in the `listing-doc-pipeline` skill) consists of:
1. **Extraction (Phase 1):** Raw documents (PDF, Excel) -> OCR/Parsing -> Consolidated Markdown (`<listing>_markdown.md`).
2. **Processing (Phase 2):** Consolidated Markdown -> AI Agents -> Final JSON (`<listing>_modular_listing_gemini3.json`).

The goal of this deep dive is to trace the flow backwards: `Final JSON` -> `Consolidated Markdown` -> `Raw Docs / temp OCR` to confirm exact correctness.

---

## 🔍 Verification Workflow

### Step 1: Locate the Listing Assets
Navigate to the specific listing directory inside `listing-docs/<ListingName>/` (e.g., `491-Baltic-Brooklyn-NY` or `Lakewire-Lakeland-FL`).

You will need to locate and reference:
1. **The Final Output:** `<listing_name>_modular_listing_gemini3.json`
2. **The Intermediate Source:** `<listing_name>_markdown.md`
3. **The Metadata/OCR Backup:** Files inside the `temp/` folder (e.g., `<doc_name>_ocr.json`) and any raw supplemental `.md` files in the listing root.

### Step 2: Establish the Verification Metrics
Review the final JSON output. Identify the critical metrics and narrative sections that need auditing. This typically includes:
- **Financials:** Target IRR, Equity Multiple, Cash on Cash, Cap Rate, Minimum Investment, Hold Period, Capital Stack.
- **Property Details:** Unit mix, square footage, year built/renovated, amenities.
- **Location:** Address, neighborhood descriptions, market metrics (population growth, median income).
- **Sponsor/Team:** Track record metrics, AUM, team member names and roles.
- **Deal Structure:** Investment type, project phase, timeline dates.

### Step 3: Backward Tracing (The Cross-Check)
For every single metric or factual claim found in the JSON:

1. **Locate the Information Source:**
   - Determine which source file the metric originated from (e.g., the original OM PDF, an Excel financial model, or the consolidated markdown). 
   - You may use a combination of tools (like `grep_search`, `view_file`, or running python scripts to extract/read data) to locate this origin context. It is not limited to simple text matching; semantic understanding or alternative verification methods are perfectly acceptable.

2. **Verify Context and Semantics:**
   - Ensure the metric in the source document has identical contextual meaning as the JSON field.
   - *Example:* Make sure `15.5%` isn't a historical return of the sponsor when the JSON claims it is the target IRR for *this* specific deal.

3. **Check for Hallucinations & Synthesis Errors:**
   - Did the AI invent a number because it looked "standard" (e.g., assuming a 10-year hold when the document says 5-7 years)?
   - Did the AI synthesize two conflicting numbers incorrectly? (e.g., Document A says 100 units, Document B says 105 units. The JSON should reflect the most authoritative source, or have noted the discrepancy implicitly via the pipeline).
   - Are names, emails, or URLs exact matches?

4. **Fallback to OCR/Source (If Needed):**
   - If the markdown text seems scrambled (a common OCR issue with complex tables), look inside the `temp/` folder at the raw OCR output or review the original PDF/Excel if possible, to confirm whether the error originated in Phase 1 (OCR) or Phase 2 (AI Processing).

### Step 4: Output the Verification Report
Create an artifact (e.g., `listing_verification_report.md`) detailing the cross-check using the following format structure:

```markdown
### [Section/Metric Category]

*   **[Metric Name]**
    *   **JSON Value:** `...`
    *   **Source Document:** `[e.g., Original-OM.pdf / consolidated markdown]`
    *   **Validation Method:** `[e.g., semantic search, exact match in JSON]`
    *   **Status:** ✅ Verified / ❌ Hallucinated / ⚠️ Needs Manual Review / ❓ Missing from Source
    *   **Notes:** (Explain any discrepancies, context mismatches, or calculation notes here).
```

---

## 🚨 Strict Rules for the Deep Dive

*   **No Assumptions:** If a metric is in the JSON but cannot be found ANYWHERE in the markdown or raw docs, it MUST be flagged as a ❌ Hallucination. Do not assume it is correct just because it is a plausible industry standard.
*   **Exact Math:** If the JSON contains a derived metric (e.g., `price_per_unit`), you must locate the raw numbers in the source (total price, total units) and re-calculate it to ensure the AI's math is correct.
*   **Formatting Nuances:** Watch out for unit mismatches (e.g., JSON says `$15M`, source says `15,000` under a header `in thousands`).
*   **Completeness:** A deep dive means checking *every* significant data point, not just a random sample, unless the user specifically asks for a targeted review.
*   **Multiple Source Resolution:** If multiple source files were combined into the consolidated markdown (e.g., an OM + a supplemental EmailInfo.md), note which file the truth was grounded in (the markdown indicates this with `SOURCE FILE:` headers).
