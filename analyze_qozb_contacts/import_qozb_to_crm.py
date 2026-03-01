"""
import_qozb_to_crm.py

Imports the QOZB Development Projects CSV into the new consolidated CRM schema.

Tables populated:
  • properties          – one per CSV row, dedup on (property_name, address)
  • organizations       – one per unique entity name, dedup on name (exact)
  • phones              – one per unique normalized phone number
  • emails              – one per unique email address (Owner only)
  • people              – deduped on (phone, normalized_name)
  • person_phones       – person ↔ phone junction
  • person_emails       – person ↔ email junction (Owner only)
  • person_organizations    – person ↔ org junction (with title = role)
  • person_properties       – person ↔ property junction (with role)
  • property_phones         – orphan property-level phones ↔ property junction
  • property_organizations  – direct property ↔ org junction (with role)

Tags applied to all imported people: ['qozb_property_contact']

Usage:
  uv run analyze_qozb_contacts/import_qozb_to_crm.py
  uv run analyze_qozb_contacts/import_qozb_to_crm.py --dry-run
  uv run analyze_qozb_contacts/import_qozb_to_crm.py --limit 100
  uv run analyze_qozb_contacts/import_qozb_to_crm.py --dry-run --limit 500

Environment variables required (in oz-doc-processor/.env):
  SUPABASE_URL              – e.g. https://xxxx.supabase.co
  SUPABASE_SERVICE_ROLE_KEY – service role key (bypasses RLS for bulk import)
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

CSV_PATH = "/Users/aryanjain/Documents/OZL/UsefulDocs/QOZB-Contacts/All QOZB Development Projects USA - 20260126.xlsx - Results.csv"

BATCH_SIZE = 500  # rows per Supabase upsert call

PEOPLE_TAGS = ["qozb_property_contact"]

# Entity name strings that are placeholders, not real organizations.
# Never create an organizations record for these.
FAKE_ENTITY_NAMES = {
    "", "nan", "n/a", "na", "none", "unknown", "tbd", "pending",
    "not available", "owner managed", "owner-managed",
    "self managed", "self-managed",
}

# CSV column definitions per role
ROLES = [
    {
        "role":      "owner",
        "entity":    "Owner",
        "first":     "Owner Contact First Name",
        "last":      "Owner Contact Last Name",
        "email":     "Owner Contact Email",        # Only Owner has email
        "phone":     "Owner Contact Phone Number",
        "addr":      "Owner Address",
        "city":      "Owner City",
        "state":     "Owner State",
        "zip":       "Owner ZIP",
        "country":   "Owner Country",
        "website":   "Owner Website",
    },
    {
        "role":      "manager",
        "entity":    "Manager",
        "first":     "Manager Contact First Name",
        "last":      "Manager Contact Last Name",
        "email":     None,
        "phone":     "Manager Contact Phone Number",
        "addr":      "Manager Address",
        "city":      "Manager City",
        "state":     "Manager State",
        "zip":       "Manager ZIP",
        "country":   "Manager Country",
        "website":   "Manager Website",
    },
    {
        "role":      "trustee",
        "entity":    "Trustee",
        "first":     "Trustee Contact First Name",
        "last":      "Trustee Contact Last Name",
        "email":     None,
        "phone":     "Trustee Contact Phone Number",
        "addr":      "Trustee Address",
        "city":      "Trustee City",
        "state":     "Trustee State",
        "zip":       "Trustee ZIP",
        "country":   "Trustee Country",
        "website":   "Trustee Website",
    },
    {
        "role":      "special_servicer",
        "entity":    "Special Servicer",
        "first":     "Special Servicer Contact First Name",
        "last":      "Special Servicer Contact Last Name",
        "email":     None,
        "phone":     "Special Servicer Contact Phone Number",
        "addr":      "Special Servicer Address",
        "city":      "Special Servicer City",
        "state":     "Special Servicer State",
        "zip":       "Special Servicer ZIP",
        "country":   "Special Servicer Country",
        "website":   "Special Servicer Website",
    },
]

console = Console()

# ─── Helpers ───────────────────────────────────────────────────────────────────

def clean_str(val) -> Optional[str]:
    """Return stripped string or None if empty/nan."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    return s if s and s.lower() != "nan" else None

