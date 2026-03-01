import pandas as pd
import os

def clean_email(email):
    if pd.isna(email):
        return None
    cleaned = str(email).strip().lower()
    return cleaned if '@' in cleaned else None

def main():
    csv_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/QOZB-Contacts/All QOZB Development Projects USA - 20260126.xlsx - Results.csv"
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig', low_memory=False)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return
        
    total_rows = len(df)
    
    all_emails = set()
    # It appears `Owner Contact Email` is the main email column
    emails_series = df.get('Owner Contact Email', pd.Series())
    
    for val in emails_series:
        e = clean_email(val)
        if e:
            all_emails.add(e)
            
    # Check if there are other email columns
    other_email_cols = [c for c in df.columns if 'email' in c.lower() and c != 'Owner Contact Email']
    
    other_emails_found = set()
    for col in other_email_cols:
        for val in df[col]:
            e = clean_email(val)
            if e:
                other_emails_found.add(e)
                all_emails.add(e)
                
    md_content = f"""# QOZB Emails Analysis

**Dataset**: QOZB Development Projects CSV
**Total Rows (Properties)**: {total_rows}

## Unique Emails Analysis

- **Total Unique `Owner Contact Email`s**: {len(set(clean_email(e) for e in emails_series if clean_email(e)))}
- **Total Unique Emails across all columns**: {len(all_emails)}

### Other Email Columns
"""
    if other_email_cols:
        md_content += "Found the following extra email columns:\n"
        for c in other_email_cols:
            md_content += f"- {c}\n"
    else:
        md_content += "No other email columns found besides `Owner Contact Email`.\n"
        
    md_content += "\n### Potential Merge / Database Impact\n"
    md_content += f"Importing this dataset will yield **{len(all_emails)}** new email entities (excluding overlaps with existing DB) into the `emails` table, which will map to QOZB property owners.\n"
    
    output_path = os.path.join(os.path.dirname(__file__), "emails_report.md")
    with open(output_path, "w") as f:
        f.write(md_content)
        
    print(f"Report written to {output_path}")

if __name__ == "__main__":
    main()
