# Ticker Changes and Identifier Handling Guide

## How FMP Handles Ticker Changes

### 1. FMP Symbol Changes API

FMP provides a **Symbol Changes API** that tracks recent ticker symbol changes:

**Endpoint**: `stable/symbol-change`

**What it provides:**
- Recent ticker changes (last 100+ changes)
- Date of change
- Old symbol → New symbol
- Company name

**Limitations:**
- Only tracks **recent** changes (not full historical database)
- May not include all historical ticker changes
- Changes are typically from corporate actions (mergers, rebranding, etc.)

**Example Response:**
```json
[
  {
    "date": "2025-12-30",
    "oldSymbol": "ABLLL",
    "newSymbol": "ABXL",
    "name": "Company Name"
  }
]
```

### 2. How Our System Handles Ticker Changes

The `FinancialDataFetcher` uses a **two-tier approach**:

#### Tier 1: Manual Ticker Changes (Primary)
- **File**: `ticker_changes.json` in base storage directory
- **Purpose**: Maintain historical ticker mappings manually
- **Format**:
```json
{
  "ANET": ["ANET", "ARST"],  // If Arista had a previous ticker
  "NVDA": ["NVDA"],          // No changes
  "GLW": ["GLW"]             // No changes
}
```

#### Tier 2: FMP Symbol Changes API (Secondary)
- **Purpose**: Automatically detect recent ticker changes
- **Limitation**: Only finds recent changes, not full history
- **Action**: When found, saves to `ticker_changes.json` for future use

### 3. How It Works in Practice

When fetching data for a symbol:

1. **Check manual ticker_changes.json** first
   - If found, use all historical symbols
   - Example: If `NVDA` has `["NVDA", "NVDA_OLD"]`, fetch data for both

2. **Query FMP Symbol Changes API** (if not in manual file)
   - Search for recent changes involving the symbol
   - If found, add to ticker_changes.json

3. **Fetch data for all related symbols**
   - Ensures complete historical coverage
   - Merges data from all symbols

### 4. Common Ticker Change Scenarios

#### Scenario 1: Company Rebranding
- **Example**: Facebook → Meta (FB → META)
- **Action**: Add both symbols to ticker_changes.json

#### Scenario 2: Merger/Acquisition
- **Example**: Company A acquires Company B
- **Action**: May need to track both old symbols

#### Scenario 3: Exchange Listing Change
- **Example**: Moving from OTC to NASDAQ
- **Action**: Usually same ticker, but verify

### 5. How to Maintain Ticker Changes

#### Option A: Manual Maintenance (Recommended for Historical Data)

1. **Research company history**:
   - Check SEC filings (EDGAR)
   - Company investor relations pages
   - Financial news archives

2. **Update ticker_changes.json:
```json
{
  "META": ["META", "FB"],           // Facebook → Meta
  "ANET": ["ANET"],                 // No changes
  "GLW": ["GLW"],                   // No changes
  "NVDA": ["NVDA"]                  // No changes
}
```

3. **File location**: `{base_storage_path}/ticker_changes.json`

#### Option B: Automatic Detection (Recent Changes Only)

The system automatically:
- Queries FMP Symbol Changes API
- Finds recent changes
- Saves to ticker_changes.json

**Note**: This only works for recent changes. For historical coverage, use Option A.

### 6. Testing Ticker Changes

To test if a symbol has changes:

```python
from lib.etf.functions.research.data_fetcher import FinancialDataFetcher
from pathlib import Path

fetcher = FinancialDataFetcher(
    api_key="your_key",
    base_storage_path=Path("./data/research/REDI")
)

# Check what symbols will be queried
symbols = fetcher._check_ticker_changes("META")
print(f"Symbols to query: {symbols}")
# Output: ["META", "FB"] if configured
```

### 7. Important Notes

1. **CIK (Central Index Key)**: 
   - SEC's permanent identifier
   - Doesn't change with ticker changes
   - Use CIK to verify same company across ticker changes

2. **Data Merging**:
   - When multiple symbols are queried, data is merged by date
   - Duplicates are removed (keeps newest record)

3. **Historical Coverage**:
   - FMP's symbol changes API only covers recent changes
   - For full historical coverage, manual maintenance is required
   - Check SEC EDGAR for complete ticker history

4. **Company Name Changes**:
   - Ticker changes often accompany name changes
   - FMP profile endpoint shows current name only
   - Historical names may require SEC filings

### 8. Example: Checking ANET

ANET (Arista Networks):
- **IPO Date**: June 6, 2014
- **Original Ticker**: ANET (no changes)
- **Data Available**: 2011-2024 (14 years)
- **Status**: No ticker changes detected

### 9. Recommendations

1. **For New Companies**: 
   - Check IPO date
   - Verify no ticker changes since IPO

2. **For Established Companies**:
   - Research company history
   - Check for mergers, acquisitions, rebranding
   - Maintain ticker_changes.json manually

3. **For Historical Analysis**:
   - Use SEC EDGAR for complete ticker history
   - Cross-reference with company investor relations
   - Update ticker_changes.json as needed

### 10. Future Enhancements

Potential improvements:
- Integration with SEC EDGAR API for historical ticker changes
- Automatic CIK-based company matching
- Database of known ticker changes
- Cross-reference with company name changes