def normalize_phone(val) -> Optional[str]:
    """Return digits-only phone string, or None if unusable."""
    s = clean_str(val)
    if not s:
        return None
    # Remove decimal suffix that pandas adds (e.g. 5184340726.0 → 5184340726)
    s = s.split(".")[0].strip()
    digits = re.sub(r"\D", "", s)
    # Must be at least 7 digits and not all zeros
    if len(digits) < 7 or all(c == "0" for c in digits):
        return None
    return digits

def normalize_email(val) -> Optional[str]:
    """Return lowercase trimmed email or None."""
    s = clean_str(val)
    if not s or "@" not in s:
        return None
    return s.lower()

def normalize_name(first, last) -> Optional[str]:
    """Return 'firstname lastname' lower-cased, or None if both empty."""
    f = clean_str(first) or ""
    l = clean_str(last) or ""
    full = f"{f} {l}".strip().lower()
    return full if full else None

def is_fake_entity(name: Optional[str]) -> bool:
    if not name:
        return True
    return name.strip().lower() in FAKE_ENTITY_NAMES

def batch(lst: list, n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]

# ─── Phase 1: First pass — collect unique entities ─────────────────────────────

def phase1_collect(df: pd.DataFrame, limit: Optional[int]):
    """
    Single pass through CSV rows. Collects:
      - unique_phones:       dict[number] = phone_data
      - unique_orgs:         dict[name] = org_data  (most-common fields wins)
      - unique_properties:   dict[(name, addr)] = property_data
      - orphan_prop_phones:  list of (prop_key, phone_digits)
      - property_org_links:  list of (prop_key, entity_name, role) — direct property↔org links
      - contact_slots:       list of dicts describing each role-slot (for Phase 3)
    """
    unique_phones:     dict[str, dict] = {}
    org_field_counts:  dict[str, dict] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    unique_orgs:       dict[str, dict] = {}
    unique_properties: dict[tuple, dict] = {}
    orphan_prop_phones: list[tuple] = []   # (prop_key, phone_digits)
    property_org_links: list[tuple] = []   # (prop_key, entity_name, role)
    contact_slots:     list[dict] = []

    rows = df.iterrows()
    total = limit or len(df)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Phase 1:[/bold blue] Scanning CSV..."),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("scan", total=total)

        for i, (_, row) in enumerate(rows):
            if limit and i >= limit:
                break
            progress.advance(task)

            # ── Property ─────────────────────────────────────────────
            prop_name = clean_str(row.get("Property Name")) or f"Unknown_{i}"
            address   = clean_str(row.get("Address")) or ""
            prop_key  = (prop_name, address)

            if prop_key not in unique_properties:
                unique_properties[prop_key] = {
                    "property_name": prop_name,
                    "address":       address,
                    "city":          clean_str(row.get("City")),
                    "state":         clean_str(row.get("State")),
                    "zip":           clean_str(row.get("ZIP")),
                    "details": {
                        "source":                   "qozb_import",
                        "qozb_property_id":         clean_str(row.get("PropertyID")),
                        "market":                   clean_str(row.get("Market")),
                        "submarket":                clean_str(row.get("Submarket")),
                        "county":                   clean_str(row.get("County")),
                        "units":                    clean_str(row.get("Units")),
                        "sqft":                     clean_str(row.get("SqFt")),
                        "completion_date":          clean_str(row.get("Completion Date")),
                        "impr_rating":              clean_str(row.get("Impr. Rating")),
                        "loc_rating":               clean_str(row.get("Loc. Rating")),
                        "property_special_status":  clean_str(row.get("Property Special Status")),
                        "latitude":                 clean_str(row.get("Latitude")),
                        "longitude":                clean_str(row.get("Longitude")),
                    },
                }

            # ── Orphan property-level phone ───────────────────────────
            prop_phone = normalize_phone(row.get("Phone Number"))
            # Collect per-row contact phones so we can detect if prop phone is orphan
            contact_phones_this_row = set()
            for rc in ROLES:
                cp = normalize_phone(row.get(rc["phone"]))
                if cp:
                    contact_phones_this_row.add(cp)

            if prop_phone and prop_phone not in contact_phones_this_row:
                orphan_prop_phones.append((prop_key, prop_phone))
                if prop_phone not in unique_phones:
                    unique_phones[prop_phone] = {"number": prop_phone, "status": "active", "metadata": {}}

            # ── Per-role contacts ─────────────────────────────────────
            for rc in ROLES:
                entity_name = clean_str(row.get(rc["entity"]))
                first_name  = clean_str(row.get(rc["first"]))
                last_name   = clean_str(row.get(rc["last"]))
                phone       = normalize_phone(row.get(rc["phone"]))
                email_col   = rc.get("email")
                email       = normalize_email(row.get(email_col)) if email_col else None

                # Org
                if not is_fake_entity(entity_name):
                    city    = clean_str(row.get(rc["city"]))
                    state   = clean_str(row.get(rc["state"]))
                    zip_    = clean_str(row.get(rc["zip"]))
                    country = clean_str(row.get(rc["country"]))
                    website = clean_str(row.get(rc["website"]))
                    addr    = clean_str(row.get(rc["addr"]))

                    # Track field occurrence counts for most-common selection
                    if city:    org_field_counts[entity_name]["city"][city]    += 1
                    if state:   org_field_counts[entity_name]["state"][state]  += 1
                    if zip_:    org_field_counts[entity_name]["zip"][zip_]     += 1
                    if website: org_field_counts[entity_name]["website"][website] += 1
                    if addr:    org_field_counts[entity_name]["address"][addr] += 1
                    if country: org_field_counts[entity_name]["country"][country] += 1

                    if entity_name not in unique_orgs:
                        unique_orgs[entity_name] = {"name": entity_name, "org_type": "qozb_entity"}

                    # Direct property → org link
                    property_org_links.append((prop_key, entity_name, rc["role"]))

                # Phone entity
                if phone and phone not in unique_phones:
                    unique_phones[phone] = {"number": phone, "status": "active", "metadata": {}}

                # Email entity
                # (will be collected into unique_emails during slot processing — below)

                # Record this slot for Phase 3
                contact_slots.append({
                    "prop_key":    prop_key,
                    "role":        rc["role"],
                    "entity_name": entity_name if not is_fake_entity(entity_name) else None,
                    "first_name":  first_name,
                    "last_name":   last_name,
                    "phone":       phone,
                    "email":       email,
                })

    # Resolve most-common field values for each org
    for org_name, field_counts in org_field_counts.items():
        if org_name in unique_orgs:
            for field, counter in field_counts.items():
                if counter:
                    top_value = max(counter, key=counter.get)
                    unique_orgs[org_name][field] = top_value

    # Collect unique emails from slots
    unique_emails: dict[str, dict] = {}
    for slot in contact_slots:
        e = slot.get("email")
        if e and e not in unique_emails:
            unique_emails[e] = {"address": e, "status": "active", "metadata": {}}

    console.print(f"  [dim]Unique properties:  {len(unique_properties):,}[/dim]")
    console.print(f"  [dim]Unique orgs:        {len(unique_orgs):,}[/dim]")
    console.print(f"  [dim]Unique phones:      {len(unique_phones):,}[/dim]")
    console.print(f"  [dim]Unique emails:      {len(unique_emails):,}[/dim]")
    console.print(f"  [dim]Contact slots:      {len(contact_slots):,}[/dim]")
    console.print(f"  [dim]Orphan prop phones: {len(orphan_prop_phones):,}[/dim]")
    console.print(f"  [dim]Property→org links: {len(property_org_links):,}[/dim]")

    return unique_phones, unique_emails, unique_orgs, unique_properties, orphan_prop_phones, property_org_links, contact_slots


