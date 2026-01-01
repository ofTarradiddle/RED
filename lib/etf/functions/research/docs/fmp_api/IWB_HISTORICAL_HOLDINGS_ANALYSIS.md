# IWB Historical Holdings Availability Analysis

## Current Status

### FMP API Testing Results
- **Current Holdings**: ✓ Available (1,010 holdings)
- **Historical Holdings**: ✗ **403 Forbidden** - Requires higher subscription tier
- **Tested Dates**: 
  - 2000-05-15 (launch date) - 403
  - 2000-12-31 - 403
  - 2005-12-31 - 403
  - 2010-12-31 - 403
  - 2015-12-31 - 403
  - 2020-12-31 - 403
  - 2024-12-31 - 403

**Conclusion**: With current FMP API key tier, **NO historical holdings data is available**. All date-specific endpoints return 403 Forbidden.

## IWB ETF Information
- **Launch Date**: May 15, 2000
- **Provider**: iShares (BlackRock)
- **Index**: Russell 1000 Index
- **Current Holdings**: ~1,000 stocks

## Options for Historical Holdings Data

### Option 1: Upgrade FMP Subscription ⭐ Recommended
**Pros:**
- Single API source
- Consistent data format
- Likely has data back to 2000
- Easy integration (already have code)

**Cons:**
- Additional cost (need to check pricing)
- May still have date limitations

**Action**: Contact FMP to check:
- Which tier includes historical ETF holdings?
- How far back does the data go?
- What's the pricing?

### Option 2: iShares/BlackRock Website
**Pros:**
- Free
- Official source
- May have historical holdings files

**Cons:**
- May require web scraping
- Data format may vary
- May not have all historical dates
- Legal/ToS considerations

**Potential Sources:**
- iShares website: https://www.ishares.com/us/products/239707/ishares-russell-1000-etf
- May have historical holdings files or API

### Option 3: Russell Index Data
**Pros:**
- IWB tracks Russell 1000 Index
- Index provider may have historical constituent data
- More stable than ETF holdings (less frequent changes)

**Cons:**
- Need to find Russell index data source
- May require subscription
- ETF holdings may differ slightly from index

**Potential Sources:**
- FTSE Russell (index provider)
- May have historical index constituent data

### Option 4: Alternative Data Providers
**Options:**
- ETF.com / ETF Database
- Morningstar Direct
- Bloomberg Terminal
- Refinitiv (formerly Thomson Reuters)
- FactSet

**Pros:**
- Professional-grade data
- Historical coverage
- Multiple ETF support

**Cons:**
- Expensive subscriptions
- May require enterprise access
- Integration complexity

### Option 5: Build Historical Database
**Approach:**
1. Start with current holdings (available now)
2. Use quarterly/annual rebalancing dates
3. Manually collect or scrape key dates
4. Build database incrementally

**Pros:**
- Free (if manual)
- Customizable
- Learn the data structure

**Cons:**
- Time-intensive
- May miss some dates
- Requires ongoing maintenance

## Recommended Approach

### Short-term (Immediate Use)
1. **Use Current Holdings** for testing backtesting framework
   - Test with current IWB holdings (1,010 stocks)
   - Use Yahoo Finance for prices (working perfectly)
   - Validate the backtesting engine works

2. **Use Proxy Approach**
   - Assume holdings are relatively stable
   - Use current holdings as proxy for recent periods
   - Acknowledge limitation in results

### Medium-term (Next Steps)
1. **Contact FMP** about subscription upgrade
   - Check pricing for historical ETF holdings
   - Verify data coverage (dates available)
   - Evaluate cost vs. benefit

2. **Explore iShares Website**
   - Check if they publish historical holdings
   - Look for downloadable files or API
   - May have quarterly/annual snapshots

3. **Consider Russell Index Data**
   - Check if Russell 1000 index constituents are available
   - May be easier to get than ETF holdings
   - ETF closely tracks index

### Long-term (Production)
1. **Establish Data Pipeline**
   - Choose primary source (FMP upgrade or alternative)
   - Set up automated data collection
   - Build validation and quality checks

2. **Build Historical Database**
   - Store holdings by date
   - Cache for performance
   - Enable point-in-time queries

## Testing Strategy

### What We Can Test Now:
1. ✅ **Backtesting Engine**: Use current holdings + Yahoo prices
2. ✅ **Factor Analysis**: Use available fundamental data
3. ✅ **Performance Calculation**: Full functionality

### What We Need for Full Backtesting:
1. ⚠️ **Historical Holdings**: Need source for point-in-time data
2. ✅ **Historical Prices**: Yahoo Finance (working)
3. ⚠️ **Historical Fundamentals**: Need financial statements (also 403)

## Next Actions

1. **Immediate**: Test backtesting with current holdings
2. **This Week**: Contact FMP about upgrade pricing
3. **This Week**: Check iShares website for historical data
4. **This Month**: Evaluate alternative data sources
5. **Ongoing**: Build historical holdings database

## Questions to Answer

1. How far back do we need to go?
   - Full history (2000-2025)?
   - Recent history (2015-2025)?
   - Specific periods?

2. What frequency do we need?
   - Daily?
   - Weekly?
   - Monthly?
   - Quarterly?

3. What's the budget for data?
   - Free options only?
   - Paid subscriptions acceptable?
   - One-time purchase?

4. How critical is historical accuracy?
   - Need exact point-in-time holdings?
   - Approximate/index-based acceptable?


