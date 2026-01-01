"""
Test script for FMP API functionality
Tests various endpoints to verify data access and quality
"""

import sys
from pathlib import Path
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime, timedelta
from lib.etf.functions.research import FMPClient, HoldingsLoader, FundamentalDataLoader, PriceLoader

# API Key - in production, use environment variable
API_KEY = "KzXIx6bXd7l7c9mIfRddOLBZY5AAgFVq"

def test_fmp_basic():
    """Test basic FMP API connectivity"""
    print("="*70)
    print("TESTING FMP API - BASIC CONNECTIVITY")
    print("="*70)
    
    fmp = FMPClient(api_key=API_KEY)
    
    # Test 1: ETF Holdings (current)
    print("\n1. Testing ETF Holdings (IWB - Russell 1000):")
    holdings = fmp.get_etf_holdings("IWB")
    if holdings:
        print(f"   ✓ Retrieved {len(holdings)} holdings")
        print(f"   Sample holdings:")
        for i, h in enumerate(holdings[:5]):
            symbol = h.get('symbol') or h.get('ticker') or h.get('assetSymbol', 'N/A')
            weight = h.get('weight', h.get('percentage', 'N/A'))
            print(f"     {i+1}. {symbol}: {weight}")
    else:
        print("   ✗ No holdings retrieved")
    
    # Test 2: ETF Holding Dates
    print("\n2. Testing ETF Holding Dates (IWB):")
    dates = fmp.get_etf_holding_dates("IWB")
    if dates:
        print(f"   ✓ Found {len(dates)} available dates")
        print(f"   First date: {dates[0]}")
        print(f"   Last date: {dates[-1]}")
    else:
        print("   ✗ No dates found")
    
    # Test 3: Price History (NVDA)
    print("\n3. Testing Price History (NVDA - last 30 days):")
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    price_df = fmp.get_price_history("NVDA", start_date=start_date, end_date=end_date)
    if not price_df.empty:
        print(f"   ✓ Retrieved {len(price_df)} days of price data")
        print(f"   Date range: {price_df.index.min()} to {price_df.index.max()}")
        print(f"   First price: ${price_df.iloc[0, 0]:.2f}")
        print(f"   Last price: ${price_df.iloc[-1, 0]:.2f}")
    else:
        print("   ✗ No price data retrieved")
    
    # Test 4: Multiple Price History
    print("\n4. Testing Multiple Price History (AAPL, MSFT, GOOGL):")
    symbols = ["AAPL", "MSFT", "GOOGL"]
    multi_price = fmp.get_multiple_price_history(symbols, start_date, end_date)
    if not multi_price.empty:
        print(f"   ✓ Retrieved data for {len(multi_price.columns)} symbols")
        print(f"   Columns: {list(multi_price.columns)}")
        print(f"   Date range: {multi_price.index.min()} to {multi_price.index.max()}")
    else:
        print("   ✗ No multi-price data retrieved")
    
    # Test 5: Enterprise Values
    print("\n5. Testing Enterprise Values (AAPL):")
    ev_data = fmp.get_enterprise_values("AAPL")
    if ev_data:
        print(f"   ✓ Retrieved enterprise value data")
        print(f"   Enterprise Value: ${ev_data.get('enterpriseValue', 'N/A'):,}" if isinstance(ev_data.get('enterpriseValue'), (int, float)) else f"   Enterprise Value: {ev_data.get('enterpriseValue', 'N/A')}")
    else:
        print("   ✗ No enterprise value data")
    
    # Test 6: Market Cap
    print("\n6. Testing Market Cap (AAPL):")
    mcap_data = fmp.get_market_cap("AAPL")
    if mcap_data:
        print(f"   ✓ Retrieved market cap data")
        mcap = mcap_data.get('marketCap', 'N/A')
        if isinstance(mcap, (int, float)):
            print(f"   Market Cap: ${mcap:,.0f}")
        else:
            print(f"   Market Cap: {mcap}")
    else:
        print("   ✗ No market cap data")
    
    # Test 7: Income Statement
    print("\n7. Testing Income Statement (AAPL - annual):")
    income = fmp.get_income_statement("AAPL", period='annual', limit=1)
    if income:
        print(f"   ✓ Retrieved income statement")
        inc = income[0]
        revenue = inc.get('revenue') or inc.get('salesRevenueNet')
        rd = inc.get('researchAndDevelopment') or inc.get('RD')
        print(f"   Revenue: ${revenue:,.0f}" if isinstance(revenue, (int, float)) else f"   Revenue: {revenue}")
        print(f"   R&D: ${rd:,.0f}" if isinstance(rd, (int, float)) else f"   R&D: {rd}")
    else:
        print("   ✗ No income statement data")
    
    # Test 8: Cash Flow Statement
    print("\n8. Testing Cash Flow Statement (AAPL - annual):")
    cashflow = fmp.get_cash_flow_statement("AAPL", period='annual', limit=1)
    if cashflow:
        print(f"   ✓ Retrieved cash flow statement")
        cf = cashflow[0]
        capex = cf.get('capitalExpenditure') or cf.get('capitalExpenditures')
        print(f"   CapEx: ${capex:,.0f}" if isinstance(capex, (int, float)) else f"   CapEx: {capex}")
    else:
        print("   ✗ No cash flow statement data")
    
    print("\n" + "="*70)
    print("BASIC API TESTS COMPLETE")
    print("="*70)
    
    return fmp


