# Controls Matrix

## Overview
This document outlines all internal controls for ETF operations, including control description, frequency, responsible party, and evidence retained.

---

## Daily Controls

### 1. NAV Calculation Control
**Control Description**: Daily NAV calculation with validation and reconciliation

**Frequency**: Daily (every business day)

**Who Performs**: Fund Administrator / Operations Team

**Control Activities**:
- Calculate NAV using approved methodology
- Validate all inputs (holdings, prices, cash, accruals)
- Check for pricing exceptions
- Reconcile NAV vs. previous day
- Validate against shadow NAV (if implemented)
- Obtain approval before publishing

**Evidence Retained**:
- NAV calculation file: `data/admin/nav_YYYY-MM-DD.json`
- NAV validation report: Included in NAV file
- Shadow NAV reconciliation: `data/shadow_accounting/nav_reconciliation_YYYY-MM-DD.json` (if applicable)
- Approval documentation: Included in audit trail

**Review Frequency**: Daily by Operations Manager

---

### 2. Price Validation Control
**Control Description**: Validate all security prices before NAV calculation

**Frequency**: Daily (every business day)

**Who Performs**: Fund Administrator / Operations Team

**Control Activities**:
- Obtain prices from approved data source
- Verify all CUSIPs have prices
- Check for stale or missing prices
- Compare prices vs. previous day (flag > 5% changes)
- Verify prices match custodian pricing
- Apply fair valuation if needed
- Document all pricing exceptions

**Evidence Retained**:
- Price validation report: Included in NAV calculation file
- Fair valuation records: `data/fair_valuation/fair_valuation_YYYY-MM-DD.json`
- Pricing exceptions log: Included in NAV file

**Review Frequency**: Daily by Operations Manager

---

### 3. Holdings Reconciliation Control
**Control Description**: Reconcile internal portfolio holdings vs. custodian holdings

**Frequency**: Daily (every business day)

**Who Performs**: Fund Administrator / Operations Team

**Control Activities**:
- Obtain holdings from custodian
- Compare quantities for each CUSIP
- Verify market values reconcile
- Investigate and resolve discrepancies
- Document all position breaks
- Obtain approval for material discrepancies

**Evidence Retained**:
- Holdings reconciliation: `data/admin/holdings_reconciliation_YYYY-MM-DD.json`
- Exception log: Included in reconciliation file
- Resolution documentation: Included in reconciliation file

**Review Frequency**: Daily by Operations Manager

---

### 4. Cash Reconciliation Control
**Control Description**: Reconcile cash balances vs. custodian statements

**Frequency**: Daily (every business day)

**Who Performs**: Fund Administrator / Operations Team

**Control Activities**:
- Obtain cash balance from custodian
- Compare to internal cash records
- Verify all cash movements accounted for
- Investigate and resolve discrepancies
- Document reconciliation results

**Evidence Retained**:
- Cash reconciliation: `data/admin/holdings_reconciliation_YYYY-MM-DD.json`
- Custodian statements: Retained per books & records policy

**Review Frequency**: Daily by Operations Manager

---

### 5. Corporate Actions Control
**Control Description**: Process and reconcile all corporate actions

**Frequency**: Daily (as corporate actions occur)

**Who Performs**: Fund Administrator / Operations Team

**Control Activities**:
- Obtain corporate actions data
- Verify corporate actions processed correctly
- Update holdings for splits
- Record dividend income
- Adjust positions for mergers/spinoffs
- Reconcile corporate actions with custodian

**Evidence Retained**:
- Corporate actions log: `data/admin/corporate_actions_YYYY-MM-DD.json`
- Security master updates: `data/supporting/security_master.json`

**Review Frequency**: Daily by Operations Manager

---

### 6. Accounting Entries Control
**Control Description**: Record all accounting entries with double-entry validation

**Frequency**: Daily (every business day)

**Who Performs**: Fund Administrator / Accounting Team

**Control Activities**:
- Record NAV entries (assets, liabilities, net assets)
- Record expense accruals
- Record income
- Verify all entries balance (debits = credits)
- Generate trial balance
- Verify trial balance balances

**Evidence Retained**:
- Journal entries: `data/accounting/journal_entries.json`
- Trial balance: `data/accounting/trial_balance_YYYY-MM-DD.json`
- General ledger: `data/accounting/general_ledger.json`

**Review Frequency**: Daily by Accounting Manager

---

### 7. Transfer Agent Reconciliation Control
**Control Description**: Reconcile TA records vs. Custodian vs. DTC

**Frequency**: Daily (every business day)

**Who Performs**: Transfer Agent / Operations Team

**Control Activities**:
- Reconcile TA vs. Custodian (total shares)
- Reconcile TA vs. DTC (Cede position)
- Update Cede file from DTC
- Process creation/redemption orders
- Verify orders processed correctly

