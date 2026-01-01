# FMP Ultimate Tier Setup Guide

## Current Issue

**Status**: API key is configured correctly, but endpoints are returning 403 "Legacy Endpoint" errors.

**Error Message**:
```
"Legacy Endpoint : Due to Legacy endpoints being no longer supported - 
This endpoint is only available for legacy users who have valid subscriptions 
prior August 31, 2025."
```

## What This Means

FMP has deprecated the `/api/v3/` and `/api/v4/` endpoints as "Legacy" for **new users** (those who subscribed after August 31, 2025). Since you just upgraded, you need to use the **NEW API endpoint format**.

## Next Steps

### 1. Check Your FMP Dashboard
- Log into your FMP account dashboard
- Verify your account shows "Ultimate" tier
- Check if a new API key was generated after upgrade
- Look for documentation on the new API endpoints

### 2. Find the New Endpoint Format
The new endpoints are likely:
- Different base URL structure
- Different endpoint naming
- May use `/stable/` prefix differently
- May require different authentication

### 3. Update the Code
Once you have the new endpoint format, we need to update:
- `FMPClient.get_income_statement()` method
- `FMPClient.get_cash_flow_statement()` method  
- `FMPClient.get_price_history()` method
- Any other methods using v3/v4 endpoints

### 4. Contact FMP Support (If Needed)
If you can't find the new endpoint format:
- Contact: https://site.financialmodelingprep.com/developer/docs/pricing
- Ask for:
  - New API endpoint documentation for Ultimate tier
  - Confirmation that your API key is activated
  - Any required API key regeneration

## Current Working Endpoints

These still work with your API key:
- ✅ `stable/etf/holdings` - Current ETF holdings
- ✅ `stable/enterprise-values` - Enterprise values
- ✅ `stable/market-capitalization` - Market cap

## What We Need

1. **New endpoint format** for income statements
2. **Confirmation** that API key is fully activated
3. **Documentation** for Ultimate tier endpoints

## Testing Once You Have New Endpoints

Once you provide the new endpoint format, I'll:
1. Update `FMPClient` to use new endpoints
2. Test NVDA sales data retrieval (30 years)
3. Verify all financial statement endpoints work
4. Update the backtesting module accordingly

## Quick Test Command

Once you have the new endpoint format, we can test with:
```python
from lib.etf.functions.research import FMPClient
fmp = FMPClient(api_key='KzXIx6bXd7l7c9mIfRddOLBZY5AAgFVq')
income = fmp.get_income_statement('NVDA', period='annual', limit=30)
```


