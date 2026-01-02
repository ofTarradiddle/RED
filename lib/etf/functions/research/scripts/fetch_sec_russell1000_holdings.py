"""
Fetch Historical Russell 1000 Constituents from SEC EDGAR Filings
Downloads N-Q (quarterly) and N-CSR (annual) filings from mutual funds tracking Russell 1000
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime
import pandas as pd
import requests
import time
import re
from typing import List, Dict, Any, Optional

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    logger.warning("BeautifulSoup not available - HTML parsing will be limited")

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SEC EDGAR base URL
SEC_BASE_URL = "https://www.sec.gov"
SEC_EDGAR_API = "https://data.sec.gov"

# Known Russell 1000 Mutual Funds with CIKs
RUSSELL_1000_FUNDS = {
    'BRGNX': {
        'name': 'BlackRock Russell 1000 Index Fund',
        'cik': '0001100663',  # BlackRock
        'series_cik': None,  # Need to find specific series CIK
    },
    'FRUSX': {
        'name': 'Fidelity Russell 1000 Index Fund',
        'cik': '0000315069',  # Fidelity
        'series_cik': None,
    },
}

# Output directory
OUTPUT_DIR = Path('./data/research/sec_russell1000_holdings')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SECEDGARClient:
    """Client for accessing SEC EDGAR data."""
    
    def __init__(self, user_agent: str = "REDI Research redi@example.com"):
        """
        Initialize SEC EDGAR client.
        
        SEC requires a User-Agent header identifying your application.
        """
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        })
        self.request_delay = 0.1  # SEC rate limit: 10 requests/second
    
    def search_company(self, company_name: str) -> List[Dict]:
        """
        Search for company by name using SEC EDGAR company search.
        
        Args:
            company_name: Company or fund name to search
            
        Returns:
            List of company matches with CIKs
        """
        url = f"{SEC_BASE_URL}/cgi-bin/browse-edgar"
        params = {'company': company_name, 'action': 'getcompany'}
        
        try:
            time.sleep(self.request_delay)
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                # Parse HTML response to extract CIKs
                # SEC returns HTML with CIK links
                cik_pattern = r'CIK=(\d+)'
                ciks = re.findall(cik_pattern, response.text)
                
                results = []
                for cik in set(ciks):
                    results.append({
                        'cik': cik.zfill(10),
                        'name': company_name
                    })
                
                return results
            return []
        except Exception as e:
            logger.error(f"Error searching for {company_name}: {e}")
            return []
    
    def get_company_filings_html(self, company_name: str, form_type: str = None,
                                start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Get company filings using HTML search (more reliable than JSON API).
        
        Args:
            company_name: Company name to search
            form_type: Filter by form type (e.g., 'N-Q', 'N-CSR')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of filing metadata dictionaries
        """
        url = f"{SEC_BASE_URL}/cgi-bin/browse-edgar"
        params = {
            'company': company_name,
            'action': 'getcompany',
            'count': '100'
        }
        if form_type:
            params['type'] = form_type
        
        try:
            time.sleep(self.request_delay)
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                filings = []
                
                if BEAUTIFULSOUP_AVAILABLE:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Find filing table rows
                    rows = soup.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            # Extract filing info
                            form_cell = cells[1].get_text(strip=True)
                            date_cell = cells[3].get_text(strip=True) if len(cells) > 3 else ''
                            
                            # Find accession number in links
                            link = row.find('a', href=re.compile(r'/Archives/edgar/data/'))
                            if link:
                                href = link.get('href', '')
                                match = re.search(r'/data/(\d+)/([^/]+)/', href)
                                if match:
                                    cik = match.group(1)
                                    acc_num = match.group(2)
                                    
                                    filing = {
                                        'form': form_cell,
                                        'date': date_cell,
                                        'accessionNumber': acc_num,
                                        'cik': cik.zfill(10),
                                        'href': href
                                    }
                                    
                                    # Filter by form type
                                    if form_type and form_cell != form_type:
                                        continue
                                    
                                    # Filter by date
                                    if start_date and date_cell < start_date:
                                        continue
                                    if end_date and date_cell > end_date:
                                        continue
                                    
                                    filings.append(filing)
                else:
                    # Fallback: regex parsing
                    cik_pattern = r'CIK=(\d{10})'
                    acc_pattern = r'/data/\d+/([^/]+)/'
                    ciks = re.findall(cik_pattern, response.text)
                    accs = re.findall(acc_pattern, response.text)
                    
                    # Try to match up (simplified)
                    for i, cik in enumerate(set(ciks)):
                        if i < len(accs):
                            filings.append({
                                'cik': cik,
                                'accessionNumber': accs[i],
                                'form': form_type or 'UNKNOWN',
                                'date': 'UNKNOWN'
                            })
                
                return filings
            return []
        except Exception as e:
            logger.error(f"Error fetching filings for {company_name}: {e}")
            return []
    
    def get_company_filings(self, cik: str, form_type: str = None, 
                           start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Get company filings from SEC EDGAR using direct company page.
        
        Args:
            cik: Company CIK
            form_type: Filter by form type (e.g., 'N-Q', 'N-CSR')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of filing metadata dictionaries
        """
        cik_clean = str(cik).lstrip('0')  # Remove leading zeros for URL
        
        # Direct company filings page
        url = f"{SEC_BASE_URL}/cgi-bin/browse-edgar"
        params = {
            'action': 'getcompany',
            'CIK': cik_clean,
            'count': '100',
            'owner': 'exclude'
        }
        if form_type:
            params['type'] = form_type
        
        try:
            time.sleep(self.request_delay)
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                filings = []
                
                # Parse HTML table
                if BEAUTIFULSOUP_AVAILABLE:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Find table with filings - try multiple class names
                    table = (soup.find('table', {'class': 'tableFile2'}) or 
                            soup.find('table', {'class': re.compile('table', re.I)}) or
                            soup.find('table'))
                    
                    if table:
                        rows = table.find_all('tr')[1:]  # Skip header
                        logger.debug(f"Found {len(rows)} table rows")
                        
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) >= 3:
                                # Extract filing info - structure varies
                                # Try to find document link (usually first cell)
                                doc_link = None
                                for cell in cells:
                                    link = cell.find('a', href=re.compile(r'/Archives/edgar/data/'))
                                    if link:
                                        doc_link = link
                                        break
                                
                                if doc_link:
                                    href = doc_link.get('href', '')
                                    # Extract accession from href
                                    match = re.search(r'/data/\d+/([^/]+)/', href)
                                    if match:
                                        acc_num = match.group(1)
                                        
                                        # Try to extract form type and date from cells
                                        form_type_cell = 'N-CSR'  # Default
                                        filing_date = 'UNKNOWN'
                                        
                                        # Look for form type and date in cells
                                        for cell in cells:
                                            text = cell.get_text(strip=True)
                                            if text in ['N-CSR', 'N-Q', 'N-CEN', 'N-CSA', 'N-CSRS']:
                                                form_type_cell = text
                                            # Look for date pattern (YYYY-MM-DD)
                                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
                                            if date_match:
                                                filing_date = date_match.group(1)
                                        
                                        filing = {
                                            'form': form_type_cell,
                                            'date': filing_date,
                                            'accessionNumber': acc_num,
                                            'cik': str(cik).zfill(10),
                                            'href': href
                                        }
                                        
                                        # Filter by form type
                                        if form_type and form_type_cell != form_type:
                                            continue
                                        
                                        # Filter by date
                                        if start_date and filing_date != 'UNKNOWN' and filing_date < start_date:
                                            continue
                                        if end_date and filing_date != 'UNKNOWN' and filing_date > end_date:
                                            continue
                                        
                                        filings.append(filing)
                else:
                    # Fallback: regex parsing
                    filing_pattern = r'/Archives/edgar/data/(\d+)/([^/]+)/([^\"\s]+)'
                    matches = re.findall(filing_pattern, response.text)
                    
                    for match in matches[:50]:  # Limit to first 50
                        cik_match, acc, doc = match
                        if 'index' in doc.lower():
                            filings.append({
                                'cik': cik_match.zfill(10),
                                'accessionNumber': acc,
                                'form': form_type or 'UNKNOWN',
                                'date': 'UNKNOWN'
                            })
                
                return filings
            return []
        except Exception as e:
            logger.error(f"Error fetching filings for CIK {cik}: {e}")
            return []
    
    def get_filing_document(self, cik: str, accession_number: str, 
                           document_name: str = None) -> Optional[str]:
        """
        Download a specific filing document.
        
        Args:
            cik: Company CIK
            accession_number: Filing accession number (e.g., 0001100663-25-000039)
            document_name: Specific document name (e.g., 'nq.htm', 'ncsa.htm')
                          If None, tries to find holdings document via index page
            
        Returns:
            Document content as string, or None if not found
        """
        cik_padded = str(cik).zfill(10)
        
        # Convert accession number to path format
        # Accession numbers from HTML parsing are like: 000110066325000026 (no dashes)
        # Need to convert to: 0001100663-25-000026 (with dashes) for URL
        # Path format: 0001100663/25-000026
        
        # Normalize accession number
        acc_clean = accession_number.replace('-', '')  # Remove any existing dashes
        
        if '-' in accession_number:
            # Already has dashes: 0001100663-25-000026
            acc_dashed = accession_number
            parts = accession_number.split('-')
            if len(parts) == 3:
                acc_path = f"{parts[0]}/{parts[1]}-{parts[2]}"
            else:
                logger.warning(f"Unexpected accession format: {accession_number}")
                return None
        elif len(acc_clean) >= 18:
            # Format: 000110066325000026 -> 0001100663-25-000026
            acc_dashed = f"{acc_clean[:10]}-{acc_clean[10:12]}-{acc_clean[12:]}"
            acc_path = f"{acc_clean[:10]}/{acc_clean[10:12]}-{acc_clean[12:]}"
        else:
            logger.warning(f"Invalid accession number format: {accession_number} (length: {len(acc_clean)})")
            return None
        
        # First, try to get the index page to find the actual document
        # Index page format: {acc_dashed}-index.htm
        index_filename = f"{acc_dashed}-index.htm"
        index_url = f"{SEC_BASE_URL}/Archives/edgar/data/{cik_padded}/{acc_path}/{index_filename}"
        
        try:
            time.sleep(self.request_delay)
            index_response = self.session.get(index_url, timeout=30)
            
            if index_response.status_code == 200:
                # Parse index to find document links
                if BEAUTIFULSOUP_AVAILABLE:
                    soup = BeautifulSoup(index_response.text, 'html.parser')
                    # Find links to HTML/XML documents
                    links = soup.find_all('a', href=re.compile(r'\.(htm|html|xml|txt)$', re.I))
                    
                    # N-CSA documents contain Schedule of Investments (the actual holdings)
                    # N-CSR documents are the main report
                    ncsa_docs = []
                    preferred_docs = []
                    other_docs = []
                    
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True).lower()
                        if 'ncsa' in text or ('schedule' in text and 'investment' in text):
                            ncsa_docs.append(href)
                        elif any(keyword in text for keyword in ['ncsr', 'holdings', 'schedule']):
                            preferred_docs.append(href)
                        else:
                            other_docs.append(href)
                    
                    # Try N-CSA documents first (they contain the actual holdings tables)
                    # Then try other preferred docs, then others
                    docs_to_try = ncsa_docs + [d for d in preferred_docs if d not in ncsa_docs] + other_docs
                    
                    if ncsa_docs:
                        logger.debug(f"Found {len(ncsa_docs)} N-CSA documents (holdings)")
                    
                    for doc_href in docs_to_try[:5]:  # Try first 5 documents
                        if doc_href.startswith('/'):
                            doc_url = f"{SEC_BASE_URL}{doc_href}"
                        else:
                            doc_url = f"{SEC_BASE_URL}/Archives/edgar/data/{cik_padded}/{acc_path}/{doc_href}"
                        
                        try:
                            time.sleep(self.request_delay)
                            doc_response = self.session.get(doc_url, timeout=30)
                            
                            if doc_response.status_code == 200:
                                logger.info(f"✓ Downloaded document: {doc_href}")
                                return doc_response.text
                        except Exception as e:
                            logger.debug(f"Error downloading {doc_href}: {e}")
                            continue
        except Exception as e:
            logger.debug(f"Error accessing index page: {e}")
        
        # Fallback: Try common document names directly
        if document_name:
            document_paths = [document_name]
        else:
            document_paths = [
                f'{accession_number}.htm', f'{accession_number}.txt',
                'ncsa.htm', 'ncsa.txt', 'ncsr.htm', 'ncsr.txt',
                'ncsa10.htm', 'ncsa10.txt'
            ]
        
        for doc_name in document_paths:
            url = f"{SEC_BASE_URL}/Archives/edgar/data/{cik_padded}/{acc_path}/{doc_name}"
            
            try:
                time.sleep(self.request_delay)
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"✓ Downloaded {doc_name}")
                    return response.text
            except Exception as e:
                logger.debug(f"Error downloading {doc_name}: {e}")
                continue
        
        return None
    
    def parse_holdings_from_filing(self, filing_content: str) -> List[Dict]:
        """
        Parse holdings from SEC filing HTML.
        
        SEC N-CSR/N-CSA filings contain Schedule of Investments with holdings data.
        This function extracts holdings from HTML tables using multiple strategies.
        """
        holdings = []
        
        # Strategy 1: Use pandas read_html (most reliable for well-formed tables)
        # SEC filings are often XHTML/XML, so we need to handle that
        tables = []
        try:
            # Try different parsers - lxml works best with XHTML
            for parser in ['lxml', 'html5lib', 'bs4']:
                try:
                    tables = pd.read_html(filing_content, flavor=parser)
                    if tables:
                        logger.info(f"Pandas found {len(tables)} tables using {parser} parser")
                        break
                except Exception as e:
                    logger.debug(f"Parser {parser} failed: {e}")
                    continue
            
            if not tables:
                try:
                    # Try default parser
                    tables = pd.read_html(filing_content)
                    if tables:
                        logger.info(f"Pandas found {len(tables)} tables using default parser")
                except Exception as e:
                    logger.debug(f"Default parser failed: {e}")
            
            # If still no tables, try parsing as XML/XHTML with BeautifulSoup
            if not tables and BEAUTIFULSOUP_AVAILABLE:
                try:
                    # Try XML parser first (SEC filings are often XHTML)
                    soup = BeautifulSoup(filing_content, 'xml')
                    html_tables = soup.find_all('table')
                    if html_tables:
                        logger.info(f"Found {len(html_tables)} <table> elements via XML parser")
                        # Convert to string and try pandas again
                        for table in html_tables:
                            try:
                                table_str = str(table)
                                table_df = pd.read_html(table_str)[0]
                                tables.append(table_df)
                            except:
                                continue
                except:
                    # Fallback to HTML parser
                    try:
                        soup = BeautifulSoup(filing_content, 'html.parser')
                        html_tables = soup.find_all('table')
                        if html_tables:
                            logger.info(f"Found {len(html_tables)} <table> elements via HTML parser")
                            for table in html_tables:
                                try:
                                    table_str = str(table)
                                    table_df = pd.read_html(table_str)[0]
                                    tables.append(table_df)
                                except:
                                    continue
                    except Exception as e:
                        logger.debug(f"BeautifulSoup parsing failed: {e}")
            
            if not tables:
                logger.warning("No tables found - filing may use embedded documents or different format")
            
            for table_idx, table in enumerate(tables):
                if table.empty:
                    continue
                
                # Normalize column names
                table.columns = [str(c).strip().lower() for c in table.columns]
                cols_lower = [str(c).lower() for c in table.columns]
                
                # Check if this looks like a holdings table
                has_ticker = any('ticker' in c or 'symbol' in c for c in cols_lower)
                has_cusip = any('cusip' in c for c in cols_lower)
                has_name = any('name' in c or 'issuer' in c or 'description' in c for c in cols_lower)
                has_shares = any('shares' in c or 'principal' in c or 'quantity' in c for c in cols_lower)
                has_value = any('value' in c or 'amount' in c or 'market value' in c for c in cols_lower)
                
                # Need at least ticker/CUSIP and shares/value to be a holdings table
                # But also accept tables with just ticker/name if they have many rows (might be holdings list)
                is_likely_holdings = ((has_ticker or has_cusip or has_name) and (has_shares or has_value)) or \
                                     ((has_ticker or has_cusip) and table.shape[0] > 10)
                
                if is_likely_holdings:
                    logger.info(f"Table {table_idx} looks like holdings table ({table.shape[0]} rows, "
                               f"ticker={has_ticker}, cusip={has_cusip}, shares={has_shares}, value={has_value})")
                    
                    # Extract holdings from this table
                    rows_processed = 0
                    for _, row in table.iterrows():
                        holding = {}
                        
                        # Extract fields based on column names
                        for col in table.columns:
                            val = row[col]
                            
                            # Skip NaN/empty values
                            if pd.isna(val) or val == '' or str(val).strip() == '':
                                continue
                            
                            col_lower = str(col).lower()
                            
                            # Ticker/Symbol
                            if 'ticker' in col_lower or 'symbol' in col_lower:
                                ticker = str(val).strip().upper()
                                if ticker and len(ticker) <= 10:  # Reasonable ticker length
                                    holding['ticker'] = ticker
                            
                            # CUSIP
                            elif 'cusip' in col_lower:
                                cusip = str(val).strip()
                                if cusip and len(cusip) >= 6:  # CUSIPs are 9 chars but some may be partial
                                    holding['cusip'] = cusip
                            
                            # Name/Issuer
                            elif 'name' in col_lower or 'issuer' in col_lower or 'description' in col_lower:
                                name = str(val).strip()
                                if name and len(name) > 2:  # Reasonable name length
                                    holding['name'] = name
                            
                            # Shares/Quantity
                            elif 'shares' in col_lower or 'principal' in col_lower or 'quantity' in col_lower:
                                try:
                                    # Remove commas and convert
                                    shares_str = str(val).replace(',', '').replace('$', '').strip()
                                    shares = float(shares_str) if shares_str else None
                                    if shares and shares > 0:
                                        holding['shares'] = shares
                                except (ValueError, TypeError):
                                    pass
                            
                            # Value/Amount
                            elif 'value' in col_lower or 'amount' in col_lower or 'market value' in col_lower:
                                try:
                                    # Remove commas, dollar signs, and convert
                                    value_str = str(val).replace(',', '').replace('$', '').strip()
                                    value = float(value_str) if value_str else None
                                    if value and value > 0:
                                        holding['value'] = value
                                except (ValueError, TypeError):
                                    pass
                        
                        # Only add if we have at least ticker/CUSIP/name
                        if holding and (holding.get('ticker') or holding.get('cusip') or holding.get('name')):
                            # Clean up ticker (remove common suffixes/prefixes)
                            if 'ticker' in holding:
                                ticker = str(holding['ticker']).strip().upper()
                                # Remove common prefixes/suffixes
                                ticker = ticker.replace('COMMON STOCK', '').replace('COMMON', '').strip()
                                ticker = re.sub(r'[^A-Z0-9]', '', ticker)  # Keep only alphanumeric
                                if len(ticker) > 0 and len(ticker) <= 10:
                                    holding['ticker'] = ticker
                                else:
                                    holding.pop('ticker', None)
                            
                            # Skip if it looks like a header row (all text, no numbers)
                            if 'shares' not in holding and 'value' not in holding:
                                # Might be header, but include if has valid ticker
                                if holding.get('ticker') and len(holding.get('ticker', '')) >= 1:
                                    holdings.append(holding)
                            else:
                                holdings.append(holding)
                                rows_processed += 1
                    
                    logger.info(f"  Extracted {rows_processed} holdings from table {table_idx}")
        
        except Exception as e:
            logger.warning(f"Pandas read_html error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        # Strategy 2: Manual BeautifulSoup parsing for XHTML/XML structures
        if not holdings and BEAUTIFULSOUP_AVAILABLE:
            try:
                # Try XML parser first (SEC filings are often XHTML)
                for parser_type in ['xml', 'html.parser', 'lxml']:
                    try:
                        soup = BeautifulSoup(filing_content, parser_type)
                        tables = soup.find_all('table')
                        
                        if tables:
                            logger.info(f"BeautifulSoup ({parser_type}) found {len(tables)} <table> elements")
                            
                            for table_idx, table in enumerate(tables):
                                rows = table.find_all('tr')
                                if len(rows) < 3:  # Skip very small tables
                                    continue
                                
                                logger.debug(f"Table {table_idx}: {len(rows)} rows")
                                
                                # Try to identify header row
                                header_row = None
                                header_cells = []
                                
                                for i, row in enumerate(rows[:10]):  # Check first 10 rows for header
                                    cells = row.find_all(['th', 'td'])
                                    cell_texts = [c.get_text(strip=True).lower() for c in cells]
                                    cell_texts_joined = ' '.join(cell_texts)
                                    
                                    # Look for holdings-related keywords
                                    if any(keyword in cell_texts_joined for keyword in 
                                          ['ticker', 'symbol', 'cusip', 'shares', 'principal', 'value', 'amount', 'market value']):
                                        header_row = i
                                        header_cells = [c.get_text(strip=True).lower() for c in cells]
                                        logger.debug(f"  Found header at row {i}: {header_cells[:6]}")
                                        break
                                
                                if header_row is not None:
                                    # Extract data rows
                                    table_holdings = []
                                    for row in rows[header_row + 1:]:
                                        cells = row.find_all(['td', 'th'])
                                        cell_texts = [c.get_text(strip=True) for c in cells]
                                        
                                        if len(cell_texts) >= len(header_cells) * 0.5:  # At least half the columns
                                            holding = {}
                                            
                                            for i, cell_text in enumerate(cell_texts):
                                                if i < len(header_cells):
                                                    header = header_cells[i]
                                                    
                                                    # Skip empty cells
                                                    if not cell_text or cell_text.strip() == '':
                                                        continue
                                                    
                                                    # Ticker/Symbol
                                                    if 'ticker' in header or 'symbol' in header:
                                                        ticker = re.sub(r'[^A-Z0-9]', '', cell_text.upper())
                                                        if 1 <= len(ticker) <= 10:
                                                            holding['ticker'] = ticker
                                                    
                                                    # CUSIP
                                                    elif 'cusip' in header:
                                                        cusip = re.sub(r'[^A-Z0-9]', '', cell_text.upper())
                                                        if len(cusip) >= 6:
                                                            holding['cusip'] = cusip
                                                    
                                                    # Name/Issuer
                                                    elif 'name' in header or 'issuer' in header or 'description' in header:
                                                        name = cell_text.strip()
                                                        if len(name) > 2:
                                                            holding['name'] = name
                                                    
                                                    # Shares/Quantity
                                                    elif 'shares' in header or 'principal' in header or 'quantity' in header:
                                                        try:
                                                            shares_str = re.sub(r'[^0-9.]', '', cell_text)
                                                            if shares_str:
                                                                holding['shares'] = float(shares_str)
                                                        except (ValueError, TypeError):
                                                            pass
                                                    
                                                    # Value/Amount
                                                    elif 'value' in header or 'amount' in header or 'market value' in header:
                                                        try:
                                                            value_str = re.sub(r'[^0-9.]', '', cell_text)
                                                            if value_str:
                                                                holding['value'] = float(value_str)
                                                        except (ValueError, TypeError):
                                                            pass
                                            
                                            # Only add if we have identifier and some data
                                            if holding and (holding.get('ticker') or holding.get('cusip') or holding.get('name')):
                                                # Skip obvious headers/totals
                                                name_lower = str(holding.get('name', '')).lower()
                                                ticker_lower = str(holding.get('ticker', '')).lower()
                                                
                                                skip_keywords = ['total', 'summary', 'schedule', 'investments', 
                                                               'assets', 'liabilities', 'net assets', 'header']
                                                if not any(kw in name_lower or kw in ticker_lower for kw in skip_keywords):
                                                    table_holdings.append(holding)
                                    
                                    if table_holdings:
                                        logger.info(f"  Extracted {len(table_holdings)} holdings from table {table_idx}")
                                        holdings.extend(table_holdings)
                            
                            if holdings:
                                break  # Found holdings, no need to try other parsers
                    except Exception as e:
                        logger.debug(f"Parser {parser_type} failed: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"BeautifulSoup parsing error: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        
        # Filter out obvious non-holdings (headers, totals, etc.)
        filtered_holdings = []
        for holding in holdings:
            # Skip if it's clearly a header/total row
            name = str(holding.get('name', '')).lower()
            ticker = str(holding.get('ticker', '')).lower()
            
            skip_keywords = ['total', 'summary', 'schedule', 'investments', 'assets', 
                           'liabilities', 'net assets', 'header', 'description']
            
            if any(kw in name or kw in ticker for kw in skip_keywords):
                continue
            
            # Must have some identifier
            if not (holding.get('ticker') or holding.get('cusip') or holding.get('name')):
                continue
            
            filtered_holdings.append(holding)
        
        logger.info(f"Extracted {len(filtered_holdings)} holdings from filing")
        return filtered_holdings


def find_russell1000_fund_ciks():
    """Search for Russell 1000 mutual fund CIKs."""
    logger.info("="*70)
    logger.info("Finding Russell 1000 Mutual Fund CIKs")
    logger.info("="*70)
    
    client = SECEDGARClient()
    
    # Known iShares Trust CIK (contains all iShares ETFs including IWB)
    ishares_cik = '1100663'
    
    logger.info(f"\nUsing iShares Trust CIK: {ishares_cik}")
    
    # Get N-CSR/N-CSRS filings (annual/semi-annual reports with holdings)
    logger.info("Fetching N-CSR filings (contain holdings)...")
    ncsr_filings = client.get_company_filings(ishares_cik, form_type='N-CSR',
                                             start_date='2000-01-01')
    
    # Also try N-CSRS (semi-annual)
    ncsrs_filings = client.get_company_filings(ishares_cik, form_type='N-CSRS',
                                              start_date='2000-01-01')
    
    # Combine both
    all_ncsr = ncsr_filings + ncsrs_filings
    
    logger.info(f"  Found {len(ncsr_filings)} N-CSR + {len(ncsrs_filings)} N-CSRS = {len(all_ncsr)} total filings since 2000")
    
    # Also get N-CEN filings (annual census, may have holdings)
    logger.info("Fetching N-CEN filings...")
    ncen_filings = client.get_company_filings(ishares_cik, form_type='N-CEN',
                                             start_date='2000-01-01')
    
    logger.info(f"  Found {len(ncen_filings)} N-CEN filings since 2000")
    
    results = {
        'iShares Trust': {
            'cik': ishares_cik,
            'ncsr_filings': len(all_ncsr),
            'ncen_filings': len(ncen_filings),
            'recent_ncsr': all_ncsr[0] if all_ncsr else None,
            'recent_ncen': ncen_filings[0] if ncen_filings else None,
            'all_ncsr_filings': all_ncsr
        }
    }
    
    return results


def fetch_holdings_for_fund(cik: str, start_date: str = '2000-01-01', 
                           end_date: str = None, max_filings: int = 10):
    """
    Fetch historical holdings for iShares Trust (includes IWB).
    
    Args:
        cik: Fund CIK (iShares Trust: 1100663)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), defaults to today
        max_filings: Maximum number of filings to process (for testing)
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info("="*70)
    logger.info(f"Fetching Holdings for iShares Trust (CIK {cik})")
    logger.info(f"Date Range: {start_date} to {end_date}")
    logger.info("="*70)
    
    client = SECEDGARClient()
    
    # Get N-CSR/N-CSRS filings (annual/semi-annual with holdings)
    logger.info("\nFetching N-CSR/N-CSRS (annual/semi-annual) filings...")
    ncsr_filings = client.get_company_filings(cik, form_type='N-CSR',
                                            start_date=start_date, end_date=end_date)
    ncsrs_filings = client.get_company_filings(cik, form_type='N-CSRS',
                                             start_date=start_date, end_date=end_date)
    
    # Combine
    all_filings = ncsr_filings + ncsrs_filings
    
    logger.info(f"Found {len(ncsr_filings)} N-CSR + {len(ncsrs_filings)} N-CSRS = {len(all_filings)} total filings")
    
    if not all_filings:
        logger.warning("No N-CSR/N-CSRS filings found")
        return []
    
    # Download and parse filings
    all_holdings = []
    
    # Process most recent filings first (they're more likely to have IWB data)
    filings_to_process = all_filings[:max_filings]
    
    for filing in filings_to_process:
        logger.info(f"\nProcessing N-CSR filing: {filing['date']} ({filing['accessionNumber']})")
        
        # Try to download the filing
        content = client.get_filing_document(cik, filing['accessionNumber'])
        if content:
            logger.info(f"  ✓ Downloaded filing document")
            
            # Check if this filing mentions Russell 1000 or IWB
            if 'Russell 1000' in content or 'IWB' in content or 'iShares Russell 1000' in content:
                logger.info(f"  ✓ Found Russell 1000/IWB mention in filing")
                # This is likely the right filing - save it for detailed parsing
                sample_file = OUTPUT_DIR / f"sample_filing_{filing['date'].replace('-', '')}_{filing['accessionNumber'][:10]}.html"
                with open(sample_file, 'w', encoding='utf-8') as f:
                    f.write(content)  # Save full content
                logger.info(f"  ✓ Saved sample filing to {sample_file} ({len(content)} chars)")
            
            # Parse holdings
            holdings = client.parse_holdings_from_filing(content)
            logger.info(f"  Extracted {len(holdings)} holdings")
            
            for holding in holdings:
                holding['filing_date'] = filing['date']
                holding['filing_type'] = 'N-CSR'
                holding['accession_number'] = filing['accessionNumber']
                all_holdings.append(holding)
        else:
            logger.warning(f"  ✗ Could not download filing document")
    
    return all_holdings


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("SEC EDGAR Russell 1000 Historical Holdings Fetcher")
    logger.info("="*70)
    
    # Step 1: Find fund CIKs
    fund_info = find_russell1000_fund_ciks()
    
    # Step 2: Fetch holdings for iShares Trust
    if fund_info:
        company = list(fund_info.keys())[0]
        info = fund_info[company]
        
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing {company}")
        logger.info(f"{'='*70}")
        
        # Start from 2000 (IWB launch date) but limit to recent filings for testing
        holdings = fetch_holdings_for_fund(info['cik'], start_date='2020-01-01', max_filings=5)
        
        if holdings:
            # Save holdings
            df = pd.DataFrame(holdings)
            output_file = OUTPUT_DIR / f"ishares_russell1000_holdings.csv"
            df.to_csv(output_file, index=False)
            logger.info(f"\n✓ Saved {len(holdings)} holdings to {output_file}")
            
            # Also save summary
            if 'filing_date' in df.columns:
                summary = df.groupby('filing_date').size().reset_index(name='holdings_count')
                summary_file = OUTPUT_DIR / f"ishares_holdings_summary.csv"
                summary.to_csv(summary_file, index=False)
                logger.info(f"✓ Saved summary to {summary_file}")
        else:
            logger.warning(f"No holdings extracted - may need to parse filing structure differently")


if __name__ == "__main__":
    main()

