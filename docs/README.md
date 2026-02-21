# Self-Service Functions Documentation

This directory contains comprehensive documentation and implementation for insourcing ETF operational functions.

## Files

### `self-service-functions.md`
Comprehensive documentation covering:
- **Self-Transfer Agent (TA)** - Non-Paying Agent
  - Complete responsibilities breakdown
  - Daily reconciliation process and data sources
  - Cede & Co. file update process
  - Real-time data sources for daily recs
  - Startup and recurring tasks
  - Detailed cost analysis
  - Comparison of paying vs. non-paying agent costs

- **Self-Administration (Admin)**
  - NAV calculation and pricing
  - Financial reporting requirements
  - Regulatory compliance (SEC filings)
  - Startup and recurring tasks
  - Detailed cost analysis
  - Data sources and processes

- **Self-Order Management (OM)**
  - NSCC PCF (Portfolio Composition File) publication
  - AP order hub management
  - Creation/redemption order processing
  - Basket construction and validation
  - Startup and recurring tasks
  - Detailed cost analysis
  - Clear distinction from TA functions

## Key Questions Answered

### Daily Reconciliations and Cede File Updates
- **Where does real-time data come from?**
  - NSCC/DTC feeds: Real-time settlement and position data
  - Custodian portal: Real-time custody account balances
  - AP order system: Real-time creation/redemption orders
  - Broker feeds: Real-time transaction data from market makers

- **Cede File Update Process:**
  - Daily end-of-day process
  - Data source: DTC position files via DTC's Participant Terminal System (PTS)
  - Represents DTC's position as nominee holder for all street-name shares
  - Must reconcile DTC position to shareholder records

### Paying Agent vs. Non-Paying Agent
- **Non-Paying Agent (Recommended):**
  - Lower regulatory burden (no money transmitter licenses)
  - No dividend payment processing
  - No cash management for distributions
  - **Estimated Annual Savings**: $50,000 - $100,000/year

- **Paying Agent (Additional Responsibilities):**
  - Process dividend/distribution payments
  - Maintain distribution bank accounts
  - Handle escheatment (unclaimed property)
  - Money transmitter licenses in all states
  - **Additional Annual Cost**: $50,000 - $100,000/year

### Order Management (OM) vs. Transfer Agent (TA)
**They are NOT the same:**

| Aspect | Order Management (OM) | Transfer Agent (TA) |
|--------|----------------------|---------------------|
| **Focus** | Order processing, basket construction, PCF publication | Shareholder recordkeeping, account management |
| **Timing** | Pre-trade and trade execution | Post-trade settlement |
| **Primary Interface** | APs, NSCC | Shareholders, DTC, broker-dealers |
| **Key Deliverable** | PCF file, order processing | Shareholder records, reconciliations |

**They are complementary:**
- **OM** handles the "front-end" - getting orders, building baskets, publishing PCF
- **TA** handles the "back-end" - recording who owns what after orders settle

## Cost Summary

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

## Implementation

See `../lib/self_service_functions.py` for Python implementation of these functions, and `../examples/self_service_example.py` for usage examples.

## Notes

- AP (Accounts Payable) and Custody will continue to use vendors for now
- All cost estimates are base ranges and may vary based on:
  - Fund size and complexity
  - Trading volume
  - Technology choices
  - Staffing levels
  - Vendor relationships

