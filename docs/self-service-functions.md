# Self-Service Functions: Admin, TA, and OM

## Overview

This document outlines the responsibilities, costs, processes, and requirements for insourcing three critical ETF operational functions:
- **Self-Administration (Admin)**
- **Self-Transfer Agent (TA)** - Non-Paying Agent
- **Self-Order Management (OM)**

**Note:** Accounts Payable (AP) and Custody will continue to use vendors for now.

---

## 1. SELF-TRANSFER AGENT (TA) - NON-PAYING AGENT

### Overview
As a **non-paying transfer agent**, we maintain shareholder records and process transactions but do not handle dividend/distribution payments. A separate paying agent handles all cash distributions.

### Core Responsibilities

#### A. Shareholder Recordkeeping
1. **Maintain shareholder registry**
   - Track all beneficial and registered shareholders
   - Maintain accurate share balances by account
   - Record share classes and series
   - Track historical ownership changes

2. **Account Management**
   - Open new shareholder accounts
   - Process account updates (address changes, name changes, etc.)
   - Close accounts (redemptions, transfers out)
   - Maintain account documentation and KYC records

3. **Transaction Processing**
   - Process share purchases (creation orders)
   - Process share redemptions
   - Handle transfers between accounts
   - Process account maintenance requests

#### B. Daily Operations

1. **Daily Reconciliation**
   - **Input Sources:**
     - NSCC (National Securities Clearing Corporation) files
     - DTC (Depository Trust Company) position files
     - Custodian statements
     - AP (Authorized Participant) creation/redemption orders
     - Broker-dealer transaction files
   
   - **Process:**
     - Reconcile share balances between:
       - TA system vs. Custodian records
       - TA system vs. DTC positions
       - TA system vs. NSCC settlement files
     - Identify and resolve discrepancies
     - Generate reconciliation reports
   
   - **Real-Time Data Sources:**
     - **NSCC/DTC feeds**: Real-time settlement and position data
     - **Custodian portal**: Real-time custody account balances
     - **AP order system**: Real-time creation/redemption orders
     - **Broker feeds**: Real-time transaction data from market makers

2. **Cede & Co. File Updates**
   - **What is it**: The Cede & Co. file represents DTC's position as nominee holder for all street-name shares
   - **Update Process:**
     - Receive daily DTC position file (typically end-of-day)
     - Reconcile DTC position to our shareholder records
     - Update Cede & Co. account balance in TA system
     - Generate Cede file for regulatory reporting
   - **Frequency**: Daily (end-of-day processing)
   - **Data Source**: DTC position files via DTC's Participant Terminal System (PTS) or file transfer

3. **Shareholder Communications**
   - Generate and mail account statements
   - Process shareholder inquiries
   - Handle proxy materials distribution
   - Manage tax reporting (1099-DIV, 1099-B preparation)

#### C. Regulatory & Compliance

1. **SEC Reporting**
   - File Form N-CEN (annual)
   - File Form N-CSR (semi-annual)
   - Maintain books and records per SEC Rule 31a-2
   - Respond to SEC inquiries

2. **State Blue Sky Compliance**
   - Track state registrations
   - File required state reports
   - Maintain state exemption records

3. **Tax Reporting**
   - Prepare 1099-DIV forms (coordinate with paying agent for distribution amounts)
   - Prepare 1099-B forms for redemptions
   - File 1099s with IRS
   - Provide backup withholding services

4. **Anti-Money Laundering (AML)**
   - Screen shareholders against OFAC and other watchlists
   - Monitor for suspicious activity
   - File SARs (Suspicious Activity Reports) if needed
   - Maintain AML compliance program

#### D. Technology & Systems

1. **TA System Requirements**
   - Shareholder recordkeeping system
   - Transaction processing system
   - Reconciliation tools
   - Reporting and compliance modules
   - Integration with NSCC/DTC systems
   - Integration with custodian systems

2. **Data Integrations**
   - NSCC/DTC file feeds (automated)
   - Custodian data feeds
   - AP order system integration
   - Broker-dealer transaction feeds

### Startup Tasks (One-Time)

1. **System Setup**
   - Select and implement TA software system
   - Set up data integrations (NSCC, DTC, custodian)
   - Configure account structures and share classes
   - Establish reconciliation processes

