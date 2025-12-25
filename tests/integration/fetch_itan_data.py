"""
Script to fetch and prepare live ITAN ETF data for testing
Fetches real market data where available, creates dummy data for unavailable sources
"""

import yfinance as yf
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
import json
import yaml

# ITAN ETF ticker
ITAN_TICKER = "ITAN"


def fetch_itan_price_history(output_path: str = "./data/itan_test/nav_history.csv"):
    """Fetch ITAN's price history to use as NAV history"""
    print("Fetching ITAN price history...")
    
    try:
        itan = yf.Ticker(ITAN_TICKER)
        hist = itan.history(period="2y")  # Last 2 years
        
        if hist.empty:
            print("⚠ No price history available, creating dummy data")
            return create_dummy_nav_history(output_path)
        
        # Convert to NAV history format
        nav_data = []
        for idx, row in hist.iterrows():
            nav_data.append({
                'date': idx.date().isoformat(),
                'nav': float(row['Close'])
            })
        
        df = pd.DataFrame(nav_data)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        print(f"✓ Fetched {len(nav_data)} days of ITAN price history")
        print(f"  Date range: {nav_data[0]['date']} to {nav_data[-1]['date']}")
        print(f"  Latest NAV: ${nav_data[-1]['nav']:.2f}")
        
        return output_path
    except Exception as e:
        print(f"⚠ Error fetching ITAN price history: {e}")
        print("  Creating dummy NAV history instead")
        return create_dummy_nav_history(output_path)


def create_dummy_nav_history(output_path: str):
    """Create dummy NAV history"""
    nav_data = []
    start_date = date.today() - timedelta(days=365)
    base_nav = 25.00
    
    current_date = start_date
    nav = base_nav
    
    while current_date <= date.today():
        # Simulate NAV growth with some volatility
        import random
        change = random.uniform(-0.02, 0.02)
        nav = nav * (1 + change)
        nav_data.append({
            'date': current_date.isoformat(),
            'nav': round(nav, 4)
        })
        current_date += timedelta(days=1)
    
    df = pd.DataFrame(nav_data)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"✓ Created dummy NAV history: {len(nav_data)} days")
    return output_path


def fetch_itan_holdings():
    """Fetch ITAN holdings - use sample based on public disclosures"""
    print("\nFetching ITAN holdings...")
    
    # ITAN's actual top holdings (based on public disclosures)
    # Note: Exact quantities are estimates based on typical ETF structure
    holdings = [
        {"ticker": "AMZN", "name": "Amazon.com Inc.", "cusip": "023135106", "quantity": 11923, "weight": 3.5},
        {"ticker": "GOOGL", "name": "Alphabet Inc. Class A", "cusip": "02079K305", "quantity": 4952, "weight": 2.8},
        {"ticker": "GOOG", "name": "Alphabet Inc. Class C", "cusip": "02079K107", "quantity": 4948, "weight": 2.8},
        {"ticker": "IBM", "name": "International Business Machines Corp", "cusip": "459200101", "quantity": 4333, "weight": 2.1},
        {"ticker": "CSCO", "name": "Cisco Systems Inc.", "cusip": "17275R102", "quantity": 14709, "weight": 1.9},
        {"ticker": "CRM", "name": "Salesforce Inc.", "cusip": "79466L302", "quantity": 4206, "weight": 1.8},
        {"ticker": "QCOM", "name": "Qualcomm Inc.", "cusip": "747525103", "quantity": 6201, "weight": 1.7},
        {"ticker": "ACN", "name": "Accenture PLC", "cusip": "G1151C101", "quantity": 3730, "weight": 1.6},
        {"ticker": "COF", "name": "Capital One Financial Corp", "cusip": "194162103", "quantity": 4124, "weight": 1.5},
        {"ticker": "T", "name": "AT&T Inc.", "cusip": "00206R102", "quantity": 40789, "weight": 1.4},
        {"ticker": "MRK", "name": "Merck & Co. Inc.", "cusip": "58933Y105", "quantity": 9508, "weight": 1.3},
        {"ticker": "WFC", "name": "Wells Fargo & Company", "cusip": "949746101", "quantity": 10284, "weight": 1.2},
        {"ticker": "PFE", "name": "Pfizer Inc.", "cusip": "717081103", "quantity": 37243, "weight": 1.1},
        {"ticker": "INTC", "name": "Intel Corp.", "cusip": "458140100", "quantity": 25570, "weight": 1.0},
        {"ticker": "DIS", "name": "Walt Disney Co.", "cusip": "254687106", "quantity": 7849, "weight": 0.9},
    ]
    
    # Try to fetch current prices for holdings
    print("  Fetching current prices...")
    tickers = [h["ticker"] for h in holdings]
    
    try:
        data = yf.download(tickers, period="1d", progress=False)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                prices = data['Close'].iloc[-1]
                for holding in holdings:
                    ticker = holding["ticker"]
                    if ticker in prices.index:
                        holding["current_price"] = float(prices[ticker])
                        holding["market_value"] = holding["quantity"] * holding["current_price"]
            else:
                # Single ticker case
                if len(tickers) == 1:
                    holding = holdings[0]
                    holding["current_price"] = float(data['Close'].iloc[-1])
                    holding["market_value"] = holding["quantity"] * holding["current_price"]
    except Exception as e:
        print(f"  ⚠ Could not fetch prices: {e}")
        # Use dummy prices
        for holding in holdings:
            holding["current_price"] = 100.0
            holding["market_value"] = holding["quantity"] * 100.0
    
    print(f"✓ Prepared {len(holdings)} ITAN holdings")
    return holdings


