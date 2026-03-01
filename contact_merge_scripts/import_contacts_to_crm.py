"""
import_contacts_to_crm.py

Migrates the `contacts` table into the consolidated CRM schema.
Reads contacts and writes to the new CRM tables (people, emails, phones,
organizations + junctions) in the same database. Run AFTER the QOZB and
Family Office imports so overlap detection works correctly.

Data flow per contact:
  contacts.email         → emails.address           + person_emails junction
  contacts.name          → people.first_name/last_name (split on first space)
  contacts.company       → organizations.name       + person_organizations junction
  contacts.role          → person_organizations.title
  contacts.phone_number  → phones.number            + person_phones junction
  contacts.contact_types → people.tags
  contacts.details       → people.details (selective merge)
  contacts.user_id       → people.user_id
  contacts.location      → people.details.location
  contacts.source        → person_emails.source
  contacts.globally_bounced      → emails.status = 'bounced'
  contacts.globally_unsubscribed → emails.status = 'suppressed'
  contacts.suppression_*         → emails.metadata

Merge rules:
  - Email match = same person → ENRICH (don't duplicate)
  - Organization match = exact name (case-insensitive) → LINK to existing
  - Lead status: warm > new (keep warmest)
  - Tags: merge (union of existing + new)
  - user_id: set if missing on existing person

Env vars required in oz-doc-processor/.env:
  SUPABASE_URL              – target database
  SUPABASE_SERVICE_ROLE_KEY – service role key

Usage:
  uv run contact_merge_scripts/import_contacts_to_crm.py [--dry-run] [--limit N]
"""

import os
import re
import sys
import json
import argparse
from collections import defaultdict, Counter
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

console = Console()

# ─── Lead status priority (higher = warmer) ────────────────────────────────────
LEAD_STATUS_PRIORITY = {
    "new": 0,
    "cold": 1,
    "warm": 2,
    "hot": 3,
    "customer": 4,
    "do_not_contact": 5,
}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def clean_str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "", "n/a") else None


def normalize_phone(val) -> Optional[str]:
    s = clean_str(val)
    if not s:
        return None
    digits = re.sub(r"\D", "", s)
    if len(digits) < 7 or all(c == "0" for c in digits):
        return None
    return digits


def split_name(full_name: str) -> tuple[Optional[str], Optional[str]]:
    """Split 'John Smith' → ('John', 'Smith'). Best effort."""
    if not full_name or not full_name.strip():
        return (None, None)
    parts = full_name.strip().split(None, 1)
    if len(parts) == 1:
        return (parts[0], None)
    return (parts[0], parts[1])


def warmer_status(a: Optional[str], b: Optional[str]) -> str:
    """Return the warmer of two lead statuses."""
    pa = LEAD_STATUS_PRIORITY.get(a or "new", 0)
    pb = LEAD_STATUS_PRIORITY.get(b or "new", 0)
    if pa >= pb:
        return a or "new"
    return b or "new"


def merge_tags(existing: list, new_tags: list) -> list:
    """Union two tag lists, preserving order."""
    seen = set(existing or [])
    result = list(existing or [])
    for t in (new_tags or []):
        if t and t not in seen:
            result.append(t)
            seen.add(t)
    return result


def clean_email(val) -> Optional[str]:
    """Normalize email: lowercase, trim, handle comma-separated (take first valid)."""
    if val is None:
        return None
    s = str(val).strip().lower()
    for candidate in s.split(","):
        candidate = candidate.strip()
        if "@" in candidate and len(candidate) <= 254:
            return candidate
    return None


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


def upsert_batch(supabase, table: str, rows: list[dict], on_conflict: str,
                 batch_size: int = 200, progress_task=None, progress=None) -> int:
    """Upsert rows in batches, return count of rows processed."""
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        result = (
            supabase.table(table)
            .upsert(batch, on_conflict=on_conflict)
            .execute()
        )
        total += len(batch)
        if progress and progress_task is not None:
            progress.update(progress_task, advance=len(batch))
    return total


