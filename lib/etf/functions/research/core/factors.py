"""
Factor Analysis Module for ETF Strategy Research
Production-ready implementation for factor estimation and analysis.

This module provides:
- estimate_rq_mixedlm: Estimate Research Quotient (RQ) using mixed linear models
  per Knott's approach for measuring firm-specific R&D productivity
- rolling_ols: Estimate rolling OLS regressions with lagged R&D variables

Example:
    >>> from lib.etf.functions.research import estimate_rq_mixedlm, rolling_ols
    >>> rq_scores = estimate_rq_mixedlm(
    ...     df=fundamental_data,
    ...     firm_col="firm_id",
    ...     year_col="year",
    ...     y_col="revenue",
    ...     k_col="ppe",
    ...     l_col="labor",
    ...     r_col="rd"
    ... )
    >>> ols_results = rolling_ols(
    ...     df=fundamental_data,
    ...     firm_col="firm_id",
    ...     year_col="year",
    ...     sales_col="revenue",
    ...     rd_col="rd"
    ... )
"""

import logging
from typing import Optional, Union
import pandas as pd
import numpy as np

try:
    import statsmodels.formula.api as smf
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logging.getLogger(__name__).warning("statsmodels not available - RQ estimation will not work")

logger = logging.getLogger(__name__)


