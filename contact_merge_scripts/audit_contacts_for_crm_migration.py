"""
audit_contacts_for_crm_migration.py

Reads the live `contacts` table from Supabase and compares against
all data already present in the new CRM schema (people, emails, phones,
organizations). Produces a detailed report of what the migration will do.

NO WRITES — read-only analysis.

Tables read:
  • contacts           (old schema — the source to migrate)
  • emails             (new schema — already populated by QOZB + FO imports)
  • phones             (new schema)
  • organizations      (new schema)
  • person_emails      (new schema — to find which person owns a matched email)
  • people             (new schema)

Output: Markdown report in this directory.

Usage:
  uv run contact_merge_scripts/audit_contacts_for_crm_migration.py
"""

import os
import re
import sys
import json
from collections import defaultdict, Counter
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

console = Console()

# ─── Helpers ───────────────────────────────────────────────────────────────────

def clean_str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "") else None

def normalize_phone(val) -> Optional[str]:
    s = clean_str(val)
    if not s:
        return None
    digits = re.sub(r"\D", "", s)
    if len(digits) < 7 or all(c == "0" for c in digits):
        return None
    return digits

def split_name(full_name: str) -> tuple[str, str]:
    """Split 'John Smith' → ('John', 'Smith'). Best effort."""
    if not full_name:
        return ("", "")
    parts = full_name.strip().split(None, 1)
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])


# ─── Fetch helpers ─────────────────────────────────────────────────────────────

