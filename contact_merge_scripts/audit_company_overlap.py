"""
audit_company_overlap.py

Compares company/organization names across email outreach lists,
QOZB entity names, and Family Office firm names to determine
how many organizations already exist in the new CRM schema.

Uses normalized (lowercased, trimmed, stripped of common suffixes) names
for matching, plus exact-match counts.

Usage:
  uv run contact_merge_scripts/audit_company_overlap.py
"""

import os
import re
import pandas as pd
from collections import defaultdict

# ─── Paths ─────────────────────────────────────────────────────────────────────

OUTREACH_DIR = "/Users/aryanjain/Documents/OZL/UsefulDocs/Outreach-Lists"
WARM_DIR = os.path.join(OUTREACH_DIR, "WarmList")
QOZB_CSV = "/Users/aryanjain/Documents/OZL/UsefulDocs/QOZB-Contacts/All QOZB Development Projects USA - 20260126.xlsx - Results.csv"
FAMILY_OFFICE_CSV = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists/USA_Family_Office_Consolidated.csv"

# Outreach CSVs with company columns
OUTREACH_LISTS = [
    ("InvestorsData (Oct 2025)", os.path.join(OUTREACH_DIR, "InvestorsData-29-10-2025_cleaned.csv"), "company"),
    ("Investor List (Jan 2026)", os.path.join(OUTREACH_DIR, "Investor-List-1-9-26.csv"), "Company"),
    ("Developers (short)", os.path.join(OUTREACH_DIR, "developers.csv"), "Company"),
    ("Developers Rows (extended)", os.path.join(OUTREACH_DIR, "Developers Rows (1).csv"), "Company"),
    ("Funds", os.path.join(OUTREACH_DIR, "funds.csv"), "Company"),
    ("CapMatch Funds", os.path.join(OUTREACH_DIR, "CapMatch Funds Rows.csv"), "company"),
    ("GHL Chris Dump", os.path.join(OUTREACH_DIR, "GHL-Chris-Dec-Dump.csv"), "Company"),  # might not have it
    ("n8n Extracted", os.path.join(OUTREACH_DIR, "OZL-Chris-n8n-extracted.csv"), "company"),
    ("n8n Leads", os.path.join(OUTREACH_DIR, "OZL-Chris-n8n-leads.csv"), "company"),
    ("Overlapping Contacts", os.path.join(OUTREACH_DIR, "overlapping_contacts_with_header.csv"), "company"),
]

# Suffixes to strip for fuzzy normalization
SUFFIXES = [
    r",?\s*(llc|l\.l\.c\.|inc\.?|incorporated|corp\.?|corporation|ltd\.?|limited|lp|l\.p\.|co\.?|company|group|partners|partnership|holdings|management|capital|advisors?|enterprises?)\.?\s*$",
]


def clean_str(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "n/a", "", "none", "unknown") else None


def normalize_company(name: str) -> str:
    """Lowercase, strip common suffixes for fuzzy matching."""
    s = name.lower().strip()
    # Remove trailing punctuation
    s = s.rstrip(".,;")
    # Strip common suffixes iteratively
    for pattern in SUFFIXES:
        s = re.sub(pattern, "", s, flags=re.IGNORECASE).strip()
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s


def load_companies(path: str, col: str) -> set[str]:
    """Load unique raw company names from a CSV."""
    companies = set()
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        col_map = {c.strip().lower(): c for c in df.columns}
        actual_col = col_map.get(col.lower())
        if actual_col is None:
            print(f"  ⚠ Column '{col}' not found in {os.path.basename(path)}. Cols: {list(df.columns)[:10]}...")
            return companies
        for val in df[actual_col]:
            c = clean_str(val)
            if c:
                companies.add(c)
    except Exception as ex:
        print(f"  ⚠ Error reading {path}: {ex}")
    return companies


