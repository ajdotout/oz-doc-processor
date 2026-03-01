"""
audit_email_list_overlap.py

Compares all email outreach list CSVs against QOZB and Family Office data
to determine the degree of overlap before migrating the contacts table
into the consolidated CRM schema.

Sources checked:
  • Investor lists (InvestorsData, Investor-List-1-9-26)
  • Developer lists (developers.csv, Developers Rows (1).csv)
  • Fund lists (funds.csv, CapMatch Funds Rows.csv)
  • Warm contacts (final_warm_contacts_merged.csv)
  • Eventbrite webinar attendees (EventBriteWebinars.csv + individual exports)
  • GHL dump, n8n leads
  • Overlapping contacts (overlapping_contacts_with_header.csv)

Against:
  • QOZB Owner Contact Emails
  • Family Office Personal/Company/Secondary Emails

Output: Markdown report saved alongside this script.

Usage:
  uv run contact_merge_scripts/audit_email_list_overlap.py
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

# Email outreach CSVs: (label, path, email_column, has_header_variations)
EMAIL_LISTS = [
    ("InvestorsData (Oct 2025, cleaned)", os.path.join(OUTREACH_DIR, "InvestorsData-29-10-2025_cleaned.csv"), "email"),
    ("Investor List (Jan 2026)", os.path.join(OUTREACH_DIR, "Investor-List-1-9-26.csv"), "Email"),
    ("Developers (short)", os.path.join(OUTREACH_DIR, "developers.csv"), "Email"),
    ("Developers Rows (extended)", os.path.join(OUTREACH_DIR, "Developers Rows (1).csv"), "Email"),
    ("Funds", os.path.join(OUTREACH_DIR, "funds.csv"), "Email"),
    ("CapMatch Funds", os.path.join(OUTREACH_DIR, "CapMatch Funds Rows.csv"), "email"),
    ("GHL Chris Dump", os.path.join(OUTREACH_DIR, "GHL-Chris-Dec-Dump.csv"), "Email"),
    ("n8n Extracted", os.path.join(OUTREACH_DIR, "OZL-Chris-n8n-extracted.csv"), "email"),
    ("n8n Leads", os.path.join(OUTREACH_DIR, "OZL-Chris-n8n-leads.csv"), "email"),
    ("Overlapping Contacts", os.path.join(OUTREACH_DIR, "overlapping_contacts_with_header.csv"), "email"),
    ("Warm Contacts (merged)", os.path.join(WARM_DIR, "final_warm_contacts_merged.csv"), "email"),
    ("EventBrite Webinars", os.path.join(WARM_DIR, "EventBriteWebinars.csv"), "Attendee email"),
]


def clean_email(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().lower()
    # Handle comma-separated emails (import_contacts.ts keeps them as-is)
    # Take the first valid one
    for candidate in s.split(","):
        candidate = candidate.strip()
        if "@" in candidate and len(candidate) <= 254:
            return candidate
    return None


def load_emails_from_csv(path: str, email_col: str) -> set[str]:
    """Load unique emails from a CSV."""
    emails = set()
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        # Handle case variations in column names
        col_map = {c.strip().lower(): c for c in df.columns}
        actual_col = col_map.get(email_col.lower())
        if actual_col is None:
            print(f"  ⚠ Column '{email_col}' not found in {os.path.basename(path)}. Available: {list(df.columns)}")
            return emails
        for val in df[actual_col]:
            e = clean_email(val)
            if e:
                emails.add(e)
    except Exception as ex:
        print(f"  ⚠ Error reading {path}: {ex}")
    return emails


def main():
    print("=" * 70)
    print("EMAIL LIST OVERLAP AUDIT")
    print("Comparing outreach lists against QOZB + Family Office data")
    print("=" * 70)

    # ── Load target datasets (already in new CRM schema) ────────────────────

    # QOZB emails
    print("\n📦 Loading QOZB emails...")
    qozb_emails = set()
    try:
        qozb_df = pd.read_csv(QOZB_CSV, encoding="utf-8-sig", low_memory=False)
        for val in qozb_df.get("Owner Contact Email", pd.Series()):
            e = clean_email(val)
            if e:
                qozb_emails.add(e)
    except Exception as ex:
        print(f"  ⚠ Error: {ex}")
    print(f"  Unique QOZB emails: {len(qozb_emails):,}")

    # Family Office emails (personal + company + secondary)
    print("\n📦 Loading Family Office emails...")
    fo_emails = set()
    fo_personal = set()
    fo_company = set()
    fo_secondary = set()
    try:
        fo_df = pd.read_csv(FAMILY_OFFICE_CSV, encoding="utf-8-sig", low_memory=False)
        for val in fo_df.get("Personal Email Address", pd.Series()):
            e = clean_email(val)
            if e:
                fo_personal.add(e)
                fo_emails.add(e)
        for val in fo_df.get("Company Email Address", pd.Series()):
            e = clean_email(val)
            if e:
                fo_company.add(e)
                fo_emails.add(e)
        for val in fo_df.get("Secondary Email", pd.Series()):
            e = clean_email(val)
            if e:
                fo_secondary.add(e)
                fo_emails.add(e)
    except Exception as ex:
        print(f"  ⚠ Error: {ex}")
    print(f"  Unique FO personal:  {len(fo_personal):,}")
    print(f"  Unique FO company:   {len(fo_company):,}")
    print(f"  Unique FO secondary: {len(fo_secondary):,}")
    print(f"  Unique FO total:     {len(fo_emails):,}")

    # Combined "already in new schema" emails
    new_schema_emails = qozb_emails | fo_emails
    print(f"\n🔗 Combined new-schema emails (QOZB ∪ FO): {len(new_schema_emails):,}")

    # ── Load each outreach list ─────────────────────────────────────────────

    print("\n" + "─" * 70)
    print("📋 Loading email outreach lists...")
    print("─" * 70)

    list_data: list[tuple[str, set[str]]] = []
    all_outreach_emails: set[str] = set()

    for label, path, col in EMAIL_LISTS:
        if not os.path.exists(path):
            print(f"\n  ⚠ MISSING: {label} ({path})")
            continue
        print(f"\n  📄 {label}")
        emails = load_emails_from_csv(path, col)
        print(f"     Unique emails: {len(emails):,}")
        list_data.append((label, emails))
        all_outreach_emails |= emails

    # ── Compute overlaps ────────────────────────────────────────────────────

    print("\n" + "=" * 70)
    print("📊 OVERLAP ANALYSIS")
    print("=" * 70)

    md = []
    md.append("# Email List Overlap Audit\n")
    md.append(f"**Total unique emails across all outreach lists**: {len(all_outreach_emails):,}\n")
    md.append(f"**QOZB unique emails**: {len(qozb_emails):,}\n")
    md.append(f"**Family Office unique emails**: {len(fo_emails):,}  (personal: {len(fo_personal):,}, company: {len(fo_company):,}, secondary: {len(fo_secondary):,})\n")
    md.append(f"**Combined new-schema emails**: {len(new_schema_emails):,}\n")

    # Overall overlap
    overall_overlap = all_outreach_emails & new_schema_emails
    overall_qozb = all_outreach_emails & qozb_emails
    overall_fo = all_outreach_emails & fo_emails
    only_outreach = all_outreach_emails - new_schema_emails

    md.append("\n## Overall Overlap Summary\n")
    md.append(f"| Metric | Count | % of Outreach |\n")
    md.append(f"|--------|------:|:--------------:|\n")
    md.append(f"| Total outreach emails | {len(all_outreach_emails):,} | 100% |\n")
    md.append(f"| Overlap with QOZB | {len(overall_qozb):,} | {100*len(overall_qozb)/max(len(all_outreach_emails),1):.1f}% |\n")
    md.append(f"| Overlap with Family Office | {len(overall_fo):,} | {100*len(overall_fo)/max(len(all_outreach_emails),1):.1f}% |\n")
    md.append(f"| Overlap with either (QOZB ∪ FO) | {len(overall_overlap):,} | {100*len(overall_overlap)/max(len(all_outreach_emails),1):.1f}% |\n")
    md.append(f"| **Unique to outreach only** | **{len(only_outreach):,}** | **{100*len(only_outreach)/max(len(all_outreach_emails),1):.1f}%** |\n")

    print(f"\n  Total outreach emails: {len(all_outreach_emails):,}")
    print(f"  Overlap with QOZB: {len(overall_qozb):,} ({100*len(overall_qozb)/max(len(all_outreach_emails),1):.1f}%)")
    print(f"  Overlap with FO:   {len(overall_fo):,} ({100*len(overall_fo)/max(len(all_outreach_emails),1):.1f}%)")
    print(f"  Overlap (total):   {len(overall_overlap):,} ({100*len(overall_overlap)/max(len(all_outreach_emails),1):.1f}%)")
    print(f"  Unique to outreach: {len(only_outreach):,} ({100*len(only_outreach)/max(len(all_outreach_emails),1):.1f}%)")

    # Per-list breakdown
    md.append("\n## Per-List Overlap Breakdown\n")
    md.append("| List | Unique Emails | ∩ QOZB | ∩ FO | ∩ Either | Only in This List |\n")
    md.append("|------|-------------:|-------:|-----:|---------:|------------------:|\n")

    for label, emails in list_data:
        qozb_hit = emails & qozb_emails
        fo_hit = emails & fo_emails
        either_hit = emails & new_schema_emails
        only_this = emails - new_schema_emails
        md.append(f"| {label} | {len(emails):,} | {len(qozb_hit):,} | {len(fo_hit):,} | {len(either_hit):,} | {len(only_this):,} |\n")

        print(f"\n  {label}:")
        print(f"    Emails: {len(emails):,}  |  ∩QOZB: {len(qozb_hit):,}  |  ∩FO: {len(fo_hit):,}  |  ∩Either: {len(either_hit):,}  |  New: {len(only_this):,}")

    # Cross-list overlap (how many lists does each email appear in?)
    md.append("\n## Cross-List Duplication\n")
    email_list_count: dict[str, int] = defaultdict(int)
    for _, emails in list_data:
        for e in emails:
            email_list_count[e] += 1

    count_dist = defaultdict(int)
    for e, c in email_list_count.items():
        count_dist[c] += 1

    md.append("| # of Lists Containing Email | # of Emails |\n")
    md.append("|:---------------------------:|------------:|\n")
    for n in sorted(count_dist.keys()):
        md.append(f"| {n} | {count_dist[n]:,} |\n")

    print(f"\n  Cross-list duplication:")
    for n in sorted(count_dist.keys()):
        print(f"    In {n} list(s): {count_dist[n]:,} emails")

    # Show some sample overlapping emails (with QOZB/FO)
    if overall_overlap:
        md.append("\n## Sample Overlapping Emails (first 20)\n")
        md.append("These emails exist in both outreach lists AND QOZB/Family Office data:\n\n")
        md.append("| Email | In QOZB? | In FO? | Outreach Lists |\n")
        md.append("|-------|:--------:|:------:|----------------|\n")
        for email in sorted(overall_overlap)[:20]:
            in_qozb = "✅" if email in qozb_emails else "—"
            in_fo = "✅" if email in fo_emails else "—"
            lists_containing = [label for label, emails in list_data if email in emails]
            md.append(f"| {email} | {in_qozb} | {in_fo} | {', '.join(lists_containing)} |\n")

    # Migration impact summary
    md.append("\n## Migration Impact Summary\n")
    md.append(f"""
After importing the email lists into the new CRM schema:

- **{len(overall_overlap):,} emails** will match existing `people` records (from QOZB/FO imports).
  These people will be **enriched** (tags, lead_status, organization links added) — NOT duplicated.

- **{len(only_outreach):,} emails** are unique to the outreach lists.
  These will create **new `people` records** + `emails` entities + junctions.

- **{len(all_outreach_emails):,} total unique emails** → will produce at most **{len(only_outreach):,} new people** 
  (assuming perfect dedup; actual count depends on name variations across lists).
""")

    # ── Write report ────────────────────────────────────────────────────────

    output_path = os.path.join(os.path.dirname(__file__), "email_list_overlap_report.md")
    with open(output_path, "w") as f:
        f.write("".join(md))

    print(f"\n{'=' * 70}")
    print(f"📄 Report written to: {output_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
