import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def create_holdings_data():
    """Create comprehensive holdings data for RED ETF"""
    
    # Set random seed for reproducibility
    np.random.seed(42)
    random.seed(42)
    
    # Sample companies with innovation focus
    companies = [
        # Technology
        ("NVDA", "NVIDIA Corporation", "67066G104", "Technology"),
        ("MSFT", "Microsoft Corporation", "594918104", "Technology"),
        ("GOOGL", "Alphabet Inc.", "02079K305", "Technology"),
        ("AAPL", "Apple Inc.", "037833100", "Technology"),
        ("TSLA", "Tesla, Inc.", "88160R101", "Consumer Discretionary"),
        ("AMZN", "Amazon.com Inc.", "023135106", "Consumer Discretionary"),
        ("META", "Meta Platforms Inc.", "30303M102", "Technology"),
        ("NFLX", "Netflix Inc.", "64110L106", "Communication Services"),
        ("CRM", "Salesforce Inc.", "79466L302", "Technology"),
        ("ADBE", "Adobe Inc.", "00724F101", "Technology"),
        
        # Healthcare/Biotech
        ("JNJ", "Johnson & Johnson", "478160104", "Healthcare"),
        ("PFE", "Pfizer Inc.", "717081103", "Healthcare"),
        ("UNH", "UnitedHealth Group Inc.", "91324P102", "Healthcare"),
        ("ABBV", "AbbVie Inc.", "00287Y109", "Healthcare"),
        ("TMO", "Thermo Fisher Scientific Inc.", "883556102", "Healthcare"),
        ("DHR", "Danaher Corporation", "235851102", "Healthcare"),
        ("LLY", "Eli Lilly and Company", "532457108", "Healthcare"),
        ("ABT", "Abbott Laboratories", "002824100", "Healthcare"),
        ("BMY", "Bristol-Myers Squibb Company", "110122108", "Healthcare"),
        ("AMGN", "Amgen Inc.", "031162100", "Healthcare"),
        
        # Financial Services
        ("JPM", "JPMorgan Chase & Co.", "46625H100", "Financial Services"),
        ("BAC", "Bank of America Corp.", "060505104", "Financial Services"),
        ("WFC", "Wells Fargo & Company", "949746101", "Financial Services"),
        ("GS", "Goldman Sachs Group Inc.", "38141G104", "Financial Services"),
        ("MS", "Morgan Stanley", "617446448", "Financial Services"),
        ("C", "Citigroup Inc.", "172967424", "Financial Services"),
        ("BLK", "BlackRock Inc.", "09247X101", "Financial Services"),
        ("SCHW", "Charles Schwab Corporation", "808513105", "Financial Services"),
        ("USB", "U.S. Bancorp", "902973304", "Financial Services"),
        
        # Consumer/Industrial
        ("PG", "Procter & Gamble Co.", "742718109", "Consumer Staples"),
        ("KO", "Coca-Cola Company", "191216100", "Consumer Staples"),
        ("PEP", "PepsiCo Inc.", "713448108", "Consumer Staples"),
        ("WMT", "Walmart Inc.", "931142103", "Consumer Staples"),
        ("HD", "Home Depot Inc.", "437076102", "Consumer Discretionary"),
        ("MCD", "McDonald's Corporation", "580135101", "Consumer Discretionary"),
        ("DIS", "Walt Disney Company", "254687106", "Communication Services"),
        ("NKE", "Nike Inc.", "654106103", "Consumer Discretionary"),
        ("SBUX", "Starbucks Corporation", "855244109", "Consumer Discretionary"),
        ("TGT", "Target Corporation", "87612E106", "Consumer Discretionary"),
        
        # Energy/Utilities
        ("XOM", "Exxon Mobil Corporation", "30231G102", "Energy"),
        ("CVX", "Chevron Corporation", "166764100", "Energy"),
        ("COP", "ConocoPhillips", "20825C104", "Energy"),
        ("EOG", "EOG Resources Inc.", "26875P101", "Energy"),
        ("SLB", "Schlumberger Limited", "806857108", "Energy"),
        ("DUK", "Duke Energy Corporation", "26441C204", "Utilities"),
        ("SO", "Southern Company", "842587107", "Utilities"),
        ("D", "Dominion Energy Inc.", "25746U109", "Utilities"),
        ("NEE", "NextEra Energy Inc.", "65339F101", "Utilities"),
        ("AEP", "American Electric Power Co.", "025537101", "Utilities"),
        
        # Materials/Real Estate
        ("LIN", "Linde plc", "532017104", "Materials"),
        ("APD", "Air Products and Chemicals Inc.", "009158106", "Materials"),
        ("ECL", "Ecolab Inc.", "278865100", "Materials"),
        ("SHW", "Sherwin-Williams Company", "824348106", "Materials"),
        ("PLD", "Prologis Inc.", "74340W103", "Real Estate"),
        ("AMT", "American Tower Corporation", "03027X100", "Real Estate"),
        ("CCI", "Crown Castle Inc.", "22822V101", "Real Estate"),
        ("EQIX", "Equinix Inc.", "29444U700", "Real Estate"),
        ("O", "Realty Income Corporation", "756109104", "Real Estate"),
        ("SPG", "Simon Property Group Inc.", "828806109", "Real Estate")
    ]
    
    # Create holdings data
    holdings_data = []
    total_assets = 100000000  # $100M fund
    
    for i, (ticker, name, cusip, sector) in enumerate(companies):
        # Generate realistic allocation percentages (weighted towards innovation sectors)
        if sector in ["Technology", "Healthcare"]:
            # Higher allocations for innovation-focused sectors
            allocation = np.random.uniform(2.0, 8.0)
        elif sector in ["Consumer Discretionary", "Communication Services"]:
            # Medium allocations for growth sectors
            allocation = np.random.uniform(1.5, 5.0)
        else:
            # Lower allocations for traditional sectors
            allocation = np.random.uniform(0.5, 3.0)
        
        # Ensure total doesn't exceed 100%
        if sum([h['allocation'] for h in holdings_data]) + allocation > 95:
            allocation = max(0.1, 95 - sum([h['allocation'] for h in holdings_data]))
        
        # Calculate market value and shares
        market_value = (allocation / 100) * total_assets
        price = np.random.uniform(50, 500)  # Realistic stock prices
        shares = int(market_value / price)
        
        # Adjust for minimum position size
        if market_value < 500000:  # $500k minimum
            market_value = 500000
            shares = int(market_value / price)
            allocation = (market_value / total_assets) * 100
        
        holdings_data.append({
            'ticker': ticker,
            'name': name,
            'cusip': cusip,
            'sector': sector,
            'allocation': round(allocation, 2),
            'shares': shares,
            'price': round(price, 2),
            'market_value': round(market_value, 0)
        })
    
    # Sort by allocation (highest first)
    holdings_data.sort(key=lambda x: x['allocation'], reverse=True)
    
    # Normalize allocations to ensure they sum to 100%
    total_allocation = sum([h['allocation'] for h in holdings_data])
    for holding in holdings_data:
        holding['allocation'] = round((holding['allocation'] / total_allocation) * 100, 2)
        holding['market_value'] = round((holding['allocation'] / 100) * total_assets, 0)
        holding['shares'] = int(holding['market_value'] / holding['price'])
    
    return holdings_data

