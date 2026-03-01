import pandas as pd
import re

def clean_firm_name(name):
    if pd.isna(name): return ""
    name = str(name).lower()
    remove_words = [
        r'\bllc\b', r'\binc\.?\b', r'\bcorp\.?\b', r'\bcorporation\b', r'\bltd\.?\b',
        r'\blimited\b', r'\bcompany\b', r'\bco\.?\b', r'\bgroup\b', r'\bpartners\b',
        r'\bcapital\b', r'\bmanagement\b', r'\binvestments\b', r'\bfamily office\b',
        r'\bfamily\b', r'\bholdings\b', r'\bassociates\b', r'\btrust\b', r'\badvisors\b',
        r'\bllp\b', r'\blp\b'
    ]
    for word in remove_words: name = re.sub(word, '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def main():
    csv_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists/USA_Family_Office_Consolidated.csv"
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error: {e}")
        return

    valid_df = df.dropna(subset=['Firm Name']).copy()
    valid_df['Normalized Name'] = valid_df['Firm Name'].apply(clean_firm_name)
    grouped = valid_df.groupby('Normalized Name')
    
    print("--- Checking duplicate firms for individual contacts ---")
    for normalized_name, group in grouped:
        if normalized_name == "": continue
        
        unique_original_names = group['Firm Name'].unique()
        if len(unique_original_names) > 1:
            print(f"\nNormalized Base: '{normalized_name}'")
            for orig in unique_original_names:
                sub_group = group[group['Firm Name'] == orig]
                contacts = sub_group[['Contact First Name', 'Contact Last Name']].dropna().apply(lambda x: f"{x['Contact First Name']} {x['Contact Last Name']}", axis=1).tolist()
                print(f"  Firm Name: {orig}")
                print(f"  Contacts: {contacts}")

if __name__ == "__main__":
    main()