# ─── Phase 2: Batch upsert entities → ID maps ──────────────────────────────────

def upsert_batch(supabase, table: str, records: list[dict], on_conflict: str, label: str) -> dict:
    """
    Batch upsert records into a table. Returns a dict keyed by the conflict field value → id.
    For composite conflict keys, the key is a tuple.
    """
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
                # Build the map key
                if len(conflict_cols) == 1:
                    key = row[conflict_cols[0]]
                else:
                    key = tuple(row[c] for c in conflict_cols)
                id_map[key] = row["id"]
            progress.advance(task, len(chunk))

    return id_map


def phase2_upsert_entities(supabase, unique_phones, unique_emails, unique_orgs, unique_properties, dry_run: bool):
    """
    Batch upsert all entity tables. Returns ID maps for phases 3 & 4.
    In dry-run mode, returns empty maps.
    """
    if dry_run:
        console.print("[yellow]DRY RUN: skipping database writes[/yellow]")
        return {}, {}, {}, {}

    phone_id_map    = upsert_batch(supabase, "phones",        list(unique_phones.values()),    "number",                "phones")
    email_id_map    = upsert_batch(supabase, "emails",        list(unique_emails.values()),    "address",               "emails")
    org_id_map      = upsert_batch(supabase, "organizations", list(unique_orgs.values()),      "name",                  "organizations")
    property_id_map = upsert_batch(supabase, "properties",    list(unique_properties.values()), "property_name,address", "properties")

    return phone_id_map, email_id_map, org_id_map, property_id_map