**Evidence Retained**:
- TA reconciliation: `data/ta/reconciliation_YYYY-MM-DD.json`
- Cede file: `data/ta/cede_file_YYYY-MM-DD.json`
- Shareholder registry: `data/ta/shareholder_registry.json`

**Review Frequency**: Daily by Operations Manager

---

### 8. PCF Publication Control
**Control Description**: Generate and publish PCF to NSCC

**Frequency**: Daily (every business day, by 8:00 AM ET)

**Who Performs**: Order Management Team (or US Bank if outsourced)

**Control Activities**:
- Generate PCF with current portfolio
- Validate PCF composition
- Verify pricing correct
- Publish to NSCC by deadline
- Verify publication confirmation

**Evidence Retained**:
- PCF file: `data/om/pcf_YYYY-MM-DD.json`
- NSCC publication confirmation: `data/om/pcf_nscc_YYYY-MM-DD.txt`

**Review Frequency**: Daily by Operations Manager

---

## Weekly Controls

### 9. Performance Calculation Control
**Control Description**: Calculate and validate performance metrics

**Frequency**: Weekly (typically Friday)

**Who Performs**: Performance Team / Operations Team

**Control Activities**:
- Calculate total returns (pre-tax and after-tax)
- Compare to benchmark
- Verify calculations correct
- Review for reasonableness
- Generate performance reports

**Evidence Retained**:
- Performance data: `data/performance/performance_YYYY-MM-DD_YYYY-MM-DD.json`
- Performance reports: `data/performance/reports/`

**Review Frequency**: Weekly by Performance Manager

---

### 10. Security Master Updates Control
**Control Description**: Update security master file with new securities

**Frequency**: Weekly (or as needed)

**Who Performs**: Operations Team

**Control Activities**:
- Add new securities to master file
- Update security details
- Validate CUSIPs
- Verify pricing sources
- Update security status

**Evidence Retained**:
- Security master file: `data/supporting/security_master.json`
- Update logs: Included in security master file

**Review Frequency**: Weekly by Operations Manager

---

## Monthly Controls

### 11. Accrual True-Up Control
**Control Description**: True-up all expense accruals to actual amounts

**Frequency**: Monthly (within 5 business days of month end)

**Who Performs**: Accounting Team

**Control Activities**:
- Review all accruals
- Compare accrued vs. actual amounts
- Calculate true-up adjustments
- Record true-up journal entries
- Verify true-ups balance
- Document all adjustments

**Evidence Retained**:
- Accrual true-up journal entries: `data/accounting/journal_entries.json`
- Accrual reconciliation: `data/accounting/accrual_reconciliation_YYYY-MM.json`
- Supporting invoices: Retained per books & records policy

**Review Frequency**: Monthly by Accounting Manager

---

### 12. Expense Allocation Control
**Control Description**: Allocate all expenses to appropriate accounts

**Frequency**: Monthly (within 5 business days of month end)

**Who Performs**: Accounting Team

**Control Activities**:
- Identify all expenses
- Allocate to appropriate accounts
- Verify allocation methodology
- Check expense ratios
- Document allocations

**Evidence Retained**:
- Expense allocation journal entries: `data/accounting/journal_entries.json`
- Expense allocation report: `data/accounting/expense_allocation_YYYY-MM.json`
- Supporting invoices: Retained per books & records policy

**Review Frequency**: Monthly by Accounting Manager

---

### 13. Trial Balance Tie-Out Control
**Control Description**: Generate and tie-out trial balance to supporting records

**Frequency**: Monthly (within 5 business days of month end)

**Who Performs**: Accounting Team

**Control Activities**:
- Generate trial balance
- Verify debits = credits
- Tie-out to supporting records
- Reconcile to financial statements
- Document tie-outs
- Obtain approval

**Evidence Retained**:
- Trial balance: `data/accounting/trial_balance_YYYY-MM-DD.json`
- Tie-out documentation: `data/accounting/tie_out_YYYY-MM.json`
- Supporting records: Retained per books & records policy

**Review Frequency**: Monthly by Accounting Manager

---

### 14. Financial Statement Generation Control
**Control Description**: Generate and review monthly financial statements

**Frequency**: Monthly (within 5 business days of month end)

**Who Performs**: Accounting Team

**Control Activities**:
- Generate balance sheet
- Generate income statement
- Review for accuracy
- Verify calculations
- Obtain approval

**Evidence Retained**:
- Balance sheet: `data/accounting/balance_sheet_YYYY-MM-DD.json`
- Income statement: `data/accounting/income_statement_YYYY-MM-DD_YYYY-MM-DD.json`
- Approval documentation: Included in audit trail

**Review Frequency**: Monthly by Accounting Manager and CFO

---

### 15. SEC Form N-PORT Filing Control
**Control Description**: Generate and file Form N-PORT with SEC

