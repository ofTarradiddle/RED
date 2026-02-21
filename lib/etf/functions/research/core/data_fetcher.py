"""
Financial Data Fetcher for REDI Research
Fetches income statements, balance sheets, and cash flow statements using FMP as-reported endpoints.
Stores data locally with proper organization and handles ticker changes.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import requests
import time

logger = logging.getLogger(__name__)


class FinancialDataFetcher:
    """
    Fetches and stores financial statements using FMP as-reported endpoints.
    
    Features:
    - Uses as-reported endpoints for accurate historical data
    - Handles 1000 record limit per request
    - Stores data in organized folder structure
    - Tracks ticker changes for historical coverage
    - Supports annual and quarterly data
    """
    
    def __init__(self, api_key: str, base_storage_path: Path):
        """
        Initialize fetcher.
        
        Args:
            api_key: FMP API key
            base_storage_path: Base path for storage (e.g., /Volumes/Passport/REDI)
        """
        self.api_key = api_key
        self.base_storage_path = Path(base_storage_path)
        # Check if path exists - if not, try to create but don't fail
        if not self.base_storage_path.exists():
            try:
                self.base_storage_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created storage directory: {self.base_storage_path}")
            except (PermissionError, OSError) as e:
                logger.warning(f"Could not create {self.base_storage_path}: {e}")
                logger.warning("Will attempt to create subdirectories during data fetch")
        else:
            logger.info(f"Using existing storage directory: {self.base_storage_path}")
        
        # API endpoints (regular/standardized - not as-reported)
        self.base_url = "https://financialmodelingprep.com"
        self.endpoints = {
            'income': 'stable/income-statement',
            'balance': 'stable/balance-sheet-statement',
            'cashflow': 'stable/cash-flow-statement'
        }
        
        # Rate limiting
        self.request_delay = 0.5  # Delay between requests (seconds)
        self.max_records_per_request = 1000
        
        # Ticker change tracking
        self.ticker_changes_file = self.base_storage_path / 'ticker_changes.json'
        self.ticker_changes = self._load_ticker_changes()
    
    def _load_ticker_changes(self) -> Dict[str, List[str]]:
        """Load ticker change history."""
        if self.ticker_changes_file.exists():
            try:
                with open(self.ticker_changes_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading ticker changes: {e}")
        return {}
    
    def _save_ticker_changes(self):
        """Save ticker change history."""
        try:
            with open(self.ticker_changes_file, 'w') as f:
                json.dump(self.ticker_changes, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving ticker changes: {e}")
    
    def _check_ticker_changes(self, symbol: str) -> List[str]:
        """
        Check for historical ticker changes using FMP symbol changes API.
        Returns list of all symbols to query for complete historical coverage.
        
        FMP provides a symbol changes API that tracks recent ticker changes.
        For historical changes, we also check manually maintained ticker_changes.json.
        """
        # First, check manually maintained ticker changes (for historical data)
        if symbol in self.ticker_changes:
            logger.info(f"Using manual ticker changes for {symbol}: {self.ticker_changes[symbol]}")
            return self.ticker_changes[symbol]
        
        # Try FMP symbol changes API
        try:
            url = f"{self.base_url}/stable/symbol-change"
            params = {'apikey': self.api_key}
            
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                changes = response.json()
                if isinstance(changes, list):
                    # Find all changes related to this symbol
                    related_symbols = {symbol}  # Start with current symbol
                    
                    for change in changes:
                        old_symbol = change.get('oldSymbol', '').upper()
                        new_symbol = change.get('newSymbol', '').upper()
                        current_upper = symbol.upper()
                        
                        # If current symbol is the new symbol, add old symbol
                        if new_symbol == current_upper:
                            related_symbols.add(old_symbol)
                            logger.info(f"Found ticker change: {old_symbol} -> {new_symbol} on {change.get('date', 'unknown')}")
                        # If current symbol is the old symbol, add new symbol
                        elif old_symbol == current_upper:
                            related_symbols.add(new_symbol)
                            logger.info(f"Found ticker change: {old_symbol} -> {new_symbol} on {change.get('date', 'unknown')}")
                    
                    if len(related_symbols) > 1:
                        # Save to ticker_changes for future use
                        self.ticker_changes[symbol] = list(related_symbols)
                        self._save_ticker_changes()
                        return list(related_symbols)
        except Exception as e:
            logger.debug(f"Error checking FMP symbol changes for {symbol}: {e}")
        
        # No changes found, return just current symbol
        return [symbol]
    
    def _fetch_data(self, endpoint: str, symbol: str, period: str = 'annual', 
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch data from FMP API with proper limit handling.
        
        Args:
            endpoint: API endpoint name
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Maximum records to fetch (None = use max)
            
        Returns:
            List of financial statement records
        """
        url = f"{self.base_url}/{endpoint}"
        params = {
            'symbol': symbol,
            'apikey': self.api_key
        }
        
        # Set limit (max 1000 per request)
        if limit:
            params['limit'] = min(limit, self.max_records_per_request)
        else:
            params['limit'] = self.max_records_per_request
        
        try:
            logger.info(f"Fetching {endpoint} for {symbol} (limit={params['limit']})")
            response = requests.get(url, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    logger.info(f"✓ Retrieved {len(data)} records for {symbol}")
                    return data
                else:
                    logger.warning(f"Unexpected response format for {symbol}")
                    return []
            elif response.status_code == 403:
                error = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                logger.error(f"403 Forbidden for {symbol}: {error.get('Error Message', 'Unknown error')}")
                return []
            else:
                logger.error(f"Request failed for {symbol}: Status {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return []
        finally:
            # Rate limiting
            time.sleep(self.request_delay)
    
    def _filter_by_period(self, data: List[Dict[str, Any]], period: str) -> List[Dict[str, Any]]:
        """Filter data by period (FY for annual, Q1-Q4 for quarterly)."""
        if period == 'annual':
            return [item for item in data if item.get('period') == 'FY']
        elif period == 'quarter':
            return [item for item in data if item.get('period') in ['Q1', 'Q2', 'Q3', 'Q4']]
        return data
    
    def _prepare_dataframe(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert data list to pandas DataFrame.
        Regular endpoints already have flat structure, so just convert directly.
        """
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Ensure date is datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)  # Newest first
        
        return df
    
    def _get_storage_path(self, symbol: str, statement_type: str) -> Path:
        """Get storage path for a symbol and statement type.
        
        Returns base storage path - files will be written directly here
        without creating subdirectories.
        """
        # Return base path directly - no subdirectory creation
        return self.base_storage_path
    
    def _save_dataframe(self, df: pd.DataFrame, storage_path: Path,
                       symbol: str, statement_type: str, period: str):
        """
        Save DataFrame to CSV/Parquet with incremental update support.
        If file exists, merges new data with existing (adds new rows, updates existing).
        """
        if df.empty:
            logger.warning(f"No data to save for {symbol} {statement_type}")
            return
        
        # File paths - write directly to base path (no subdirectories)
        csv_file = storage_path / f"{symbol}_{statement_type}_{period}.csv"
        parquet_file = storage_path / f"{symbol}_{statement_type}_{period}.parquet"
        
        try:
            # Check if file exists - if so, load and merge
            if csv_file.exists():
                logger.info(f"Loading existing data from {csv_file}")
                existing_df = pd.read_csv(csv_file, parse_dates=['date'])
                
                # Merge: keep existing, add new, update if date matches
                # Use date as key for deduplication
                if 'date' in existing_df.columns and 'date' in df.columns:
                    # Combine and drop duplicates (keep newest)
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                    combined_df = combined_df.sort_values('date', ascending=False)
                    combined_df = combined_df.drop_duplicates(subset=['date'], keep='first')
                    combined_df = combined_df.sort_values('date', ascending=False)  # Newest first
                    df = combined_df
                    logger.info(f"Merged with existing data: {len(existing_df)} existing + {len(df) - len(existing_df)} new = {len(df)} total")
                else:
                    # No date column, just append
                    df = pd.concat([existing_df, df], ignore_index=True)
                    df = df.drop_duplicates(keep='last')
                    logger.info(f"Appended to existing data: {len(df)} total records")
            else:
                logger.info(f"Creating new file: {csv_file}")
            
            # Save as CSV (human-readable) - try multiple methods
            try:
                df.to_csv(csv_file, index=False)
                logger.info(f"✓ Saved {len(df)} records to {csv_file}")
            except (PermissionError, OSError) as e:
                # Try alternative: write to string first, then file
                try:
                    csv_content = df.to_csv(index=False)
                    with open(csv_file, 'w', encoding='utf-8') as f:
                        f.write(csv_content)
                    logger.info(f"✓ Saved {len(df)} records to {csv_file} (alternative method)")
                except Exception as e2:
                    logger.error(f"✗ Failed to save CSV: {e2}")
                    raise
            
            # Save as Parquet (more efficient, preserves types)
            try:
                df.to_parquet(parquet_file, index=False, engine='pyarrow')
                logger.info(f"✓ Saved {len(df)} records to {parquet_file}")
            except (PermissionError, OSError) as e:
                logger.warning(f"Could not save Parquet file: {e}")
                logger.warning("CSV file saved successfully, continuing...")
            
            # Save metadata
            metadata = {
                'symbol': symbol,
                'statement_type': statement_type,
                'period': period,
                'records_count': len(df),
                'date_range': {
                    'earliest': df['date'].min().isoformat() if 'date' in df.columns and not df['date'].empty else None,
                    'latest': df['date'].max().isoformat() if 'date' in df.columns and not df['date'].empty else None
                },
                'last_updated': datetime.now().isoformat(),
                'api_endpoint': self.endpoints.get(statement_type, 'unknown'),
                'columns': list(df.columns)
            }
            
            metadata_file = storage_path / f"{symbol}_{statement_type}_{period}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving data for {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    def fetch_all_statements(self, symbol: str, period: str = 'annual', 
                            limit: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch all financial statements for a symbol.
        
        Args:
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Maximum records per statement type
            
        Returns:
            Dictionary with 'income', 'balance', 'cashflow' keys
        """
        logger.info(f"="*70)
        logger.info(f"Fetching financial data for {symbol} ({period})")
        logger.info(f"="*70)
        
        # Check for ticker changes
        symbols_to_check = self._check_ticker_changes(symbol)
        logger.info(f"Symbols to check: {symbols_to_check}")
        
        results = {}
        
        for statement_type, endpoint in self.endpoints.items():
            logger.info(f"\nFetching {statement_type} statement...")
            
            # Fetch for all historical symbols
            all_data = []
            for sym in symbols_to_check:
                data = self._fetch_data(endpoint, sym, period, limit)
                if data:
                    all_data.extend(data)
            
            # Filter by period
            filtered_data = self._filter_by_period(all_data, period)
            
            if filtered_data:
                # Remove duplicates (same date) - keep first occurrence
                seen_dates = set()
                unique_data = []
                for item in filtered_data:
                    date = item.get('date')
                    if date and date not in seen_dates:
                        seen_dates.add(date)
                        unique_data.append(item)
                
                # Convert to DataFrame
                df = self._prepare_dataframe(unique_data)
                
                if not df.empty:
                    # Save as DataFrame (CSV + Parquet) with incremental update
                    storage_path = self._get_storage_path(symbol, statement_type)
                    self._save_dataframe(df, storage_path, symbol, statement_type, period)
                
                results[statement_type] = unique_data
                logger.info(f"✓ {statement_type}: {len(unique_data)} unique records")
            else:
                logger.warning(f"✗ No {statement_type} data retrieved")
                results[statement_type] = []
        
        return results
    
    def fetch_multiple_symbols(self, symbols: List[str], period: str = 'annual',
                               limit: Optional[int] = None):
        """
        Fetch data for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            period: 'annual' or 'quarter'
            limit: Maximum records per statement type
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"Fetching data for {len(symbols)} symbols: {symbols}")
        logger.info(f"{'='*70}\n")
        
        summary = {}
        
        for symbol in symbols:
            try:
                results = self.fetch_all_statements(symbol, period, limit)
                summary[symbol] = {
                    'income': len(results.get('income', [])),
                    'balance': len(results.get('balance', [])),
                    'cashflow': len(results.get('cashflow', []))
                }
                logger.info(f"\n{symbol} summary: {summary[symbol]}\n")
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                summary[symbol] = {'error': str(e)}
        
        # Save summary
        summary_file = self.base_storage_path / f"fetch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'fetch_date': datetime.now().isoformat(),
                'symbols': symbols,
                'period': period,
                'summary': summary
            }, f, indent=2)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"Fetch complete! Summary saved to {summary_file}")
        logger.info(f"{'='*70}")
        
        return summary
    
    def analyze_field_transitions(self, symbol: str, statement_type: str = 'income', 
                                  period: str = 'annual') -> Dict[str, Any]:
        """
        Analyze field value transitions to detect when fields start being reported.
        Useful for identifying disclosure changes (e.g., R&D starting in 1996).
        
        Args:
            symbol: Stock symbol
            statement_type: 'income', 'balance', or 'cashflow'
            period: 'annual' or 'quarter'
            
        Returns:
            Dictionary with field transition analysis
        """
        storage_path = self._get_storage_path(symbol, statement_type)
        csv_file = storage_path / f"{symbol}_{statement_type}_{period}.csv"
        
        if not csv_file.exists():
            logger.warning(f"No data file found: {csv_file}")
            return {}
        
        df = pd.read_csv(csv_file, parse_dates=['date'])
        df = df.sort_values('date')
        
        analysis = {
            'symbol': symbol,
            'statement_type': statement_type,
            'period': period,
            'field_transitions': {},
            'summary': {}
        }
        
        # Analyze each numeric field
        numeric_cols = df.select_dtypes(include=[float, int]).columns.tolist()
        
        for col in numeric_cols:
            if col == 'date':
                continue
                
            # Find first non-zero, non-null value
            non_zero = df[df[col].notna() & (df[col] != 0)]
            
            if not non_zero.empty:
                first_date = non_zero.iloc[0]['date']
                first_value = non_zero.iloc[0][col]
                
                # Check if field was zero/null before first value
                before_first = df[df['date'] < first_date]
                if before_first.empty:
                    was_zero_before = True
                else:
                    # Check if all values before first are null or zero
                    was_zero_before = (before_first[col].isna() | (before_first[col] == 0)).all()
                
                analysis['field_transitions'][col] = {
                    'first_reported_date': first_date.isoformat() if hasattr(first_date, 'isoformat') else str(first_date),
                    'first_reported_value': float(first_value),
                    'was_zero_before': was_zero_before,
                    'years_before_first': len(before_first) if not before_first.empty else 0,
                    'total_years_with_data': len(non_zero),
                    'total_years_in_dataset': len(df)
                }
        
        # Summary statistics
        transitions_with_gaps = [
            col for col, info in analysis['field_transitions'].items()
            if info['was_zero_before'] and info['years_before_first'] > 0
        ]
        
        analysis['summary'] = {
            'total_fields_analyzed': len(analysis['field_transitions']),
            'fields_with_disclosure_gaps': len(transitions_with_gaps),
            'fields_with_gaps': transitions_with_gaps[:10]  # Top 10
        }
        
        # Save analysis
        analysis_file = storage_path / f"{symbol}_{statement_type}_{period}_field_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        logger.info(f"Field analysis saved to {analysis_file}")
        
        return analysis

