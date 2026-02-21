# Books & Records Map

## Overview
This document maps all books and records maintained for ETF operations, including what gets retained, where it's stored, and retention periods per SEC Rule 31a-2.

**Regulatory Basis**: SEC Rule 31a-2 requires maintaining complete books and records for at least 6 years (first 2 years in an easily accessible place).

---

## Record Categories

### 1. NAV Calculation Records

**What Gets Retained**:
- Daily NAV calculations
- Complete holdings breakdown (CUSIP, ticker, quantity, price, market value)
- Cash balances
- Accrued income and expenses
- Shares outstanding
- Pricing exceptions
- Validation results
- Shadow NAV reconciliations (if applicable)

**Where Stored**:
- Primary: `data/admin/nav_YYYY-MM-DD.json`
- Shadow NAV: `data/shadow_accounting/shadow_nav_YYYY-MM-DD.json`
- Reconciliation: `data/shadow_accounting/nav_reconciliation_YYYY-MM-DD.json`
- Audit trail: `data/audit_trail/nav_calculation_YYYY-MM-DD_*.json`

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2, SEC Rule 2a-5

---

### 2. Accounting Records

**What Gets Retained**:
- General ledger
- Journal entries (all entries with complete details)
- Trial balances
- Balance sheets
- Income statements
- Chart of accounts
- Account reconciliations

**Where Stored**:
- General ledger: `data/accounting/general_ledger.json`
- Journal entries: `data/accounting/journal_entries.json`
- Trial balances: `data/accounting/trial_balance_YYYY-MM-DD.json`
- Balance sheets: `data/accounting/balance_sheet_YYYY-MM-DD.json`
- Income statements: `data/accounting/income_statement_YYYY-MM-DD_YYYY-MM-DD.json`
- Audit trail: `data/audit_trail/journal_entry_YYYY-MM-DD_*.json`

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2

---

### 3. Holdings and Reconciliation Records

**What Gets Retained**:
- Portfolio holdings (daily)
- Holdings reconciliations (TA vs. Custodian)
- Cash reconciliations
- Position break reports
- Exception logs
- Resolution documentation

**Where Stored**:
- Holdings reconciliation: `data/admin/holdings_reconciliation_YYYY-MM-DD.json`
- Portfolio holdings: Included in NAV files
- Custodian statements: Retained per custodian agreement

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2

---

### 4. Corporate Actions Records

**What Gets Retained**:
- Corporate actions log (all actions processed)
- Dividend income records
- Split adjustments
- Merger/spinoff adjustments
- Security master updates

**Where Stored**:
- Corporate actions: `data/admin/corporate_actions_YYYY-MM-DD.json`
- Security master: `data/supporting/security_master.json`
- Audit trail: Included in audit records

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2

---

### 5. Transfer Agent Records

**What Gets Retained**:
- Shareholder registry (all accounts)
- TA reconciliation reports (TA vs. Custodian vs. DTC)
- Cede & Co. position files
- Creation/redemption order records
- Shareholder transaction history

**Where Stored**:
- Shareholder registry: `data/ta/shareholder_registry.json`
- TA reconciliation: `data/ta/reconciliation_YYYY-MM-DD.json`
- Cede file: `data/ta/cede_file_YYYY-MM-DD.json`
- Order records: `data/ta/orders/`

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2

---

### 6. Order Management Records

**What Gets Retained**:
- PCF files (daily)
- NSCC publication confirmations
- AP order records
- Basket validation results
- Rule 6c-11 compliance records

**Where Stored**:
- PCF files: `data/om/pcf_YYYY-MM-DD.json`
- NSCC confirmations: `data/om/pcf_nscc_YYYY-MM-DD.txt`
- Order records: `data/om/orders/`
- Rule 6c-11: `data/compliance/rule_6c11/rule_6c11_validation_YYYY-MM-DD.json`

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2, SEC Rule 6c-11

---

### 7. Distribution Records

**What Gets Retained**:
- Distribution calculations
- Distribution declarations
- Distribution payment records
- Distribution schedules
- Exchange notifications

**Where Stored**:
- Distributions: `data/distributor/distributions.json`
- Distribution notices: `data/distributor/distribution_notice_*.json`
- Payment records: `data/distributor/payment_*.json`
- Schedules: `data/distributor/distribution_schedule_YYYY.json`

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2, IRS requirements

---

### 8. Tax Records

**What Gets Retained**:
- Tax lot records (all lots with cost basis)
- Realized gain/loss records
- Unrealized gain/loss records
- Tax form data (1099-DIV, 1099-B, 1120-RIC, 8613)
- Tax return filings
- M-1 book-to-tax adjustments
- State tax returns

**Where Stored**:
- Tax lots: `data/tax_lots/tax_lots.json`
- Tax forms: `data/tax/form_*.json`
- Tax returns: `data/tax/returns/`
- Tax adjustments: `data/tax/adjustments/`

**Retention Period**: 7 years (IRS requirement)

**Regulatory Requirement**: IRS requirements, SEC Rule 31a-2

---

### 9. Compliance Records

**What Gets Retained**:
- SEC filings (N-PORT, N-CEN, N-CSR, N-Q, N-MFP, 8-K)
- SEC filing confirmations
- Compliance reports
- Exception logs
- Control test results

**Where Stored**:
- SEC filings: `data/compliance/n_port_*.xml`, `data/compliance/n_cen_*.json`, etc.
- Filing confirmations: `data/compliance/*_filing_*.json`
- Compliance reports: `data/compliance/compliance_reports_*.json`
- Control tests: `data/compliance/control_tests/`

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2, SEC filing requirements

