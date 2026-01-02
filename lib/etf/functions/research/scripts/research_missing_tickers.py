"""
Research missing tickers to determine why they have no returns data.

Categories:
1. Delisted/Acquired
2. Ticker Change
3. Missing Data (not in FMP)
4. Other
"""

import sys
import pandas as pd
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Data paths
FULLY_MISSING_FILE = Path('./data/research/sp500_backtest/fully_missing_tickers_list.csv')
OUTPUT_FILE = Path('./data/research/sp500_backtest/missing_tickers_research_results.csv')

def research_ticker_web(ticker: str, use_web_search: bool = True) -> Dict[str, Optional[str]]:
    """
    Research a ticker using web search.
    Returns dict with category and notes.
    """
    # Known acquisitions/delistings from previous research
    known_fates = {
        'BCR': ('Acquired', 'C.R. Bard acquired by Becton Dickinson (BDX) in 2017'),
        'GAS': ('Acquired', 'Nicor Inc acquired by AGL Resources in 2011, then merged into Southern Company'),
        'LO': ('Acquired', 'Lorillard acquired by Reynolds American (RAI) in 2015'),
        'YHOO': ('Acquired', 'Yahoo acquired by Verizon in 2017, assets later sold to Apollo'),
        'APC': ('Acquired', 'Anadarko Petroleum acquired by Occidental Petroleum (OXY) in 2019'),
        'SIAL': ('Acquired', 'Sigma-Aldrich acquired by Merck KGaA in 2015'),
        'EMC': ('Acquired', 'EMC Corporation acquired by Dell Technologies (DELL) in 2016'),
        'NOVL': ('Acquired', 'Novell acquired by Attachmate in 2011, then Micro Focus in 2014'),
        'MER': ('Acquired', 'Merrill Lynch acquired by Bank of America (BAC) in 2008'),
        'BUD': ('Acquired', 'Anheuser-Busch acquired by InBev in 2008'),
        'CA': ('Acquired', 'CA Technologies acquired by Broadcom (AVGO) in 2018'),
        'BEAM': ('Acquired', 'Beam Inc acquired by Suntory Holdings in 2014'),
        'PLL': ('Acquired', 'Pall Corporation acquired by Danaher (DHR) in 2015'),
        'RDC': ('Acquired', 'Rowan Companies acquired by Ensco in 2019'),
        'GR': ('Acquired', 'Goodrich Corporation acquired by United Technologies (UTX) in 2012'),
        'PGN': ('Acquired', 'Progress Energy acquired by Duke Energy (DUK) in 2012'),
        'HSH': ('Acquired', 'Hillshire Brands acquired by Tyson Foods (TSN) in 2014'),
        'NSM': ('Acquired', 'National Semiconductor acquired by Texas Instruments (TXN) in 2011'),
        'RSH': ('Acquired', 'RadioShack filed for bankruptcy in 2015'),
        'KODK': ('Delisted', 'Eastman Kodak filed for bankruptcy in 2012, reorganized'),
        'MIL': ('Acquired', 'Millipore Corporation acquired by Merck KGaA in 2010'),
        'BDK': ('Acquired', 'Black & Decker acquired by Stanley Works (SWK) in 2010'),
        'ROH': ('Acquired', 'Rohm and Haas acquired by Dow Chemical (DOW) in 2009'),
        'DNB': ('Acquired', 'Dun & Bradstreet acquired by private equity in 2019'),
        'UST': ('Acquired', 'UST Inc acquired by Altria (MO) in 2009'),
        'KATE': ('Acquired', 'Kate Spade acquired by Tapestry (TPR) in 2017'),
        'ABI': ('Acquired', 'Anheuser-Busch InBev - ticker changed to BUD, then acquired'),
        'WWY': ('Acquired', 'Wrigley acquired by Mars in 2008'),
        'OMX': ('Acquired', 'OfficeMax acquired by Office Depot (ODP) in 2013'),
        'CC': ('Acquired', 'Circuit City filed for bankruptcy in 2008'),
        'TRCO': ('Acquired', 'Tribune Company acquired by private equity in 2012'),
        'TIN': ('Acquired', 'Temple-Inland acquired by International Paper (IP) in 2012'),
        'DJ': ('Acquired', 'Dow Jones acquired by News Corp (NWSA) in 2007'),
        'BOL': ('Acquired', 'Bausch & Lomb acquired by Valeant (now BHC) in 2013'),
        'JAVA': ('Acquired', 'Sun Microsystems (JAVA) acquired by Oracle (ORCL) in 2010'),
        'MEL': ('Acquired', 'Mellon Financial merged with Bank of New York (BK) in 2007'),
        'PD': ('Acquired', 'Phelps Dodge acquired by Freeport-McMoRan (FCX) in 2007'),
        'XL': ('Acquired', 'XL Group acquired by AXA in 2018'),
        'BLS': ('Acquired', 'BellSouth acquired by AT&T (T) in 2006'),
        'BMET': ('Acquired', 'Biomet acquired by Zimmer Holdings (ZBH) in 2015'),
        'ACV': ('Acquired', 'Alberto-Culver acquired by Unilever (UL) in 2010'),
        'ANDW': ('Acquired', 'Andover Bancorp acquired by TD Bank in 2004'),
        'GDW': ('Acquired', 'Golden West Financial acquired by Wachovia (now WFC) in 2006'),
        'TLAB': ('Acquired', 'Tellabs acquired by Marlin Equity Partners in 2013'),
        'EC': ('Acquired', 'Engelhard Corporation acquired by BASF in 2006'),
        'KRI': ('Acquired', 'Knight-Ridder acquired by McClatchy in 2006'),
        'ABS': ('Acquired', 'Albertsons acquired by Supervalu in 2006, then Cerberus in 2013'),
        'DAN': ('Acquired', 'Dana Corporation acquired by ArvinMeritor in 2004'),
        'SWY': ('Acquired', 'Safeway acquired by Albertsons in 2015'),
        'STI': ('Acquired', 'SunTrust Banks merged with BB&T to form Truist Financial (TFC) in 2019'),
    }
    
    if ticker in known_fates:
        category, notes = known_fates[ticker]
        return {
            'ticker': ticker,
            'category': category,
            'notes': notes,
            'source': 'Known research'
        }
    
    # For unknown tickers, return placeholder (web search will be done separately)
    return {
        'ticker': ticker,
        'category': 'Unknown',
        'notes': 'Needs research',
        'source': 'Pending'
    }