def estimate_rq_mixedlm(
    df: pd.DataFrame,
    firm_col: str = "firm_id",
    year_col: str = "year",
    y_col: str = "revenue",
    k_col: str = "ppe",
    l_col: str = "labor",
    r_col: str = "rd",
    a_col: Optional[str] = None,
    s_col: Optional[str] = None,
    window_years: int = 7,
    end_year: Optional[int] = None,
    add_year_fe: bool = True,
    full_random_slopes: bool = False,
    reml: bool = False
) -> pd.Series:
    """
    Estimate Research Quotient (RQ) as firm-specific output elasticity of R&D (gamma)
    using a random-coefficients (mixed effects) model, per Knott's 'fully specified' approach.

    Model (log form): lnY_it = (b0 + u0_i) + sum_j (bj + uji) * lnXjit + e_it
    RQ_i = gamma_i = (b_R + u_R,i) where R corresponds to ln(R&D).

    The RQ metric measures how effectively a firm converts R&D investment into revenue/output.
    Higher RQ indicates more productive R&D spending.

    Args:
        df: DataFrame with firm-year observations containing the required columns
        firm_col: Column name for firm identifier
        year_col: Column name for year
        y_col: Column name for output/revenue (dependent variable)
        k_col: Column name for physical capital (PPE)
        l_col: Column name for labor
        r_col: Column name for R&D spending
        a_col: Optional column name for advertising spending
        s_col: Optional column name for spillovers (external R&D effects)
        window_years: Number of years in the moving window (default: 7, per Knott tutorial)
        end_year: Specific end year for the window (default: max year in data)
        add_year_fe: Whether to include year fixed effects (helps control macro conditions)
        full_random_slopes: If True, random slopes for all inputs; else random slope only for ln(R&D)
        reml: Whether to use REML estimation (default: False, uses ML)

    Returns:
        pandas.Series indexed by firm_id with estimated RQ (gamma) for the chosen window.
        RQ values represent the firm-specific elasticity of output with respect to R&D.

    Raises:
        ValueError: If df is empty or required columns are missing
        ImportError: If statsmodels is not available

    Example:
        >>> df = pd.DataFrame({
        ...     'firm_id': ['A', 'A', 'B', 'B'],
        ...     'year': [2020, 2021, 2020, 2021],
        ...     'revenue': [100, 110, 200, 220],
        ...     'ppe': [50, 55, 100, 110],
        ...     'labor': [30, 32, 60, 65],
        ...     'rd': [10, 12, 20, 22]
        ... })
        >>> rq = estimate_rq_mixedlm(df, firm_col='firm_id', year_col='year')
        >>> print(rq)
    """
    if not STATSMODELS_AVAILABLE:
        raise ImportError(
            "statsmodels library is required for RQ estimation. "
            "Install with: pip install statsmodels"
        )

    if df is None or len(df) == 0:
        raise ValueError("df is empty")

    d = df.copy()

    # Validate and clean required columns
    required_cols = [firm_col, year_col, y_col, k_col, l_col, r_col]
    missing_cols = [col for col in required_cols if col not in d.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    d = d.dropna(subset=[firm_col, year_col, y_col, k_col, l_col, r_col])
    d[year_col] = pd.to_numeric(d[year_col], errors="coerce")
    d = d.dropna(subset=[year_col])

    if d.empty:
        raise ValueError("No valid data after cleaning required columns")

    # Choose estimation window
    if end_year is None:
        end_year = int(d[year_col].max())
    else:
        end_year = int(end_year)

    start_year = end_year - window_years + 1
    d = d[(d[year_col] >= start_year) & (d[year_col] <= end_year)].copy()

    if d.empty:
        raise ValueError(
            f"No data available for window {start_year}-{end_year}. "
            f"Check your data range and window_years parameter."
        )

    logger.info(
        f"Estimating RQ for {len(d[firm_col].unique())} firms "
        f"over window {start_year}-{end_year} ({len(d)} observations)"
    )

    # Build list of required columns and enforce positivity for logs
    needed = [(y_col, "y"), (k_col, "k"), (l_col, "l"), (r_col, "r")]
    if a_col is not None:
        if a_col not in d.columns:
            logger.warning(f"Advertising column '{a_col}' not found, ignoring")
            a_col = None
        else:
            needed.append((a_col, "a"))
    if s_col is not None:
        if s_col not in d.columns:
            logger.warning(f"Spillovers column '{s_col}' not found, ignoring")
            s_col = None
        else:
            needed.append((s_col, "s"))

    # Convert to numeric and drop missing
    for col, _ in needed:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.dropna(subset=[col for col, _ in needed])

    # Enforce positivity for logs
    for col, _ in needed:
        d = d[d[col] > 0] # todo is this accurate

    if d.empty:
        raise ValueError("No data remaining after enforcing positivity for log transformation")

    # Create log variables
    d["ln_y"] = np.log(d[y_col])
    d["ln_k"] = np.log(d[k_col])
    d["ln_l"] = np.log(d[l_col])
    d["ln_r"] = np.log(d[r_col])
    if a_col is not None:
        d["ln_a"] = np.log(d[a_col])
    if s_col is not None:
        d["ln_s"] = np.log(d[s_col])

    # Build fixed effects formula
    x_terms = ["ln_k", "ln_l", "ln_r"]
    if a_col is not None:
        x_terms.append("ln_a")
    if s_col is not None:
        x_terms.append("ln_s")

    fe = " + ".join(x_terms)
    if add_year_fe:
        fe += f" + C({year_col})"

    formula = f"ln_y ~ {fe}"

    # Random effects structure (grouped by firm)
    if full_random_slopes:
        # Random intercept + random slopes on all included inputs
        re_formula = "1 + " + " + ".join(x_terms)
    else:
        # Random intercept + random slope only on ln_r (RQ)
        re_formula = "1 + ln_r"

    logger.debug(f"Model formula: {formula}")
    logger.debug(f"Random effects: {re_formula}")

    # Fit model
    try:
        model = smf.mixedlm(formula, d, groups=d[firm_col], re_formula=re_formula)
        fit = model.fit(reml=reml, method="lbfgs", maxiter=200, disp=False)
    except Exception as e:
        logger.error(f"Error fitting mixed effects model: {e}")
        raise ValueError(f"Model estimation failed: {e}")

    # Extract fixed gamma (population-level R&D elasticity)
    gamma_fixed = fit.fe_params.get("ln_r", np.nan)

    if np.isnan(gamma_fixed):
        logger.warning("Fixed effect for ln_r not found in model results")
        gamma_fixed = 0.0

    # Extract firm-specific RQ = fixed gamma + random gamma
    rqs = {}
    for firm, re_params in fit.random_effects.items():
        # random_effects is a dict; key depends on re_formula structure
        gamma_random = 0.0
        if isinstance(re_params, (pd.Series, dict)):
            gamma_random = re_params.get("ln_r", 0.0)
        elif isinstance(re_params, np.ndarray):
            # Handle case where random effects might be returned as array
            # This depends on statsmodels version and re_formula structure
            logger.debug(f"Random effects for {firm} returned as array, extracting ln_r component")
            # For "1 + ln_r" structure, ln_r is typically the second element
            if len(re_params) >= 2:
                gamma_random = float(re_params[1])
        
        rqs[firm] = float(gamma_fixed + gamma_random)

    if not rqs:
        logger.warning("No firm-specific RQ estimates extracted from model")
        return pd.Series(dtype=float, name="RQ_gamma")

    result = pd.Series(rqs, name="RQ_gamma")
    logger.info(
        f"RQ estimation complete. Mean RQ: {result.mean():.4f}, "
        f"Std RQ: {result.std():.4f}, Range: [{result.min():.4f}, {result.max():.4f}]"
    )

    return result


def rolling_ols(
    df: pd.DataFrame,
    firm_col: str,
    year_col: str,
    sales_col: str,
    rd_col: str,
    controls: Optional[list] = None
) -> pd.DataFrame:
    """
    Estimate rolling OLS regressions with lagged R&D variables.
    
    For each firm-year, estimates 5 SEPARATE OLS regressions (one for each lag):
    - Regression 1: log(sales_t) = β₀ + β₁·log(R&D_{t-1}) + ε_t
    - Regression 2: log(sales_t) = β₀ + β₂·log(R&D_{t-2}) + ε_t
    - Regression 3: log(sales_t) = β₀ + β₃·log(R&D_{t-3}) + ε_t
    - Regression 4: log(sales_t) = β₀ + β₄·log(R&D_{t-4}) + ε_t
    - Regression 5: log(sales_t) = β₀ + β₅·log(R&D_{t-5}) + ε_t
    
    Uses a rolling 8-year window. Requires at least 4 non-missing lags for 
    each observation.
    
    Args:
        df: DataFrame with firm-year observations
        firm_col: Column name for firm identifier
        year_col: Column name for year
        sales_col: Column name for sales/revenue
        rd_col: Column name for R&D spending
        controls: Optional list of additional control variable column names (NOT USED in separate regressions)
        
    Returns:
        DataFrame indexed by [firm_col, year_col] with coefficients:
        - const: Intercept (average of 5 intercepts)
        - lag1, lag2, ..., lag5: Coefficients from each separate regression
        
    Example:
        >>> df = pd.DataFrame({
        ...     'firm_id': ['A', 'A', 'A', 'B', 'B', 'B'],
        ...     'year': [2020, 2021, 2022, 2020, 2021, 2022],
        ...     'sales': [100, 110, 120, 200, 220, 240],
        ...     'rd': [10, 12, 14, 20, 22, 24]
        ... })
        >>> results = rolling_ols(df, 'firm_id', 'year', 'sales', 'rd')
        >>> print(results)
    """
    if df is None or len(df) == 0:
        raise ValueError("df is empty")
    
    # Validate required columns
    required_cols = [firm_col, year_col, sales_col, rd_col]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Sort and compute logs; treat non-positive R&D as NaN
    d = df.sort_values([firm_col, year_col]).copy()
    d['log_sales'] = np.log(d[sales_col])
    d['log_rd'] = np.log(d[rd_col].where(d[rd_col] > 0, np.nan))
    
    # Create 5 lagged log(R&D) columns
    for i in range(1, 6):
        d[f'lag{i}'] = d.groupby(firm_col)['log_rd'].shift(i)
    
    results = []
    
    # Loop by firm and year
    for firm, grp in d.groupby(firm_col):
        grp = grp.set_index(year_col).sort_index()
        for year in grp.index.unique():
            # Require ≥4 non-missing lags for current year
            lags = grp.loc[year, [f'lag{i}' for i in range(1, 6)]]
            if lags.isna().sum() > 1:
                continue
            
            # Take up to 8-year window ending in current year
            window = grp[(grp.index >= year - 7) & (grp.index <= year)]
            if window.empty:
                continue
            
            # Run 5 SEPARATE regressions, one for each lag
            lag_coefs = {}
            lag_consts = {}
            
            for lag_num in range(1, 6):
                lag_col = f'lag{lag_num}'
                
                # Get data with this lag and log_sales (drop rows where either is NaN)
                data = window[['log_sales', lag_col]].dropna()
                if len(data) < 4:  # Need at least 4 observations
                    lag_coefs[lag_col] = np.nan
                    lag_consts[lag_col] = np.nan
                    continue
                
                Y = data['log_sales'].to_numpy()
                X_lag = data[lag_col].to_numpy().reshape(-1, 1)
                
                # Add constant (intercept) column
                X = np.column_stack([np.ones(len(X_lag)), X_lag])
                
                # Solve OLS: coefficients = [const, lag_coef]
                try:
                    coefs = np.linalg.lstsq(X, Y, rcond=None)[0]
                    lag_consts[lag_col] = coefs[0]
                    lag_coefs[lag_col] = coefs[1]
                except np.linalg.LinAlgError as e:
                    logger.warning(f"OLS estimation failed for {firm} in {year}, lag{lag_num}: {e}")
                    lag_coefs[lag_col] = np.nan
                    lag_consts[lag_col] = np.nan
                    continue
            
            # Record results - average intercept across the 5 regressions
            valid_consts = [c for c in lag_consts.values() if pd.notna(c)]
            avg_const = np.mean(valid_consts) if valid_consts else np.nan
            
            res = {
                firm_col: firm,
                year_col: year,
                'const': avg_const
            }
            # Add each lag coefficient
            for lag_col, coef in lag_coefs.items():
                res[lag_col] = coef
            
            results.append(res)
    
    out = pd.DataFrame(results)
    if out.empty:
        logger.warning("No valid OLS estimates computed")
        return out.set_index([firm_col, year_col])
    
    out = out.set_index([firm_col, year_col])
    return out.sort_index()