2. **Regulatory Setup**
   - Register as transfer agent with SEC (Form TA-1)
   - Obtain state licenses as required
   - Establish AML compliance program
   - Set up tax reporting systems

3. **Process Development**
   - Document all TA procedures
   - Establish reconciliation workflows
   - Create reporting templates
   - Set up shareholder communication templates

4. **Staffing**
   - Hire/assign TA operations staff
   - Train staff on TA systems and processes
   - Establish backup coverage

5. **Testing**
   - Test all system integrations
   - Perform end-to-end transaction testing
   - Test reconciliation processes
   - Validate regulatory reporting

### Recurring Tasks

#### Daily
- Process creation/redemption orders
- Reconcile share balances (TA vs. Custodian vs. DTC)
- Update Cede & Co. file
- Process shareholder transactions
- Handle shareholder inquiries
- Monitor for exceptions and discrepancies

#### Weekly
- Generate shareholder activity reports
- Review reconciliation exceptions
- Process account maintenance requests
- Review AML screening results

#### Monthly
- Generate monthly shareholder statements
- Reconcile all accounts
- Review compliance metrics
- Update shareholder records

#### Quarterly
- File state reports (if required)
- Review and update AML procedures
- Generate quarterly shareholder reports

#### Annually
- File Form N-CEN
- File Form N-CSR
- Prepare and distribute tax forms (1099s)
- Annual compliance review
- Update state registrations

### Cost Analysis

#### One-Time Startup Costs
- **TA Software System**: $50,000 - $150,000 (license + implementation)
- **System Integration**: $25,000 - $75,000 (NSCC, DTC, custodian)
- **SEC Registration**: $500 - $2,000 (Form TA-1)
- **State Licenses**: $5,000 - $15,000 (varies by state)
- **Training & Setup**: $10,000 - $25,000
- **Total Startup**: $90,000 - $267,000

#### Annual Recurring Costs
- **TA Software License**: $30,000 - $80,000/year
- **NSCC/DTC Fees**: $15,000 - $40,000/year
  - NSCC membership: ~$5,000/year
  - DTC participant fees: ~$10,000/year
  - Transaction fees: variable
- **Staffing**: $150,000 - $300,000/year
  - 1-2 FTE TA operations staff
- **Compliance & Reporting**: $20,000 - $50,000/year
  - AML screening tools: $5,000 - $15,000/year
  - Tax reporting software: $5,000 - $10,000/year
  - Legal/compliance support: $10,000 - $25,000/year
- **Technology & Infrastructure**: $15,000 - $30,000/year
  - Servers/hosting
  - Backup systems
  - Security tools
- **Shareholder Communications**: $10,000 - $25,000/year
  - Statement printing/mailing
  - Postage
- **Total Annual**: $240,000 - $525,000/year

#### Cost Comparison: Non-Paying vs. Paying Agent

**Non-Paying Agent (Current Plan)**
- No dividend payment processing
- No cash management for distributions
- No bank account management for distributions
- Lower regulatory burden (no money transmitter licenses)
- **Estimated Annual Savings vs. Paying Agent**: $50,000 - $100,000/year

**Paying Agent (Additional Responsibilities)**
- Process dividend/distribution payments
- Maintain distribution bank accounts
- Handle escheatment (unclaimed property)
- Money transmitter licenses in all states
- Additional compliance and reporting
- **Additional Annual Cost**: $50,000 - $100,000/year

### Data Flow & Input/Output Process

#### Daily Inputs
1. **NSCC Files** (end-of-day)
   - Creation/redemption orders
   - Settlement confirmations
   - Share balance positions

2. **DTC Position Files** (end-of-day)
   - Cede & Co. position
   - Street-name share balances
   - Participant positions

3. **Custodian Statements** (real-time/end-of-day)
   - Fund share balances
   - Cash positions
   - Transaction history

4. **AP Orders** (real-time)
   - Creation baskets
   - Redemption requests
   - Order confirmations

5. **Broker-Dealer Feeds** (real-time)
   - Retail transactions
   - Account openings/closings
   - Account maintenance