def create_holdings_excel():
    """Create Excel file with holdings data"""
    
    holdings_data = create_holdings_data()
    
    # Create DataFrame
    df = pd.DataFrame(holdings_data)
    
    # Add additional columns
    df['date'] = datetime.now().strftime('%Y-%m-%d')
    df['fund'] = 'RED'
    df['fund_name'] = 'Diamond Brothers Innovation Factor ETF'
    
    # Reorder columns
    columns_order = [
        'fund', 'fund_name', 'date', 'ticker', 'name', 'cusip', 'sector',
        'allocation', 'shares', 'price', 'market_value'
    ]
    df = df[columns_order]
    
    # Create Excel file
    filename = 'red_holdings.xlsx'
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Main holdings sheet
        df.to_excel(writer, sheet_name='Holdings', index=False)
        
        # Summary sheet
        summary_data = []
        for sector in df['sector'].unique():
            sector_data = df[df['sector'] == sector]
            summary_data.append({
                'Sector': sector,
                'Holdings': len(sector_data),
                'Allocation': round(sector_data['allocation'].sum(), 2),
                'Market Value': round(sector_data['market_value'].sum(), 0)
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values('Allocation', ascending=False)
        summary_df.to_excel(writer, sheet_name='Sector Summary', index=False)
        
        # Fund details sheet
        fund_details = {
            'Fund Ticker': ['RED'],
            'Fund Name': ['Diamond Brothers Innovation Factor ETF'],
            'Total Holdings': [len(df)],
            'Total Market Value': [df['market_value'].sum()],
            'Date': [datetime.now().strftime('%Y-%m-%d')],
            'Top 10 Allocation': [df.head(10)['allocation'].sum()],
            'Technology Allocation': [df[df['sector'] == 'Technology']['allocation'].sum()],
            'Healthcare Allocation': [df[df['sector'] == 'Healthcare']['allocation'].sum()]
        }
        
        fund_df = pd.DataFrame(fund_details)
        fund_df.to_excel(writer, sheet_name='Fund Details', index=False)
    
    print(f"Holdings Excel file created: {filename}")
    print(f"Total holdings: {len(df)}")
    print(f"Total allocation: {df['allocation'].sum():.2f}%")
    print(f"Top 10 holdings allocation: {df.head(10)['allocation'].sum():.2f}%")
    
    return filename

if __name__ == "__main__":
    create_holdings_excel() 