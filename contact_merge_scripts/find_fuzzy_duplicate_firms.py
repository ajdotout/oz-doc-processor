import pandas as pd
import re

def clean_firm_name(name):
    if pd.isna(name):
        return ""
    
    name = str(name).lower()
    
    # Remove common suffixes and punctuation
    remove_words = [
        r'\bllc\b', r'\binc\.?\b', r'\bcorp\.?\b', r'\bcorporation\b', r'\bltd\.?\b',
        r'\blimited\b', r'\bcompany\b', r'\bco\.?\b', r'\bgroup\b', r'\bpartners\b',
        r'\bcapital\b', r'\bmanagement\b', r'\binvestments\b', r'\bfamily office\b',
        r'\bfamily\b', r'\bholdings\b', r'\bassociates\b', r'\btrust\b', r'\badvisors\b',
        r'\bllp\b', r'\blp\b'
    ]
    
    for word in remove_words:
        name = re.sub(word, '', name)
        
    # Remove punctuation and extra whitespace
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def main():
    csv_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists/USA_Family_Office_Consolidated.csv"
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    valid_df = df.dropna(subset=['Firm Name']).copy()
    
    # Create normalized name
    valid_df['Normalized Name'] = valid_df['Firm Name'].apply(clean_firm_name)
    
    # Group by normalized name
    grouped = valid_df.groupby('Normalized Name')
    
    duplicate_groups = []
    
    for normalized_name, group in grouped:
        if normalized_name == "":
            continue
            
        unique_original_names = group['Firm Name'].unique()
        if len(unique_original_names) > 1:
            duplicate_groups.append((normalized_name, unique_original_names))
            
    # Sort groups by length of normalized name (or somewhat alphabetical)
    duplicate_groups.sort(key=lambda x: x[0])
    
    print("--- Potential Duplicate Firms Detected ---")
    for normalized_name, original_names in duplicate_groups:
        print(f"\nNormalized Base: '{normalized_name}'")
        for orig in original_names:
            print(f"  - {orig}")
            
    print(f"\nTotal potential duplicate groups: {len(duplicate_groups)}")

if __name__ == "__main__":
    main()
