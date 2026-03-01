import pandas as pd
import os

def clean_phone(phone):
    if pd.isna(phone):
        return None
    cleaned = str(phone).split('.')[0].strip()
    return cleaned if cleaned else None

def main():
    csv_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/QOZB-Contacts/All QOZB Development Projects USA - 20260126.xlsx - Results.csv"
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig', low_memory=False)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    total_rows = len(df)
    
    orphan_count = 0
    orphan_with_entity = 0
    orphan_no_entity = 0
    
    # Track details for sample
    sample_orphans = []
    
    for _, row in df.iterrows():
        prop_phone = clean_phone(row.get('Phone Number'))
        if not prop_phone:
            continue
            
        owner_phone = clean_phone(row.get('Owner Contact Phone Number'))
        manager_phone = clean_phone(row.get('Manager Contact Phone Number'))
        trustee_phone = clean_phone(row.get('Trustee Contact Phone Number'))
        special_phone = clean_phone(row.get('Special Servicer Contact Phone Number'))
        
        contact_phones = {owner_phone, manager_phone, trustee_phone, special_phone}
        contact_phones.discard(None)
        
        # 1. How many rows have a property-level `Phone Number` that does NOT match any Owner/Manager/Trustee Contact Phone Number?
        is_orphan = prop_phone not in contact_phones
        
        if is_orphan:
            orphan_count += 1
            
            # 2. Look for entities
            owner_entity = str(row.get('Owner', '')).strip()
            manager_entity = str(row.get('Manager', '')).strip()
            trustee_entity = str(row.get('Trustee', '')).strip()
            special_entity = str(row.get('Special Servicer', '')).strip()
            
            has_entity = False
            for ent in [owner_entity, manager_entity, trustee_entity, special_entity]:
                if ent and ent.lower() != 'nan':
                    has_entity = True
                    break
                    
            if has_entity:
                orphan_with_entity += 1
            else:
                orphan_no_entity += 1
                
            if len(sample_orphans) < 5:
                sample_orphans.append({
                    'Property Name': row.get('Property Name'),
                    'Property Phone': prop_phone,
                    'Has Entity': has_entity,
                    'Contact Phones': list(contact_phones)
                })

    md_content = f"""# Orphan Property Phones Analysis

Based on the [Consolidated CRM Planning Doc](oz-dev-dash/docs/consolidated-crm-planning.md), we need to analyze how to handle property-level phone numbers during migration.

**Dataset**: QOZB Development Projects CSV
**Total Properties (Rows)**: {total_rows}

## Questions & Answers

**1. How many rows have a property-level `Phone Number` that does NOT match any Owner/Manager/Trustee Contact Phone Number?**
- Answer: **{orphan_count}** rows

**2. Of those orphan phones, how many have at least one entity name (Owner/Manager/Trustee company)?**
- Answer: **{orphan_with_entity}** rows (These can potentially be linked to an Organization)

**3. Of those orphans, how many have NO entity at all?**
- Answer: **{orphan_no_entity}** rows (These might require a synthetic person or organization, or might just remain unlinked data)

---

### Sample Orphans
"""
    for sample in sample_orphans:
        md_content += f"- **Property**: {sample['Property Name']}\n"
        md_content += f"  - Property Phone: {sample['Property Phone']}\n"
        md_content += f"  - Contact Phones Present: {sample['Contact Phones']}\n"
        md_content += f"  - Has Entity Context: {sample['Has Entity']}\n\n"

    output_path = os.path.join(os.path.dirname(__file__), "orphan_phones_report.md")
    with open(output_path, "w") as f:
        f.write(md_content)
        
    print(f"Report written to {output_path}")

if __name__ == "__main__":
    main()