def fetch_all(supabase, table: str, select: str = "*", page_size: int = 1000) -> list[dict]:
    """Paginate through an entire table."""
    all_rows = []
    offset = 0
    while True:
        result = (
            supabase.table(table)
            .select(select)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = result.data
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return all_rows


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    console.print(Panel(
        "[bold]Contacts → CRM Migration Analysis[/bold]\n"
        "Read-only audit of contacts table vs. new CRM schema",
        title="oz-doc-processor",
    ))

    # ── Connect to both Supabase instances ──────────────────────────────────
    # Production: has the contacts table (source to migrate)
    # Local: has the new CRM schema (people, emails, phones, organizations)
    env_path = os.path.join(os.path.dirname(__file__), "../.env")
    load_dotenv(env_path)

    prod_url = os.getenv("SUPABASE_URL")
    prod_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    local_url = os.getenv("LOCAL_SUPABASE_URL")
    local_key = os.getenv("LOCAL_SUPABASE_SERVICE_ROLE_KEY")

    if not prod_url or not prod_key:
        console.print("[red]ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required in .env[/red]")
        sys.exit(1)
    if not local_url or not local_key:
        console.print("[red]ERROR: LOCAL_SUPABASE_URL and LOCAL_SUPABASE_SERVICE_ROLE_KEY required in .env[/red]")
        sys.exit(1)

    from supabase import create_client
    prod_supabase = create_client(prod_url, prod_key)
    local_supabase = create_client(local_url, local_key)
    console.print(f"[green]Connected to Production:[/green] {prod_url}")
    console.print(f"[green]Connected to Local:[/green]      {local_url}")

    # ── Fetch all data ───────────────────────────────────────────────────────

    console.print("\n[bold]Fetching data...[/bold]")

    console.print("  [bold]Production:[/bold] Fetching contacts...")
    contacts = fetch_all(prod_supabase, "contacts",
        "id,email,name,company,role,location,source,phone_number,details,contact_type,contact_types,user_id,globally_bounced,globally_unsubscribed,suppression_reason,suppression_date,created_at")
    console.print(f"  [dim]→ {len(contacts):,} contacts[/dim]")

    console.print("  [bold]Local:[/bold] Fetching emails (new schema)...")
    existing_emails = fetch_all(local_supabase, "emails", "id,address,status")
    console.print(f"  [dim]→ {len(existing_emails):,} email entities[/dim]")

    console.print("  [bold]Local:[/bold] Fetching phones (new schema)...")
    existing_phones = fetch_all(local_supabase, "phones", "id,number,status")
    console.print(f"  [dim]→ {len(existing_phones):,} phone entities[/dim]")

    console.print("  [bold]Local:[/bold] Fetching organizations (new schema)...")
    existing_orgs = fetch_all(local_supabase, "organizations", "id,name,org_type")
    console.print(f"  [dim]→ {len(existing_orgs):,} organizations[/dim]")

    console.print("  [bold]Local:[/bold] Fetching person_emails (new schema)...")
    existing_person_emails = fetch_all(local_supabase, "person_emails", "person_id,email_id")
    console.print(f"  [dim]→ {len(existing_person_emails):,} person_email links[/dim]")

    console.print("  [bold]Local:[/bold] Fetching people (new schema)...")
    existing_people = fetch_all(local_supabase, "people", "id,first_name,last_name,tags,lead_status,user_id")
    console.print(f"  [dim]→ {len(existing_people):,} people[/dim]")

    # ── Build lookup maps ────────────────────────────────────────────────────

    console.print("\n[bold]Building lookup maps...[/bold]")

    # email address (lowercase) → email entity id
    email_id_map = {e["address"].lower().strip(): e["id"] for e in existing_emails if e.get("address")}

    # email entity id → person_id (first match)
    email_to_person = {}
    for pe in existing_person_emails:
        eid = pe["email_id"]
        if eid not in email_to_person:
            email_to_person[eid] = pe["person_id"]

    # phone number (digits) → phone entity id
    phone_id_map = {p["number"]: p["id"] for p in existing_phones if p.get("number")}

    # org name (lowercase, trimmed) → org id
    org_id_map = {o["name"].lower().strip(): o["id"] for o in existing_orgs if o.get("name")}

    # person id → person record
    person_map = {p["id"]: p for p in existing_people}

    console.print(f"  [dim]Email map:  {len(email_id_map):,} entries[/dim]")
    console.print(f"  [dim]Phone map:  {len(phone_id_map):,} entries[/dim]")
    console.print(f"  [dim]Org map:    {len(org_id_map):,} entries[/dim]")
    console.print(f"  [dim]Person map: {len(person_map):,} entries[/dim]")

    # ── Analyze each contact ─────────────────────────────────────────────────

    console.print("\n[bold]Analyzing contacts...[/bold]")

    # Counters
    stats = {
        "total": 0,
        "email_match": 0,           # email already in emails table
        "email_match_with_person": 0, # ... and linked to a person
        "email_new": 0,              # email not in emails table
        "phone_present": 0,          # contact has a phone number
        "phone_match": 0,            # phone already in phones table
        "phone_new": 0,              # phone not in phones table
        "company_present": 0,        # contact has a company
        "company_match": 0,          # company already in organizations table
        "company_new": 0,            # company not in organizations table
        "role_present": 0,           # contact has a role
        "user_id_present": 0,        # contact has user_id
        "user_id_on_existing_person": 0, # user_id match where person already exists
        "user_id_new_person": 0,     # user_id on a person we'll create
        "bounced": 0,
        "unsubscribed": 0,
        "has_details": 0,
        "has_location": 0,
        "has_name": 0,
    }

    # Track field completeness
    source_counts = Counter()
    contact_type_counts = Counter()
    lead_status_counts = Counter()

    # For dedup analysis: how many contacts share the same email
    email_seen = Counter()

    # Track which new orgs will be created
    new_orgs: set[str] = set()
    matched_orgs: dict[str, str] = {}  # contact company → matched org name

    # Track new people vs enriched
    new_people_emails: set[str] = set()
    enriched_people: list[dict] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Analyzing...[/bold blue]"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("contacts", total=len(contacts))

        for c in contacts:
            progress.advance(task)
            stats["total"] += 1

            email = (c.get("email") or "").lower().strip()
            name = clean_str(c.get("name"))
            company = clean_str(c.get("company"))
            role = clean_str(c.get("role"))
            phone = normalize_phone(c.get("phone_number"))
            source = clean_str(c.get("source"))
            details = c.get("details") or {}
            contact_types = c.get("contact_types") or []
            user_id = c.get("user_id")
            bounced = c.get("globally_bounced")
            unsub = c.get("globally_unsubscribed")
            location = clean_str(c.get("location"))

            if not email:
                continue

            email_seen[email] += 1

            # ── Email overlap ─────────────────────────────────────
            email_entity_id = email_id_map.get(email)
            if email_entity_id:
                stats["email_match"] += 1
                person_id = email_to_person.get(email_entity_id)
                if person_id:
                    stats["email_match_with_person"] += 1
                    person = person_map.get(person_id, {})
                    enriched_people.append({
                        "email": email,
                        "contact_name": name,
                        "person_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                        "person_tags": person.get("tags", []),
                        "contact_types": contact_types,
                        "contact_source": source,
                    })
                    if user_id:
                        stats["user_id_on_existing_person"] += 1
            else:
                stats["email_new"] += 1
                new_people_emails.add(email)
                if user_id:
                    stats["user_id_new_person"] += 1

            # ── Phone overlap ─────────────────────────────────────
            if phone:
                stats["phone_present"] += 1
                if phone in phone_id_map:
                    stats["phone_match"] += 1
                else:
                    stats["phone_new"] += 1

            # ── Company overlap ───────────────────────────────────
            if company:
                stats["company_present"] += 1
                company_lower = company.lower().strip()
                if company_lower in org_id_map:
                    stats["company_match"] += 1
                    matched_orgs[company] = company_lower
                else:
                    stats["company_new"] += 1
                    new_orgs.add(company)

            # ── Other fields ──────────────────────────────────────
            if role:
                stats["role_present"] += 1
            if user_id:
                stats["user_id_present"] += 1
            if bounced:
                stats["bounced"] += 1
            if unsub:
                stats["unsubscribed"] += 1
            if details and details != {}:
                stats["has_details"] += 1
            if location:
                stats["has_location"] += 1
            if name:
                stats["has_name"] += 1

            # Track distributions
            if source:
                source_counts[source] += 1
            for ct in contact_types:
                contact_type_counts[ct] += 1
            ls = details.get("lead_status") if isinstance(details, dict) else None
            lead_status_counts[ls or "(none)"] += 1

    # ── Duplicate emails within contacts ─────────────────────────────────
    dup_emails = {e: c for e, c in email_seen.items() if c > 1}

    # ── Print Results ────────────────────────────────────────────────────

    console.print("\n")

    # Summary table
    t = Table(title="Migration Analysis Summary", show_header=True, header_style="bold magenta")
    t.add_column("Metric", style="cyan")
    t.add_column("Count", justify="right", style="green")
    t.add_column("% of Total", justify="right", style="dim")
    t.add_column("Notes", style="dim")

    total = stats["total"]
    def pct(n): return f"{100*n/max(total,1):.1f}%"

    t.add_row("Total contacts", f"{total:,}", "100%", "")
    t.add_row("", "", "", "")
    t.add_row("[bold]EMAIL OVERLAP[/bold]", "", "", "")
    t.add_row("  Email already in new schema", f"{stats['email_match']:,}", pct(stats['email_match']), "Will ENRICH existing person")
    t.add_row("    ...with linked person", f"{stats['email_match_with_person']:,}", "", "")
    t.add_row("  Email NOT in new schema", f"{stats['email_new']:,}", pct(stats['email_new']), "Will CREATE new person")
    t.add_row("", "", "", "")
    t.add_row("[bold]PHONE OVERLAP[/bold]", "", "", "")
    t.add_row("  Has phone number", f"{stats['phone_present']:,}", pct(stats['phone_present']), "")
    t.add_row("  Phone already in new schema", f"{stats['phone_match']:,}", "", "Will link to existing phone entity")
    t.add_row("  Phone NOT in new schema", f"{stats['phone_new']:,}", "", "Will create new phone entity")
    t.add_row("", "", "", "")
    t.add_row("[bold]COMPANY OVERLAP[/bold]", "", "", "")
    t.add_row("  Has company", f"{stats['company_present']:,}", pct(stats['company_present']), "")
    t.add_row("  Company already in new schema", f"{stats['company_match']:,}", "", "Will link to existing org (exact match)")
    t.add_row("  Company NOT in new schema", f"{stats['company_new']:,}", "", f"Will create {len(new_orgs):,} new orgs")
    t.add_row("", "", "", "")
    t.add_row("[bold]FIELD COMPLETENESS[/bold]", "", "", "")
    t.add_row("  Has name", f"{stats['has_name']:,}", pct(stats['has_name']), "→ people.first_name / last_name")
    t.add_row("  Has role", f"{stats['role_present']:,}", pct(stats['role_present']), "→ person_organizations.title")
    t.add_row("  Has location", f"{stats['has_location']:,}", pct(stats['has_location']), "→ people.details.location")
    t.add_row("  Has user_id", f"{stats['user_id_present']:,}", pct(stats['user_id_present']), "→ people.user_id")
    t.add_row("    ...on existing person", f"{stats['user_id_on_existing_person']:,}", "", "Will set user_id on existing person")
    t.add_row("    ...on new person", f"{stats['user_id_new_person']:,}", "", "Will set user_id on new person")
    t.add_row("  Has details JSONB", f"{stats['has_details']:,}", pct(stats['has_details']), "→ people.details")
    t.add_row("", "", "", "")
    t.add_row("[bold]SUPPRESSION STATE[/bold]", "", "", "")
    t.add_row("  Globally bounced", f"{stats['bounced']:,}", pct(stats['bounced']), "→ emails.status = 'bounced'")
    t.add_row("  Globally unsubscribed", f"{stats['unsubscribed']:,}", pct(stats['unsubscribed']), "→ emails.status = 'suppressed'")
    t.add_row("", "", "", "")
    t.add_row("[bold]DUPLICATE EMAILS[/bold]", "", "", "")
    t.add_row("  Emails appearing >1 time", f"{len(dup_emails):,}", "", "Should be 0 (UNIQUE constraint)")

    console.print(t)

    # Source distribution
    console.print("\n[bold]Source Distribution (top 15):[/bold]")
    for source, count in source_counts.most_common(15):
        console.print(f"  {source}: {count:,}")

    # Contact types
    console.print("\n[bold]Contact Types Distribution:[/bold]")
    for ct, count in contact_type_counts.most_common():
        console.print(f"  {ct}: {count:,}")

    # Lead status
    console.print("\n[bold]Lead Status Distribution (from details JSONB):[/bold]")
    for ls, count in lead_status_counts.most_common():
        console.print(f"  {ls}: {count:,}")

    # Sample enriched people
    if enriched_people:
        console.print(f"\n[bold]Sample Enriched People (first 10 of {len(enriched_people)}):[/bold]")
        et = Table(show_header=True, header_style="bold")
        et.add_column("Contact Email")
        et.add_column("Contact Name")
        et.add_column("Existing Person")
        et.add_column("Existing Tags")
        et.add_column("Contact Types")
        et.add_column("Source")
        for ep in enriched_people[:10]:
            et.add_row(
                ep["email"],
                ep["contact_name"] or "—",
                ep["person_name"] or "—",
                str(ep["person_tags"]),
                str(ep["contact_types"]),
                ep["contact_source"] or "—",
            )
        console.print(et)

    # ── Write markdown report ────────────────────────────────────────────

    md = []
    md.append("# Contacts → CRM Migration Analysis\n")
    md.append(f"**Source**: Live `contacts` table ({total:,} rows)\n")
    md.append(f"**Target**: New CRM schema (people, emails, phones, organizations + junctions)\n\n")

    md.append("## Migration Impact Summary\n\n")
    md.append("| Action | Count | Notes |\n")
    md.append("|--------|------:|-------|\n")
    md.append(f"| **People to ENRICH** (email match) | {stats['email_match_with_person']:,} | Existing person gets new tags, lead_status, org links |\n")
    md.append(f"| **People to CREATE** (new email) | {stats['email_new']:,} | New person + email entity + junctions |\n")
    md.append(f"| Emails to create | {stats['email_new']:,} | |\n")
    md.append(f"| Emails already existing | {stats['email_match']:,} | |\n")
    md.append(f"| Phones to create | {stats['phone_new']:,} | |\n")
    md.append(f"| Phones already existing | {stats['phone_match']:,} | |\n")
    md.append(f"| Organizations to create | {len(new_orgs):,} | |\n")
    md.append(f"| Organizations to link (existing) | {stats['company_match']:,} | Exact name match |\n")
    md.append(f"| Bounce status to set | {stats['bounced']:,} | emails.status = 'bounced' |\n")
    md.append(f"| Suppression status to set | {stats['unsubscribed']:,} | emails.status = 'suppressed' |\n")
    md.append(f"| user_id links to set | {stats['user_id_present']:,} | |\n\n")

    md.append("## Post-Migration Totals (estimated)\n\n")
    md.append(f"| Entity | Current | + New | = Total |\n")
    md.append(f"|--------|--------:|------:|--------:|\n")
    md.append(f"| People | {len(existing_people):,} | {stats['email_new']:,} | ~{len(existing_people) + stats['email_new']:,} |\n")
    md.append(f"| Emails | {len(existing_emails):,} | {stats['email_new']:,} | ~{len(existing_emails) + stats['email_new']:,} |\n")
    md.append(f"| Phones | {len(existing_phones):,} | {stats['phone_new']:,} | ~{len(existing_phones) + stats['phone_new']:,} |\n")
    md.append(f"| Organizations | {len(existing_orgs):,} | {len(new_orgs):,} | ~{len(existing_orgs) + len(new_orgs):,} |\n\n")

    md.append("## Source Distribution\n\n")
    md.append("| Source | Count |\n")
    md.append("|--------|------:|\n")
    for source, count in source_counts.most_common():
        md.append(f"| {source} | {count:,} |\n")

    md.append("\n## Contact Types Distribution\n\n")
    md.append("| Type | Count |\n")
    md.append("|------|------:|\n")
    for ct, count in contact_type_counts.most_common():
        md.append(f"| {ct} | {count:,} |\n")

    md.append("\n## Lead Status Distribution\n\n")
    md.append("| Status | Count |\n")
    md.append("|--------|------:|\n")
    for ls, count in lead_status_counts.most_common():
        md.append(f"| {ls} | {count:,} |\n")

    output_path = os.path.join(os.path.dirname(__file__), "contacts_migration_analysis_report.md")
    with open(output_path, "w") as f:
        f.write("".join(md))

    console.print(f"\n📄 Report written to: {output_path}")


if __name__ == "__main__":
    main()
