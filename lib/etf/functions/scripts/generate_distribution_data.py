#!/usr/bin/env python3
"""
Generate distribution data for ETF website display
"""

import os
import sys
import json
from pathlib import Path
from datetime import date
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

# Load .env
env_file = Path(__file__).parent.parent.parent.parent.parent / '.env'
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

from lib.etf.adapters import FMPDataSourceAdapter
from lib.etf.functions.research.core.backtesting import FMPClient
from lib.etf.functions.core.distribution_calculator import DistributionCalculator
from lib.etf.functions.core import FundAdministration
from test_itan_fmp_workflows import ITAN_HOLDINGS, format_holdings_for_adapter


def generate_distribution_data(etf_symbol: str = "ITAN", output_path: str = None):
    """
    Generate distribution data for the ETF and save to JSON file.
    
    Args:
        etf_symbol: ETF ticker symbol
        output_path: Path to save JSON file (default: etfs/{symbol}/distributions.json)
    """
    # Setup
    holdings = format_holdings_for_adapter([
        h for h in ITAN_HOLDINGS 
        if h['ticker'] not in ['Cash&Other', 'BBG01SQXBKP2', 'FGXXX']
    ])
    
    fmp_client = FMPClient(api_key=os.getenv('FMP_API_KEY'))
    adapter = FMPDataSourceAdapter(manual_holdings=holdings, api_key=os.getenv('FMP_API_KEY'))
    admin = FundAdministration(data_adapter=adapter, storage_path='./data/admin')
    
    # Calculate NAV to get shares outstanding
    nav_calc = admin.calculate_nav(date.today())
    if nav_calc.nav_per_share > 0:
        shares_outstanding = nav_calc.net_assets / nav_calc.nav_per_share
    else:
        shares_outstanding = nav_calc.net_assets / Decimal('50')
    
    calculator = DistributionCalculator(fmp_client, adapter)
    
    # Calculate distributions for last 2 years
    start_date = date(2023, 1, 1)
    end_date = date.today()
    expense_ratio = Decimal('0.0075')  # 0.75% annual expense ratio
    
    distributions = calculator.calculate_distributions(
        start_date, 
        end_date, 
        shares_outstanding,
        expense_ratio=expense_ratio
    )
    
    # Format for website display
    formatted_distributions = []
    for dist in distributions:
        formatted_distributions.append({
            'ex_date': dist['ex_date'].isoformat(),
            'record_date': dist['record_date'].isoformat(),
            'payable_date': dist['payable_date'].isoformat(),
            'income': round(dist['income'], 4),
            'short_term_capital_gain': round(dist['short_term_capital_gain'], 4),
            'long_term_capital_gain': round(dist['long_term_capital_gain'], 4),
            'total_capital_gain': round(dist['total_capital_gain'], 4),
            'total_distribution': round(dist['total_distribution'], 4)
        })
    
    # Save to file
    if output_path is None:
        output_path = f"etfs/{etf_symbol.lower()}/distributions.json"
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            'etf_symbol': etf_symbol,
            'last_updated': date.today().isoformat(),
            'distributions': formatted_distributions
        }, f, indent=2)
    
    print(f"Generated distribution data: {len(formatted_distributions)} distributions")
    print(f"Saved to: {output_path}")
    
    return formatted_distributions


if __name__ == '__main__':
    generate_distribution_data("ITAN", "etfs/redi/distributions.json")

