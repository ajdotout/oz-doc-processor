
import os
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(f"Error connecting to Supabase: {e}")
    exit(1)

# Load CSV
csv_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists/USA_Family_Office_Consolidated.csv"
try:
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
except:
    df = pd.read_csv(csv_path, encoding='latin1')

# 1. Audit CSV for Emails (Personal + Company)
def extract_clean_emails(series):
    return series.dropna().astype(str).str.strip().str.lower()

company_emails = extract_clean_emails(df.get('Company Email Address', pd.Series()))
personal_emails = extract_clean_emails(df.get('Personal Email Address', pd.Series()))
secondary_emails = extract_clean_emails(df.get('Secondary Email', pd.Series()))

# Create a master set of all unique emails in the CSV
all_csv_emails = set()
for e in company_emails:
    if '@' in e: all_csv_emails.add(e)
for e in personal_emails:
    if '@' in e: all_csv_emails.add(e)
for e in secondary_emails:
    if '@' in e: all_csv_emails.add(e)

print(f"\n--- CSV Audit ---")
print(f"Total Rows: {len(df)}")
print(f"Total Unique Company Emails:  {len(set(e for e in company_emails if '@' in e))}")
print(f"Total Unique Personal Emails: {len(set(e for e in personal_emails if '@' in e))}")
if not secondary_emails.empty:
    print(f"Total Unique Secondary Emails: {len(set(e for e in secondary_emails if '@' in e))}")
    
print(f"Total UNIQUE Emails across all columns: {len(all_csv_emails)}")

# 2. Fetch DB Emails
print(f"\nFetching emails from DB...")
all_db_emails = set()
try:
    count = 0
    step = 1000
    while True:

        # We start by querying 'email' which is guaranteed.
        # If 'personal_email' or 'work_email' columns exist, query them.
        # Given the error, we will assume standard 'email' column and perhaps others might be named differently
        # or just query 'email' for now.
        response = supabase.table('contacts').select('email').range(count, count + step - 1).execute()
        data = response.data
        if not data:
            break
            
        for row in data:
            if row.get('email'): all_db_emails.add(str(row['email']).strip().lower())
        
        count += len(data)

        if len(data) < step:
            break
            
    print(f"Fetched {len(all_db_emails)} unique emails from Supabase contacts.")

except Exception as e:
    print(f"Error querying Supabase: {e}")
    exit(1)

# 3. Compare Both Sets
found_emails = all_csv_emails.intersection(all_db_emails)
missing_emails = all_csv_emails - all_db_emails

print(f"\n--- Final Comparison ---")
print(f"Start with: {len(all_csv_emails)} emails from CSV")
print(f"Already in DB: {len(found_emails)} ({len(found_emails)/len(all_csv_emails)*100:.1f}%)")
print(f"NET NEW Emails: {len(missing_emails)} ({len(missing_emails)/len(all_csv_emails)*100:.1f}%)")

if found_emails:
    print(f"\nSample Overlap (first 5):")
    for e in list(found_emails)[:5]:
        print(f"  {e}")