#### Daily Outputs
1. **Reconciliation Reports**
   - TA vs. Custodian reconciliation
   - TA vs. DTC reconciliation
   - Exception reports

2. **Updated Cede File**
   - Current DTC position
   - Share balance by participant

3. **Transaction Confirmations**
   - Creation confirmations to APs
   - Redemption confirmations to APs
   - Account update confirmations

4. **Regulatory Reports** (as needed)
   - SEC filings
   - State reports
   - AML reports

---

## 2. SELF-ADMINISTRATION (ADMIN)

### Overview
Fund administration encompasses NAV calculation, financial reporting, regulatory compliance, and overall fund operations management.

### Core Responsibilities

#### A. NAV Calculation & Pricing

1. **Daily NAV Calculation**
   - **Input Sources:**
     - Custodian holdings and pricing data
     - Market data feeds (Bloomberg, Refinitiv, etc.)
     - Corporate actions data
     - Foreign exchange rates (if applicable)
     - Accrued income/expenses
   
   - **Process:**
     - Calculate fund assets (holdings × prices)
     - Calculate fund liabilities
     - Calculate accrued income
     - Calculate accrued expenses
     - Calculate net assets
     - Calculate NAV per share
     - Validate pricing (price tolerance checks)
     - Publish NAV to market data vendors

2. **Pricing Sources**
   - **Real-Time Data:**
     - Market data vendors (Bloomberg, Refinitiv): Real-time pricing
     - Custodian pricing feeds: End-of-day pricing
     - Exchange data: Real-time last sale prices
   - **Corporate Actions:**
     - DTCC Corporate Actions: Real-time corporate action notifications
     - Custodian corporate actions feed
   - **Foreign Exchange:**
     - FX data vendors: Real-time FX rates
     - Federal Reserve: End-of-day FX rates

3. **NAV Validation**
   - Price tolerance checks (vs. previous day, vs. index)
   - Holdings reconciliation
   - Cash reconciliation
   - Expense accrual validation

#### B. Financial Reporting

1. **Daily Reports**
   - NAV calculation worksheet
   - Holdings report
   - Performance reports
   - Cash position reports

2. **Monthly Reports**
   - Monthly performance reports
   - Holdings reports
   - Expense ratio calculations
   - Portfolio turnover calculations

3. **Quarterly Reports**
   - Form N-Q (quarterly holdings)
   - Financial statements
   - Management discussion and analysis

4. **Annual Reports**
   - Form N-CSR (annual report)
   - Form N-CEN (annual census)
   - Audited financial statements
   - Tax reporting

#### C. Regulatory Compliance

1. **SEC Filings**
   - Form N-CEN (annual)
   - Form N-CSR (semi-annual)
   - Form N-Q (quarterly holdings)
   - Form N-PORT (monthly portfolio holdings)
   - Form N-MFP (monthly flow)
   - Form 8-K (material events)
   - Proxy statements (as needed)

2. **Tax Compliance**
   - Calculate and report tax distributions
   - Prepare tax returns (Form 1120-RIC)
   - Coordinate with tax advisors
   - Maintain tax records

3. **Blue Sky Compliance**
   - Track state registrations
   - File state reports
   - Maintain exemption records

#### D. Operations Management

1. **Expense Management**
   - Calculate and accrue expenses daily
   - Process expense payments
   - Monitor expense ratios
   - Budget and forecast expenses

2. **Cash Management**
   - Monitor fund cash positions
   - Coordinate with custodian on cash movements
   - Manage creation/redemption cash flows
   - Optimize cash balances

3. **Vendor Management**
   - Manage relationships with service providers
   - Monitor vendor performance
   - Process vendor invoices
   - Negotiate vendor contracts

### Startup Tasks (One-Time)

1. **System Setup**
   - Select and implement NAV calculation system
   - Set up market data feeds
   - Configure pricing sources
   - Establish reconciliation processes

2. **Regulatory Setup**
   - Register with SEC (if not already done)
   - Establish compliance procedures
   - Set up filing systems
   - Create reporting templates

3. **Process Development**
   - Document NAV calculation procedures
   - Establish reporting workflows
   - Create compliance checklists
   - Set up expense management processes

4. **Staffing**
   - Hire/assign fund administration staff
   - Train staff on systems and processes
   - Establish backup coverage

