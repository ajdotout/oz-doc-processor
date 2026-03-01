import pandas as pd
import sys

def main():
    csv_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists/USA_Family_Office_Consolidated.csv"
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    print(f"Total rows: {len(df)}")
    
    # Check if 'Firm Name' and 'Company Email Address' exist
    if 'Firm Name' not in df.columns or 'Company Email Address' not in df.columns:
        print("Missing required columns")
        return

    # Filter out companies with no valid 'Firm Name' or no valid 'Company Email Address'
    valid_df = df.dropna(subset=['Firm Name', 'Company Email Address']).copy()
    print(f"Rows with valid Firm Name and Company Email Address: {len(valid_df)}")
    
    # Group by Firm Name
    grouped = valid_df.groupby('Firm Name')
    
    firms_with_multiple_contacts = 0
    firms_with_different_emails = 0
    firms_with_same_email = 0
    
    for firm_name, group in grouped:
        if len(group) > 1:
            firms_with_multiple_contacts += 1
            unique_emails = group['Company Email Address'].str.lower().str.strip().unique()
            if len(unique_emails) > 1:
                firms_with_different_emails += 1
                if firms_with_different_emails <= 5: # Print some examples
                    print(f"\nFirm with different emails: {firm_name}")
                    print(group[['Contact First Name', 'Contact Last Name', 'Company Email Address']])
            else:
                firms_with_same_email += 1
                
    print(f"\n--- Summary ---")
    print(f"Total Unique Firms with > 1 Contact (and valid company emails): {firms_with_multiple_contacts}")
    print(f"Firms where all contacts have the SAME company email: {firms_with_same_email}")
    print(f"Firms where contacts have DIFFERENT company emails: {firms_with_different_emails}")

if __name__ == "__main__":
    main()
