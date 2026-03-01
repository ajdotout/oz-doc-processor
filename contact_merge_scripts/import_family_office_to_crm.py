"""
import_family_office_to_crm.py

Imports the Family Office Club CSV into the consolidated CRM schema.

Tables populated:
  • organizations       – one per unique firm name, dedup on name (exact)
  • people              – deduped on LinkedIn URL → personal email → phone+name
  • phones              – one per unique normalized phone number
  • emails              – one per unique email address (personal + secondary)
  • linkedin_profiles   – one per unique LinkedIn URL
  • person_phones       – person ↔ phone junction
  • person_emails       – person ↔ email junction (personal + secondary)
  • person_linkedin     – person ↔ linkedin junction
  • person_organizations– person ↔ org junction (with title)

Tags applied to all imported people: ['family_office']
Org type applied: 'family_office'

Usage:
  uv run contact_merge_scripts/import_family_office_to_crm.py
  uv run contact_merge_scripts/import_family_office_to_crm.py --dry-run
  uv run contact_merge_scripts/import_family_office_to_crm.py --limit 100
  uv run contact_merge_scripts/import_family_office_to_crm.py --dry-run --limit 500

Environment variables required (in oz-doc-processor/.env):
  SUPABASE_URL              – e.g. https://xxxx.supabase.co
  SUPABASE_SERVICE_ROLE_KEY – service role key (bypasses RLS)
"""

import os
import re
import sys
import json
import argparse
from collections import defaultdict
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.table import Table
from rich.panel import Panel

# ─── Configuration ─────────────────────────────────────────────────────────────

CSV_PATH = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists/USA_Family_Office_Consolidated.csv"

BATCH_SIZE = 500

PEOPLE_TAGS = ["family_office"]

console = Console()

# ─── Helpers ───────────────────────────────────────────────────────────────────