5. **Testing**
   - Test NAV calculation system
   - Test all data integrations
   - Perform end-to-end reporting testing
   - Validate regulatory filings

### Recurring Tasks

#### Daily
- Calculate NAV
- Reconcile holdings and cash
- Validate pricing
- Publish NAV
- Monitor cash positions
- Process corporate actions

#### Weekly
- Review expense accruals
- Monitor expense ratios
- Review performance metrics
- Process vendor invoices

#### Monthly
- File Form N-PORT
- File Form N-MFP
- Generate monthly reports
- Reconcile all accounts
- Review compliance metrics

#### Quarterly
- File Form N-Q
- Prepare quarterly financial statements
- Review and update expense budgets
- Quarterly compliance review

#### Annually
- File Form N-CEN
- File Form N-CSR
- Prepare annual financial statements
- Coordinate annual audit
- File tax returns
- Annual compliance review

### Cost Analysis

#### One-Time Startup Costs
- **NAV Calculation System**: $75,000 - $200,000 (license + implementation)
- **Market Data Feeds**: $10,000 - $25,000 (setup)
  - Bloomberg Terminal: ~$2,000/month
  - Refinitiv: ~$1,500/month
  - Other data vendors: variable
- **System Integration**: $25,000 - $75,000 (custodian, data vendors)
- **Regulatory Setup**: $5,000 - $15,000
- **Training & Setup**: $15,000 - $30,000
- **Total Startup**: $130,000 - $345,000

#### Annual Recurring Costs
- **NAV Calculation System License**: $40,000 - $100,000/year
- **Market Data Feeds**: $50,000 - $120,000/year
  - Bloomberg: ~$24,000/year
  - Refinitiv: ~$18,000/year
  - Other vendors: variable
- **Staffing**: $200,000 - $400,000/year
  - 2-3 FTE fund administration staff
- **Compliance & Reporting**: $30,000 - $75,000/year
  - SEC filing software: $10,000 - $25,000/year
  - Legal/compliance support: $20,000 - $50,000/year
- **Technology & Infrastructure**: $20,000 - $40,000/year
  - Servers/hosting
  - Backup systems
  - Security tools
- **Audit & Tax Services**: $50,000 - $150,000/year
  - Annual audit: $40,000 - $100,000
  - Tax preparation: $10,000 - $50,000
- **Total Annual**: $390,000 - $885,000/year

### Data Flow & Input/Output Process

#### Daily Inputs
1. **Custodian Data** (end-of-day)
   - Holdings positions
   - Cash balances
   - Transaction history
   - Corporate actions

2. **Market Data Feeds** (real-time/end-of-day)
   - Security prices
   - Exchange rates
   - Index values
   - Corporate actions

3. **Expense Data** (as needed)
   - Vendor invoices
   - Management fees
   - Other expenses

#### Daily Outputs
1. **NAV Calculation**
   - NAV per share
   - Total net assets
   - Share count

2. **NAV Distribution**
   - Market data vendors (Bloomberg, Refinitiv)
   - Fund website
   - Regulatory filings

3. **Reconciliation Reports**
   - Holdings reconciliation
   - Cash reconciliation
   - Pricing validation reports

#### Monthly/Quarterly/Annual Outputs
1. **Regulatory Filings**
   - Form N-PORT (monthly)
   - Form N-MFP (monthly)
   - Form N-Q (quarterly)
   - Form N-CEN (annual)
   - Form N-CSR (semi-annual)

2. **Financial Reports**
   - Monthly performance reports
   - Quarterly financial statements
   - Annual audited financials

---

## 3. SELF-ORDER MANAGEMENT (OM)

### Overview
Order Management (OM) is **distinct from Transfer Agent (TA)** functions. OM handles the creation/redemption order process, basket construction, and NSCC PCF publication. TA handles shareholder recordkeeping after orders settle.

### Core Responsibilities

#### A. Creation/Redemption Order Processing

1. **AP Order Receipt & Validation**
   - Receive creation/redemption orders from APs
   - Validate order details (basket composition, share quantity, etc.)
   - Check AP authorization status
   - Validate order timing (cut-off times)
   - Confirm order acceptance/rejection

