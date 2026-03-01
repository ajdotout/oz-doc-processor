import pandas as pd
import os
from collections import defaultdict

def clean_phone(phone):
    if pd.isna(phone):
        return None
    cleaned = str(phone).split('.')[0].strip()
    return cleaned if cleaned else None

def get_entities(row):
    entities = []
    for col in ['Owner', 'Manager', 'Trustee', 'Special Servicer']:
        val = str(row.get(col, '')).strip()
        if val and val.lower() != 'nan':
            entities.append(val)
    return entities

def main():
    csv_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/QOZB-Contacts/All QOZB Development Projects USA - 20260126.xlsx - Results.csv"
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig', low_memory=False)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return
        
    total_rows = len(df)
    
    # In /admin/prospects we aggregate by phone number. Let's see how phones map to properties.
    phone_to_properties = defaultdict(list)
    phone_to_entities = defaultdict(set)
    phone_to_contacts = defaultdict(set)
    
    all_unique_phones = set()
    
    for idx, row in df.iterrows():
        phones_in_row = set()
        
        for col in ['Phone Number', 'Owner Contact Phone Number', 'Manager Contact Phone Number', 'Trustee Contact Phone Number', 'Special Servicer Contact Phone Number']:
            p = clean_phone(row.get(col))
            if p:
                phones_in_row.add(p)
                all_unique_phones.add(p)
                
        entities = get_entities(row)
        
        contact_names = []
        for col_prefix in ['Owner', 'Manager', 'Trustee', 'Special Servicer']:
            first = str(row.get(f"{col_prefix} Contact First Name", '')).strip()
            last = str(row.get(f"{col_prefix} Contact Last Name", '')).strip()
            if first and first.lower() != 'nan':
                contact_names.append(f"{first} {last}".strip())
                
        prop_id = row.get('PropertyID', f"Row_{idx}")
                
        for p in phones_in_row:
            phone_to_properties[p].append(prop_id)
            for e in entities:
                phone_to_entities[p].add(e)
            for c in contact_names:
                phone_to_contacts[p].add(c)
                
    # Analysis
    phones_with_multiple_properties = {p: props for p, props in phone_to_properties.items() if len(props) > 1}
    phones_sorted_by_prop_count = sorted(phone_to_properties.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Let's find phones with multiple entities (which means one phone connects different companies)
    phones_with_multiple_entities = {p: ents for p, ents in phone_to_entities.items() if len(ents) > 1}
    
    md_content = f"""# QOZB Phones Aggregation Analysis

This report analyzes the phone number aggregation in the QOZB dataset, mirroring the logic used in the `/admin/prospects` page of `oz-dev-dash`.

**Dataset**: QOZB Development Projects CSV
**Total Rows (Properties)**: {total_rows}
**Total Unique Phones found**: {len(all_unique_phones)}

## Aggregation Stats

In the CRM UI, a single phone number represents a "Communication Channel", which is linked to potentially multiple properties, entities, and contacts.

- **Phones linked to 1 Property**: {len(all_unique_phones) - len(phones_with_multiple_properties)}
- **Phones linked to >1 Properties**: {len(phones_with_multiple_properties)}
- **Phones linking >1 distinct Entity names**: {len(phones_with_multiple_entities)}

### Top 10 Phones by Property Count (Highly Aggregated)
"""
    for p, props in phones_sorted_by_prop_count[:10]:
        ents = list(phone_to_entities[p])[:3]
        contacts = list(phone_to_contacts[p])[:3]
        md_content += f"- **{p}**: {len(props)} properties\n"
        md_content += f"  - Entities: {ents}\n"
        md_content += f"  - Contacts: {contacts}\n"
        
    output_path = os.path.join(os.path.dirname(__file__), "phones_aggregation_report.md")
    with open(output_path, "w") as f:
        f.write(md_content)
        
    print(f"Report written to {output_path}")

if __name__ == "__main__":
    main()
