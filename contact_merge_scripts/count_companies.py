
import pandas as pd

file_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/FamilyOfficeDatabase-Lists/USA_Family_Office_Consolidated.csv"

try:
    df = pd.read_csv(file_path, encoding='utf-8-sig')
except:
    df = pd.read_csv(file_path, encoding='latin1')

# Normalize Firm Names
# Strip whitespace and convert to lower case to avoid duplicates like "Firm A" vs "firm a"
# Also handle NaN
unique_firms = df['Firm Name'].astype(str).str.strip().str.lower().unique()
# Remove 'nan' if present (converted from actual NaN)
unique_firms = [f for f in unique_firms if f != 'nan' and f != '']

print(f"Total rows: {len(df)}")
print(f"Total unique companies: {len(unique_firms)}")

# Optional: Top 5 most frequent firms simply to verify
print("\nTop 5 Firms by Contact Count:")
print(df['Firm Name'].value_counts().head(5))
