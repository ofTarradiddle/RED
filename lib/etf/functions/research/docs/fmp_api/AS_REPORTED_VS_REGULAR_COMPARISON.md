# As-Reported vs Regular Endpoints - Complete Comparison

## Overview

FMP provides two types of financial statement endpoints:
1. **Regular/Standardized** (`stable/income-statement`)
2. **As-Reported** (`stable/income-statement-as-reported`)

## Key Differences

### 1. Data Source & Accuracy

**Regular Endpoint:**
- ✅ Standardized and cleaned data
- ✅ FMP processes and normalizes the data
- ✅ Field names are consistent across companies
- ⚠️ May involve interpretation/estimation for missing fields

**As-Reported Endpoint:**
- ✅ **Exact data as filed with SEC** (XBRL format)
- ✅ No modifications or interpretations
- ✅ Raw, unaltered financial statements
- ✅ Most accurate representation of what company actually reported
- ✅ Better for audits and compliance

### 2. Data Structure

**Regular Endpoint:**
```json
{
  "symbol": "AAPL",
  "date": "2025-09-27",
  "revenue": 416161000000,
  "costOfRevenue": 220960000000,
  "researchAndDevelopmentExpenses": 34550000000,
  "sellingGeneralAndAdministrativeExpenses": 27601000000
}
```
- **Flat structure** - all fields at top level
- **Clean field names** - camelCase, standardized

**As-Reported Endpoint:**
```json
{
  "symbol": "AAPL",
  "date": "2025-09-27",
  "data": {
    "revenuefromcontractwithcustomerexcludingassessedtax": 416161000000,
    "costofgoodsandservicessold": 220960000000,
    "researchanddevelopmentexpense": 34550000000,
    "sellinggeneralandadministrativeexpense": 27601000000
  }
}
```
- **Nested structure** - data in `data` dictionary
- **XBRL tag names** - exact SEC filing tags (lowercase, no spaces)

### 3. Historical Coverage

**Regular Endpoint:**
- ✅ **More historical data available**
- ✅ Can go back to company IPO or earlier
- ✅ Example: NVDA has 27 years (1999-2025)
- ✅ Example: GLW has 40 years (1985-2024)

**As-Reported Endpoint:**
- ⚠️ **Limited to XBRL era** (~2010+)
- ⚠️ XBRL filing became mandatory in 2009-2010
- ⚠️ Example: NVDA has 16 years (2010-2025) - missing 11 years
- ⚠️ Example: GLW has 14 years (2009-2024) - missing 26 years

**Why the difference?**
- XBRL (eXtensible Business Reporting Language) became mandatory for SEC filings around 2009-2010
- As-reported endpoints use XBRL data directly
- Regular endpoints may use older filing formats (HTML, PDF) that were digitized

### 4. Field Naming

**Regular Endpoint:**
- Standardized field names
- Consistent across companies
- Examples:
  - `revenue`
  - `researchAndDevelopmentExpenses`
  - `sellingGeneralAndAdministrativeExpenses`

**As-Reported Endpoint:**
- Exact XBRL tag names from SEC filings
- May vary slightly by company
- Examples:
  - `revenuefromcontractwithcustomerexcludingassessedtax`
  - `researchanddevelopmentexpense`
  - `sellinggeneralandadministrativeexpense`

### 5. Data Completeness

**Regular Endpoint:**
- FMP may fill in missing fields using estimates
- Standardized format ensures all companies have same fields
- May combine or split line items for consistency

**As-Reported Endpoint:**
- Only includes what company actually reported
- Missing fields are truly missing (not estimated)
- Preserves company's original classification

### 6. Use Cases

**Use Regular Endpoint When:**
- ✅ Comparing multiple companies
- ✅ Building models that need consistent field names
- ✅ Need maximum historical coverage
- ✅ Want standardized, clean data
- ✅ Building backtests with long history

**Use As-Reported Endpoint When:**
- ✅ Need exact SEC filing data (audits, compliance)
- ✅ Analyzing company-specific line items
- ✅ Want to see how company actually classified items
- ✅ Building research that requires raw, unmodified data
- ✅ Need data from 2010+ (XBRL era)

## Comparison Table

| Feature | Regular Endpoint | As-Reported Endpoint |
|---------|-----------------|---------------------|
| **Data Source** | Standardized/cleaned | Exact SEC XBRL filings |
| **Structure** | Flat | Nested (`data` dictionary) |
| **Field Names** | Standardized (camelCase) | XBRL tags (lowercase) |
| **Historical Coverage** | Full history (IPO+) | XBRL era only (~2010+) |
| **Data Completeness** | May include estimates | Only actual filings |
| **Comparability** | High (standardized) | Lower (company-specific) |
| **Accuracy** | High (cleaned) | Highest (exact filings) |
| **Best For** | Analysis, comparisons | Audits, compliance, research |

## Example: NVDA Data Comparison

### Regular Endpoint
- **Years available**: 27 (1999-2025)
- **Structure**: Flat
- **Revenue field**: `revenue`
- **Use case**: Long-term backtesting, trend analysis

### As-Reported Endpoint
- **Years available**: 16 (2010-2025)
- **Structure**: Nested
- **Revenue field**: `revenuefromcontractwithcustomerexcludingassessedtax` (in `data` dict)
- **Use case**: Exact SEC filing analysis, compliance

## Recommendation

**For Your Research (REDI):**

1. **Primary**: Use **As-Reported** endpoints
   - More accurate (exact SEC filings)
   - Better for research and factor analysis
   - Preserves company-specific classifications

2. **Supplement**: Use **Regular** endpoints for pre-2010 data
   - Fill in missing historical years
   - Maintain in separate files or merge carefully

3. **Hybrid Approach**:
   - 2010+: As-reported (most accurate)
   - Pre-2010: Regular (only option available)
   - Document which source was used for each period

## Implementation Note

The `FinancialDataFetcher` currently uses as-reported endpoints. To get maximum historical coverage, you could:

1. Fetch as-reported data (2010+)
2. Fetch regular data for pre-2010 period
3. Merge with clear source attribution
4. Store both versions with metadata

This would give you:
- Maximum accuracy (as-reported for XBRL era)
- Maximum coverage (regular for pre-XBRL era)
- Clear documentation of data sources

