# Daily Operations Checklist

## Overview
This checklist ensures all daily ETF operations are completed accurately and on time. Complete each item in order and verify completion before proceeding.

**Target Completion Time**: All items should be completed by 6:00 PM ET on the business day.

---

## Pre-Market Operations (Before 8:00 AM ET)

### 1. PCF Publication
- [ ] **Generate PCF** (`OrderManagement.generate_pcf()`)
  - Location: `lib/etf/functions/operations/order_management.py`
  - Verify all securities included
  - Verify creation unit size correct
  - Verify total estimated value calculated correctly
  
- [ ] **Publish PCF to NSCC** (if self-administering)
  - Format: NSCC PCF format (fixed-width text file)
  - Deadline: 8:00 AM ET
  - **Note**: US Bank handles this if using US Bank for order management
  - Verify publication confirmation received
  
- [ ] **Validate PCF** 
  - Check for pricing exceptions
  - Verify basket composition matches portfolio
  - Confirm no missing securities

**Evidence Retained**: 
- PCF file: `data/om/pcf_YYYY-MM-DD.json`
- NSCC publication confirmation (if applicable)

---

## Market Hours Operations (During Trading Day)

### 2. AP Order Processing
- [ ] **Monitor AP Orders** (if self-administering)
  - Check for creation/redemption orders submitted
  - Validate order cut-off time (4:00 PM ET)
  - Verify AP authorization
  - **Note**: US Bank handles this if using US Bank for order management

- [ ] **Process Valid Orders**
  - Validate basket composition
  - Check Rule 6c-11 compliance (for custom baskets)
  - Calculate creation/redemption fees
  - Route to custodian for settlement

**Evidence Retained**:
- Order records: `data/om/orders/`
- Validation results: `data/compliance/rule_6c11/`

---

## Post-Market Operations (After 4:00 PM ET)

### 3. Price Checks
- [ ] **Obtain Market Prices**
  - Source: Market data provider (Bloomberg, Refinitiv, or yfinance for testing)
  - Verify all CUSIPs have prices
  - Check for stale prices (missing or zero)
  
- [ ] **Price Validation**
  - Compare current prices vs. previous day
  - Flag price changes > 5% (configurable tolerance)
  - Verify prices match custodian pricing
  - Check for corporate action impacts on pricing
  
- [ ] **Fair Valuation Review** (if needed)
  - Identify securities requiring fair valuation
  - Apply fair valuation methodology
  - Document reason for fair valuation
  - Obtain approval if required

**Evidence Retained**:
- Price validation report: Included in NAV calculation file
- Fair valuation records: `data/fair_valuation/fair_valuation_YYYY-MM-DD.json`
- Pricing exceptions log: `data/admin/nav_YYYY-MM-DD.json`

---

### 4. Corporate Actions
- [ ] **Obtain Corporate Actions Data**
  - Source: Custodian or corporate actions data provider
  - Check for dividends, splits, mergers, spinoffs
  - Verify ex-dates and pay dates
  
- [ ] **Process Corporate Actions**
  - Update holdings for splits
  - Record dividend income
  - Adjust positions for mergers/spinoffs
  - Update security master file
  
- [ ] **Reconcile Corporate Actions**
  - Verify custodian processed correctly
  - Check cash movements match expected
  - Confirm position adjustments accurate

**Evidence Retained**:
- Corporate actions log: `data/admin/corporate_actions_YYYY-MM-DD.json`
- Security master updates: `data/supporting/security_master.json`

---

### 5. Cash Movements
- [ ] **Obtain Cash Balances**
  - Source: Custodian statements
  - Verify cash balance matches expected
  - Check for pending transactions
  
- [ ] **Reconcile Cash**
  - Compare custodian cash vs. internal records
  - Verify all cash movements accounted for
  - Check for unrecorded transactions
  - Resolve any discrepancies
  
- [ ] **Cash Reconciliation Report**
  - Document starting balance
  - Document all cash movements (income, expenses, trades)
  - Document ending balance
  - Verify ending balance matches custodian

**Evidence Retained**:
- Cash reconciliation: `data/admin/holdings_reconciliation_YYYY-MM-DD.json`
- Custodian statements: Retained per books & records policy

---

### 6. Position Breaks (Holdings Reconciliation)
- [ ] **Obtain Holdings from Custodian**
  - Source: Custodian daily holdings file
  - Verify file received and parsed correctly
  - Check for missing securities
  
- [ ] **Compare Holdings**
  - Compare internal portfolio vs. custodian holdings
  - Verify quantities match for each CUSIP
  - Check for missing or extra positions
  - Verify market values reconcile
  
- [ ] **Investigate Discrepancies**
  - Document all position breaks
  - Identify root cause (timing, corporate actions, trades)
  - Resolve or escalate as needed
  - Document resolution
  
- [ ] **Holdings Reconciliation Report**
  - Generate reconciliation report
  - List all exceptions
  - Document resolution status
  - Obtain approval if material discrepancies

