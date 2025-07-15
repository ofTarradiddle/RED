import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create the data
dates = pd.date_range(start='2024-01-01', end='2024-12-19', freq='D')

# Create more realistic price movements with volatility
np.random.seed(42)  # For reproducible results

# Start with base values
red_etf_base = 100
nav_base = 100
sp500_base = 100

red_etf = []
nav = []
sp500 = []
premium_discount = []

for i in range(len(dates)):
    # Add some daily variation
    red_etf_change = np.random.normal(0.15, 0.8)  # Daily return with volatility
    nav_change = np.random.normal(0.14, 0.75)
    sp500_change = np.random.normal(0.08, 0.6)
    
    if i == 0:
        red_etf.append(red_etf_base)
        nav.append(nav_base)
        sp500.append(sp500_base)
        premium_discount.append(100.00)  # Start at 100
    else:
        red_etf.append(red_etf[-1] * (1 + red_etf_change/100))
        nav.append(nav[-1] * (1 + nav_change/100))
        sp500.append(sp500[-1] * (1 + sp500_change/100))
        
        # Calculate premium/discount (around 100 with small volatility)
        premium = ((red_etf[-1] - nav[-1]) / nav[-1] * 100) + 100
        premium_discount.append(premium)

# Create DataFrame
df = pd.DataFrame({
    'Date': dates,
    'RED_ETF': [round(x, 2) for x in red_etf],
    'NAV': [round(x, 2) for x in nav],
    'SP500': [round(x, 2) for x in sp500],
    'Premium_Discount': [round(x, 2) for x in premium_discount]
})

# Save to Excel with formatting
with pd.ExcelWriter('data/performance_data.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Performance Data', index=False)
    
    # Get the workbook and worksheet
    workbook = writer.book
    worksheet = writer.sheets['Performance Data']
    
    # Format the date column
    from openpyxl.styles import Font, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    
    # Header formatting
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="8B0000", end_color="8B0000", fill_type="solid")
    
    for col in range(1, 6):  # Columns A to E
        cell = worksheet.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
    
    # Auto-adjust column widths
    for column in worksheet.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 20)
        worksheet.column_dimensions[column_letter].width = adjusted_width

print("Excel file created: data/performance_data.xlsx")
print(f"Data points: {len(df)}")
print("Sample data:")
print(df.head())
print("\nLatest values:")
print(df.tail()) 