"""
Summarize the Innovation Factor Regression Methodology
Analyze what the regression is doing and identify potential issues.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

from lib.etf.functions.research.core.factors import rolling_ols

OUTPUT_DIR = Path('./data/research/sp500_backtest')
FUNDAMENTALS_DIR = Path('./data/research/sp500_fundamentals')

def analyze_regression_methodology():
    """Analyze the regression methodology step by step."""
    
    print("="*70)
    print("INNOVATION FACTOR REGRESSION METHODOLOGY SUMMARY")
    print("="*70)
    
    print("\n" + "="*70)
    print("1. REGRESSION SPECIFICATION")
    print("="*70)
    print("""
    Model: log(sales_t) = β₀ + β₁·log(R&D_{t-1}) + β₂·log(R&D_{t-2}) + 
                          β₃·log(R&D_{t-3}) + β₄·log(R&D_{t-4}) + β₅·log(R&D_{t-5}) + ε_t
    
    Innovation Factor = Average of (β₁, β₂, β₃, β₄, β₅)
    
    Interpretation:
    - Each βᵢ measures the elasticity of sales with respect to R&D spending i years ago
    - The innovation factor is the average long-term impact of R&D on sales
    - Higher values indicate more effective R&D spending
    """)
    
    print("\n" + "="*70)
    print("2. ROLLING WINDOW APPROACH")
    print("="*70)
    print("""
    For each firm-year observation:
    - Uses an 8-year rolling window ending at the current year
    - Example: For year 2010, uses data from 2003-2010
    - Requires at least 4 out of 5 lags to be non-missing
    - Estimates OLS regression on all available observations in the window
    
    Window Selection:
    - Window: [year - 7, year] (8 years total)
    - Only uses data STRICTLY BEFORE the rebalance date (point-in-time)
    """)
    
    print("\n" + "="*70)
    print("3. DATA REQUIREMENTS")
    print("="*70)
    print("""
    Required for each firm:
    - At least 8 years of annual data
    - Both sales/revenue and R&D spending must be positive
    - At least 4 out of 5 lagged R&D values must be non-missing
    
    Data Filtering:
    - Drops rows with missing or non-positive sales/R&D
    - Uses log transformation: log(sales) and log(R&D)
    - Non-positive R&D values are set to NaN before lagging
    """)
    
    print("\n" + "="*70)
    print("4. POTENTIAL ISSUES TO CHECK")
    print("="*70)
    
    # Load sample data to check
    print("\n4.1 Checking sample ticker (AAPL)...")
    try:
        aapl_file = FUNDAMENTALS_DIR / 'AAPL_income_annual.csv'
        if aapl_file.exists():
            aapl_df = pd.read_csv(aapl_file)
            aapl_df['date'] = pd.to_datetime(aapl_df['date'])
            aapl_df = aapl_df.sort_values('date')
            
            # Find sales and R&D columns
            sales_col = None
            rd_col = None
            for col in aapl_df.columns:
                col_lower = col.lower()
                if 'revenue' in col_lower or 'sales' in col_lower:
                    if sales_col is None:
                        sales_col = col
                if 'research' in col_lower or 'rd' in col_lower or 'r&d' in col_lower:
                    if rd_col is None:
                        rd_col = col
            
            if sales_col and rd_col:
                print(f"  Sales column: {sales_col}")
                print(f"  R&D column: {rd_col}")
                
                # Prepare data
                prep_df = aapl_df[[sales_col, rd_col, 'date']].copy()
                prep_df['year'] = prep_df['date'].dt.year
                prep_df['ticker'] = 'AAPL'
                prep_df = prep_df.dropna()
                prep_df = prep_df[(prep_df[sales_col] > 0) & (prep_df[rd_col] > 0)]
                
                print(f"  Years of data: {len(prep_df)}")
                print(f"  Year range: {prep_df['year'].min()} to {prep_df['year'].max()}")
                
                # Run rolling OLS for a sample year
                sample_year = 2010
                prep_df_filtered = prep_df[prep_df['year'] <= sample_year].copy()
                
                if len(prep_df_filtered) >= 8:
                    results = rolling_ols(
                        df=prep_df_filtered,
                        firm_col='ticker',
                        year_col='year',
                        sales_col=sales_col,
                        rd_col=rd_col
                    )
                    
                    if not results.empty:
                        # Get results for sample_year
                        if (prep_df_filtered['ticker'].iloc[0], sample_year) in results.index:
                            row = results.loc[(prep_df_filtered['ticker'].iloc[0], sample_year)]
                            print(f"\n  Sample regression results for {sample_year}:")
                            print(f"    Intercept: {row.get('const', 'N/A'):.4f}")
                            for i in range(1, 6):
                                lag_val = row.get(f'lag{i}', np.nan)
                                print(f"    lag{i} (β{i}): {lag_val:.4f}")
                            
                            lag_coefs = [row.get(f'lag{i}', np.nan) for i in range(1, 6)]
                            valid_coefs = [c for c in lag_coefs if pd.notna(c)]
                            innovation_factor = np.mean(valid_coefs)
                            print(f"    Innovation Factor (avg): {innovation_factor:.4f}")
    except Exception as e:
        print(f"  Error checking sample: {e}")
    
    print("\n4.2 Potential Issues:")
    print("""
    A. COEFFICIENT STABILITY:
       - Coefficients are calculated annually but used monthly
       - Same coefficient value used for all months in a year
       - This is CORRECT (annual data, monthly rebalancing)
    
    B. WINDOW SELECTION:
       - Uses 8-year window ending at current year
       - For year 2010, uses 2003-2010 data
       - This means the regression includes the current year's sales
       - QUESTION: Should we exclude current year to avoid look-ahead?
    
    C. LAG REQUIREMENTS:
       - Requires ≥4 non-missing lags out of 5
       - This is reasonable but may exclude early years
    
    D. POINT-IN-TIME FILTERING:
       - Filters data to be BEFORE rebalance date
       - Uses most recent available year < rebalance_year
       - This is CORRECT for point-in-time analysis
    
    E. AVERAGING COEFFICIENTS:
       - Innovation factor = mean(β₁, β₂, β₃, β₄, β₅)
       - This assumes equal weights for all lags
       - Alternative: Could weight by lag (e.g., more weight to recent lags)
    """)
    
    print("\n" + "="*70)
    print("5. CHECKING FOR SPECIFIC ISSUES")
    print("="*70)
    
    # Check if coefficients are being calculated correctly
    print("\n5.1 Checking coefficient calculation logic...")
    print("""
    Current Implementation:
    1. For each rebalance date, filter fundamentals to data < rebalance_date
    2. Run rolling_ols on filtered data
    3. Find most recent year < rebalance_year in results
    4. Extract lag1-lag5 coefficients
    5. Average them (excluding NaN)
    
    Potential Issue:
    - The rolling_ols function calculates coefficients for EACH year in the data
    - But we only use the most recent year's coefficients
    - This means we're using a regression that includes the current year's sales
    - This could be a look-ahead bias if the current year's sales are not yet known
    """)
    
    # Check the actual coefficients file
    print("\n5.2 Analyzing coefficient patterns...")
    coeff_file = OUTPUT_DIR / 'innovation_coefficients_all_constituents.csv'
    if coeff_file.exists():
        df = pd.read_csv(coeff_file)
        
        # Check if same ticker has same coefficient across months
        sample_ticker = 'AAPL'
        aapl_data = df[df['ticker'] == sample_ticker].head(12)
        if not aapl_data.empty:
            print(f"\n  {sample_ticker} coefficients across first 12 months:")
            print(aapl_data[['year_month', 'innovation_coefficient']].to_string())
            
            # Check if values are identical
            unique_vals = aapl_data['innovation_coefficient'].nunique()
            print(f"\n  Unique values in first 12 months: {unique_vals}")
            if unique_vals == 1:
                print("  ⚠️  WARNING: Same coefficient used for all months in a year")
                print("     This is expected for annual data, but verify it updates yearly")
        
        # Check when coefficients change
        print("\n  Checking when coefficients change for AAPL...")
        aapl_all = df[df['ticker'] == sample_ticker].sort_values('year_month')
        aapl_all['coef_changed'] = aapl_all['innovation_coefficient'].diff() != 0
        changes = aapl_all[aapl_all['coef_changed'] == True]
        if not changes.empty:
            print(f"  Coefficient changes at {len(changes)} year-months:")
            print(changes[['year_month', 'innovation_coefficient']].head(10).to_string())
        else:
            print("  No changes detected (coefficient is constant)")
    
    print("\n" + "="*70)
    print("6. RECOMMENDATIONS")
    print("="*70)
    print("""
    1. VERIFY WINDOW SELECTION:
       - Current: Uses [year-7, year] window
       - Question: Should we use [year-8, year-1] to exclude current year?
       - This would avoid using current year's sales to predict current year
    
    2. VERIFY LAG CALCULATION:
       - Current: lag1 = R&D from 1 year ago, lag2 = 2 years ago, etc.
       - Verify: Are lags calculated correctly within each firm's time series?
    
    3. VERIFY POINT-IN-TIME FILTERING:
       - Current: Filters to data < rebalance_date
       - Verify: Is the most recent year truly before the rebalance date?
    
    4. CHECK FOR MULTICOLLINEARITY:
       - Lagged R&D variables are likely highly correlated
       - This could cause unstable coefficient estimates
       - Consider: Principal components or regularization
    
    5. VERIFY AVERAGING METHOD:
       - Current: Simple average of 5 coefficients
       - Alternative: Weighted average (more weight to recent lags)
       - Alternative: Use only lag1 (most recent impact)
    """)
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("""
    The regression methodology:
    ✓ Uses point-in-time data (filters to before rebalance date)
    ✓ Uses 8-year rolling window
    ✓ Requires sufficient data (≥8 years, ≥4 lags)
    ✓ Averages 5 lag coefficients
    
    Potential issues:
    ⚠️  Window includes current year (could be look-ahead bias)
    ⚠️  Same coefficient used for all months in a year (expected but verify updates)
    ⚠️  Simple averaging may not be optimal
    ⚠️  Multicollinearity in lagged variables
    """)

if __name__ == '__main__':
    analyze_regression_methodology()

