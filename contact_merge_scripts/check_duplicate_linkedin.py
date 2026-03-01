import pandas as pd

def main():
    csv_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists/USA_Family_Office_Consolidated.csv"
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    print(f"Total Rows in CSV: {len(df)}")
    
    # 1. Check for Duplicate LinkedIn Profile URLs
    # Clean the URLs first (strip whitespace, trailing slashes, perhaps make lowercase)
    # We will just strip whitespace for a basic check
    df_with_li = df.dropna(subset=['LinkedIn Profile']).copy()
    df_with_li['Cleaned_LinkedIn'] = df_with_li['LinkedIn Profile'].astype(str).str.strip()
    
    li_counts = df_with_li['Cleaned_LinkedIn'].value_counts()
    duplicate_li = li_counts[li_counts > 1]
    print(f"\n--- Duplicate LinkedIn URLs ---")
    print(f"Total unique duplicate URLs found: {len(duplicate_li)}")
    if not duplicate_li.empty:
        for url, count in duplicate_li.head(10).items():
            print(f"{url}: {count} occurrences")
            # show the names associated with this url
            rows = df_with_li[df_with_li['Cleaned_LinkedIn'] == url]
            for _, row in rows.iterrows():
                print(f"    - {row['Contact First Name']} {row['Contact Last Name']} | {row['Firm Name']}")

    # 2. Check for Duplicate Name + Firm Combinations
    df['Full Name'] = df['Contact First Name'].astype(str) + " " + df['Contact Last Name'].astype(str)
    name_firm_counts = df.groupby(['Full Name', 'Firm Name']).size()
    duplicate_name_firms = name_firm_counts[name_firm_counts > 1]
    
    print(f"\n--- Duplicate Name + Firm Combinations ---")
    print(f"Total unique duplicate combinations found: {len(duplicate_name_firms)}")
    if not duplicate_name_firms.empty:
        for index, count in duplicate_name_firms.head(10).items():
            print(f"{index[0]} at {index[1]}: {count} occurrences")

if __name__ == "__main__":
    main()
