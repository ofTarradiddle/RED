#!/usr/bin/env python3
"""
Convert CSV to Excel with correct column names
"""

import pandas as pd

# Read the updated CSV file
df = pd.read_csv('data/performance_data.csv')

# Convert date column to datetime
df['Date'] = pd.to_datetime(df['Date'])

# Save to Excel with correct column names
df.to_excel('data/performance_data.xlsx', sheet_name='Performance Data', index=False)

print("Excel file updated with correct column names!")
print("Columns:", df.columns.tolist())
