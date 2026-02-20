
import pandas as pd
import glob
import os

base_dir = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists"
files = [
    f"{base_dir}/USA Family Office.csv",
    f"{base_dir}/Multifamily-Office-USAFilter.csv",
    f"{base_dir}/RealEstate-SFO-MFO-USAFilter.csv",
    f"{base_dir}/Single-Family-USAFilter.csv"
]

dfs = {}
for f in files:
    name = os.path.basename(f)
    try:
        try:
            df = pd.read_csv(f, encoding='utf-8-sig')
        except:
             df = pd.read_csv(f, encoding='latin1')
             
        dfs[name] = df
        print(f"Loaded {name}: {len(df)} rows")
    except Exception as e:
        print(f"Error loading {name}: {e}")

if "USA Family Office.csv" in dfs:
    main_name = "USA Family Office.csv"
    main_df = dfs[main_name]
    
    # Define columns to use as key
    # Make sure we select columns that exist in all files or handle missing columns intelligently
    # For now assume these exist as seen in head
    key_cols = ['Firm Name', 'Contact First Name', 'Contact Last Name', 'Company Email Address']
    # Filter to only columns present in main_df
    key_cols = [c for c in key_cols if c in main_df.columns]
    
    def get_keys(df, cols):
        # Create a set of tuples representing rows based on key columns
        # Handle NaN by treating it as empty string
        # Lowercase and strip strings
        
        # Check if cols exist in df
        cols_present = [c for c in cols if c in df.columns]
        if not cols_present:
            return set()
            
        def process_val(x):
            if pd.isna(x):
                return ""
            return str(x).lower().strip()
            
        return set(
            tuple(process_val(row[c]) for c in cols_present)
            for _, row in df.iterrows()
        )

    main_keys = get_keys(main_df, key_cols)
    print(f"\nMain File ({main_name}) has {len(main_keys)} unique keys based on {key_cols}")

    # Check each file against main
    for name, df in dfs.items():
        if name == main_name:
            continue
            
        sub_keys = get_keys(df, key_cols)
        overlap = len(sub_keys.intersection(main_keys))
        total = len(sub_keys)
        
        print(f"\n--- Comparing {name} ---")
        print(f"Total Unique Keys: {total}")
        print(f"Overlap with Main: {overlap} ({overlap/total*100:.1f}%)")
        

        missing = sub_keys - main_keys
        if not missing:
            print("✅ COMPLETE SUBSET")
        else:
            print(f"❌ Has {len(missing)} unique keys NOT in Main")
            
            # Check for name-only matches in Main
            print("Checking if missing records exist in Main with different Firm Name...")
            # Create name map for main
            # (first, last) -> [firms]
            name_map = {}
            for _, row in main_df.iterrows():
                k = (str(row.get('Contact First Name', '')).strip().lower(), str(row.get('Contact Last Name', '')).strip().lower())
                if k not in name_map: name_map[k] = []
                name_map[k].append(str(row.get('Firm Name', '')))
                
            found_by_name = 0
            for firm, first, last, email in missing:
                k = (str(first).strip().lower(), str(last).strip().lower())
                if k in name_map:
                    found_by_name += 1
                    if found_by_name <= 3:
                         print(f"  Possible match: {first} {last} at '{firm}' (In Main at: {name_map[k]})")

            print(f"  {found_by_name} / {len(missing)} missing records have a name match in Main (different firm/email)")
            print(f"  {len(missing) - found_by_name} seem to be genuinely new contacts.")

    # Check Union of Multifamily and SingleFamily

    if "Multifamily-Office-USAFilter.csv" in dfs and "Single-Family-USAFilter.csv" in dfs:
        m_keys = get_keys(dfs["Multifamily-Office-USAFilter.csv"], key_cols)
        s_keys = get_keys(dfs["Single-Family-USAFilter.csv"], key_cols)
        
        union_keys = m_keys.union(s_keys)
        print(f"\n--- Union Check (Multi + Single) vs Main ---")
        print(f"Union Keys: {len(union_keys)}")
        print(f"Main Keys: {len(main_keys)}")
        
        common = len(union_keys.intersection(main_keys))
        print(f"Overlap: {common}")
        
        extra_in_union = union_keys - main_keys
        extra_in_main = main_keys - union_keys
        
        if not extra_in_union and not extra_in_main:
             print("✅ PERFECT MATCH: USA Family Office = Multifamily + SingleFamily")
        else:
             if extra_in_union:
                 print(f"Union has {len(extra_in_union)} keys NOT in Main")
             if extra_in_main:
                 print(f"Main has {len(extra_in_main)} keys NOT in Union (Multi+Single)")

else:
    print("Could not find main file 'USA Family Office.csv'")