def main():
    print("=" * 70)
    print("COMPANY / ORGANIZATION OVERLAP AUDIT")
    print("=" * 70)

    # ── QOZB entity names ───────────────────────────────────────────────────
    print("\n📦 Loading QOZB entity names...")
    qozb_entities_raw: set[str] = set()
    entity_cols = ["Owner", "Manager", "Trustee", "Special Servicer"]
    fake = {"", "nan", "n/a", "na", "none", "unknown", "tbd", "pending",
            "not available", "owner managed", "owner-managed",
            "self managed", "self-managed"}
    try:
        qozb_df = pd.read_csv(QOZB_CSV, encoding="utf-8-sig", low_memory=False)
        for col in entity_cols:
            if col in qozb_df.columns:
                for val in qozb_df[col]:
                    c = clean_str(val)
                    if c and c.lower() not in fake:
                        qozb_entities_raw.add(c)
    except Exception as ex:
        print(f"  ⚠ Error: {ex}")
    print(f"  Unique QOZB entities: {len(qozb_entities_raw):,}")

    # ── Family Office firm names ────────────────────────────────────────────
    print("\n📦 Loading Family Office firm names...")
    fo_firms_raw: set[str] = set()
    try:
        fo_df = pd.read_csv(FAMILY_OFFICE_CSV, encoding="utf-8-sig", low_memory=False)
        for val in fo_df.get("Firm Name", pd.Series()):
            c = clean_str(val)
            if c:
                fo_firms_raw.add(c)
    except Exception as ex:
        print(f"  ⚠ Error: {ex}")
    print(f"  Unique FO firms: {len(fo_firms_raw):,}")

    # Build normalized lookup maps for new-schema orgs
    qozb_norm = {normalize_company(c): c for c in qozb_entities_raw}
    fo_norm = {normalize_company(c): c for c in fo_firms_raw}
    new_schema_norm = {**qozb_norm, **fo_norm}
    new_schema_raw = qozb_entities_raw | fo_firms_raw

    print(f"\n🔗 Combined new-schema orgs: {len(new_schema_raw):,} raw, {len(new_schema_norm):,} normalized")

    # ── Load outreach list companies ────────────────────────────────────────
    print("\n" + "─" * 70)
    print("📋 Loading outreach list companies...")
    print("─" * 70)

    list_data: list[tuple[str, set[str]]] = []
    all_outreach_raw: set[str] = set()

    for label, path, col in OUTREACH_LISTS:
        if not os.path.exists(path):
            print(f"\n  ⚠ MISSING: {label}")
            continue
        print(f"\n  📄 {label}")
        companies = load_companies(path, col)
        print(f"     Unique companies: {len(companies):,}")
        list_data.append((label, companies))
        all_outreach_raw |= companies

    all_outreach_norm = {normalize_company(c): c for c in all_outreach_raw}

    # ── Compute overlaps ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("📊 OVERLAP ANALYSIS")
    print("=" * 70)

    # Exact match
    exact_qozb = all_outreach_raw & qozb_entities_raw
    exact_fo = all_outreach_raw & fo_firms_raw
    exact_either = all_outreach_raw & new_schema_raw

    # Normalized match
    norm_overlap_qozb = set(all_outreach_norm.keys()) & set(qozb_norm.keys())
    norm_overlap_fo = set(all_outreach_norm.keys()) & set(fo_norm.keys())
    norm_overlap_either = set(all_outreach_norm.keys()) & set(new_schema_norm.keys())
    norm_only_outreach = set(all_outreach_norm.keys()) - set(new_schema_norm.keys())

    print(f"\n  Total unique outreach companies: {len(all_outreach_raw):,} raw, {len(all_outreach_norm):,} normalized")

    print(f"\n  EXACT MATCH:")
    print(f"    ∩ QOZB:   {len(exact_qozb):,}")
    print(f"    ∩ FO:     {len(exact_fo):,}")
    print(f"    ∩ Either: {len(exact_either):,}")

    print(f"\n  NORMALIZED MATCH (stripped suffixes like LLC, Inc, Corp):")
    print(f"    ∩ QOZB:   {len(norm_overlap_qozb):,}")
    print(f"    ∩ FO:     {len(norm_overlap_fo):,}")
    print(f"    ∩ Either: {len(norm_overlap_either):,}")
    print(f"    Only in outreach: {len(norm_only_outreach):,}")

    # ── Build report ────────────────────────────────────────────────────────
    md = []
    md.append("# Company / Organization Overlap Audit\n")
    md.append(f"**Total unique outreach companies**: {len(all_outreach_raw):,} (raw), {len(all_outreach_norm):,} (normalized)\n")
    md.append(f"**QOZB entities**: {len(qozb_entities_raw):,}\n")
    md.append(f"**Family Office firms**: {len(fo_firms_raw):,}\n")
    md.append(f"**Combined new-schema orgs**: {len(new_schema_raw):,} (raw), {len(new_schema_norm):,} (normalized)\n")

    md.append("\n## Overlap Summary\n")
    md.append("| Match Type | ∩ QOZB | ∩ FO | ∩ Either | Only Outreach |\n")
    md.append("|------------|-------:|-----:|---------:|--------------:|\n")
    md.append(f"| Exact match | {len(exact_qozb):,} | {len(exact_fo):,} | {len(exact_either):,} | {len(all_outreach_raw - new_schema_raw):,} |\n")
    md.append(f"| Normalized match | {len(norm_overlap_qozb):,} | {len(norm_overlap_fo):,} | {len(norm_overlap_either):,} | {len(norm_only_outreach):,} |\n")

    # Per-list breakdown
    md.append("\n## Per-List Breakdown (Normalized Match)\n")
    md.append("| List | Companies | ∩ QOZB | ∩ FO | ∩ Either | New |\n")
    md.append("|------|----------:|-------:|-----:|---------:|----:|\n")

    for label, companies in list_data:
        comp_norm = {normalize_company(c) for c in companies}
        qh = comp_norm & set(qozb_norm.keys())
        fh = comp_norm & set(fo_norm.keys())
        eh = comp_norm & set(new_schema_norm.keys())
        new = comp_norm - set(new_schema_norm.keys())
        md.append(f"| {label} | {len(companies):,} | {len(qh):,} | {len(fh):,} | {len(eh):,} | {len(new):,} |\n")
        print(f"\n  {label}:")
        print(f"    Companies: {len(companies):,}  |  ∩QOZB: {len(qh):,}  |  ∩FO: {len(fh):,}  |  ∩Either: {len(eh):,}  |  New: {len(new):,}")

    # Sample overlaps
    if norm_overlap_either:
        md.append("\n## Sample Overlapping Companies (first 30)\n")
        md.append("| Outreach Name | Matched To | Source |\n")
        md.append("|---------------|------------|--------|\n")
        count = 0
        for norm_key in sorted(norm_overlap_either):
            if count >= 30:
                break
            outreach_name = all_outreach_norm[norm_key]
            if norm_key in qozb_norm:
                matched = qozb_norm[norm_key]
                src = "QOZB"
            else:
                matched = fo_norm[norm_key]
                src = "Family Office"
            md.append(f"| {outreach_name} | {matched} | {src} |\n")
            count += 1

    md.append(f"\n## Migration Impact\n")
    md.append(f"""
- **{len(norm_overlap_either):,} companies** from outreach lists match existing organizations in the new schema.
  These will be **linked** to existing `organizations` records (not duplicated).

- **{len(norm_only_outreach):,} companies** are unique to outreach lists.
  These will create **new `organizations` records**.

- Total organizations after import: ~{len(new_schema_norm) + len(norm_only_outreach):,} (normalized).
""")

    output_path = os.path.join(os.path.dirname(__file__), "company_overlap_report.md")
    with open(output_path, "w") as f:
        f.write("".join(md))

    print(f"\n{'=' * 70}")
    print(f"📄 Report written to: {output_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