def insert_batch(supabase, table: str, rows: list[dict],
                 batch_size: int = 200, progress_task=None, progress=None) -> int:
    """Insert rows in batches, return count."""
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        result = (
            supabase.table(table)
            .insert(batch)
            .execute()
        )
        total += len(batch)
        if progress and progress_task is not None:
            progress.update(progress_task, advance=len(batch))
    return total


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Migrate contacts → CRM")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, no writes")
    parser.add_argument("--limit", type=int, default=0, help="Limit contacts to process (0 = all)")
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else "LIVE"

    console.print(Panel(
        f"[bold]Contacts → CRM Migration[/bold]\n"
        f"Reads contacts and writes to new CRM schema (same database)\n"
        f"Mode: [{'yellow' if args.dry_run else 'red'}]{mode}[/{'yellow' if args.dry_run else 'red'}]"
        + (f"\nLimit: {args.limit:,} contacts" if args.limit else ""),
        title="oz-doc-processor",
    ))

    # ── Connect ──────────────────────────────────────────────────────────────
    env_path = os.path.join(os.path.dirname(__file__), "../.env")
    load_dotenv(env_path)

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        console.print("[red]ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required[/red]")
        sys.exit(1)

    from supabase import create_client
    supabase = create_client(url, key)
    console.print(f"[green]Connected to:[/green] {url}")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 1: Fetch all data
    # ══════════════════════════════════════════════════════════════════════════

    console.print("\n[bold magenta]Phase 1: Fetching data[/bold magenta]")

    console.print("  Fetching contacts...")
    contacts = fetch_all(supabase, "contacts",
        "id,email,name,company,role,location,source,phone_number,details,"
        "contact_type,contact_types,user_id,"
        "globally_bounced,globally_unsubscribed,suppression_reason,suppression_date,"
        "created_at,updated_at")
    console.print(f"  → {len(contacts):,} contacts")

    if args.limit:
        contacts = contacts[:args.limit]
        console.print(f"  [yellow]Limited to {len(contacts):,} contacts[/yellow]")

    console.print("  Fetching existing CRM entities...")
    existing_emails = fetch_all(supabase, "emails", "id,address,status")
    existing_phones = fetch_all(supabase, "phones", "id,number")
    existing_orgs = fetch_all(supabase, "organizations", "id,name,org_type")
    existing_people = fetch_all(supabase, "people", "id,first_name,last_name,tags,lead_status,user_id")
    existing_pe = fetch_all(supabase, "person_emails", "person_id,email_id")
    existing_po = fetch_all(supabase, "person_organizations", "person_id,organization_id")
    existing_pp = fetch_all(supabase, "person_phones", "person_id,phone_id")

    console.print(f"  → emails: {len(existing_emails):,}  phones: {len(existing_phones):,}  "
                  f"orgs: {len(existing_orgs):,}  people: {len(existing_people):,}")

    # ── Build lookup maps ────────────────────────────────────────────────────
    email_id_map = {e["address"].lower().strip(): e["id"]
                    for e in existing_emails if e.get("address")}
    phone_id_map = {p["number"]: p["id"]
                    for p in existing_phones if p.get("number")}
    org_id_map = {o["name"].lower().strip(): o["id"]
                  for o in existing_orgs if o.get("name")}

    # email_id → person_id
    email_to_person = {}
    for pe in existing_pe:
        eid = pe["email_id"]
        if eid not in email_to_person:
            email_to_person[eid] = pe["person_id"]

    # person_id → person record
    person_map = {p["id"]: p for p in existing_people}

    # existing junction sets (to avoid duplicate inserts)
    existing_pe_set = {(pe["person_id"], pe["email_id"]) for pe in existing_pe}
    existing_po_set = {(po["person_id"], po["organization_id"]) for po in existing_po}
    existing_pp_set = {(pp["person_id"], pp["phone_id"]) for pp in existing_pp}

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 2: Collect unique entities from contacts
    # ══════════════════════════════════════════════════════════════════════════

    console.print("\n[bold magenta]Phase 2: Collecting unique entities[/bold magenta]")

    # Dedup tracking
    emails_to_upsert: dict[str, dict] = {}     # address → record
    phones_to_upsert: dict[str, dict] = {}     # digits → record
    orgs_to_upsert: dict[str, dict] = {}       # name_lower → record
    seen_contact_emails: set[str] = set()       # handle the 4 duplicate emails

    # Per-contact parsed data for phase 4
    parsed_contacts: list[dict] = []

    with Progress(
        SpinnerColumn(), TextColumn("[bold blue]Scanning contacts...[/bold blue]"),
        BarColumn(), MofNCompleteColumn(), console=console,
    ) as progress:
        task = progress.add_task("scan", total=len(contacts))

        for c in contacts:
            progress.advance(task)

            email = clean_email(c.get("email"))
            if not email:
                continue

            # Handle duplicate emails (4 cases) — first wins
            if email in seen_contact_emails:
                continue
            seen_contact_emails.add(email)

            name = clean_str(c.get("name"))
            company = clean_str(c.get("company"))
            role = clean_str(c.get("role"))
            phone = normalize_phone(c.get("phone_number"))
            source = clean_str(c.get("source"))
            location = clean_str(c.get("location"))
            details = c.get("details") if isinstance(c.get("details"), dict) else {}
            contact_types = c.get("contact_types") or []
            user_id = c.get("user_id")
            bounced = c.get("globally_bounced") or False
            unsub = c.get("globally_unsubscribed") or False
            supp_reason = clean_str(c.get("suppression_reason"))
            supp_date = c.get("suppression_date")
            created_at = c.get("created_at")
            updated_at = c.get("updated_at")

            first_name, last_name = split_name(name)

            # Determine email status from suppression fields
            email_status = "active"
            email_metadata: dict = {}
            if bounced:
                email_status = "bounced"
            if unsub:
                email_status = "suppressed"
                if supp_reason:
                    email_metadata["suppression_reason"] = supp_reason
                if supp_date:
                    email_metadata["suppression_date"] = supp_date

            if isinstance(details, dict) and "email_status" in details:
                email_metadata["verification_status"] = details["email_status"]

            # Determine lead_status
            lead_status = details.get("lead_status", "new") if isinstance(details, dict) else "new"
            if not lead_status or lead_status not in LEAD_STATUS_PRIORITY:
                lead_status = "new"

            # Determine org_type from contact_types
            org_type = None
            if "developer" in contact_types:
                org_type = "developer"
            elif "investor" in contact_types:
                org_type = "investor"
            elif "fund" in contact_types:
                org_type = "fund"

            # ── Collect email entity ─────────────────────────────
            if email not in emails_to_upsert:
                emails_to_upsert[email] = {
                    "address": email,
                    "status": email_status,
                    "metadata": email_metadata if email_metadata else {},
                }
            else:
                # If this email is bounced/suppressed, mark it
                existing = emails_to_upsert[email]
                if email_status != "active":
                    existing["status"] = email_status
                    if email_metadata:
                        existing["metadata"] = {**existing.get("metadata", {}), **email_metadata}

            # ── Collect phone entity ─────────────────────────────
            if phone and phone not in phones_to_upsert:
                phones_to_upsert[phone] = {"number": phone, "status": "active"}

            # ── Collect org entity ───────────────────────────────
            if company:
                company_lower = company.lower().strip()
                if company_lower not in orgs_to_upsert and company_lower not in org_id_map:
                    orgs_to_upsert[company_lower] = {
                        "name": company,   # preserve original casing
                        "org_type": org_type,
                    }

            # ── Build people details ─────────────────────────────
            # Selective migration of details JSONB
            people_details: dict = {}
            if location:
                people_details["location"] = location
            if source:
                people_details["import_source"] = source
            # Carry over useful details fields
            for key in ("engagement_type", "last_webinar_attended",
                        "order_id", "order_date", "event_name", "ticket_type",
                        "raw", "lead_status"):
                if key in details and key != "lead_status":
                    people_details[key] = details[key]

            parsed_contacts.append({
                "contact_id": c["id"],
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "company": company,
                "company_lower": company.lower().strip() if company else None,
                "role": role,
                "phone": phone,
                "source": source,
                "contact_types": contact_types,
                "user_id": user_id,
                "lead_status": lead_status,
                "details": people_details,
                "created_at": created_at,
                "updated_at": updated_at,
            })

    # Only upsert emails that don't already exist
    new_emails = {addr: rec for addr, rec in emails_to_upsert.items() if addr not in email_id_map}
    existing_email_contacts = {addr: rec for addr, rec in emails_to_upsert.items() if addr in email_id_map}

    # Only upsert phones that don't already exist
    new_phones = {num: rec for num, rec in phones_to_upsert.items() if num not in phone_id_map}

    console.print(f"  Unique contacts (after dedup): {len(parsed_contacts):,}")
    console.print(f"  Emails: {len(new_emails):,} new, {len(existing_email_contacts):,} existing")
    console.print(f"  Phones: {len(new_phones):,} new, {len(phones_to_upsert) - len(new_phones):,} existing")
    console.print(f"  Organizations: {len(orgs_to_upsert):,} new")

    if args.dry_run:
        console.print("\n[yellow]DRY RUN — no writes performed.[/yellow]")
        _print_summary(parsed_contacts, new_emails, existing_email_contacts,
                       new_phones, orgs_to_upsert, email_id_map, email_to_person, person_map)
        return

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 3: Upsert entity tables
    # ══════════════════════════════════════════════════════════════════════════

    console.print("\n[bold magenta]Phase 3: Upserting entity tables[/bold magenta]")

    with Progress(
        SpinnerColumn(), TextColumn("[bold blue]Upserting...[/bold blue]"),
        BarColumn(), MofNCompleteColumn(), console=console,
    ) as progress:

        # ── Emails ────────────────────────────────────────────
        if new_emails:
            t = progress.add_task("Upserting emails...", total=len(new_emails))
            email_rows = list(new_emails.values())
            upsert_batch(supabase, "emails", email_rows, on_conflict="address",
                         progress_task=t, progress=progress)

        # Also update status on existing emails if they're now bounced/suppressed
        status_updates = []
        for addr, rec in existing_email_contacts.items():
            if rec["status"] != "active":
                status_updates.append({
                    "address": addr,
                    "status": rec["status"],
                    "metadata": rec.get("metadata", {}),
                })
        if status_updates:
            t = progress.add_task("Updating email statuses...", total=len(status_updates))
            upsert_batch(supabase, "emails", status_updates, on_conflict="address",
                         progress_task=t, progress=progress)
            console.print(f"  Updated {len(status_updates):,} email statuses (bounced/suppressed)")

        # ── Phones ────────────────────────────────────────────
        if new_phones:
            t = progress.add_task("Upserting phones...", total=len(new_phones))
            phone_rows = list(new_phones.values())
            upsert_batch(supabase, "phones", phone_rows, on_conflict="number",
                         progress_task=t, progress=progress)

        # ── Organizations ─────────────────────────────────────
        if orgs_to_upsert:
            t = progress.add_task("Upserting organizations...", total=len(orgs_to_upsert))
            org_rows = list(orgs_to_upsert.values())
            upsert_batch(supabase, "organizations", org_rows, on_conflict="name",
                         progress_task=t, progress=progress)

    # ── Refresh ID maps after upserts ────────────────────────────────────
    console.print("  Refreshing ID maps...")
    all_emails_now = fetch_all(supabase, "emails", "id,address")
    email_id_map = {e["address"].lower().strip(): e["id"] for e in all_emails_now if e.get("address")}

    all_phones_now = fetch_all(supabase, "phones", "id,number")
    phone_id_map = {p["number"]: p["id"] for p in all_phones_now if p.get("number")}

    all_orgs_now = fetch_all(supabase, "organizations", "id,name")
    org_id_map = {o["name"].lower().strip(): o["id"] for o in all_orgs_now if o.get("name")}

    console.print(f"  → emails: {len(email_id_map):,}  phones: {len(phone_id_map):,}  orgs: {len(org_id_map):,}")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 4: Resolve people (match existing or prepare new)
    # ══════════════════════════════════════════════════════════════════════════

    console.print("\n[bold magenta]Phase 4: Resolving people[/bold magenta]")

    new_people_records: list[dict] = []         # people to INSERT
    enrichments: list[dict] = []                # existing people to UPDATE
    contact_id_to_person_idx: dict[str, int] = {}  # contact_id → index in new_people_records
    contact_id_to_existing: dict[str, str] = {}    # contact_id → existing person_id

    # Junction records to insert
    junction_pe: list[dict] = []   # person_emails
    junction_pp: list[dict] = []   # person_phones
    junction_po: list[dict] = []   # person_organizations

    with Progress(
        SpinnerColumn(), TextColumn("[bold blue]Resolving people...[/bold blue]"),
        BarColumn(), MofNCompleteColumn(), console=console,
    ) as progress:
        task = progress.add_task("resolve", total=len(parsed_contacts))

        for pc in parsed_contacts:
            progress.advance(task)

            email = pc["email"]
            email_id = email_id_map.get(email)
            if not email_id:
                console.print(f"  [red]WARNING: email '{email}' not in email_id_map after upsert![/red]")
                continue

            phone = pc["phone"]
            phone_id = phone_id_map.get(phone) if phone else None

            company_lower = pc["company_lower"]
            org_id = org_id_map.get(company_lower) if company_lower else None

            # ── Check if email is already linked to a person ──
            existing_person_id = email_to_person.get(email_id)
            if existing_person_id:
                # ENRICH existing person
                person = person_map.get(existing_person_id, {})
                existing_tags = person.get("tags") or []
                existing_lead = person.get("lead_status") or "new"

                merged_tags = merge_tags(existing_tags, pc["contact_types"])
                merged_lead = warmer_status(existing_lead, pc["lead_status"])

                enrichment = {
                    "person_id": existing_person_id,
                    "updates": {},
                }

                if merged_tags != existing_tags:
                    enrichment["updates"]["tags"] = merged_tags
                if merged_lead != existing_lead:
                    enrichment["updates"]["lead_status"] = merged_lead
                if pc["user_id"] and not person.get("user_id"):
                    enrichment["updates"]["user_id"] = pc["user_id"]
                # Merge details
                existing_details = person.get("details") or {}
                if pc["details"]:
                    merged_details = {**existing_details, **pc["details"]}
                    if merged_details != existing_details:
                        enrichment["updates"]["details"] = merged_details

                if enrichment["updates"]:
                    enrichments.append(enrichment)

                contact_id_to_existing[pc["contact_id"]] = existing_person_id
                person_id_placeholder = existing_person_id

                # Add phone junction if missing
                if phone_id and (existing_person_id, phone_id) not in existing_pp_set:
                    junction_pp.append({
                        "person_id": existing_person_id,
                        "phone_id": phone_id,
                        "label": "work",
                        "source": "contacts_import",
                    })
                    existing_pp_set.add((existing_person_id, phone_id))

                # Add org junction if missing
                if org_id and (existing_person_id, org_id) not in existing_po_set:
                    junction_po.append({
                        "person_id": existing_person_id,
                        "organization_id": org_id,
                        "title": pc["role"],
                    })
                    existing_po_set.add((existing_person_id, org_id))

            else:
                # CREATE new person
                person_record = {
                    "first_name": pc["first_name"],
                    "last_name": pc["last_name"],
                    "tags": pc["contact_types"] if pc["contact_types"] else [],
                    "lead_status": pc["lead_status"],
                    "details": pc["details"] if pc["details"] else {},
                    "created_at": pc["created_at"],
                }
                if pc["user_id"]:
                    person_record["user_id"] = pc["user_id"]

                idx = len(new_people_records)
                new_people_records.append(person_record)
                contact_id_to_person_idx[pc["contact_id"]] = idx

                # We'll create junctions after we have person IDs
                # Store the pending junction data on the record itself
                person_record["_email_id"] = email_id
                person_record["_phone_id"] = phone_id
                person_record["_org_id"] = org_id
                person_record["_role"] = pc["role"]
                person_record["_source"] = pc["source"]
                person_record["_contact_id"] = pc["contact_id"]

    console.print(f"  New people to create: {len(new_people_records):,}")
    console.print(f"  Existing people to enrich: {len(enrichments):,}")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 5: Insert new people
    # ══════════════════════════════════════════════════════════════════════════

    console.print("\n[bold magenta]Phase 5: Inserting people[/bold magenta]")

    # Strip internal fields before insert
    people_to_insert = []
    for pr in new_people_records:
        clean_record = {k: v for k, v in pr.items() if not k.startswith("_")}
        people_to_insert.append(clean_record)

    # Insert in batches and collect IDs
    new_person_ids: list[str] = []
    batch_size = 200
    with Progress(
        SpinnerColumn(), TextColumn("[bold blue]Inserting people...[/bold blue]"),
        BarColumn(), MofNCompleteColumn(), console=console,
    ) as progress:
        task = progress.add_task("insert", total=len(people_to_insert))

        for i in range(0, len(people_to_insert), batch_size):
            batch = people_to_insert[i : i + batch_size]
            result = supabase.table("people").insert(batch).execute()
            for row in result.data:
                new_person_ids.append(row["id"])
            progress.update(task, advance=len(batch))

    console.print(f"  Inserted {len(new_person_ids):,} people")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 6: Enrich existing people
    # ══════════════════════════════════════════════════════════════════════════

    console.print("\n[bold magenta]Phase 6: Enriching existing people[/bold magenta]")

    with Progress(
        SpinnerColumn(), TextColumn("[bold blue]Enriching...[/bold blue]"),
        BarColumn(), MofNCompleteColumn(), console=console,
    ) as progress:
        task = progress.add_task("enrich", total=len(enrichments))

        for enr in enrichments:
            if enr["updates"]:
                supabase.table("people").update(enr["updates"]).eq("id", enr["person_id"]).execute()
            progress.advance(task)

    console.print(f"  Enriched {len(enrichments):,} existing people")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 7: Insert junction records
    # ══════════════════════════════════════════════════════════════════════════

    console.print("\n[bold magenta]Phase 7: Inserting junction records[/bold magenta]")

    # Build junctions for new people (now that we have IDs)
    for idx, person_id in enumerate(new_person_ids):
        pr = new_people_records[idx]

        email_id = pr["_email_id"]
        phone_id = pr["_phone_id"]
        org_id = pr["_org_id"]
        role = pr["_role"]
        source = pr["_source"]
        contact_id = pr["_contact_id"]

        # person ↔ email
        junction_pe.append({
            "person_id": person_id,
            "email_id": email_id,
            "label": "primary",
            "is_primary": True,
            "source": source or "contacts_import",
        })

        # person ↔ phone
        if phone_id:
            junction_pp.append({
                "person_id": person_id,
                "phone_id": phone_id,
                "label": "work",
                "source": "contacts_import",
            })

        # person ↔ org
        if org_id:
            junction_po.append({
                "person_id": person_id,
                "organization_id": org_id,
                "title": role,
            })

        # Map contact_id → person_id
        contact_id_to_existing[contact_id] = person_id

    with Progress(
        SpinnerColumn(), TextColumn("[bold blue]Upserting junctions...[/bold blue]"),
        BarColumn(), MofNCompleteColumn(), console=console,
    ) as progress:

        if junction_pe:
            t = progress.add_task("person_emails...", total=len(junction_pe))
            upsert_batch(supabase, "person_emails", junction_pe,
                         on_conflict="person_id,email_id", progress_task=t, progress=progress)
            console.print(f"  person_emails: {len(junction_pe):,} rows")

        if junction_pp:
            t = progress.add_task("person_phones...", total=len(junction_pp))
            upsert_batch(supabase, "person_phones", junction_pp,
                         on_conflict="person_id,phone_id", progress_task=t, progress=progress)
            console.print(f"  person_phones: {len(junction_pp):,} rows")

        if junction_po:
            t = progress.add_task("person_organizations...", total=len(junction_po))
            upsert_batch(supabase, "person_organizations", junction_po,
                         on_conflict="person_id,organization_id", progress_task=t, progress=progress)
            console.print(f"  person_organizations: {len(junction_po):,} rows")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 8: Save contacts.id → people.id mapping
    # ══════════════════════════════════════════════════════════════════════════

    console.print("\n[bold magenta]Phase 8: Saving contact→person mapping[/bold magenta]")

    # Build enriched mapping that includes user_id for production backfill
    mapping_with_user_ids = {}
    for pc in parsed_contacts:
        person_id = contact_id_to_existing.get(pc["contact_id"])
        if person_id:
            entry = {"person_id": person_id}
            if pc.get("user_id"):
                entry["user_id"] = pc["user_id"]
            mapping_with_user_ids[pc["contact_id"]] = entry

    mapping_path = os.path.join(os.path.dirname(__file__), "contacts_to_people_mapping.json")
    with open(mapping_path, "w") as f:
        json.dump(mapping_with_user_ids, f, indent=2)
    console.print(f"  Mapping saved: {mapping_path}")
    console.print(f"  Total mappings: {len(mapping_with_user_ids):,}")

    user_id_count = sum(1 for v in mapping_with_user_ids.values() if "user_id" in v)
    console.print(f"  Mappings with user_id: {user_id_count:,} (for production backfill)")

    # ══════════════════════════════════════════════════════════════════════════
    # Summary
    # ══════════════════════════════════════════════════════════════════════════

    t = Table(title="Import Summary", show_header=True, header_style="bold magenta")
    t.add_column("Table", style="cyan")
    t.add_column("Records", justify="right", style="green")
    t.add_column("Notes", style="dim")
    t.add_row("emails (new)", f"{len(new_emails):,}", "upserted on address")
    t.add_row("emails (status updated)", f"{len(status_updates):,}" if status_updates else "0", "bounced/suppressed")
    t.add_row("phones (new)", f"{len(new_phones):,}", "upserted on number")
    t.add_row("organizations (new)", f"{len(orgs_to_upsert):,}", "upserted on name")
    t.add_row("people (created)", f"{len(new_person_ids):,}", "new people from contacts")
    t.add_row("people (enriched)", f"{len(enrichments):,}", "existing people updated")
    t.add_row("person_emails", f"{len(junction_pe):,}", "")
    t.add_row("person_phones", f"{len(junction_pp):,}", "")
    t.add_row("person_organizations", f"{len(junction_po):,}", "")
    t.add_row("contact→person mapping", f"{len(contact_id_to_existing):,}", mapping_path)
    console.print(t)

    console.print(Panel("[bold green]Import complete.[/bold green]"))


def _print_summary(parsed, new_emails, existing_emails, new_phones, new_orgs,
                   email_id_map, email_to_person, person_map):
    """Print dry-run summary."""
    enrich_count = 0
    create_count = 0
    for pc in parsed:
        email_id = email_id_map.get(pc["email"])
        if email_id and email_to_person.get(email_id):
            enrich_count += 1
        else:
            create_count += 1

    t = Table(title="Dry Run Summary", show_header=True, header_style="bold yellow")
    t.add_column("Action", style="cyan")
    t.add_column("Count", justify="right", style="green")
    t.add_row("Contacts processed", f"{len(parsed):,}")
    t.add_row("Emails to create", f"{len(new_emails):,}")
    t.add_row("Emails already existing", f"{len(existing_emails):,}")
    t.add_row("Phones to create", f"{len(new_phones):,}")
    t.add_row("Organizations to create", f"{len(new_orgs):,}")
    t.add_row("People to CREATE", f"{create_count:,}")
    t.add_row("People to ENRICH", f"{enrich_count:,}")
    console.print(t)


if __name__ == "__main__":
    main()