def test_holdings_loader():
    """Test HoldingsLoader functionality"""
    print("\n" + "="*70)
    print("TESTING HOLDINGS LOADER")
    print("="*70)
    
    fmp = FMPClient(api_key=API_KEY)
    loader = HoldingsLoader(fmp, etf_symbol="IWB")
    
    # Get recent date
    dates = fmp.get_etf_holding_dates("IWB")
    if dates:
        test_date = dates[-1]  # Most recent date
        print(f"\nTesting holdings for date: {test_date}")
        holdings = loader.get_holdings_by_date(test_date)
        print(f"✓ Retrieved {len(holdings)} holdings")
        print(f"Sample symbols: {holdings[:10]}")
    else:
        print("✗ No dates available for testing")


def test_fundamental_loader():
    """Test FundamentalDataLoader functionality"""
    print("\n" + "="*70)
    print("TESTING FUNDAMENTAL DATA LOADER")
    print("="*70)
    
    fmp = FMPClient(api_key=API_KEY)
    loader = FundamentalDataLoader(fmp)
    
    # Test with a few tech stocks
    test_symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "META"]
    print(f"\nTesting fundamental factors for: {test_symbols}")
    
    factors = loader.get_fundamental_factors(test_symbols)
    
    if not factors.empty:
        print(f"✓ Retrieved factors for {len(factors)} symbols")
        print("\nFactor Data:")
        print(factors.to_string())
    else:
        print("✗ No factor data retrieved")


def test_price_loader():
    """Test PriceLoader functionality"""
    print("\n" + "="*70)
    print("TESTING PRICE LOADER (FMP)")
    print("="*70)
    
    fmp = FMPClient(api_key=API_KEY)
    loader = PriceLoader(fmp)
    
    # Test with multiple symbols
    symbols = ["AAPL", "MSFT", "NVDA"]
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    
    print(f"\nTesting price data for: {symbols}")
    print(f"Date range: {start_date} to {end_date}")
    
    prices = loader.get_adjusted_close(symbols, start_date, end_date)
    
    if not prices.empty:
        print(f"✓ Retrieved price data")
        print(f"Shape: {prices.shape}")
        print(f"Date range: {prices.index.min()} to {prices.index.max()}")
        print("\nFirst few rows:")
        print(prices.head())
        print("\nLast few rows:")
        print(prices.tail())
        
        # Test returns calculation
        returns = loader.calculate_returns(prices)
        print(f"\n✓ Calculated returns for {len(returns)} days")
        print("Sample returns:")
        print(returns.head())
    else:
        print("✗ No price data retrieved")


def test_query_log():
    """Show query log to understand API usage"""
    print("\n" + "="*70)
    print("QUERY LOG SUMMARY")
    print("="*70)
    
    fmp = FMPClient(api_key=API_KEY)
    
    # Run a few queries
    fmp.get_etf_holdings("IWB")
    fmp.get_price_history("AAPL", start_date="2024-01-01", end_date="2024-12-31")
    
    print(f"\nTotal queries made: {len(fmp.query_log)}")
    print("\nQuery log:")
    for i, query in enumerate(fmp.query_log, 1):
        cached = "✓ cached" if query.get('cached') else "→ API call"
        print(f"  {i}. {query['endpoint']} {cached}")
        params = {k: v for k, v in query['params'].items() if k != 'apikey'}
        if params:
            print(f"     Params: {params}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("FMP API TESTING SUITE")
    print("="*70)
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-5:]}")
    print("="*70)
    
    try:
        # Run all tests
        fmp = test_fmp_basic()
        test_holdings_loader()
        test_fundamental_loader()
        test_price_loader()
        test_query_log()
        
        print("\n" + "="*70)
        print("ALL TESTS COMPLETE")
        print("="*70)
        print("\nNext steps:")
        print("1. Review the data quality and coverage")
        print("2. Identify any data gaps or issues")
        print("3. Build a data plan for your research needs")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