# ─── Phase 3: Resolve people + collect junction records ─────────────────────────

def phase3_resolve_people(contact_slots, phone_id_map, email_id_map, org_id_map, property_id_map, dry_run: bool):
    """
    Walk all contact slots. Dedup people by (phone, normalized_name).
    Returns:
      - people_to_insert:  list of dicts to INSERT into `people`
      - people_key_map:    people_key → people_list_index
      - junction_records:  dict of table → list of (person_idx, record_dict)
            person_idx is an index into people_to_insert (resolved to UUID in Phase 4)
    """
    people_to_insert: list[dict] = []
    people_key_map:   dict[tuple, int] = {}   # (phone, name_lower) → index

    # Junction collection: list of (person_list_index, record_dict_WITHOUT_person_id)
    j_person_phones:  list[tuple[int, dict]] = []
    j_person_emails:  list[tuple[int, dict]] = []
    j_person_orgs:    list[tuple[int, dict]] = []
    j_person_props:   list[tuple[int, dict]] = []
    j_property_phones: list[dict] = []   # these don't need person_id

    stats = {"new_people": 0, "reused_people": 0, "skipped_nameless": 0}

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Phase 3:[/bold blue] Resolving people..."),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("people", total=len(contact_slots))

        for slot in contact_slots:
            progress.advance(task)

            first = slot["first_name"]
            last  = slot["last_name"]
            phone = slot["phone"]
            email = slot["email"]
            role  = slot["role"]
            entity_name = slot["entity_name"]
            prop_key    = slot["prop_key"]

            name_lower = normalize_name(first, last)

            # ── Skip if no name (phone-only slots handled via property_phones) ──
            if not name_lower:
                stats["skipped_nameless"] += 1
                continue

            # ── Resolve or create person ─────────────────────────────────
            people_key = (phone, name_lower) if phone else None

            if people_key and people_key in people_key_map:
                person_idx = people_key_map[people_key]
                stats["reused_people"] += 1
            else:
                person_idx = len(people_to_insert)
                people_to_insert.append({
                    "first_name": first or "",
                    "last_name":  last or "",
                    "lead_status": "new",
                    "tags": PEOPLE_TAGS,
                    "details": {"source": "qozb_import"},
                })
                if people_key:
                    people_key_map[people_key] = person_idx
                stats["new_people"] += 1

            # ── Junction: person_phones ──────────────────────────────────
            if phone and (not dry_run):
                phone_id = phone_id_map.get(phone)
                if phone_id:
                    j_person_phones.append((person_idx, {
                        "phone_id": phone_id,
                        "label":    "work",
                        "is_primary": True,
                        "source":   "qozb_import",
                    }))

            # ── Junction: person_emails ──────────────────────────────────
            if email and (not dry_run):
                email_id = email_id_map.get(email)
                if email_id:
                    j_person_emails.append((person_idx, {
                        "email_id":  email_id,
                        "label":     "work",
                        "is_primary": True,
                        "source":    "qozb_import",
                    }))

            # ── Junction: person_organizations ───────────────────────────
            if entity_name and (not dry_run):
                org_id = org_id_map.get(entity_name)
                if org_id:
                    j_person_orgs.append((person_idx, {
                        "organization_id": org_id,
                        "title":           role,
                        "is_primary":      False,
                    }))

            # ── Junction: person_properties ──────────────────────────────
            if not dry_run:
                prop_id = property_id_map.get(prop_key)
                if prop_id:
                    j_person_props.append((person_idx, {
                        "property_id": prop_id,
                        "role":        role,
                    }))

    console.print(f"  [dim]New people to insert: {stats['new_people']:,}[/dim]")
    console.print(f"  [dim]Reused (deduped):     {stats['reused_people']:,}[/dim]")
    console.print(f"  [dim]Nameless slots skipped: {stats['skipped_nameless']:,}[/dim]")

    return people_to_insert, people_key_map, {
        "person_phones":  j_person_phones,
        "person_emails":  j_person_emails,
        "person_orgs":    j_person_orgs,
        "person_props":   j_person_props,
    }


