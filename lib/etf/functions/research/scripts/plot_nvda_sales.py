"""
Plot NVDA Sales Data (27 years from FMP)
"""

import sys
from pathlib import Path
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

api_key = os.getenv('FMP_API_KEY')
if not api_key:
    raise ValueError("FMP_API_KEY environment variable is required. Set it in your .env file or export it.")

from lib.etf.functions.research import FMPClient

def plot_nvda_sales():
    """Plot 27 years of NVDA sales data"""
    
    print("="*70)
    print("NVDA Sales Data Visualization (27 Years)")
    print("="*70)
    
    fmp = FMPClient(api_key=api_key)
    
    # Get income statements
    print("\nFetching NVDA income statements...")
    income = fmp.get_income_statement('NVDA', period='annual', limit=30)
    
    if not income:
        print("✗ No data retrieved")
        return
    
    print(f"✓ Retrieved {len(income)} annual statements")
    
    # Extract sales data
    sales_data = []
    for stmt in income:
        date = stmt.get('date', 'N/A')
        revenue = stmt.get('revenue', 0)
        if revenue:
            sales_data.append({
                'date': pd.to_datetime(date),
                'year': int(date[:4]) if date and len(date) >= 4 else None,
                'revenue_billions': revenue / 1e9,
                'revenue': revenue
            })
    
    if not sales_data:
        print("✗ No revenue data found")
        return
    
    df = pd.DataFrame(sales_data).sort_values('date')
    df.set_index('date', inplace=True)
    
    print(f"\nData range: {df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}")
    print(f"Revenue range: ${df['revenue_billions'].min():.2f}B to ${df['revenue_billions'].max():.2f}B")
    
    # Create figure with subplots
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    fig.suptitle('NVDA Revenue/Sales Analysis (1999-2025)', fontsize=18, fontweight='bold')
    
    # Plot 1: Revenue over time (line chart)
    axes[0].plot(df.index, df['revenue_billions'], linewidth=3, marker='o', 
                 markersize=6, color='#1f77b4', label='Annual Revenue')
    axes[0].fill_between(df.index, df['revenue_billions'], alpha=0.3, color='#1f77b4')
    axes[0].set_title('NVDA Annual Revenue (Billions USD)', fontsize=14, fontweight='bold', pad=15)
    axes[0].set_ylabel('Revenue (Billions USD)', fontsize=12)
    axes[0].grid(True, alpha=0.3, linestyle='--')
    axes[0].legend(fontsize=11)
    
    # Add value labels for key years
    for year in [1999, 2005, 2010, 2015, 2020, 2025]:
        if year in df['year'].values:
            row = df[df['year'] == year].iloc[0]
            axes[0].annotate(f'${row["revenue_billions"]:.1f}B', 
                           xy=(row.name, row['revenue_billions']),
                           xytext=(10, 10), textcoords='offset points',
                           fontsize=9, bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Plot 2: Year-over-year growth rate
    df['yoy_growth'] = df['revenue_billions'].pct_change() * 100
    axes[1].bar(df.index[1:], df['yoy_growth'].iloc[1:], 
                color=['green' if x > 0 else 'red' for x in df['yoy_growth'].iloc[1:]],
                alpha=0.7, width=200)
    axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    axes[1].set_title('Year-over-Year Revenue Growth (%)', fontsize=14, fontweight='bold', pad=15)
    axes[1].set_ylabel('Growth Rate (%)', fontsize=12)
    axes[1].grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # Plot 3: Log scale to show exponential growth
    axes[2].semilogy(df.index, df['revenue_billions'], linewidth=3, marker='o', 
                     markersize=6, color='purple', label='Revenue (Log Scale)')
    axes[2].set_title('NVDA Revenue (Log Scale) - Shows Exponential Growth', 
                     fontsize=14, fontweight='bold', pad=15)
    axes[2].set_ylabel('Revenue (Billions USD, Log Scale)', fontsize=12)
    axes[2].set_xlabel('Year', fontsize=12)
    axes[2].grid(True, alpha=0.3, linestyle='--', which='both')
    axes[2].legend(fontsize=11)
    
    # Fix x-axis formatting for all plots
    for ax in axes:
        # Use YearLocator and YearFormatter for proper year display
        ax.xaxis.set_major_locator(mdates.YearLocator(5))  # Show every 5 years
        ax.xaxis.set_minor_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.2, which='minor', linestyle=':')
    
    plt.tight_layout()
    
    # Save plot
    output_dir = Path("./data/research")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "nvda_sales_27_years.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Plot saved to: {output_file}")
    
    # Save data
    csv_file = output_dir / "nvda_sales_27_years.csv"
    df_export = df.reset_index()
    df_export['date'] = df_export['date'].dt.strftime('%Y-%m-%d')
    df_export.to_csv(csv_file, index=False)
    print(f"✓ Data saved to: {csv_file}")
    
    # Print summary statistics
    print("\n" + "="*70)
    print("Summary Statistics")
    print("="*70)
    print(f"Years of data: {len(df)}")
    print(f"Starting revenue (1999): ${df['revenue_billions'].iloc[0]:.2f}B")
    print(f"Ending revenue (2025): ${df['revenue_billions'].iloc[-1]:.2f}B")
    
    total_growth = ((df['revenue_billions'].iloc[-1] / df['revenue_billions'].iloc[0]) - 1) * 100
    years = len(df) - 1
    cagr = ((df['revenue_billions'].iloc[-1] / df['revenue_billions'].iloc[0]) ** (1/years) - 1) * 100
    
    print(f"Total growth: {total_growth:,.1f}%")
    print(f"CAGR: {cagr:.2f}%")
    print(f"Average YoY growth: {df['yoy_growth'].mean():.1f}%")
    print(f"Best year growth: {df['yoy_growth'].max():.1f}% ({df.loc[df['yoy_growth'].idxmax(), 'year']})")
    print(f"Worst year growth: {df['yoy_growth'].min():.1f}% ({df.loc[df['yoy_growth'].idxmin(), 'year']})")
    
    # Open the plot
    import subprocess
    try:
        subprocess.run(['open', str(output_file)], check=True)
        print(f"\n✓ Plot opened in default viewer")
    except:
        print(f"\nPlot saved at: {output_file}")

if __name__ == "__main__":
    plot_nvda_sales()

