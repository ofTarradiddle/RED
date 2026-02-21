# Monthly Close Checklist

## Overview
This checklist ensures all monthly close operations are completed accurately and within regulatory deadlines. Complete each item in order and verify completion before proceeding.

**Target Completion**: Within 5 business days of month end

---

## Month-End Operations (Within 5 Business Days)

### 1. Accrual True-Ups
- [ ] **Review All Accruals**
  - Management fee accruals
  - Administration fee accruals
  - Other operating expense accruals
  - Interest expense accruals
  
- [ ] **Verify Accrual Calculations**
  - Check daily accrual rates correct
  - Verify number of days accrued
  - Confirm base amounts correct (AUM, expense bases)
  - Recalculate accruals for accuracy
  
- [ ] **True-Up Accruals**
  - Compare accrued amounts vs. actual invoices
  - Adjust for any differences
  - Record true-up journal entries
  - Verify true-ups balance
  
- [ ] **Document Accrual True-Ups**
  - Document all adjustments made
  - Explain reason for each adjustment
  - Obtain approval for material adjustments
  - Retain supporting documentation

**Evidence Retained**:
- Accrual true-up journal entries: `data/accounting/journal_entries.json`
- Accrual reconciliation: `data/accounting/accrual_reconciliation_YYYY-MM.json`
- Supporting invoices: Retained per books & records policy

---

### 2. Expense Allocations
- [ ] **Identify All Expenses**
  - Management fees
  - Administration fees
  - Custodian fees
  - Transfer agent fees
  - Legal and audit fees
  - Other operating expenses
  
- [ ] **Allocate Expenses**
  - Allocate to appropriate expense accounts
  - Verify expense categories correct
  - Check expense allocation percentages (if multiple share classes)
  - Confirm expense caps/waivers applied correctly
  
- [ ] **Verify Expense Allocations**
  - Reconcile allocated expenses vs. total expenses
  - Verify no double-counting
  - Check expense ratios calculated correctly
  - Confirm expense allocations match budget
  
- [ ] **Document Expense Allocations**
  - Document allocation methodology
  - List all expenses allocated
  - Show allocation calculations
  - Retain supporting documentation

**Evidence Retained**:
- Expense allocation journal entries: `data/accounting/journal_entries.json`
- Expense allocation report: `data/accounting/expense_allocation_YYYY-MM.json`
- Supporting invoices: Retained per books & records policy

---

### 3. Trial Balance Tie-Outs
- [ ] **Generate Trial Balance**
  - Run `Accounting.generate_trial_balance()`
  - Verify trial balance date correct (month end)
  - Check all accounts included
  - Verify account balances current
  
- [ ] **Verify Trial Balance Balances**
  - Confirm total debits = total credits
  - Check for unbalanced accounts
  - Verify account balances reasonable
  - Review for unusual balances
  
- [ ] **Tie-Out to Supporting Records**
  - Tie cash to bank statements
  - Tie investments to custodian statements
  - Tie receivables to supporting documentation
  - Tie payables to invoices
  - Tie expenses to expense reports
  - Tie income to income records
  
- [ ] **Reconcile Trial Balance to Financial Statements**
  - Tie trial balance to balance sheet
  - Tie trial balance to income statement
  - Verify net assets match NAV calculation
  - Confirm all accounts properly classified
  
- [ ] **Document Tie-Outs**
  - Document all tie-out procedures
  - List any exceptions found
  - Document resolution of exceptions
  - Obtain approval for tie-outs

**Evidence Retained**:
- Trial balance: `data/accounting/trial_balance_YYYY-MM-DD.json`
- Tie-out documentation: `data/accounting/tie_out_YYYY-MM.json`
- Supporting records: Retained per books & records policy

---

### 4. Financial Statement Generation
- [ ] **Generate Balance Sheet**
  - Run `Accounting.generate_balance_sheet()`
  - Verify balance sheet date correct (month end)
  - Check all assets included
  - Check all liabilities included
  - Verify net assets calculated correctly
  
- [ ] **Generate Income Statement**
  - Run `Accounting.generate_income_statement()`
  - Verify period correct (month)
  - Check all income included
  - Check all expenses included
  - Verify net investment income calculated correctly
  
- [ ] **Review Financial Statements**
  - Review for reasonableness
  - Check for unusual items
  - Verify calculations correct
  - Confirm formatting correct
  
- [ ] **Approve Financial Statements**
  - Review with fund administrator
  - Obtain approval from authorized personnel
  - Document approval
  - Retain approved statements

**Evidence Retained**:
- Balance sheet: `data/accounting/balance_sheet_YYYY-MM-DD.json`
- Income statement: `data/accounting/income_statement_YYYY-MM-DD_YYYY-MM-DD.json`
- Approval documentation: Included in audit trail

---

### 5. SEC Form N-PORT Filing
- [ ] **Generate N-PORT Data**
  - Run `Compliance.generate_form_n_port()`
  - Collect portfolio holdings as of month end
  - Calculate risk metrics (duration, credit quality, etc.)
  - Verify all required data included
  
- [ ] **Validate N-PORT Data**
  - Validate against SEC schema
  - Check for missing required fields
  - Verify data accuracy
  - Review for errors
  
- [ ] **Prepare N-PORT XML**
  - Format data per SEC requirements
  - Generate XML file
  - Validate XML structure
  - Test XML parsing
  
