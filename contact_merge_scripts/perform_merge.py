
import pandas as pd
import os

base_dir = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists"
main_file = f"{base_dir}/USA Family Office.csv"
target_file = f"{base_dir}/RealEstate-SFO-MFO-USAFilter.csv"
output_file = f"{base_dir}/USA_Family_Office_Consolidated.csv"

def load_csv(f):
    try:
        return pd.read_csv(f, encoding='utf-8-sig')
    except:
        return pd.read_csv(f, encoding='latin1')

print("Loading files...")
main_df = load_csv(main_file)
target_df = load_csv(target_file)

print(f"Loaded Main: {len(main_df)} rows")
print(f"Loaded Target: {len(target_df)} rows")

# 1. Normalize Schema
# Identify common columns and ensure we only keep columns from main_df structure
main_cols = list(main_df.columns)
target_df_aligned = target_df.reindex(columns=main_cols)

# 2. Key Generation
def clean(val):
    return str(val).lower().strip() if pd.notna(val) else ""

def get_key(row):
    # Composite key: Firm, First, Last, Email
    return (
        clean(row.get('Firm Name')),
        clean(row.get('Contact First Name')),
        clean(row.get('Contact Last Name')),
        clean(row.get('Company Email Address'))
    )

existing_keys = set()
for _, row in main_df.iterrows():
    existing_keys.add(get_key(row))

# 3. Filter New Records
new_rows = []
skipped_count = 0

for _, row in target_df_aligned.iterrows():
    k = get_key(row)
    if k not in existing_keys:
        new_rows.append(row)
    else:
        skipped_count += 1

print(f"Skipped {skipped_count} duplicate records.")
print(f"Found {len(new_rows)} unique records to append.")

# 4. Smart Conflict Resolution (Optional Step - currently just appending unique keys)
# If a record has same Name but differs in Firm/Email, it triggers a new key,
# so it is effectively added as a new row (job change or stale data).
# This aligns with the 'Append' strategy for unique fingerprints.

if new_rows:
    new_df = pd.DataFrame(new_rows)
    # Concatenate
    final_df = pd.concat([main_df, new_df], ignore_index=True)
else:
    final_df = main_df

# 5. Save
print(f"Saving consolidated list with {len(final_df)} rows...")
final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"Saved to: {output_file}")
print("Done.")
