"""
FMP Data Source Adapter for Accounting & Administration
Uses Financial Modeling Prep (FMP) APIs to provide all data needed for ETF operations.
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from lib.etf.shared import DataSourceAdapter, APOrder
from lib.etf.functions.research.core.backtesting import FMPClient

logger = logging.getLogger(__name__)


class FMPDataSourceAdapter(DataSourceAdapter):
    """
    FMP-based data source adapter for ETF accounting and administration.
    
    This adapter uses FMP APIs to provide:
    - Market prices (batch quotes, historical EOD)
    - Corporate actions (splits, symbol changes)
    - Dividend data (calendar, company-specific)
    - Security identifiers (CUSIP, CIK)
    - Index/benchmark data
    - Company profiles and metrics
    
    Args:
        fmp_client: FMPClient instance (optional, will create one if not provided)
        etf_symbol: ETF symbol for holdings lookups
        api_key: FMP API key (optional, uses env var if not provided)
        fallback_adapter: Optional fallback adapter for data not available via FMP
    """
    
    def __init__(self, etf_symbol: str = "", fmp_client: Optional[FMPClient] = None,
                 api_key: Optional[str] = None, fallback_adapter: Optional[DataSourceAdapter] = None,
                 manual_holdings: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize FMP Data Source Adapter.
        
        Args:
            etf_symbol: ETF symbol (optional if using manual holdings)
            fmp_client: FMPClient instance (optional, will create one if not provided)
            api_key: FMP API key (optional, uses env var if not provided)
            fallback_adapter: Optional fallback adapter for data not available via FMP
            manual_holdings: Optional list of manual holdings (for pre-launch ETFs).
                           Format: [{"ticker": "AAPL", "cusip": "...", "quantity": 100, ...}, ...]
        """
        self.etf_symbol = etf_symbol
        self.fmp_client = fmp_client or FMPClient(api_key=api_key)
        self.fallback_adapter = fallback_adapter
        self.manual_holdings = manual_holdings or []
        
        # Cache for holdings and prices to reduce API calls
        self._holdings_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._prices_cache: Dict[str, Dict[str, Decimal]] = {}
        self._ticker_to_cusip: Dict[str, str] = {}
    
    def get_nscc_files(self, date: date) -> Dict[str, Any]:
        """
        Get NSCC files for the given date.
        Note: FMP doesn't provide NSCC data - use fallback adapter if available.
        """
        if self.fallback_adapter:
            return self.fallback_adapter.get_nscc_files(date)
        logger.warning("NSCC files not available via FMP - returning empty data")
        return {"settled_shares": 0, "creation_orders": [], "redemption_orders": []}
    
    def get_dtc_position_file(self, date: date) -> Dict[str, Any]:
        """
        Get DTC position file for the given date.
        Note: FMP doesn't provide DTC data - use fallback adapter if available.
        """
        if self.fallback_adapter:
            return self.fallback_adapter.get_dtc_position_file(date)
        logger.warning("DTC position file not available via FMP - returning empty data")
        return {"cede_position": 0, "participant_positions": []}
    
    def get_custodian_statements(self, date: date) -> Dict[str, Any]:
        """
        Get custodian statements for the given date.
        Note: FMP doesn't provide custodian data - use fallback adapter if available.
        Also includes cash from manual holdings (Cash&Other, money market funds).
        """
        if self.fallback_adapter:
            result = self.fallback_adapter.get_custodian_statements(date)
            # Add cash from manual holdings
            cash_from_holdings = self._get_cash_from_holdings()
            if cash_from_holdings > 0:
                existing_cash = Decimal(str(result.get('cash_balance', 0)))
                result['cash_balance'] = float(existing_cash + cash_from_holdings)
            return result
        
        # Extract cash from manual holdings
        cash_balance = self._get_cash_from_holdings()
        
        return {
            "total_shares": 0, 
            "cash_balance": float(cash_balance),
            "holdings": []
        }
    
    def _get_cash_from_holdings(self) -> Decimal:
        """Extract cash and money market fund values from manual holdings"""
        cash_total = Decimal('0')
        if self.manual_holdings:
            for holding in self.manual_holdings:
                ticker = holding.get('ticker', '').upper()
                # Check if it's cash or money market
                if 'CASH' in ticker or 'FGXXX' in ticker or ticker.startswith('BBG'):
                    market_value = Decimal(str(holding.get('market_value', 0)))
                    if market_value > 0:
                        cash_total += market_value
                        logger.debug(f"Including cash/money market: {ticker} = ${market_value}")
        return cash_total
    
    def get_portfolio_holdings(self, date: date) -> List[Dict[str, Any]]:
        """
        Get portfolio holdings for the given date.
        
        Priority:
        1. Manual holdings (if provided - for pre-launch ETFs)
        2. Fallback adapter holdings
        3. FMP ETF holdings API (if ETF is live)
        """
        if date is None:
            date = date.today()
        date_str = date.isoformat()
        
        # Check cache
        if date_str in self._holdings_cache:
            return self._holdings_cache[date_str]
        
        holdings = []
        
        # 1. Try manual holdings first (for pre-launch ETFs)
        if self.manual_holdings:
            logger.info(f"Using {len(self.manual_holdings)} manual holdings for {date_str}")
            holdings = []
            for holding in self.manual_holdings:
                # Ensure all required fields are present
                ticker = holding.get('ticker')
                if not ticker:
                    continue
                
                # Get CUSIP if not provided
                cusip = holding.get('cusip') or self._ticker_to_cusip.get(ticker)
                if not cusip:
                    try:
                        profile = self.fmp_client.get_company_profile(ticker)
                        if profile:
                            cusip = profile.get('cusip') or profile.get('cusipNumber')
                            if cusip:
                                self._ticker_to_cusip[ticker] = cusip
                    except:
                        pass
                
                formatted_holding = {
                    'ticker': ticker,
                    'cusip': cusip or holding.get('cusip', ''),
                    'quantity': float(holding.get('quantity', 0)),
                    'weight': float(holding.get('weight', 0)),
                    'market_value': float(holding.get('market_value', 0)),
                    'name': holding.get('name', ''),
                    'isin': holding.get('isin', ''),
                }
                holdings.append(formatted_holding)
            
            # Cache result
            self._holdings_cache[date_str] = holdings
            return holdings
        
        # 2. Try fallback adapter
        if self.fallback_adapter:
            try:
                holdings = self.fallback_adapter.get_portfolio_holdings(date)
                if holdings:
                    logger.info(f"Retrieved {len(holdings)} holdings from fallback adapter")
                    # Cache result
                    self._holdings_cache[date_str] = holdings
                    return holdings
            except Exception as e:
                logger.warning(f"Fallback adapter failed: {e}")
        
        # 3. Try FMP ETF holdings API (only if ETF is live)
        if self.etf_symbol:
            try:
                holdings_data = self.fmp_client.get_etf_holdings(self.etf_symbol, date_str)
                
                if holdings_data:
                    # Transform FMP format to internal format
                    for item in holdings_data:
                        # FMP returns: asset (symbol), sharesNumber, weightPercentage, marketValue, etc.
                        symbol = item.get('asset') or item.get('symbol') or item.get('ticker')
                        if not symbol or symbol == self.etf_symbol:
                            continue
                        
                        # Try to get CUSIP from FMP or use cached mapping
                        cusip = item.get('securityCusip') or item.get('cusip') or self._ticker_to_cusip.get(symbol)
                        
                        # If no CUSIP, try to look it up
                        if not cusip:
                            profile = self.fmp_client.get_company_profile(symbol)
                            if profile:
                                cusip = profile.get('cusip') or profile.get('cusipNumber')
                                if cusip:
                                    self._ticker_to_cusip[symbol] = cusip
                        
                        holding = {
                            'ticker': symbol,
                            'cusip': cusip or '',
                            'quantity': float(item.get('sharesNumber', 0)),
                            'weight': float(item.get('weightPercentage', 0)),
                            'market_value': float(item.get('marketValue', 0)),
                            'name': item.get('name', ''),
                            'isin': item.get('isin', ''),
                        }
                        holdings.append(holding)
                    
                    # Cache result
                    self._holdings_cache[date_str] = holdings
                    logger.info(f"Retrieved {len(holdings)} holdings for {date_str} from FMP")
                    return holdings
            except Exception as e:
                logger.warning(f"FMP ETF holdings API failed (ETF may not be live): {e}")
        
        # No holdings found
        logger.warning(f"No holdings found for {date_str}. Provide manual_holdings or use fallback_adapter.")
        return []
    
    def get_market_prices(self, date: date, cusips: List[str]) -> Dict[str, Decimal]:
        """
        Get market prices for given CUSIPs on the given date using FMP APIs.
        Always uses FMP prices, never uses prices from manual holdings.
        """
        date_str = date.isoformat()
        cache_key = f"{date_str}_{','.join(sorted(cusips))}"
        
        # Check cache
        if cache_key in self._prices_cache:
            return self._prices_cache[cache_key]
        
        prices = {}
        
        try:
            # Get holdings to map CUSIPs to tickers
            holdings = self.get_portfolio_holdings(date)
            cusip_to_ticker = {h.get('cusip'): h.get('ticker') for h in holdings if h.get('cusip') and h.get('ticker')}
            
            # Get tickers for the CUSIPs we need
            tickers = [cusip_to_ticker.get(cusip) for cusip in cusips if cusip_to_ticker.get(cusip)]
            tickers = [t for t in tickers if t]  # Remove None values
            
            if not tickers:
                logger.warning(f"No tickers found for CUSIPs: {cusips}")
                return {}
            
            # Always fetch prices from FMP (never use manual holdings prices)
            # Use historical-price-eod endpoint for all dates (works reliably)
            # Process in chunks to avoid rate limiting
            BATCH_SIZE = 50
            for i in range(0, len(tickers), BATCH_SIZE):
                batch_tickers = tickers[i:i+BATCH_SIZE]
                for ticker in batch_tickers:
                    try:
                        # Get EOD price for the date
                        price_data = self.fmp_client.get_historical_price_eod(ticker, date_str)
                        if price_data:
                            # Use adjusted close if available, otherwise close
                            price = price_data.get('adjClose') or price_data.get('close')
                            if price:
                                # Find corresponding CUSIP
                                for cusip, mapped_ticker in cusip_to_ticker.items():
                                    if mapped_ticker == ticker and cusip in cusips:
                                        prices[cusip] = Decimal(str(price))
                                        break
                    except Exception as e:
                        logger.warning(f"Error fetching price for {ticker}: {e}")
                        continue
            
            # Cache result
            self._prices_cache[cache_key] = prices
            logger.info(f"Retrieved prices for {len(prices)} securities from FMP")
            
            return prices
            
        except Exception as e:
            logger.error(f"Error fetching market prices from FMP: {e}")
            if self.fallback_adapter:
                return self.fallback_adapter.get_market_prices(date, cusips)
            return {}
    
    def get_corporate_actions(self, date: date) -> List[Dict[str, Any]]:
        """
        Get corporate actions for the given date using FMP APIs.
        Checks for splits, symbol changes, and other corporate actions.
        """
        date_str = date.isoformat()
        actions = []
        
        try:
            # Get holdings to check for corporate actions
            holdings = self.get_portfolio_holdings(date)
            tickers = [h.get('ticker') for h in holdings if h.get('ticker')]
            
            # Check for stock splits
            # Get splits calendar around this date
            start_date = (date - timedelta(days=7)).isoformat()
            end_date = (date + timedelta(days=7)).isoformat()
            
            splits = self.fmp_client.get_stock_splits_calendar(start_date, end_date)
            for split in splits:
                symbol = split.get('symbol') or split.get('ticker')
                if symbol in tickers:
                    actions.append({
                        'action_type': 'split',
                        'ticker': symbol,
                        'cusip': self._ticker_to_cusip.get(symbol, ''),
                        'date': split.get('date') or date_str,
                        'split_ratio': split.get('ratio') or split.get('splitRatio', 1),
                        'description': f"Stock split: {split.get('ratio', 'N/A')}"
                    })
            
            # Check for symbol changes
            symbol_changes = self.fmp_client.get_symbol_changes(start_date, end_date)
            for change in symbol_changes:
                old_symbol = change.get('oldSymbol') or change.get('symbol')
                new_symbol = change.get('newSymbol') or change.get('newTicker')
                if old_symbol in tickers or new_symbol in tickers:
                    actions.append({
                        'action_type': 'symbol_change',
                        'ticker': old_symbol,
                        'new_ticker': new_symbol,
                        'cusip': self._ticker_to_cusip.get(old_symbol, ''),
                        'date': change.get('date') or date_str,
                        'description': f"Symbol change: {old_symbol} -> {new_symbol}"
                    })
            
            logger.info(f"Found {len(actions)} corporate actions for {date_str}")
            return actions
            
        except Exception as e:
            logger.error(f"Error fetching corporate actions from FMP: {e}")
            if self.fallback_adapter:
                return self.fallback_adapter.get_corporate_actions(date)
            return []
    
    def get_expense_data(self, date: date) -> Dict[str, Any]:
        """
        Get expense data for the given date.
        FMP can provide ETF expense ratio for verification, but actual expense accruals
        come from internal calculations.
        """
        expense_data = {
            'accrued_expenses': Decimal('0'),
            'accrued_income': Decimal('0'),
            'payables': Decimal('0'),
            'management_fee': Decimal('0'),
            'admin_expenses': Decimal('0'),
            'custodial_fee': Decimal('0'),
            'other_expenses': Decimal('0'),
        }
        
        try:
            # Get ETF info to verify expense ratio
            etf_info = self.fmp_client.get_etf_info(self.etf_symbol)
            if etf_info:
                expense_ratio = etf_info.get('expenseRatio') or etf_info.get('expense_ratio')
                if expense_ratio:
                    expense_data['expense_ratio'] = float(expense_ratio)
                    logger.info(f"ETF expense ratio from FMP: {expense_ratio}")
        except Exception as e:
            logger.warning(f"Could not fetch ETF expense ratio from FMP: {e}")
        
        # Try fallback for actual expense amounts
        if self.fallback_adapter:
            fallback_data = self.fallback_adapter.get_expense_data(date)
            expense_data.update(fallback_data)
        
        return expense_data
    
    def get_ap_orders(self, date: date) -> List[APOrder]:
        """
        Get AP orders for the given date.
        Note: FMP doesn't provide AP order data - use fallback adapter if available.
        """
        if self.fallback_adapter:
            return self.fallback_adapter.get_ap_orders(date)
        logger.warning("AP orders not available via FMP - returning empty list")
        return []
    
    def get_accounting_data(self, date: date) -> Dict[str, Any]:
        """
        Get accounting data for the given date.
        Combines expense data with dividend income data from FMP.
        """
        accounting_data = {
            'expenses': self.get_expense_data(date),
            'income': {}
        }
        
        try:
            # Get dividend data for holdings
            holdings = self.get_portfolio_holdings(date)
            tickers = [h.get('ticker') for h in holdings if h.get('ticker')]
            
            # Check for dividends around this date
            start_date = (date - timedelta(days=30)).isoformat()
            end_date = (date + timedelta(days=30)).isoformat()
            
            dividend_calendar = self.fmp_client.get_dividends_calendar(start_date, end_date)
            
            total_dividend_income = Decimal('0')
            for div in dividend_calendar:
                symbol = div.get('symbol') or div.get('ticker')
                if symbol in tickers:
                    ex_date = div.get('exDate') or div.get('ex_date')
                    pay_date = div.get('paymentDate') or div.get('pay_date')
                    amount = div.get('dividend') or div.get('amount', 0)
                    
                    # Calculate income based on holdings
                    for holding in holdings:
                        if holding.get('ticker') == symbol:
                            quantity = Decimal(str(holding.get('quantity', 0)))
                            dividend_per_share = Decimal(str(amount))
                            total_dividend_income += quantity * dividend_per_share
                            break
            
            accounting_data['income'] = {
                'dividend_income': str(total_dividend_income),
                'interest_income': '0'
            }
            
        except Exception as e:
            logger.warning(f"Error fetching dividend data from FMP: {e}")
        
        # Try fallback for other accounting data
        if self.fallback_adapter:
            fallback_data = self.fallback_adapter.get_accounting_data(date)
            accounting_data.update(fallback_data)
        
        return accounting_data
    
    def get_distribution_data(self, date: date) -> Dict[str, Any]:
        """
        Get distribution data for the given date.
        Note: FMP doesn't provide distribution data - use fallback adapter if available.
        """
        if self.fallback_adapter:
            return self.fallback_adapter.get_distribution_data(date)
        logger.warning("Distribution data not available via FMP - returning empty data")
        return {}
    
    # ========== Additional Helper Methods for Admin/Accounting Workflows ==========
    
    def get_benchmark_data(self, benchmark_symbol: str, date: date) -> Optional[Dict[str, Any]]:
        """
        Get benchmark index data for NAV verification.
        
        Args:
            benchmark_symbol: Benchmark symbol (e.g., "SPY" for S&P 500)
            date: Date for benchmark data
            
        Returns:
            Dictionary with benchmark level and change, or None
        """
        try:
            if date == date.today():
                return self.fmp_client.get_index_market_data(benchmark_symbol)
            else:
                # For historical dates, get historical price
                price_data = self.fmp_client.get_historical_price_eod(benchmark_symbol, date.isoformat())
                if price_data:
                    return {
                        'price': price_data.get('close'),
                        'change': price_data.get('change') or price_data.get('changePercent'),
                        'date': date.isoformat()
                    }
        except Exception as e:
            logger.error(f"Error fetching benchmark data: {e}")
        return None
    
    def get_security_identifiers(self, ticker: str) -> Dict[str, Optional[str]]:
        """
        Get security identifiers (CUSIP, CIK, ISIN) for a ticker.
        Used for regulatory filings.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with cusip, cik, isin, etc.
        """
        identifiers = {
            'cusip': None,
            'cik': None,
            'isin': None,
            'ticker': ticker
        }
        
        try:
            profile = self.fmp_client.get_company_profile(ticker)
            if profile:
                identifiers['cusip'] = profile.get('cusip') or profile.get('cusipNumber')
                identifiers['cik'] = profile.get('cik')
                identifiers['isin'] = profile.get('isin')
                identifiers['name'] = profile.get('companyName') or profile.get('name')
        except Exception as e:
            logger.warning(f"Error fetching identifiers for {ticker}: {e}")
        
        return identifiers
    
    def get_portfolio_metrics(self, date: date) -> Dict[str, Any]:
        """
        Get portfolio-level metrics (weighted P/E, dividend yield, etc.) for investor reporting.
        
        Args:
            date: Date for metrics calculation
            
        Returns:
            Dictionary with portfolio metrics
        """
        metrics = {
            'weighted_pe': None,
            'weighted_dividend_yield': None,
            'sector_allocations': {}
        }
        
        try:
            holdings = self.get_portfolio_holdings(date)
            tickers = [h.get('ticker') for h in holdings if h.get('ticker')]
            weights = {h.get('ticker'): float(h.get('weight', 0)) / 100.0 for h in holdings if h.get('ticker')}
            
            # Get key metrics for each holding
            total_weighted_pe = 0.0
            total_weighted_yield = 0.0
            
            for ticker in tickers:
                weight = weights.get(ticker, 0)
                if weight == 0:
                    continue
                
                key_metrics = self.fmp_client.get_key_metrics_ttm(ticker)
                if key_metrics:
                    pe = key_metrics.get('peRatio') or key_metrics.get('pe_ratio')
                    div_yield = key_metrics.get('dividendYield') or key_metrics.get('dividend_yield')
                    
                    if pe:
                        total_weighted_pe += pe * weight
                    if div_yield:
                        total_weighted_yield += div_yield * weight
            
            metrics['weighted_pe'] = total_weighted_pe if total_weighted_pe > 0 else None
            metrics['weighted_dividend_yield'] = total_weighted_yield if total_weighted_yield > 0 else None
            
            # Get sector allocations
            sector_weightings = self.fmp_client.get_etf_sector_weightings(self.etf_symbol)
            if sector_weightings:
                metrics['sector_allocations'] = {
                    item.get('sector'): float(item.get('weightPercentage', 0))
                    for item in sector_weightings
                }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
        
        return metrics

