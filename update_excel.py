#!/usr/bin/env python3
"""
Script to update Excel file column names to match data_server.py expectations
"""

import pandas as pd
import os

def update_excel_columns():
    """Update Excel file column names"""
    try:
        # Read the Excel file
        df = pd.read_excel('data/performance_data.xlsx', sheet_name='Performance Data')
        print('Current columns:', df.columns.tolist())
        
        # Rename SP500 column to Morningstar US Market Index
        if 'SP500' in df.columns:
            df = df.rename(columns={'SP500': 'Morningstar US Market Index'})
            print('Renamed SP500 to Morningstar US Market Index')
        else:
            print('SP500 column not found, checking for other variations...')
            print('Available columns:', df.columns.tolist())
        
        # Save back to Excel
        df.to_excel('data/performance_data.xlsx', sheet_name='Performance Data', index=False)
        print('Excel file updated successfully!')
        print('New columns:', df.columns.tolist())
        
    except Exception as e:
        print(f'Error updating Excel file: {e}')

if __name__ == "__main__":
    update_excel_columns()