def clean_str(val) -> Optional[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    return s if s and s.lower() != "nan" else None

def normalize_phone(val) -> Optional[str]:
    s = clean_str(val)
    if not s:
        return None
    s = s.split(".")[0].strip()
    digits = re.sub(r"\D", "", s)
    if len(digits) < 7 or all(c == "0" for c in digits):
        return None
    return digits

def normalize_email(val) -> Optional[str]:
    s = clean_str(val)
    if not s or "@" not in s:
        return None
    s = s.lower().strip()
    # RFC 5321: max email length is 254 chars. Anything longer is garbage data.
    if len(s) > 254:
        return None
    return s

def normalize_linkedin(val) -> Optional[str]:
    s = clean_str(val)
    if not s:
        return None
    s = s.strip().rstrip("/")
    s = s.split("?")[0]
    return s.lower()

def normalize_name(first, last) -> Optional[str]:
    f = clean_str(first) or ""
    l = clean_str(last) or ""
    full = f"{f} {l}".strip().lower()
    return full if full else None

def batch(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


# ─── Phase 1: Collect unique entities ──────────────────────────────────────────

def phase1_collect(df: pd.DataFrame, limit: Optional[int]):
    """
    Single pass through CSV. Collects unique orgs, phones, emails, LinkedIn
    profiles, and builds a list of person_slots for dedup in Phase 3.
    """
    unique_phones:    dict[str, dict] = {}
    unique_emails:    dict[str, dict] = {}
    unique_linkedins: dict[str, dict] = {}
    unique_orgs:      dict[str, dict] = {}
    # Track org fields for most-common resolution (company_email, address, etc.)
    org_field_counts: dict[str, dict] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    person_slots:     list[dict] = []

    total = limit or len(df)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Phase 1:[/bold blue] Scanning CSV..."),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("scan", total=total)

        for i, (_, row) in enumerate(df.iterrows()):
            if limit and i >= limit:
                break
            progress.advance(task)

            firm_name       = clean_str(row.get("Firm Name"))
            first_name      = clean_str(row.get("Contact First Name"))
            last_name       = clean_str(row.get("Contact Last Name"))
            title           = clean_str(row.get("Contact Title/Position"))
            phone           = normalize_phone(row.get("Phone Number"))
            personal_email  = normalize_email(row.get("Personal Email Address"))
            company_email   = normalize_email(row.get("Company Email Address"))
            secondary_email = normalize_email(row.get("Secondary Email"))
            linkedin        = normalize_linkedin(row.get("LinkedIn Profile"))
            category        = clean_str(row.get("Category"))
            website         = clean_str(row.get("Website"))
            address         = clean_str(row.get("Company Street Address"))
            city            = clean_str(row.get("City"))
            state           = clean_str(row.get("State/ Province"))
            zip_            = clean_str(row.get("Postal/Zip Code"))
            country         = clean_str(row.get("Country"))
            alma_mater      = clean_str(row.get("Alma Mater"))
            investment_prefs= clean_str(row.get("Company's Areas of Investments/Interest"))
            year_founded    = clean_str(row.get("Year Founded"))
            aum             = clean_str(row.get("AUM"))
            about           = clean_str(row.get("About Company"))

            # ── Organization ──────────────────────────────────────────────
            if firm_name:
                if firm_name not in unique_orgs:
                    unique_orgs[firm_name] = {
                        "name": firm_name,
                        "org_type": "family_office",
                    }

                # Track field counts for most-common resolution
                if company_email: org_field_counts[firm_name]["company_email"][company_email] += 1
                if website:       org_field_counts[firm_name]["website"][website] += 1
                if address:       org_field_counts[firm_name]["address"][address] += 1
                if city:          org_field_counts[firm_name]["city"][city] += 1
                if state:         org_field_counts[firm_name]["state"][state] += 1
                if zip_:          org_field_counts[firm_name]["zip"][zip_] += 1
                if country:       org_field_counts[firm_name]["country"][country] += 1
                if category:      org_field_counts[firm_name]["category"][category] += 1
                if aum:           org_field_counts[firm_name]["_aum"][aum] += 1
                if year_founded:  org_field_counts[firm_name]["_year_founded"][year_founded] += 1
                if investment_prefs: org_field_counts[firm_name]["_investment_prefs"][investment_prefs] += 1
                if about:         org_field_counts[firm_name]["_about"][about] += 1

            # ── Phone ────────────────────────────────────────────────────
            if phone and phone not in unique_phones:
                unique_phones[phone] = {"number": phone, "status": "active", "metadata": {}}

            # ── Emails ───────────────────────────────────────────────────
            if personal_email and personal_email not in unique_emails:
                unique_emails[personal_email] = {"address": personal_email, "status": "active", "metadata": {}}
            if secondary_email and secondary_email not in unique_emails:
                unique_emails[secondary_email] = {"address": secondary_email, "status": "active", "metadata": {}}
            # Company email goes to org level, not emails table

            # ── LinkedIn ─────────────────────────────────────────────────
            if linkedin and linkedin not in unique_linkedins:
                profile_name = None
                if first_name and last_name:
                    profile_name = f"{first_name} {last_name}"
                unique_linkedins[linkedin] = {
                    "url": linkedin,
                    "profile_name": profile_name,
                    "connection_status": "none",
                    "metadata": {},
                }

            # ── Record slot for Phase 3 ──────────────────────────────────
            person_slots.append({
                "first_name":      first_name,
                "last_name":       last_name,
                "title":           title,
                "phone":           phone,
                "personal_email":  personal_email,
                "secondary_email": secondary_email,
                "linkedin":        linkedin,
                "firm_name":       firm_name,
                "alma_mater":      alma_mater,
            })

    # Resolve most-common field values for each org
    for org_name, field_counts in org_field_counts.items():
        if org_name in unique_orgs:
            details = {}
            for field, counter in field_counts.items():
                if counter:
                    top_value = max(counter, key=counter.get)
                    if field.startswith("_"):
                        # Goes into details JSONB
                        details[field[1:]] = top_value
                    else:
                        unique_orgs[org_name][field] = top_value
            if details:
                unique_orgs[org_name]["details"] = details

    console.print(f"  [dim]Unique orgs:        {len(unique_orgs):,}[/dim]")
    console.print(f"  [dim]Unique phones:      {len(unique_phones):,}[/dim]")
    console.print(f"  [dim]Unique emails:      {len(unique_emails):,}[/dim]")
    console.print(f"  [dim]Unique LinkedIn:    {len(unique_linkedins):,}[/dim]")
    console.print(f"  [dim]Person slots:       {len(person_slots):,}[/dim]")

    return unique_phones, unique_emails, unique_linkedins, unique_orgs, person_slots


# ─── Phase 2: Batch upsert entity tables → ID maps ────────────────────────────

def upsert_batch(supabase, table: str, records: list[dict], on_conflict: str, label: str) -> dict:
    id_map = {}
    conflict_cols = [c.strip() for c in on_conflict.split(",")]

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Upserting {label}...[/bold blue]"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(label, total=len(records))

        for chunk in batch(records, BATCH_SIZE):
            result = (
                supabase.table(table)
                .upsert(chunk, on_conflict=on_conflict)
                .execute()
            )
            for row in result.data:
                if len(conflict_cols) == 1:
                    key = row[conflict_cols[0]]
                else:
                    key = tuple(row[c] for c in conflict_cols)
                id_map[key] = row["id"]
            progress.advance(task, len(chunk))

    return id_map


def phase2_upsert_entities(supabase, unique_phones, unique_emails, unique_linkedins, unique_orgs, dry_run: bool):
    if dry_run:
        console.print("[yellow]DRY RUN: skipping database writes[/yellow]")
        return {}, {}, {}, {}

    phone_id_map    = upsert_batch(supabase, "phones",            list(unique_phones.values()),    "number",  "phones")
    email_id_map    = upsert_batch(supabase, "emails",            list(unique_emails.values()),    "address", "emails")
    linkedin_id_map = upsert_batch(supabase, "linkedin_profiles", list(unique_linkedins.values()), "url",     "linkedin_profiles")
    org_id_map      = upsert_batch(supabase, "organizations",     list(unique_orgs.values()),      "name",    "organizations")

    return phone_id_map, email_id_map, linkedin_id_map, org_id_map


# ─── Phase 3: Resolve people + collect junction records ────────────────────────

def phase3_resolve_people(person_slots, phone_id_map, email_id_map, linkedin_id_map, org_id_map, dry_run: bool):
    """
    Walk all person slots. Dedup people using a priority chain:
      1. LinkedIn URL (highest priority — 89% fill)
      2. Personal email (96% fill, unique per person)
      3. Phone + name (fallback)
    """
    people_to_insert: list[dict] = []

    # Dedup maps: identifier → person_list_index
    linkedin_dedup: dict[str, int] = {}
    email_dedup:    dict[str, int] = {}
    phone_name_dedup: dict[tuple, int] = {}

    # Junction collection
    j_person_phones:   list[tuple[int, dict]] = []
    j_person_emails:   list[tuple[int, dict]] = []
    j_person_linkedin: list[tuple[int, dict]] = []
    j_person_orgs:     list[tuple[int, dict]] = []

    stats = {"new_people": 0, "reused_people": 0, "skipped_nameless": 0}

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Phase 3:[/bold blue] Resolving people..."),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("people", total=len(person_slots))

        for slot in person_slots:
            progress.advance(task)

            first    = slot["first_name"]
            last     = slot["last_name"]
            title    = slot["title"]
            phone    = slot["phone"]
            p_email  = slot["personal_email"]
            s_email  = slot["secondary_email"]
            linkedin = slot["linkedin"]
            firm     = slot["firm_name"]
            alma     = slot["alma_mater"]

            name_lower = normalize_name(first, last)

            if not name_lower:
                stats["skipped_nameless"] += 1
                continue

            # ── Resolve or create person (priority chain) ────────────────
            person_idx = None

            # Priority 1: LinkedIn
            if linkedin and linkedin in linkedin_dedup:
                person_idx = linkedin_dedup[linkedin]
                stats["reused_people"] += 1

            # Priority 2: Personal email
            elif p_email and p_email in email_dedup:
                person_idx = email_dedup[p_email]
                stats["reused_people"] += 1

            # Priority 3: Phone + name
            elif phone and (phone, name_lower) in phone_name_dedup:
                person_idx = phone_name_dedup[(phone, name_lower)]
                stats["reused_people"] += 1

            # New person
            if person_idx is None:
                person_idx = len(people_to_insert)
                details = {"source": "family_office_import"}
                if alma:
                    details["alma_mater"] = alma
                people_to_insert.append({
                    "first_name": first or "",
                    "last_name":  last or "",
                    "lead_status": "new",
                    "tags": PEOPLE_TAGS,
                    "details": details,
                })
                stats["new_people"] += 1

            # Register in all applicable dedup maps (so future dupes merge)
            if linkedin:
                linkedin_dedup[linkedin] = person_idx
            if p_email:
                email_dedup[p_email] = person_idx
            if phone and name_lower:
                phone_name_dedup[(phone, name_lower)] = person_idx

            # ── Junction: person_phones ──────────────────────────────────
            if phone and not dry_run:
                phone_id = phone_id_map.get(phone)
                if phone_id:
                    j_person_phones.append((person_idx, {
                        "phone_id": phone_id,
                        "label":    "work",
                        "is_primary": True,
                        "source":   "family_office_import",
                    }))

            # ── Junction: person_emails ──────────────────────────────────
            if p_email and not dry_run:
                email_id = email_id_map.get(p_email)
                if email_id:
                    j_person_emails.append((person_idx, {
                        "email_id":  email_id,
                        "label":     "personal",
                        "is_primary": True,
                        "source":    "family_office_import",
                    }))

            if s_email and not dry_run:
                email_id = email_id_map.get(s_email)
                if email_id:
                    j_person_emails.append((person_idx, {
                        "email_id":  email_id,
                        "label":     "secondary",
                        "is_primary": False,
                        "source":    "family_office_import",
                    }))

            # ── Junction: person_linkedin ────────────────────────────────
            if linkedin and not dry_run:
                li_id = linkedin_id_map.get(linkedin)
                if li_id:
                    j_person_linkedin.append((person_idx, {
                        "linkedin_id": li_id,
                        "is_primary":  True,
                        "source":      "family_office_import",
                    }))

            # ── Junction: person_organizations ───────────────────────────
            if firm and not dry_run:
                org_id = org_id_map.get(firm)
                if org_id:
                    j_person_orgs.append((person_idx, {
                        "organization_id": org_id,
                        "title":           title,
                        "is_primary":      True,
                    }))

    console.print(f"  [dim]New people to insert: {stats['new_people']:,}[/dim]")
    console.print(f"  [dim]Reused (deduped):     {stats['reused_people']:,}[/dim]")
    console.print(f"  [dim]Nameless slots skipped: {stats['skipped_nameless']:,}[/dim]")

    return people_to_insert, {
        "person_phones":   j_person_phones,
        "person_emails":   j_person_emails,
        "person_linkedin": j_person_linkedin,
        "person_orgs":     j_person_orgs,
    }


# ─── Phase 4: Insert people → get IDs ──────────────────────────────────────────

def phase4_insert_people(supabase, people_to_insert: list[dict], dry_run: bool) -> list[str]:
    if dry_run or not people_to_insert:
        console.print(f"[yellow]DRY RUN: would insert {len(people_to_insert):,} people[/yellow]")
        return ["dry-run-id"] * len(people_to_insert)

    person_uuids: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Phase 4:[/bold blue] Inserting people..."),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("people", total=len(people_to_insert))

        for chunk in batch(people_to_insert, BATCH_SIZE):
            result = supabase.table("people").insert(chunk).execute()
            for row in result.data:
                person_uuids.append(row["id"])
            progress.advance(task, len(chunk))

    return person_uuids


# ─── Phase 5: Insert all junction records ──────────────────────────────────────

def phase5_insert_junctions(supabase, junctions: dict, person_uuids: list[str], dry_run: bool):
    if dry_run:
        for table_key, records in junctions.items():
            console.print(f"[yellow]DRY RUN: would insert {len(records):,} {table_key} rows[/yellow]")
        return

    # ── person_phones ──────────────────────────────────────────────────────────
    pp_records = []
    seen = set()
    for (pidx, data) in junctions["person_phones"]:
        pid = person_uuids[pidx]
        key = (pid, data["phone_id"])
        if key not in seen:
            seen.add(key)
            pp_records.append({"person_id": pid, **data})
    _batch_upsert(supabase, "person_phones", pp_records, "person_id,phone_id", "person_phones")

    # ── person_emails ──────────────────────────────────────────────────────────
    pe_records = []
    seen = set()
    for (pidx, data) in junctions["person_emails"]:
        pid = person_uuids[pidx]
        key = (pid, data["email_id"])
        if key not in seen:
            seen.add(key)
            pe_records.append({"person_id": pid, **data})
    _batch_upsert(supabase, "person_emails", pe_records, "person_id,email_id", "person_emails")

    # ── person_linkedin ────────────────────────────────────────────────────────
    pl_records = []
    seen = set()
    for (pidx, data) in junctions["person_linkedin"]:
        pid = person_uuids[pidx]
        key = (pid, data["linkedin_id"])
        if key not in seen:
            seen.add(key)
            pl_records.append({"person_id": pid, **data})
    _batch_upsert(supabase, "person_linkedin", pl_records, "person_id,linkedin_id", "person_linkedin")

    # ── person_organizations ───────────────────────────────────────────────────
    po_records = []
    seen = set()
    for (pidx, data) in junctions["person_orgs"]:
        pid = person_uuids[pidx]
        key = (pid, data["organization_id"])
        if key not in seen:
            seen.add(key)
            po_records.append({"person_id": pid, **data})
    _batch_upsert(supabase, "person_organizations", po_records, "person_id,organization_id", "person_organizations")


def _batch_upsert(supabase, table: str, records: list[dict], on_conflict: str, label: str):
    if not records:
        console.print(f"  [dim]{label}: 0 records, skipping[/dim]")
        return

    inserted = 0
    with Progress(
        SpinnerColumn(),
        TextColumn(f"  [bold blue]Upserting {label}...[/bold blue]"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(label, total=len(records))
        for chunk in batch(records, BATCH_SIZE):
            supabase.table(table).upsert(chunk, on_conflict=on_conflict).execute()
            inserted += len(chunk)
            progress.advance(task, len(chunk))

    console.print(f"  [dim]{label}: {inserted:,} rows upserted[/dim]")


# ─── Summary ───────────────────────────────────────────────────────────────────

def print_summary(unique_phones, unique_emails, unique_linkedins, unique_orgs,
                  people_to_insert, dry_run: bool):
    table = Table(title="Family Office Import Summary", show_header=True, header_style="bold magenta")
    table.add_column("Table", style="cyan")
    table.add_column("Records", justify="right", style="green")
    table.add_column("Notes", style="dim")

    table.add_row("organizations",     f"{len(unique_orgs):,}",        "dedup on name (exact)")
    table.add_row("phones",            f"{len(unique_phones):,}",      "dedup on normalized digits")
    table.add_row("emails",            f"{len(unique_emails):,}",      "personal + secondary")
    table.add_row("linkedin_profiles", f"{len(unique_linkedins):,}",   "dedup on URL")
    table.add_row("people",            f"{len(people_to_insert):,}",   "dedup: linkedin → email → phone+name")
    table.add_row("person_phones",     "—",                            "see junction phase")
    table.add_row("person_emails",     "—",                            "see junction phase")
    table.add_row("person_linkedin",   "—",                            "see junction phase")
    table.add_row("person_organizations", "—",                         "see junction phase")

    console.print(table)
    if dry_run:
        console.print(Panel("[yellow bold]DRY RUN complete — no data was written to the database.[/yellow bold]"))
    else:
        console.print(Panel("[green bold]Family Office import complete.[/green bold]"))


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Import Family Office CSV into consolidated CRM schema")
    parser.add_argument("--dry-run", action="store_true", help="Scan and plan but do not write to DB")
    parser.add_argument("--limit",   type=int, default=None, help="Only process first N CSV rows")
    args = parser.parse_args()

    console.print(Panel(
        f"[bold]Family Office → CRM Import[/bold]\n"
        f"CSV: {CSV_PATH}\n"
        f"Mode: {'[yellow]DRY RUN[/yellow]' if args.dry_run else '[green]LIVE[/green]'}"
        + (f"\nLimit: first {args.limit} rows" if args.limit else ""),
        title="oz-doc-processor",
    ))

    # ── Load .env and connect ────────────────────────────────────────────────
    env_path = os.path.join(os.path.dirname(__file__), "../.env")
    load_dotenv(env_path)

    supabase = None
    if not args.dry_run:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            console.print("[red]ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in oz-doc-processor/.env[/red]")
            sys.exit(1)
        from supabase import create_client
        supabase = create_client(url, key)
        console.print(f"[green]Connected to Supabase:[/green] {url}")

    # ── Load CSV ─────────────────────────────────────────────────────────────
    console.print(f"\nLoading CSV...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", low_memory=False)
    console.print(f"[dim]Loaded {len(df):,} rows[/dim]")

    # ── Phase 1 ──────────────────────────────────────────────────────────────
    console.print("\n[bold]Phase 1: Collecting unique entities[/bold]")
    (unique_phones, unique_emails, unique_linkedins, unique_orgs,
     person_slots) = phase1_collect(df, args.limit)

    # ── Phase 2 ──────────────────────────────────────────────────────────────
    console.print("\n[bold]Phase 2: Upserting entity tables[/bold]")
    phone_id_map, email_id_map, linkedin_id_map, org_id_map = phase2_upsert_entities(
        supabase, unique_phones, unique_emails, unique_linkedins, unique_orgs, args.dry_run
    )

    # ── Phase 3 ──────────────────────────────────────────────────────────────
    console.print("\n[bold]Phase 3: Resolving people & collecting junction records[/bold]")
    people_to_insert, junctions = phase3_resolve_people(
        person_slots, phone_id_map, email_id_map, linkedin_id_map, org_id_map, args.dry_run
    )

    # ── Phase 4 ──────────────────────────────────────────────────────────────
    console.print("\n[bold]Phase 4: Inserting people[/bold]")
    person_uuids = phase4_insert_people(supabase, people_to_insert, args.dry_run)

    # ── Phase 5 ──────────────────────────────────────────────────────────────
    console.print("\n[bold]Phase 5: Inserting junction records[/bold]")
    phase5_insert_junctions(supabase, junctions, person_uuids, args.dry_run)

    # ── Summary ──────────────────────────────────────────────────────────────
    console.print("\n")
    print_summary(
        unique_phones, unique_emails, unique_linkedins, unique_orgs,
        people_to_insert, args.dry_run
    )


if __name__ == "__main__":
    main()
