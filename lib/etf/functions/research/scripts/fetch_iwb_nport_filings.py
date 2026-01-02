"""
Fetch Historical IWB (Russell 1000) Holdings from SEC N-PORT Filings
N-PORT is the monthly form that ETFs file with the SEC containing their holdings.
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
import json
import time
import re
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SEC EDGAR Configuration
SEC_BASE_URL = "https://www.sec.gov"
SEC_EDGAR_API = "https://data.sec.gov"
IWB_CIK = "1100663"  # iShares Trust CIK (manages IWB)
IWB_LAUNCH_DATE = "2000-05-15"

# Output directories
OUTPUT_DIR = Path('./data/research/russell1000_constituents')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Request headers (SEC requires User-Agent)
HEADERS = {
    'User-Agent': 'REDI Research redi@example.com',
    'Accept-Encoding': 'gzip, deflate',
    'Host': 'www.sec.gov'
}


class SECNPortClient:
    """Client for fetching and parsing SEC N-PORT filings."""
    
    def __init__(self, cik: str, request_delay: float = 0.1):
        """
        Initialize SEC N-PORT client.
        
        Args:
            cik: Company CIK (10-digit, zero-padded)
            request_delay: Delay between requests (seconds)
        """
        self.cik = str(cik).zfill(10)
        self.request_delay = request_delay
        self.session = requests.Session()
        # SEC requires User-Agent header - must be set before any requests
        self.session.headers.update(HEADERS)
        # Remove Host header as it's set automatically
        if 'Host' in self.session.headers:
            del self.session.headers['Host']
    
    def get_company_filings(self, form_type: str = "NPORT-P", 
                           start_date: str = None, 
                           end_date: str = None) -> List[Dict]:
        """
        Get list of N-PORT filings for the company.
        
        Args:
            form_type: Form type (NPORT-P for monthly, NPORT-EX for exempt)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of filing dictionaries
        """
        # Use the submissions endpoint to get filing list
        # Format: CIK0001100663.json (CIK is already zero-padded to 10 digits)
        submissions_url = f"{SEC_EDGAR_API}/submissions/CIK{self.cik}.json"
        
        try:
            time.sleep(self.request_delay)
            response = self.session.get(submissions_url, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Failed to get submissions: HTTP {response.status_code} for URL: {submissions_url}")
                logger.warning(f"Response: {response.text[:200] if hasattr(response, 'text') else 'N/A'}")
                # Try HTML search as fallback
                return self._get_filings_from_html(form_type, start_date, end_date)
            
            data = response.json()
            
            # Get recent filings
            recent_filings = data.get('filings', {}).get('recent', {})
            forms = recent_filings.get('form', [])
            filing_dates = recent_filings.get('filingDate', [])
            accession_numbers = recent_filings.get('accessionNumber', [])
            
            # Filter for N-PORT filings
            nport_filings = []
            for i, form in enumerate(forms):
                if form_type in form.upper():
                    filing_date = filing_dates[i] if i < len(filing_dates) else None
                    accession = accession_numbers[i] if i < len(accession_numbers) else None
                    
                    # Filter by date if provided
                    if start_date and filing_date:
                        if filing_date < start_date:
                            continue
                    if end_date and filing_date:
                        if filing_date > end_date:
                            continue
                    
                    nport_filings.append({
                        'form': form,
                        'filingDate': filing_date,
                        'accessionNumber': accession
                    })
            
            logger.info(f"Found {len(nport_filings)} {form_type} filings from JSON API")
            return nport_filings
            
        except Exception as e:
            logger.error(f"Error getting filings from JSON: {e}")
            # Try HTML search as fallback
            return self._get_filings_from_html(form_type, start_date, end_date)
    
    def _get_filings_from_html(self, form_type: str, start_date: str = None, 
                               end_date: str = None) -> List[Dict]:
        """Get filings from HTML search page as fallback."""
        url = f"{SEC_BASE_URL}/cgi-bin/browse-edgar"
        params = {
            'action': 'getcompany',
            'CIK': self.cik,
            'type': form_type,
            'dateb': '',
            'owner': 'exclude',
            'count': '100'
        }
        
        try:
            time.sleep(self.request_delay)
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"HTML search failed: HTTP {response.status_code}")
                return []
            
            # Parse HTML to extract filing information
            # SEC HTML format: <td>NPORT-P</td><td>2025-12-30</td><td><a href="...">0001193125-25-336760</a></td>
            html = response.text
            
            # Extract filing rows using regex
            # Pattern: NPORT-P followed by date and accession number
            pattern = r'<td[^>]*>NPORT-P</td>\s*<td[^>]*>(\d{4}-\d{2}-\d{2})</td>.*?href="[^"]*accession-number=([^"]+)"'
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            
            filings = []
            for filing_date, accession in matches:
                # Clean accession number
                accession = accession.replace('&amp;', '&').split('&')[0]
                
                # Filter by date if provided
                if start_date and filing_date < start_date:
                    continue
                if end_date and filing_date > end_date:
                    continue
                
                filings.append({
                    'form': form_type,
                    'filingDate': filing_date,
                    'accessionNumber': accession
                })
            
            logger.info(f"Found {len(filings)} {form_type} filings from HTML search")
            return filings
            
        except Exception as e:
            logger.error(f"Error parsing HTML filings: {e}")
            return []
    
    def get_filing_document(self, accession_number: str) -> Optional[str]:
        """
        Download N-PORT filing document.
        N-PORT filings are typically in XML format.
        
        Args:
            accession_number: Filing accession number (e.g., 0001410368-25-043533)
                              Note: First 10 digits are the series CIK, not trust CIK
            
        Returns:
            Document content as string, or None if not found
        """
        # Extract series CIK from accession number (first 10 digits)
        # 0001410368-25-043533 -> series CIK is 0001410368
        acc_dashed = accession_number
        if '-' not in accession_number:
            if len(accession_number) >= 18:
                acc_dashed = f"{accession_number[:10]}-{accession_number[10:12]}-{accession_number[12:]}"
        
        parts = acc_dashed.split('-')
        if len(parts) == 3:
            series_cik = parts[0]  # Series CIK from accession number
            acc_path = f"{parts[0]}/{parts[1]}-{parts[2]}"
        else:
            logger.warning(f"Unexpected accession format: {accession_number}")
            return None
        
        # N-PORT filings are stored under the series CIK, not trust CIK
        base_url = f"{SEC_BASE_URL}/Archives/edgar/data/{series_cik}/{acc_path}"
        
        # First, try to get the index page to find the actual document
        index_url = f"{base_url}/{acc_dashed}-index.htm"
        
        try:
            time.sleep(self.request_delay)
            index_response = self.session.get(index_url, timeout=30)
            
            if index_response.status_code == 200:
                # Parse index to find XML document
                xml_links = re.findall(r'href="([^"]*\.xml)"', index_response.text, re.I)
                
                # Prefer primary_doc.xml or files with "primary" in name
                preferred = [l for l in xml_links if 'primary' in l.lower()]
                other_xml = [l for l in xml_links if l not in preferred]
                
                for xml_link in preferred + other_xml:
                    if xml_link.startswith('http'):
                        doc_url = xml_link
                    elif xml_link.startswith('/'):
                        doc_url = f"{SEC_BASE_URL}{xml_link}"
                    else:
                        doc_url = f"{base_url}/{xml_link}"
                    
                    try:
                        time.sleep(self.request_delay)
                        doc_response = self.session.get(doc_url, timeout=30)
                        if doc_response.status_code == 200:
                            logger.info(f"✓ Downloaded N-PORT XML: {xml_link}")
                            return doc_response.text
                    except Exception as e:
                        logger.debug(f"Error downloading {xml_link}: {e}")
                        continue
        except Exception as e:
            logger.debug(f"Error accessing index page: {e}")
        
        # Fallback: Try common file names directly
        possible_names = [
            'primary_doc.xml',
            'primary_document.xml',
            f'{acc_dashed}.xml',
            'nport.xml',
            'NPORT.xml'
        ]
        
        for doc_name in possible_names:
            doc_url = f"{base_url}/{doc_name}"
            try:
                time.sleep(self.request_delay)
                response = self.session.get(doc_url, timeout=30)
                if response.status_code == 200:
                    logger.info(f"✓ Downloaded N-PORT XML: {doc_name}")
                    return response.text
            except Exception as e:
                logger.debug(f"Error downloading {doc_name}: {e}")
                continue
        
        return None
    
    def is_iwb_filing(self, xml_content: str) -> bool:
        """
        Check if this N-PORT filing is for IWB (Russell 1000 ETF).
        
        Args:
            xml_content: N-PORT XML content
            
        Returns:
            True if this is an IWB filing
        """
        # Check for IWB indicators in the XML
        iwb_indicators = ['IWB', 'Russell 1000', 'R1000', 'iShares Russell 1000']
        content_upper = xml_content.upper()
        
        for indicator in iwb_indicators:
            if indicator.upper() in content_upper:
                return True
        
        return False
    
    def parse_nport_xml(self, xml_content: str) -> List[Dict]:
        """
        Parse N-PORT XML to extract holdings.
        Uses BeautifulSoup for more robust parsing of potentially malformed XML.
        
        Args:
            xml_content: N-PORT XML content
            
        Returns:
            List of holding dictionaries
        """
        # First check if this is an IWB filing
        if not self.is_iwb_filing(xml_content):
            logger.debug("Filing is not for IWB, skipping")
            return []
        
        holdings = []
        
        try:
            # Try using BeautifulSoup for more forgiving XML parsing
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(xml_content, 'xml')
                
                # N-PORT structure: invstOrSecs -> invstOrSec
                invst_secs = soup.find_all('invstOrSec')
                
                for sec in invst_secs:
                    holding = {}
                    
                    # Extract fields
                    name_elem = sec.find('name')
                    if name_elem:
                        holding['name'] = name_elem.get_text(strip=True)
                    
                    ticker_elem = sec.find('ticker')
                    if ticker_elem:
                        holding['ticker'] = ticker_elem.get_text(strip=True)
                    
                    cusip_elem = sec.find('cusip')
                    if cusip_elem:
                        holding['cusip'] = cusip_elem.get_text(strip=True)
                    
                    # Value and shares
                    val_elem = sec.find('valUSD') or sec.find('value')
                    if val_elem:
                        holding['value'] = val_elem.get_text(strip=True)
                    
                    shr_elem = sec.find('balance') or sec.find('shrsOrPrnAmt')
                    if shr_elem:
                        holding['shares'] = shr_elem.get_text(strip=True)
                    
                    # Only add if we have at least a ticker or name
                    if holding.get('ticker') or holding.get('name'):
                        holdings.append(holding)
                
                logger.info(f"Parsed {len(holdings)} holdings from N-PORT XML using BeautifulSoup")
                return holdings
                
            except ImportError:
                logger.warning("BeautifulSoup not available, using regex parsing")
                return self._parse_nport_regex(xml_content)
            
        except Exception as e:
            logger.error(f"Error parsing N-PORT XML: {e}")
            # Fallback to regex
            return self._parse_nport_regex(xml_content)
    
    def _parse_nport_regex(self, xml_content: str) -> List[Dict]:
        """Regex-based parsing method as fallback."""
        holdings = []
        
        # Extract invstOrSec blocks
        invst_sec_pattern = r'<invstOrSec[^>]*>(.*?)</invstOrSec>'
        sec_blocks = re.findall(invst_sec_pattern, xml_content, re.DOTALL | re.I)
        
        for block in sec_blocks:
            holding = {}
            
            # Extract fields from each block
            ticker_match = re.search(r'<ticker[^>]*>([^<]+)</ticker>', block, re.I)
            if ticker_match:
                holding['ticker'] = ticker_match.group(1).strip()
            
            name_match = re.search(r'<name[^>]*>([^<]+)</name>', block, re.I)
            if name_match:
                holding['name'] = name_match.group(1).strip()
            
            cusip_match = re.search(r'<cusip[^>]*>([^<]+)</cusip>', block, re.I)
            if cusip_match:
                holding['cusip'] = cusip_match.group(1).strip()
            
            # Only add if we have at least a ticker or name
            if holding.get('ticker') or holding.get('name'):
                holdings.append(holding)
        
        logger.info(f"Regex parsing found {len(holdings)} holdings")
        return holdings


def fetch_iwb_nport_filings(start_date: str = None, end_date: str = None) -> Dict[str, List[str]]:
    """
    Fetch IWB holdings from N-PORT filings and construct monthly lists.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        Dictionary mapping dates to ticker lists
    """
    logger.info("="*70)
    logger.info("Fetching IWB Holdings from SEC N-PORT Filings")
    logger.info("="*70)
    
    if start_date is None:
        start_date = IWB_LAUNCH_DATE
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    client = SECNPortClient(IWB_CIK)
    
    # Get N-PORT filings
    logger.info("Fetching N-PORT filing list...")
    filings = client.get_company_filings(
        form_type="NPORT-P",
        start_date=start_date,
        end_date=end_date
    )
    
    if not filings:
        logger.warning("No N-PORT filings found. Trying alternative methods...")
        # Try NPORT-EX (exempt filings)
        filings = client.get_company_filings(
            form_type="NPORT-EX",
            start_date=start_date,
            end_date=end_date
        )
    
    if not filings:
        logger.error("No N-PORT filings found. Cannot proceed.")
        return {}
    
    logger.info(f"Found {len(filings)} N-PORT filings to process")
    
    # Fetch and parse each filing
    holdings_by_date = {}
    successful = 0
    failed = 0
    
    for i, filing in enumerate(filings, 1):
        filing_date = filing.get('filingDate')
        accession = filing.get('accessionNumber')
        
        logger.info(f"\n[{i}/{len(filings)}] Processing filing {filing_date} ({accession})...")
        
        try:
            # Download filing
            xml_content = client.get_filing_document(accession)
            
            if not xml_content:
                logger.warning(f"  ✗ Could not download filing document")
                failed += 1
                continue
            
            # Parse holdings
            holdings = client.parse_nport_xml(xml_content)
            
            if holdings:
                # Extract tickers
                tickers = []
                for h in holdings:
                    ticker = h.get('ticker', '').strip()
                    if ticker and ticker not in tickers:
                        tickers.append(ticker)
                
                if tickers:
                    holdings_by_date[filing_date] = sorted(tickers)
                    successful += 1
                    logger.info(f"  ✓ Extracted {len(tickers)} holdings for {filing_date}")
                else:
                    logger.warning(f"  ⚠ No tickers found in holdings")
                    failed += 1
            else:
                logger.warning(f"  ✗ No holdings parsed from XML")
                failed += 1
        
        except Exception as e:
            logger.error(f"  ✗ Error processing filing: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
            continue
    
    logger.info(f"\n{'='*70}")
    logger.info(f"N-PORT Fetching Summary")
    logger.info(f"  Successful: {successful}/{len(filings)}")
    logger.info(f"  Failed: {failed}/{len(filings)}")
    logger.info(f"{'='*70}")
    
    return holdings_by_date


def construct_monthly_constituents(holdings_by_date: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Construct monthly constituent lists from N-PORT filing dates."""
    logger.info("="*70)
    logger.info("Constructing Monthly Constituent Lists")
    logger.info("="*70)
    
    if not holdings_by_date:
        return {}
    
    # Get date range
    dates = sorted(holdings_by_date.keys())
    start_date = pd.to_datetime(dates[0])
    end_date = pd.to_datetime(dates[-1])
    
    # Generate all month-end dates
    monthly_dates = pd.date_range(start=start_date, end=end_date, freq='M')
    
    monthly_constituents = {}
    last_known_holdings = None
    
    for month_end in monthly_dates:
        month_str = month_end.strftime('%Y-%m-%d')
        
        # Find the most recent filing before or on this month
        for filing_date in reversed(dates):
            filing_datetime = pd.to_datetime(filing_date)
            if filing_datetime <= month_end:
                last_known_holdings = holdings_by_date[filing_date]
                break
        
        if last_known_holdings:
            monthly_constituents[month_str] = last_known_holdings
    
    logger.info(f"Constructed {len(monthly_constituents)} monthly constituent lists")
    return monthly_constituents