def create_itan_config(output_path: str = "./data/itan_test/config.yaml"):
    """Create ITAN configuration file"""
    print("\nCreating ITAN configuration...")
    
    config = {
        'fund': {
            'name': 'Sparkline Intangible Value ETF',
            'ticker': 'ITAN',
            'inception_date': '2021-06-28',
            'fiscal_year_end': '12-31',
            'shares_outstanding': 1730000,  # Approximate
            'benchmark': '^GSPC'  # S&P 500
        },
        'distributions': {
            'frequency': 'Quarterly',
            'payout_ratio': 0.95  # 95% distribution, 5% retained
        },
        'tax': {
            'corporate_rate': 0.21,
            'excise_rate': 0.04,
            'dividend_tax_rate': 0.15,
            'lt_capital_gains_tax_rate': 0.20,
            'st_capital_gains_tax_rate': 0.37
        },
        'logging': {
            'level': 'INFO',
            'file': './data/itan_test/fund_admin.log'
        },
        'paths': {
            'nav_history': './data/itan_test/nav_history.csv',
            'distribution_history': './data/itan_test/distributions.csv',
            'admin_storage': './data/itan_test/admin',
            'accounting_storage': './data/itan_test/accounting',
            'tax_lot_storage': './data/itan_test/tax_lots',
            'distributor_storage': './data/itan_test/distributor',
            'performance_storage': './data/itan_test/performance',
            'tax_storage': './data/itan_test/tax'
        },
        'holdings': []  # Will be populated from fetched holdings
    }
    
    # Add holdings to config
    holdings = fetch_itan_holdings()
    for h in holdings:
        config['holdings'].append({
            'ticker': h['ticker'],
            'shares': h['quantity'],
            'cost_basis': h.get('current_price', 100.0) * 0.9  # Assume 10% gain
        })
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"✓ Created ITAN configuration: {output_path}")
    return output_path


def create_dummy_distributions(output_path: str = "./data/itan_test/distributions.csv"):
    """Create dummy distribution history"""
    print("\nCreating distribution history...")
    
    distributions = []
    current_date = date(2024, 1, 1)
    
    # Quarterly distributions
    while current_date <= date.today():
        if current_date.month in [3, 6, 9, 12]:
            # End of quarter
            distributions.append({
                'date': current_date.isoformat(),
                'distribution_per_share': 0.10,  # $0.10 per share
                'distribution_type': 'dividend'
            })
        current_date += timedelta(days=1)
    
    df = pd.DataFrame(distributions)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"✓ Created distribution history: {len(distributions)} distributions")
    return output_path


def main():
    """Main function to fetch and prepare all ITAN data"""
    print("=" * 60)
    print("ITAN ETF Live Data Preparation")
    print("=" * 60)
    
    data_dir = Path("./data/itan_test")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Fetch NAV history
    nav_file = fetch_itan_price_history(str(data_dir / "nav_history.csv"))
    
    # 2. Create distribution history
    dist_file = create_dummy_distributions(str(data_dir / "distributions.csv"))
    
    # 3. Create configuration
    config_file = create_itan_config(str(data_dir / "config.yaml"))
    
    # 4. Save holdings
    holdings = fetch_itan_holdings()
    holdings_file = data_dir / "holdings.json"
    with open(holdings_file, 'w') as f:
        json.dump(holdings, f, indent=2)
    print(f"\n✓ Saved holdings to {holdings_file}")
    
    print("\n" + "=" * 60)
    print("✓ ITAN data preparation complete!")
    print("=" * 60)
    print(f"\nData files created in: {data_dir}")
    print(f"  - NAV history: {nav_file}")
    print(f"  - Distributions: {dist_file}")
    print(f"  - Configuration: {config_file}")
    print(f"  - Holdings: {holdings_file}")
    print("\nYou can now run integration tests with:")
    print("  pytest tests/integration/test_itan_live_data.py -v")


if __name__ == "__main__":
    main()

