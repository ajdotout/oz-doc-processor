import pandas as pd
import os
from collections import Counter

def main():
    csv_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/QOZB-Contacts/All QOZB Development Projects USA - 20260126.xlsx - Results.csv"
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig', low_memory=False)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return
        
    total_rows = len(df)
    
    entity_roles = ['Owner', 'Manager', 'Trustee', 'Special Servicer']
    
    unique_entities_per_role = {}
    total_unique_entities = set()
    
    entity_counts = Counter()
    
    for role in entity_roles:
        entities = df.get(role, pd.Series()).dropna().astype(str).str.strip()
        entities = [e for e in entities if e.lower() != 'nan' and e != '']
        unique_entities_per_role[role] = set(entities)
        for e in entities:
            total_unique_entities.add(e)
            entity_counts[e] += 1
            
    md_content = f"""# QOZB Entities Analysis

This analyzes the unique organizations (Entities) represented in the QOZB dataset. In the consolidated CRM logic, these map to the `organizations` table.

**Dataset**: QOZB Development Projects CSV
**Total Rows (Properties)**: {total_rows}
**Total Unique Entities (Across all roles)**: {len(total_unique_entities)}

## Entities by Role

"""
    for role in entity_roles:
        md_content += f"- **{role}**: {len(unique_entities_per_role[role])} unique names\n"
        
    md_content += "\n## Top Entities by Property Count\n\n"
    
    md_content += "| Entity Name | Mentions |\n"
    md_content += "|---|---|\n"
    for ent, count in entity_counts.most_common(20):
        md_content += f"| {ent} | {count} |\n"
        
    output_path = os.path.join(os.path.dirname(__file__), "entities_report.md")
    with open(output_path, "w") as f:
        f.write(md_content)
        
    print(f"Report written to {output_path}")

if __name__ == "__main__":
    main()