---

### 10. Performance Records

**What Gets Retained**:
- Performance calculations (total return, pre-tax, after-tax)
- Benchmark comparisons
- Performance reports
- Attribution analysis

**Where Stored**:
- Performance data: `data/performance/performance_YYYY-MM-DD_YYYY-MM-DD.json`
- Performance reports: `data/performance/reports/`

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2

---

### 11. Audit Trail Records

**What Gets Retained**:
- Complete audit trail of all operations
- All NAV calculations
- All journal entries
- All reconciliations
- All corporate actions
- All trades
- Operation timestamps
- User information (if applicable)

**Where Stored**:
- Master audit log: `data/audit_trail/audit_records.json`
- Individual audit files: `data/audit_trail/*_YYYY-MM-DD_*.json`
- Audit packages: `data/audit_trail/audit_package_*.json`

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2

---

### 12. Pricing and Valuation Records

**What Gets Retained**:
- Market prices (daily)
- Price validation reports
- Fair valuation records
- Pricing exception logs
- Valuation methodology documentation

**Where Stored**:
- Price validation: Included in NAV files
- Fair valuation: `data/fair_valuation/fair_valuation_YYYY-MM-DD.json`
- Pricing exceptions: Included in NAV files

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2, SEC Rule 2a-5

---

### 13. Expense Records

**What Gets Retained**:
- Expense accruals (daily)
- Expense allocations (monthly)
- Accrual true-ups (monthly)
- Expense invoices
- Expense reconciliation

**Where Stored**:
- Expense accruals: Included in journal entries
- Expense allocations: `data/accounting/expense_allocation_YYYY-MM.json`
- Accrual reconciliations: `data/accounting/accrual_reconciliation_YYYY-MM.json`
- Invoices: Retained per vendor agreements

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2

---

### 14. Trading Records

**What Gets Retained**:
- Trade orders
- Trade executions
- Trade settlements
- Trade confirmations

**Where Stored**:
- Trade orders: `data/trading/trades.json`
- Daily trades: `data/trading/daily_trades_YYYY-MM-DD.json`
- Trade confirmations: Retained per custodian agreement

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2

---

### 15. Risk Management Records

**What Gets Retained**:
- Liquidity risk assessments
- Intraday NAV monitoring
- Spread management reports
- Risk metrics

**Where Stored**:
- Liquidity risk: `data/liquidity_risk/liquidity_assessment_YYYY-MM-DD.json`
- Intraday NAV: `data/intraday_nav/intraday_snapshots_YYYY-MM-DD.json`

**Retention Period**: 6 years (first 2 years easily accessible)

**Regulatory Requirement**: SEC Rule 31a-2

---

## Storage Locations Summary

### Primary Storage
- **Local Storage**: `./data/` directory structure
- **Backup**: Regular backups to secure location
- **Archive**: Archived records moved to archive storage after 2 years

### File Naming Convention
- Date-based: `YYYY-MM-DD` format
- Type-based: Descriptive names (e.g., `nav_`, `trial_balance_`, `reconciliation_`)
- Version-based: Sequential numbers for multiple files per day

---

## Retention Periods Summary

| Record Type | Retention Period | Easily Accessible Period |
|-------------|----------------|-------------------------|
| NAV Calculations | 6 years | 2 years |
| Accounting Records | 6 years | 2 years |
| Holdings/Reconciliations | 6 years | 2 years |
| Corporate Actions | 6 years | 2 years |
| Transfer Agent | 6 years | 2 years |
| Order Management | 6 years | 2 years |
| Distributions | 6 years | 2 years |
| Tax Records | 7 years | 2 years |
| Compliance Records | 6 years | 2 years |
| Performance Records | 6 years | 2 years |
| Audit Trail | 6 years | 2 years |
| Pricing/Valuation | 6 years | 2 years |
| Expense Records | 6 years | 2 years |
| Trading Records | 6 years | 2 years |
| Risk Management | 6 years | 2 years |

---

## Access and Retrieval

### Easy Access (First 2 Years)
- Records stored in primary `data/` directory
- Indexed by date and type
- Quick retrieval via file system or database queries

### Archive Access (Years 3-6)
- Records moved to archive storage
- Indexed for retrieval
- Retrieval process documented

### Retrieval Procedures
1. Identify record type and date
2. Locate in appropriate storage location
3. Retrieve record
4. Document retrieval
5. Return to storage after use

---

## Backup and Disaster Recovery

### Backup Frequency
- **Daily**: All new records backed up
- **Weekly**: Full system backup
- **Monthly**: Archive backup

### Backup Locations
- Primary backup: Secure cloud storage
- Secondary backup: Off-site physical storage
- Test restores: Quarterly

### Disaster Recovery
- Recovery procedures documented
- Recovery time objective: 24 hours
- Recovery point objective: 1 day

---

## SEC Examination Access

### SEC Access Requirements
- SEC examiners must have access to all records
- Records must be provided within reasonable time
- Electronic access preferred

### Preparation for SEC Exams
- Maintain organized record structure
- Index all records
- Document record locations
- Test record retrieval procedures

---

## Record Destruction

### Destruction Procedures
- Records may be destroyed after retention period
- Destruction must be documented
- Destruction must be secure (shredding, secure deletion)
- Destruction log maintained

### Destruction Schedule
- Records older than retention period reviewed quarterly
- Approved for destruction by authorized personnel
- Destruction executed and documented

---

## Notes
- All records must be maintained per SEC Rule 31a-2
- All records must be accessible to SEC examiners
- All records must be backed up regularly
- All record access must be logged
- All record destruction must be documented