**Frequency**: Monthly (within 30 days of month end)

**Who Performs**: Compliance Team

**Control Activities**:
- Generate N-PORT data
- Validate against SEC schema
- Prepare XML file
- File with SEC via EDGAR
- Verify filing successful
- Retain confirmation

**Evidence Retained**:
- N-PORT XML file: `data/compliance/n_port_YYYY-MM-DD.xml`
- SEC filing confirmation: `data/compliance/n_port_filing_YYYY-MM-DD.json`
- N-PORT data: `data/compliance/n_port_YYYY-MM-DD.json`

**Review Frequency**: Monthly by Compliance Manager

---

## Quarterly Controls

### 16. Distribution Processing Control
**Control Description**: Calculate, declare, and process distributions

**Frequency**: Quarterly (if distributions due)

**Who Performs**: Distributor Team / Operations Team

**Control Activities**:
- Calculate distribution amount
- Verify distribution type
- Declare distribution
- Notify exchanges
- Process distribution payments
- Reconcile payments

**Evidence Retained**:
- Distribution calculations: `data/distributor/distributions.json`
- Distribution declarations: `data/distributor/distribution_notice_*.json`
- Distribution payments: `data/distributor/payment_*.json`

**Review Frequency**: Quarterly by Operations Manager

---

## Annual Controls

### 17. Tax Reporting Control
**Control Description**: Generate and file all tax forms

**Frequency**: Annual (by tax deadlines)

**Who Performs**: Tax Team / Accounting Team

**Control Activities**:
- Generate Form 1099-DIV
- Generate Form 1099-B
- Generate Form 1120-RIC
- Generate Form 8613
- File with IRS
- Verify filing successful

**Evidence Retained**:
- Tax forms: `data/tax/form_*.json`
- IRS filing confirmations: `data/tax/filing_confirmations/`

**Review Frequency**: Annual by Tax Manager

---

### 18. SEC Form N-CEN Filing Control
**Control Description**: Generate and file Form N-CEN with SEC

**Frequency**: Annual (within 75 days of fiscal year end)

**Who Performs**: Compliance Team

**Control Activities**:
- Generate N-CEN data
- Validate against SEC requirements
- File with SEC via EDGAR
- Verify filing successful
- Retain confirmation

**Evidence Retained**:
- N-CEN data: `data/compliance/n_cen_YYYY.json`
- SEC filing confirmation: `data/compliance/n_cen_filing_YYYY.json`

**Review Frequency**: Annual by Compliance Manager

---

### 19. SEC Form N-CSR Filing Control
**Control Description**: Generate and file Form N-CSR with SEC

**Frequency**: Semi-annual (within 60 days of period end)

**Who Performs**: Compliance Team

**Control Activities**:
- Generate N-CSR data
- Include financial statements
- Include performance data
- File with SEC via EDGAR
- Verify filing successful
- Retain confirmation

**Evidence Retained**:
- N-CSR data: `data/compliance/n_csr_YYYY-MM-DD.json`
- SEC filing confirmation: `data/compliance/n_csr_filing_YYYY-MM-DD.json`

**Review Frequency**: Semi-annual by Compliance Manager

---

### 20. Audit Trail Control
**Control Description**: Maintain complete audit trail of all operations

**Frequency**: Continuous (for all operations)

**Who Performs**: All Teams (automated)

**Control Activities**:
- Log all NAV calculations
- Log all journal entries
- Log all reconciliations
- Log all corporate actions
- Verify audit trail complete
- Export audit packages as needed

**Evidence Retained**:
- Audit records: `data/audit_trail/audit_records.json`
- Individual audit files: `data/audit_trail/*_YYYY-MM-DD_*.json`
- Audit packages: `data/audit_trail/audit_package_*.json`

**Review Frequency**: Continuous by Operations Manager, Annual by Auditors

---

## Control Testing

### Testing Frequency
- **Daily Controls**: Tested daily through execution
- **Weekly Controls**: Tested weekly through execution
- **Monthly Controls**: Tested monthly through execution
- **Quarterly Controls**: Tested quarterly through execution
- **Annual Controls**: Tested annually through execution

### Testing Procedures
- Execute control activities
- Verify evidence retained
- Review control effectiveness
- Document test results
- Remediate any deficiencies

### Testing Documentation
- Test results: `data/compliance/control_tests/`
- Test reports: `data/compliance/control_test_reports/`

---

## Control Owner

**Overall Responsibility**: Chief Compliance Officer

**Daily Operations**: Operations Manager

**Accounting**: Accounting Manager

**Compliance**: Compliance Manager

**Tax**: Tax Manager

---

## Notes
- All controls must be performed as specified
- All evidence must be retained per books & records policy
- All exceptions must be documented and resolved
- Control testing must be performed regularly
- Control deficiencies must be remediated promptly