def save_constituents(holdings_by_date: Dict[str, List[str]], 
                     monthly_constituents: Dict[str, List[str]]):
    """Save constituent data to CSV files."""
    logger.info("="*70)
    logger.info("Saving Constituent Data")
    logger.info("="*70)
    
    # Save filing-based holdings
    filing_records = []
    for date, tickers in holdings_by_date.items():
        for ticker in tickers:
            filing_records.append({'date': date, 'symbol': ticker, 'source': 'N-PORT'})
    
    if filing_records:
        filing_df = pd.DataFrame(filing_records)
        filing_file = OUTPUT_DIR / 'IWB_nport_holdings.csv'
        filing_df.to_csv(filing_file, index=False)
        logger.info(f"✓ Saved {len(filing_records)} holdings to {filing_file}")
    
    # Save monthly constituents
    monthly_records = []
    for date, tickers in monthly_constituents.items():
        for ticker in tickers:
            monthly_records.append({'date': date, 'symbol': ticker})
    
    if monthly_records:
        monthly_df = pd.DataFrame(monthly_records)
        monthly_file = OUTPUT_DIR / 'IWB_monthly_constituents.csv'
        monthly_df.to_csv(monthly_file, index=False)
        logger.info(f"✓ Saved {len(monthly_records)} monthly constituents to {monthly_file}")
    
    # Save summary
    summary_records = []
    for date, tickers in monthly_constituents.items():
        summary_records.append({
            'date': date,
            'count': len(tickers),
            'symbols': ','.join(tickers)
        })
    
    if summary_records:
        summary_df = pd.DataFrame(summary_records)
        summary_file = OUTPUT_DIR / 'IWB_monthly_summary.csv'
        summary_df.to_csv(summary_file, index=False)
        logger.info(f"✓ Saved monthly summary to {summary_file}")


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("IWB N-PORT Holdings Fetcher")
    logger.info("="*70)
    
    # Fetch N-PORT filings
    holdings_by_date = fetch_iwb_nport_filings(
        start_date=IWB_LAUNCH_DATE,
        end_date=None
    )
    
    if not holdings_by_date:
        logger.error("No holdings data retrieved. Exiting.")
        return
    
    # Construct monthly constituents
    monthly_constituents = construct_monthly_constituents(holdings_by_date)
    
    if not monthly_constituents:
        logger.error("No monthly constituents constructed. Exiting.")
        return
    
    # Save data
    save_constituents(holdings_by_date, monthly_constituents)
    
    logger.info("\n" + "="*70)
    logger.info("Complete!")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("="*70)


if __name__ == "__main__":
    main()