# ─── Phase 4: Insert people → get IDs ──────────────────────────────────────────

def phase4_insert_people(supabase, people_to_insert: list[dict], dry_run: bool) -> list[str]:
    """
    Batch insert all people records. Returns list of UUIDs in the same order
    as people_to_insert.
    """
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

def phase5_insert_junctions(supabase, junctions: dict, person_uuids: list[str],
                             property_id_map: dict, phone_id_map: dict, org_id_map: dict,
                             orphan_prop_phones: list[tuple],
                             property_org_links: list[tuple], dry_run: bool):
    if dry_run:
        for table_key, records in junctions.items():
            console.print(f"[yellow]DRY RUN: would insert {len(records):,} {table_key} rows[/yellow]")
        console.print(f"[yellow]DRY RUN: would insert {len(orphan_prop_phones):,} property_phones rows[/yellow]")
        console.print(f"[yellow]DRY RUN: would insert {len(property_org_links):,} property_organizations rows[/yellow]")
        return

    # ── person_phones ──────────────────────────────────────────────────────────
    pp_records = []
    seen_person_phone = set()
    for (person_idx, data) in junctions["person_phones"]:
        pid = person_uuids[person_idx]
        key = (pid, data["phone_id"])
        if key not in seen_person_phone:
            seen_person_phone.add(key)
            pp_records.append({"person_id": pid, **data})

    _batch_upsert_junctions(supabase, "person_phones", pp_records, "person_id,phone_id", "person_phones")

    # ── person_emails ──────────────────────────────────────────────────────────
    pe_records = []
    seen_person_email = set()
    for (person_idx, data) in junctions["person_emails"]:
        pid = person_uuids[person_idx]
        key = (pid, data["email_id"])
        if key not in seen_person_email:
            seen_person_email.add(key)
            pe_records.append({"person_id": pid, **data})

    _batch_upsert_junctions(supabase, "person_emails", pe_records, "person_id,email_id", "person_emails")

    # ── person_organizations ───────────────────────────────────────────────────
    po_records = []
    seen_person_org = set()
    for (person_idx, data) in junctions["person_orgs"]:
        pid = person_uuids[person_idx]
        key = (pid, data["organization_id"])
        if key not in seen_person_org:
            seen_person_org.add(key)
            po_records.append({"person_id": pid, **data})

    _batch_upsert_junctions(supabase, "person_organizations", po_records, "person_id,organization_id", "person_organizations")

    # ── person_properties ─────────────────────────────────────────────────────
    pr_records = []
    seen_person_prop = set()
    for (person_idx, data) in junctions["person_props"]:
        pid = person_uuids[person_idx]
        key = (pid, data["property_id"], data["role"])
        if key not in seen_person_prop:
            seen_person_prop.add(key)
            pr_records.append({"person_id": pid, **data})

    _batch_upsert_junctions(supabase, "person_properties", pr_records, "person_id,property_id,role", "person_properties")

    # ── property_phones (orphan property-level phones) ─────────────────────────
    orp_records = []
    seen_prop_phone = set()
    for (prop_key, phone_digits) in orphan_prop_phones:
        prop_id  = property_id_map.get(prop_key)
        phone_id = phone_id_map.get(phone_digits)
        if prop_id and phone_id:
            key = (prop_id, phone_id)
            if key not in seen_prop_phone:
                seen_prop_phone.add(key)
                orp_records.append({
                    "property_id": prop_id,
                    "phone_id":    phone_id,
                    "label":       "property_line",
                    "source":      "qozb_import",
                })

    _batch_upsert_junctions(supabase, "property_phones", orp_records, "property_id,phone_id", "property_phones")

    # ── property_organizations (direct property → org links) ───────────────────
    po_records = []
    seen_prop_org = set()
    for (prop_key, entity_name, role) in property_org_links:
        prop_id = property_id_map.get(prop_key)
        org_id  = org_id_map.get(entity_name)
        if prop_id and org_id:
            key = (prop_id, org_id, role)
            if key not in seen_prop_org:
                seen_prop_org.add(key)
                po_records.append({
                    "property_id":     prop_id,
                    "organization_id": org_id,
                    "role":            role,
                    "source":          "qozb_import",
                })

    _batch_upsert_junctions(supabase, "property_organizations", po_records, "property_id,organization_id,role", "property_organizations")