- [ ] **File N-PORT with SEC**
  - Submit via SEC EDGAR system
  - Verify submission successful
  - Obtain confirmation number
  - Retain confirmation
  
- [ ] **Deadline**: 30 days after month end

**Evidence Retained**:
- N-PORT XML file: `data/compliance/n_port_YYYY-MM-DD.xml`
- SEC filing confirmation: `data/compliance/n_port_filing_YYYY-MM-DD.json`
- N-PORT data: `data/compliance/n_port_YYYY-MM-DD.json`

---

### 6. Performance Reporting
- [ ] **Calculate Monthly Performance**
  - Calculate total return for month
  - Calculate year-to-date return
  - Compare to benchmark
  - Calculate after-tax returns (if applicable)
  
- [ ] **Generate Performance Reports**
  - Create performance summary
  - Include attribution analysis
  - Include risk metrics
  - Format for distribution
  
- [ ] **Review Performance Reports**
  - Review for accuracy
  - Check calculations
  - Verify benchmark comparison
  - Confirm formatting correct

**Evidence Retained**:
- Performance data: `data/performance/performance_YYYY-MM-DD_YYYY-MM-DD.json`
- Performance reports: `data/performance/reports/`

---

### 7. Distribution Processing (If Applicable)
- [ ] **Check Distribution Schedule**
  - Review distribution calendar
  - Identify if distribution due this month
  - Verify distribution type (dividend, capital gain, ROC)
  
- [ ] **Calculate Distribution** (if due)
  - Run `Distributor.calculate_distribution()`
  - Verify distribution amount correct
  - Check payout ratio
  - Confirm distribution type
  
- [ ] **Declare Distribution** (if due)
  - Declare distribution amount
  - Set ex-date, record date, pay date
  - Notify exchanges
  - Publish distribution notice
  
- [ ] **Process Distribution Payment** (if pay date in month)
  - Process distribution payments
  - Verify payments processed correctly
  - Reconcile distribution payments
  - Document payment processing

**Evidence Retained**:
- Distribution calculations: `data/distributor/distributions.json`
- Distribution declarations: `data/distributor/distribution_notice_*.json`
- Distribution payments: `data/distributor/payment_*.json`

---

### 8. Tax Lot Updates
- [ ] **Update Tax Lots**
  - Process all purchases during month
  - Process all sales during month
  - Update holding periods
  - Calculate realized gains/losses
  
- [ ] **Reconcile Tax Lots**
  - Verify tax lots match custodian records
  - Check for missing lots
  - Verify cost basis correct
  - Confirm holding periods accurate

**Evidence Retained**:
- Tax lot records: `data/tax_lots/tax_lots.json`
- Tax lot reconciliation: `data/tax_lots/reconciliation_YYYY-MM.json`

---

### 9. Compliance Review
- [ ] **Review Compliance Status**
  - Check for any compliance violations
  - Review concentration limits
  - Verify diversification requirements
  - Check liquidity requirements
  
- [ ] **Document Compliance**
  - Document compliance status
  - List any exceptions
  - Document resolution of exceptions
  - Retain compliance reports

**Evidence Retained**:
- Compliance reports: `data/compliance/compliance_reports_YYYY-MM.json`
- Exception logs: Included in compliance reports

---

### 10. Audit Trail Review
- [ ] **Verify Audit Trail Complete**
  - Check all operations logged
  - Verify audit records complete
  - Confirm audit trail accessible
  - Test audit trail export
  
- [ ] **Review Audit Trail**
  - Review for completeness
  - Check for missing records
  - Verify data integrity
  - Document any issues

**Evidence Retained**:
- Audit trail review: `data/audit_trail/review_YYYY-MM.json`
- Audit records: `data/audit_trail/audit_records.json`

---

## Month-End Sign-Off

### 11. Final Review and Sign-Off
- [ ] **Complete All Items Above**
  - Verify all checkboxes completed
  - Review any exceptions or issues
  - Document any unresolved items
  
- [ ] **Review Month-End Package**
  - Financial statements
  - Trial balance
  - Accrual reconciliations
  - Expense allocations
  - Compliance reports
  
- [ ] **Obtain Sign-Off**
  - Review with fund administrator
  - Obtain approval from authorized personnel
  - Document sign-off
  - Retain signed documentation

**Evidence Retained**:
- Month-end package: Compiled in `data/month_end/YYYY-MM/`
- Sign-off documentation: Included in audit trail

---

## Regulatory Deadlines

| Item | Deadline | Regulation |
|------|----------|------------|
| Form N-PORT | 30 days after month end | SEC Rule 30b1-9 |
| Financial Statements | 5 business days after month end | Internal policy |
| Trial Balance | 5 business days after month end | Internal policy |

---

## Escalation Procedures

### Material Issues Requiring Escalation:
- Trial balance doesn't balance
- Financial statement errors
- N-PORT filing errors
- Accrual true-ups > $10,000
- Expense allocation errors
- Compliance violations

**Escalation Contact**: Fund Administrator, Chief Compliance Officer, or Board of Directors

---

## Notes
- All deadlines are business days
- All operations should be completed within 5 business days of month end
- Any exceptions should be documented and resolved before sign-off
- All evidence should be retained per books & records policy

