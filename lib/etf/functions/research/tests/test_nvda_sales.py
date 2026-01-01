"""
Test script to get NVDA sales data going back as far as possible
"""

import sys
from pathlib import Path
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

import yfinance as yf
import matplotlib
matplotlib.use('Agg')

def get_nvda_sales_data():
    """Get NVDA sales/revenue data from available sources"""
    
    print("="*70)
    print("NVDA Sales Data Retrieval")
    print("="*70)
    
    ticker = yf.Ticker('NVDA')
    
    # Get annual financials
    print("\n1. Annual Financial Statements (Yahoo Finance):")
    financials = ticker.financials
    if not financials.empty:
        print(f"   ✓ Retrieved {len(financials.columns)} years of annual data")
        print(f"   Date range: {financials.columns[-1].strftime('%Y-%m-%d')} to {financials.columns[0].strftime('%Y-%m-%d')}")
        
        # Extract revenue
        revenue_rows = financials[financials.index.str.contains('Total Revenue|Operating Revenue', case=False, na=False)]
        if not revenue_rows.empty:
            revenue = revenue_rows.iloc[0]
            print(f"\n   Annual Revenue Data:")
            sales_data = []
            for date, value in revenue.items():
                if pd.notna(value):
                    sales_data.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'year': date.year,
                        'revenue': value / 1e9  # Convert to billions
                    })
            
            df_annual = pd.DataFrame(sales_data).sort_values('year')
            print(df_annual.to_string(index=False))
            
            # Get quarterly data for more granular view
            print("\n2. Quarterly Financial Statements:")
            quarterly = ticker.quarterly_financials
            if not quarterly.empty:
                print(f"   ✓ Retrieved {len(quarterly.columns)} quarters")
                print(f"   Date range: {quarterly.columns[-1].strftime('%Y-%m-%d')} to {quarterly.columns[0].strftime('%Y-%m-%d')}")
                
                q_revenue_rows = quarterly[quarterly.index.str.contains('Total Revenue|Operating Revenue', case=False, na=False)]
                if not q_revenue_rows.empty:
                    q_revenue = q_revenue_rows.iloc[0]
                    q_sales_data = []
                    for date, value in q_revenue.items():
                        if pd.notna(value):
                            q_sales_data.append({
                                'date': date.strftime('%Y-%m-%d'),
                                'quarter': f"{date.year}-Q{(date.month-1)//3 + 1}",
                                'revenue': value / 1e9
                            })
                    
                    df_quarterly = pd.DataFrame(q_sales_data).sort_values('date')
                    print(f"\n   Quarterly Revenue Data (last 10 quarters):")
                    print(df_quarterly.tail(10).to_string(index=False))
                    
                    # Combine for visualization
                    return df_annual, df_quarterly
    
    return None, None


def plot_nvda_sales(df_annual, df_quarterly):
    """Plot NVDA sales data"""
    
    if df_annual is None or df_annual.empty:
        print("\nNo data to plot")
        return
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('NVDA Revenue/Sales Analysis', fontsize=16, fontweight='bold')
    
    # Annual plot
    axes[0].bar(df_annual['year'], df_annual['revenue'], color='blue', alpha=0.7)
    axes[0].set_title('NVDA Annual Revenue (Billions USD)', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Year', fontsize=10)
    axes[0].set_ylabel('Revenue (Billions USD)', fontsize=10)
    axes[0].grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for year, revenue in zip(df_annual['year'], df_annual['revenue']):
        axes[0].text(year, revenue, f'${revenue:.1f}B', 
                    ha='center', va='bottom', fontsize=9)
    
    # Quarterly plot
    if df_quarterly is not None and not df_quarterly.empty:
        df_quarterly_sorted = df_quarterly.sort_values('date')
        axes[1].plot(range(len(df_quarterly_sorted)), df_quarterly_sorted['revenue'], 
                    marker='o', linewidth=2, markersize=6, color='green')
        axes[1].set_title('NVDA Quarterly Revenue (Billions USD)', fontsize=12, fontweight='bold')
        axes[1].set_xlabel('Quarter', fontsize=10)
        axes[1].set_ylabel('Revenue (Billions USD)', fontsize=10)
        axes[1].grid(True, alpha=0.3)
        
        # Set x-axis labels to quarters
        n_labels = min(10, len(df_quarterly_sorted))
        step = max(1, len(df_quarterly_sorted) // n_labels)
        axes[1].set_xticks(range(0, len(df_quarterly_sorted), step))
        axes[1].set_xticklabels([df_quarterly_sorted.iloc[i]['quarter'] 
                                 for i in range(0, len(df_quarterly_sorted), step)], 
                                rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save plot
    output_dir = Path("./data/research")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "nvda_sales_plot.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Plot saved to: {output_file}")
    
    # Save data
    csv_file = output_dir / "nvda_sales_data.csv"
    if df_quarterly is not None:
        combined = pd.concat([
            df_annual.assign(period='annual'),
            df_quarterly.assign(period='quarterly')
        ], ignore_index=True)
        combined.to_csv(csv_file, index=False)
    else:
        df_annual.to_csv(csv_file, index=False)
    print(f"✓ Data saved to: {csv_file}")


def check_historical_availability():
    """Check what historical data is available"""
    print("\n" + "="*70)
    print("Historical Data Availability Check")
    print("="*70)
    
    ticker = yf.Ticker('NVDA')
    info = ticker.info
    
    print(f"\nNVDA Company Info:")
    print(f"  IPO Date: {info.get('ipoDate', 'N/A')}")
    print(f"  Founded: {info.get('founded', 'N/A')}")
    print(f"  Current Revenue (TTM): ${info.get('totalRevenue', 0):,.0f}")
    
    print(f"\nNote: Yahoo Finance typically provides:")
    print(f"  - Annual financials: Last 4-5 years")
    print(f"  - Quarterly financials: Last 5-8 quarters")
    print(f"  - For full 30-year history, need:")
    print(f"    1. SEC EDGAR (free, but requires parsing)")
    print(f"    2. Premium data provider (Bloomberg, FactSet, etc.)")
    print(f"    3. FMP API upgrade (if they have historical data)")


if __name__ == "__main__":
    df_annual, df_quarterly = get_nvda_sales_data()
    
    if df_annual is not None:
        plot_nvda_sales(df_annual, df_quarterly)
        
        # Summary statistics
        print("\n" + "="*70)
        print("Summary Statistics")
        print("="*70)
        print(f"Years of data: {len(df_annual)}")
        print(f"Revenue range: ${df_annual['revenue'].min():.2f}B to ${df_annual['revenue'].max():.2f}B")
        print(f"Average annual growth: {((df_annual['revenue'].iloc[-1] / df_annual['revenue'].iloc[0]) ** (1/(len(df_annual)-1)) - 1) * 100:.1f}%")
        print(f"Total growth: {(df_annual['revenue'].iloc[-1] / df_annual['revenue'].iloc[0] - 1) * 100:.1f}%")
    
    check_historical_availability()


