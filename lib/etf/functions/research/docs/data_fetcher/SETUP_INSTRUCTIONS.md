# Financial Data Fetcher Setup Instructions

## External Drive Setup

The data fetcher stores financial data on your external drive (My Passport) under a REDI folder.

### Step 1: Create the REDI Directory

Due to macOS permissions on external drives, you may need to create the directory manually:

```bash
mkdir -p "/Volumes/My Passport/REDI"
```

Or if your drive is mounted at a different location:
```bash
mkdir -p "/path/to/your/drive/REDI"
```

### Step 2: Verify Permissions

Check that you can write to the drive:
```bash
touch "/Volumes/My Passport/REDI/.test"
rm "/Volumes/My Passport/REDI/.test
```

### Step 3: Update Path in Script (if needed)

If your external drive is mounted at a different location, update `EXTERNAL_DRIVE_PATH` in `fetch_financial_data.py`:

```python
EXTERNAL_DRIVE_PATH = Path('/Volumes/YourDriveName/REDI')
```

## Directory Structure

Data will be organized as:
```
/Volumes/My Passport/REDI/
├── NVDA/
│   ├── income/
│   │   ├── NVDA_income_annual.json
│   │   └── NVDA_income_annual_metadata.json
│   ├── balance/
│   │   ├── NVDA_balance_annual.json
│   │   └── NVDA_balance_annual_metadata.json
│   └── cashflow/
│       ├── NVDA_cashflow_annual.json
│       └── NVDA_cashflow_annual_metadata.json
├── GLW/
│   └── ...
├── ANET/
│   └── ...
└── ticker_changes.json
```

## Running the Fetcher

```bash
python lib/etf/functions/research/fetch_financial_data.py
```

## Features

- ✅ Uses as-reported endpoints for accurate historical data
- ✅ Handles 1000 record limit per request
- ✅ Stores data in organized folder structure
- ✅ Tracks ticker changes (manual maintenance required)
- ✅ Supports annual and quarterly data
- ✅ Flattens nested as-reported data structure
- ✅ Removes duplicate records
- ✅ Creates metadata files with fetch information

## Ticker Changes

The fetcher includes infrastructure for handling ticker changes, but FMP doesn't provide this information via API. You may need to:

1. Manually maintain `ticker_changes.json` with historical symbol mappings
2. Use external sources (SEC filings, company websites)
3. Check company history for mergers, name changes, etc.

Example ticker_changes.json:
```json
{
  "ANET": ["ANET", "ARST"],  // If Arista Networks had a previous ticker
  "NVDA": ["NVDA"],          // No changes
  "GLW": ["GLW"]             // No changes
}
```