2. **Basket Construction & Validation**
   - **Creation Baskets:**
     - Construct creation basket based on current portfolio
     - Validate basket components (CUSIPs, quantities)
     - Calculate cash component
     - Validate against PCF (Portfolio Composition File)
   
   - **Redemption Baskets:**
     - Construct redemption basket (typically in-kind)
     - Validate basket components
     - Calculate cash component
     - Validate against PCF

3. **Order Routing**
   - Route orders to custodian
   - Route orders to NSCC for settlement
   - Coordinate with AP on order execution
   - Handle order modifications/cancellations

#### B. NSCC PCF (Portfolio Composition File) Publication

1. **PCF Generation**
   - **What is PCF**: Daily file published to NSCC containing the fund's portfolio composition for creation/redemption baskets
   - **Contents:**
     - Security identifiers (CUSIPs)
     - Share quantities per creation unit
     - Cash component
     - Estimated cash component
     - Other required fields
   
   - **Process:**
     - Generate PCF from current portfolio holdings
     - Validate PCF data (CUSIPs, quantities, etc.)
     - Submit PCF to NSCC by deadline (typically 8:00 AM ET)
     - Publish PCF to APs via NSCC system
     - Handle PCF corrections/updates

2. **PCF Data Sources**
   - **Real-Time Data:**
     - Current portfolio holdings (from custodian or portfolio system)
     - Security identifiers and pricing
     - Cash positions
   - **Timing:**
     - PCF must be published before market open
     - Typically generated from previous day's closing positions
     - Updated for corporate actions and cash flows

3. **PCF Maintenance**
   - Update for corporate actions
   - Update for portfolio changes
   - Handle PCF exceptions
   - Maintain PCF history

#### C. AP Order Hub Management

1. **AP Portal/System**
   - Provide APs with order submission system
   - Display current PCF
   - Show order status
   - Provide order history
   - Handle AP authentication and authorization

2. **Order Tracking**
   - Track order status (pending, accepted, rejected, settled)
   - Monitor order settlement
   - Handle order exceptions
   - Generate order reports

3. **AP Communication**
   - Notify APs of order acceptance/rejection
   - Communicate basket changes
   - Provide order confirmations
   - Handle AP inquiries

#### D. Settlement Coordination

1. **NSCC Settlement**
   - Coordinate with NSCC on order settlement
   - Monitor settlement status
   - Handle settlement failures
   - Reconcile settled orders

2. **Custodian Coordination**
   - Coordinate with custodian on basket delivery
   - Monitor cash movements
   - Handle settlement exceptions
   - Reconcile settled transactions

### Startup Tasks (One-Time)

1. **System Setup**
   - Select and implement order management system
   - Set up NSCC connectivity (NSCC Participant Terminal System)
   - Configure PCF generation system
   - Establish AP order hub/portal

2. **NSCC Membership & Setup**
   - Become NSCC participant (if not already)
   - Set up NSCC connectivity
   - Configure PCF submission process
   - Test NSCC integrations

3. **Process Development**
   - Document order processing procedures
   - Establish PCF generation workflows
   - Create order validation rules
   - Set up AP communication processes

4. **Staffing**
   - Hire/assign order management staff
   - Train staff on systems and processes
   - Establish backup coverage

5. **Testing**
   - Test order processing system
   - Test PCF generation and submission
   - Test NSCC connectivity
   - Perform end-to-end order testing

### Recurring Tasks

#### Daily
- Generate and publish PCF (by 8:00 AM ET)
- Receive and validate AP orders
- Process creation/redemption orders
- Route orders to custodian and NSCC
- Monitor order settlement
- Handle order exceptions
- Update PCF for corporate actions (as needed)

#### Weekly
- Review order processing metrics
- Review PCF accuracy
- Handle AP inquiries
- Review settlement exceptions

#### Monthly
- Generate order processing reports
- Review AP activity
- Update order processing procedures (as needed)

### Cost Analysis

#### One-Time Startup Costs
- **Order Management System**: $50,000 - $150,000 (license + implementation)
- **NSCC Connectivity**: $10,000 - $30,000 (setup)
  - NSCC participant fees: ~$5,000 (one-time)
  - System integration: $5,000 - $25,000
