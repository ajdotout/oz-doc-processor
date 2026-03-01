import pandas as pd
import sys

def main():
    csv_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists/USA_Family_Office_Consolidated.csv"
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    # Filter out companies with no valid 'Firm Name' or no valid 'Company Email Address'
    valid_df = df.dropna(subset=['Firm Name', 'Company Email Address']).copy()
    
    # Clean email strings
    valid_df['Company Email Address'] = valid_df['Company Email Address'].str.lower().str.strip()
    
    grouped = valid_df.groupby('Firm Name')
    
    print("--- Companies with Conflicting Emails ---")
    
    for firm_name, group in grouped:
        if len(group) > 1:
            unique_emails = group['Company Email Address'].unique()
            if len(unique_emails) > 1:
                print(f"\nFirm: {firm_name}")
                print("Available Emails:")
                for email in unique_emails:
                    count = len(group[group['Company Email Address'] == email])
                    print(f"  - {email} (used by {count} contacts)")

if __name__ == "__main__":
    main()
