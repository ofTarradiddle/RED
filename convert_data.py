#!/usr/bin/env python3
"""
Data conversion script to convert Excel/CSV data to JSON format for the website
"""

import pandas as pd
import json
import os
from datetime import datetime

def convert_performance_data():
    """Convert performance data from Excel/CSV to JSON"""
    try:
        # Try to read from Excel first
        if os.path.exists('data/performance_data.xlsx'):
            df = pd.read_excel('data/performance_data.xlsx', sheet_name='Performance Data')
            print("✓ Loaded performance data from Excel file")
        elif os.path.exists('data/performance_data.csv'):
            df = pd.read_csv('data/performance_data.csv')
            print("✓ Loaded performance data from CSV file")
        else:
            print("❌ No performance data file found")
            return None
        
        # Convert date column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Convert to the format expected by the website
        performance_data = []
        for _, row in df.iterrows():
            performance_data.append({
                'date': row['Date'].strftime('%Y-%m-%d'),
                'red_etf': float(row['RED_ETF']),
                'nav': float(row['NAV']),
                'sp500': float(row['SP500']),
                'premium_discount': float(row['Premium_Discount'])
            })
        
        # Save to JSON
        with open('data/performance_data.json', 'w') as f:
            json.dump(performance_data, f, indent=2)
        
        print(f"✓ Converted {len(performance_data)} performance data points to JSON")
        return performance_data
        
    except Exception as e:
        print(f"❌ Error converting performance data: {e}")
        return None

def convert_holdings_data():
    """Convert holdings data from Excel to JSON"""
    try:
        if os.path.exists('red_holdings.xlsx'):
            df = pd.read_excel('red_holdings.xlsx', sheet_name='Holdings')
            print("✓ Loaded holdings data from Excel file")
        else:
            print("❌ No holdings data file found")
            return None
        
        # Convert to the format expected by the website
        holdings_data = []
        for _, row in df.iterrows():
            # Calculate weight as percentage of total market value
            total_market_value = df['market_value'].sum()
            weight = (row['market_value'] / total_market_value) * 100
            
            holdings_data.append({
                'name': str(row.get('name', '')),
                'ticker': str(row.get('ticker', '')),
                'weight': round(weight, 2),
                'sector': str(row.get('sector', '')),
                'country': 'USA'  # Default to USA
            })
        
        # Save to JSON
        with open('data/holdings_data.json', 'w') as f:
            json.dump(holdings_data, f, indent=2)
        
        print(f"✓ Converted {len(holdings_data)} holdings to JSON")
        return holdings_data
        
    except Exception as e:
        print(f"❌ Error converting holdings data: {e}")
        return None

def calculate_metrics(performance_data):
    """Calculate performance metrics from the data"""
    if not performance_data:
        return None
    
    # Convert to DataFrame for easier calculations
    df = pd.DataFrame(performance_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Get latest and earliest dates
    latest = df.iloc[-1]
    earliest = df.iloc[0]
    
    # Calculate returns
    ytd_start = df[df['date'].dt.year == latest['date'].year].iloc[0]
    ytd_return = ((latest['red_etf'] / ytd_start['red_etf']) - 1) * 100
    
    # Calculate other periods
    one_month_ago = df[df['date'] >= (latest['date'] - pd.Timedelta(days=30))].iloc[0]
    one_month_return = ((latest['red_etf'] / one_month_ago['red_etf']) - 1) * 100
    
    three_month_ago = df[df['date'] >= (latest['date'] - pd.Timedelta(days=90))].iloc[0]
    three_month_return = ((latest['red_etf'] / three_month_ago['red_etf']) - 1) * 100
    
    six_month_ago = df[df['date'] >= (latest['date'] - pd.Timedelta(days=180))].iloc[0]
    six_month_return = ((latest['red_etf'] / six_month_ago['red_etf']) - 1) * 100
    
    one_year_ago = df[df['date'] >= (latest['date'] - pd.Timedelta(days=365))].iloc[0]
    one_year_return = ((latest['red_etf'] / one_year_ago['red_etf']) - 1) * 100
    
    since_inception = ((latest['red_etf'] / earliest['red_etf']) - 1) * 100
    
    metrics = {
        'ytd': round(ytd_return, 2),
        'one_month': round(one_month_return, 2),
        'three_month': round(three_month_return, 2),
        'six_month': round(six_month_return, 2),
        'one_year': round(one_year_return, 2),
        'since_inception': round(since_inception, 2),
        'latest_date': latest['date'].strftime('%Y-%m-%d'),
        'latest_red_etf': round(latest['red_etf'], 2),
        'latest_nav': round(latest['nav'], 2),
        'latest_sp500': round(latest['sp500'], 2)
    }
    
    # Save metrics
    with open('data/metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print("✓ Calculated and saved performance metrics")
    return metrics

def main():
    """Main function to convert all data"""
    print("🔄 Converting data files for website integration...")
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Convert performance data
    performance_data = convert_performance_data()
    
    # Convert holdings data
    holdings_data = convert_holdings_data()
    
    # Calculate metrics
    if performance_data:
        metrics = calculate_metrics(performance_data)
        if metrics:
            print(f"\n📊 Performance Summary:")
            print(f"   YTD Return: {metrics['ytd']:+.2f}%")
            print(f"   1 Month: {metrics['one_month']:+.2f}%")
            print(f"   3 Month: {metrics['three_month']:+.2f}%")
            print(f"   6 Month: {metrics['six_month']:+.2f}%")
            print(f"   1 Year: {metrics['one_year']:+.2f}%")
            print(f"   Since Inception: {metrics['since_inception']:+.2f}%")
            print(f"   Latest Date: {metrics['latest_date']}")
            print(f"   Latest RED ETF: ${metrics['latest_red_etf']:.2f}")
    
    if holdings_data:
        print(f"\n📈 Holdings Summary:")
        print(f"   Total Holdings: {len(holdings_data)}")
        sectors = {}
        countries = {}
        for holding in holdings_data:
            sectors[holding['sector']] = sectors.get(holding['sector'], 0) + holding['weight']
            countries[holding['country']] = countries.get(holding['country'], 0) + holding['weight']
        
        print(f"   Sectors: {len(sectors)}")
        print(f"   Countries: {len(countries)}")
        print(f"   Top Sector: {max(sectors, key=sectors.get)} ({max(sectors.values()):.1f}%)")
        print(f"   Top Country: {max(countries, key=countries.get)} ({max(countries.values()):.1f}%)")
    
    print("\n✅ Data conversion completed!")
    print("   Files created:")
    print("   - data/performance_data.json")
    print("   - data/holdings_data.json")
    print("   - data/metrics.json")

if __name__ == "__main__":
    main()