**Evidence Retained**:
- Holdings reconciliation: `data/admin/holdings_reconciliation_YYYY-MM-DD.json`
- Exception log: Included in reconciliation file
- Resolution documentation: Included in reconciliation file

---

### 7. NAV Calculation
- [ ] **Calculate NAV**
  - Run `FundAdministration.calculate_nav()`
  - Verify all inputs correct (holdings, prices, cash, accruals)
  - Check for pricing exceptions
  - Verify shares outstanding correct
  
- [ ] **NAV Validation**
  - Compare NAV vs. previous day (check for unusual changes)
  - Verify NAV calculation formula correct
  - Check for rounding errors
  - Validate against shadow NAV (if implemented)
  
- [ ] **NAV Review**
  - Review pricing exceptions
  - Review corporate action impacts
  - Review expense accruals
  - Obtain approval if material exceptions
  
- [ ] **Publish NAV**
  - Submit NAV to market data vendors
  - Verify publication confirmation
  - Update NAV history

**Evidence Retained**:
- NAV calculation: `data/admin/nav_YYYY-MM-DD.json`
- NAV validation report: Included in NAV file
- Shadow NAV reconciliation: `data/shadow_accounting/nav_reconciliation_YYYY-MM-DD.json` (if applicable)

---

### 8. Accounting Entries
- [ ] **Record NAV Entries**
  - Record assets, liabilities, net assets
  - Update general ledger
  - Verify entries balance
  
- [ ] **Record Expense Accruals**
  - Accrue daily management fees
  - Accrue daily admin fees
  - Accrue other operating expenses
  - Verify accrual calculations correct
  
- [ ] **Record Income**
  - Record dividend income received
  - Record interest income
  - Record other income
  - Verify income recognition correct
  
- [ ] **Generate Trial Balance**
  - Run `Accounting.generate_trial_balance()`
  - Verify debits = credits
  - Check for unbalanced accounts
  - Resolve any imbalances

**Evidence Retained**:
- Journal entries: `data/accounting/journal_entries.json`
- Trial balance: `data/accounting/trial_balance_YYYY-MM-DD.json`
- General ledger: `data/accounting/general_ledger.json`

---

### 9. Transfer Agent Reconciliation
- [ ] **TA vs. Custodian Reconciliation**
  - Compare TA shareholder records vs. custodian
  - Verify total shares match
  - Check for account discrepancies
  - Resolve any differences
  
- [ ] **TA vs. DTC Reconciliation**
  - Compare TA street-name shares vs. DTC Cede position
  - Verify Cede position matches street-name accounts
  - Check for timing differences
  - Resolve any discrepancies
  
- [ ] **Update Cede File**
  - Update Cede & Co. position from DTC file
  - Verify Cede position correct
  - Document any adjustments
  
- [ ] **Process Creation/Redemption Orders**
  - Process creation orders (increase shares)
  - Process redemption orders (decrease shares)
  - Update shareholder registry
  - Verify orders processed correctly

**Evidence Retained**:
- TA reconciliation: `data/ta/reconciliation_YYYY-MM-DD.json`
- Cede file: `data/ta/cede_file_YYYY-MM-DD.json`
- Shareholder registry: `data/ta/shareholder_registry.json`

---

### 10. Audit Trail
- [ ] **Log All Operations**
  - Verify NAV calculation logged
  - Verify journal entries logged
  - Verify reconciliations logged
  - Verify corporate actions logged
  
- [ ] **Verify Audit Trail Complete**
  - Check all operations have audit records
  - Verify audit records have complete data
  - Confirm audit trail accessible
  - Test audit trail export

**Evidence Retained**:
- Audit records: `data/audit_trail/audit_records.json`
- Individual audit files: `data/audit_trail/*_YYYY-MM-DD_*.json`

---

## End-of-Day Verification

### 11. Final Checks
- [ ] **Complete All Items Above**
  - Verify all checkboxes completed
  - Review any exceptions or issues
  - Document any unresolved items
  
- [ ] **Data Backup**
  - Verify all data files saved
  - Confirm backup completed
  - Test data recovery if applicable
  
- [ ] **Sign-Off**
  - Review daily operations summary
  - Sign off on NAV calculation
  - Sign off on reconciliations
  - Document any issues for follow-up

**Evidence Retained**:
- Daily operations summary: Generated by orchestrator
- Sign-off documentation: Included in audit trail

---

## Escalation Procedures

### Material Issues Requiring Escalation:
- NAV calculation errors > 0.01%
- Position breaks > $10,000
- Cash reconciliation differences > $1,000
- Missing prices for > 5% of portfolio
- Corporate actions not processed correctly
- TA reconciliation differences > 1,000 shares

**Escalation Contact**: Fund Administrator or Chief Compliance Officer

---

## Notes
- All times are Eastern Time (ET)
- All operations should be completed by 6:00 PM ET
- Any exceptions should be documented and resolved before end of day
- All evidence should be retained per books & records policy