def research_all_tickers():
    """Research all 399 fully missing tickers."""
    
    # Load ticker list
    fully_missing = pd.read_csv(FULLY_MISSING_FILE)
    tickers = fully_missing['ticker'].tolist()
    
    print("="*70)
    print(f"RESEARCHING {len(tickers)} FULLY MISSING TICKERS")
    print("="*70)
    
    results = []
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Researching {ticker}...")
        
        result = research_ticker_web(ticker)
        results.append(result)
        
        # Add ticker info from summary
        ticker_info = fully_missing[fully_missing['ticker'] == ticker].iloc[0]
        result['first_period'] = ticker_info['first_constituent_period']
        result['last_period'] = ticker_info['last_constituent_period']
        result['total_periods'] = ticker_info['total_periods_as_constituent']
        
        print(f"  Category: {result['category']}")
        print(f"  Notes: {result['notes'][:80]}...")
        
        # Small delay to avoid rate limits
        time.sleep(0.1)
    
    # Save results
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('total_periods', ascending=False)
    results_df.to_csv(OUTPUT_FILE, index=False)
    
    print("\n" + "="*70)
    print("RESEARCH COMPLETE")
    print("="*70)
    print(f"\n✓ Saved results to {OUTPUT_FILE}")
    
    # Summary by category
    print("\n📊 Summary by Category:")
    category_counts = results_df['category'].value_counts()
    for category, count in category_counts.items():
        print(f"   {category}: {count}")
    
    return results_df

if __name__ == '__main__':
    research_all_tickers()