def _batch_upsert_junctions(supabase, table: str, records: list[dict], on_conflict: str, label: str):
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

    console.print(f"  [dim]{label}: {inserted:,} rows inserted/upserted[/dim]")


# ─── Summary ───────────────────────────────────────────────────────────────────

def print_summary(unique_phones, unique_emails, unique_orgs, unique_properties,
                  people_to_insert, orphan_prop_phones, property_org_links, dry_run: bool):
    table = Table(title="Import Summary", show_header=True, header_style="bold magenta")
    table.add_column("Table", style="cyan")
    table.add_column("Records", justify="right", style="green")
    table.add_column("Notes", style="dim")

    table.add_row("properties",        f"{len(unique_properties):,}", "dedup on (property_name, address)")
    table.add_row("organizations",     f"{len(unique_orgs):,}",       "dedup on name (exact)")
    table.add_row("phones",            f"{len(unique_phones):,}",     "dedup on normalized digits")
    table.add_row("emails",            f"{len(unique_emails):,}",     "Owner Contact Email only")
    table.add_row("people",            f"{len(people_to_insert):,}",  "dedup on (phone, name)")
    table.add_row("property_phones",   f"{len(orphan_prop_phones):,}","orphan property-level phones")
    table.add_row("property_organizations", f"{len(property_org_links):,}", "direct property ↔ org links")
    table.add_row("person_phones",     "—",                           "see junction phase")
    table.add_row("person_emails",     "—",                           "see junction phase")
    table.add_row("person_organizations","—",                         "see junction phase")
    table.add_row("person_properties", "—",                           "see junction phase")

    console.print(table)
    if dry_run:
        console.print(Panel("[yellow bold]DRY RUN complete — no data was written to the database.[/yellow bold]"))
    else:
        console.print(Panel("[green bold]Import complete.[/green bold]"))


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Import QOZB contacts into consolidated CRM schema")
    parser.add_argument("--dry-run", action="store_true", help="Scan and plan but do not write to DB")
    parser.add_argument("--limit",   type=int, default=None, help="Only process first N CSV rows")
    args = parser.parse_args()

    console.print(Panel(
        f"[bold]QOZB → CRM Import[/bold]\n"
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
    (unique_phones, unique_emails, unique_orgs, unique_properties,
     orphan_prop_phones, property_org_links, contact_slots) = phase1_collect(df, args.limit)

    # ── Phase 2 ──────────────────────────────────────────────────────────────
    console.print("\n[bold]Phase 2: Upserting entity tables[/bold]")
    phone_id_map, email_id_map, org_id_map, property_id_map = phase2_upsert_entities(
        supabase, unique_phones, unique_emails, unique_orgs, unique_properties, args.dry_run
    )

    # ── Phase 3 ──────────────────────────────────────────────────────────────
    console.print("\n[bold]Phase 3: Resolving people & collecting junction records[/bold]")
    people_to_insert, people_key_map, junctions = phase3_resolve_people(
        contact_slots, phone_id_map, email_id_map, org_id_map, property_id_map, args.dry_run
    )

    # ── Phase 4 ──────────────────────────────────────────────────────────────
    console.print("\n[bold]Phase 4: Inserting people[/bold]")
    person_uuids = phase4_insert_people(supabase, people_to_insert, args.dry_run)

    # ── Phase 5 ──────────────────────────────────────────────────────────────
    console.print("\n[bold]Phase 5: Inserting junction records[/bold]")
    phase5_insert_junctions(
        supabase, junctions, person_uuids,
        property_id_map, phone_id_map, org_id_map,
        orphan_prop_phones, property_org_links, args.dry_run
    )

    # ── Summary ──────────────────────────────────────────────────────────────
    console.print("\n")
    print_summary(
        unique_phones, unique_emails, unique_orgs, unique_properties,
        people_to_insert, orphan_prop_phones, property_org_links, args.dry_run
    )


if __name__ == "__main__":
    main()