- **AP Order Hub/Portal**: $25,000 - $75,000 (development)
- **System Integration**: $15,000 - $50,000 (custodian, portfolio system)
- **Training & Setup**: $10,000 - $25,000
- **Total Startup**: $110,000 - $330,000

#### Annual Recurring Costs
- **Order Management System License**: $30,000 - $80,000/year
- **NSCC Fees**: $20,000 - $50,000/year
  - NSCC membership: ~$10,000/year
  - Transaction fees: variable
  - PCF submission fees: ~$5,000/year
- **AP Order Hub/Portal**: $10,000 - $25,000/year (hosting/maintenance)
- **Staffing**: $100,000 - $200,000/year
  - 1-2 FTE order management staff
- **Technology & Infrastructure**: $10,000 - $20,000/year
  - Servers/hosting
  - Backup systems
  - Security tools
- **Total Annual**: $170,000 - $375,000/year

### Data Flow & Input/Output Process

#### Daily Inputs
1. **Portfolio Holdings** (end-of-day previous day)
   - Current portfolio composition
   - Security identifiers (CUSIPs)
   - Share quantities
   - Cash positions

2. **AP Orders** (real-time during trading day)
   - Creation orders
   - Redemption orders
   - Order details (quantity, basket, etc.)

3. **Corporate Actions** (as needed)
   - Stock splits
   - Dividends
   - Mergers/acquisitions
   - Other corporate actions

4. **NSCC Data** (real-time)
   - Settlement confirmations
   - Order status updates
   - PCF submission confirmations

#### Daily Outputs
1. **PCF File** (by 8:00 AM ET)
   - Published to NSCC
   - Available to APs via NSCC system
   - Contains creation/redemption basket composition

2. **Order Confirmations**
   - Order acceptance/rejection notices to APs
   - Order status updates
   - Settlement confirmations

3. **Order Reports**
   - Daily order summary
   - Order exception reports
   - Settlement reports

### Key Differences: OM vs. TA

| Aspect | Order Management (OM) | Transfer Agent (TA) |
|--------|----------------------|---------------------|
| **Focus** | Order processing, basket construction, PCF publication | Shareholder recordkeeping, account management |
| **Timing** | Pre-trade and trade execution | Post-trade settlement |
| **Primary Interface** | APs, NSCC | Shareholders, DTC, broker-dealers |
| **Key Deliverable** | PCF file, order processing | Shareholder records, reconciliations |
| **Data Flow** | Portfolio → PCF → Orders → Settlement | Settled orders → Shareholder records → Reconciliations |
| **Systems** | Order management system, NSCC connectivity | TA system, DTC connectivity |

**They are complementary but distinct functions:**
- **OM** handles the "front-end" - getting orders, building baskets, publishing PCF
- **TA** handles the "back-end" - recording who owns what after orders settle

---

## SUMMARY: TOTAL COSTS FOR ALL THREE FUNCTIONS

### One-Time Startup Costs
- **Self-TA**: $90,000 - $267,000
- **Self-Admin**: $130,000 - $345,000
- **Self-OM**: $110,000 - $330,000
- **Total Startup**: $330,000 - $942,000

### Annual Recurring Costs
- **Self-TA**: $240,000 - $525,000/year
- **Self-Admin**: $390,000 - $885,000/year
- **Self-OM**: $170,000 - $375,000/year
- **Total Annual**: $800,000 - $1,785,000/year

### Key Considerations
1. **Scale**: Costs are higher for smaller funds but become more efficient as AUM grows
2. **Complexity**: More complex portfolios (international, derivatives, etc.) increase costs
3. **Volume**: Higher trading volume increases transaction-based fees
4. **Staffing**: Most significant cost driver; can be optimized with automation
5. **Technology**: Upfront investment in systems reduces long-term operational costs

---

## RECOMMENDATIONS

1. **Phased Approach**: Consider implementing functions in phases (e.g., OM first, then TA, then Admin)
2. **Vendor Evaluation**: Compare insourcing costs to current vendor costs to ensure savings
3. **Automation**: Invest in automation to reduce staffing needs
4. **Scale Planning**: Ensure systems can scale as AUM grows
5. **Risk Management**: Maintain strong controls and backup procedures for all functions

