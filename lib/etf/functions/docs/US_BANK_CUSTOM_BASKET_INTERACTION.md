# US Bank Custom/In-Kind Basket Interaction Guide

## Overview

This guide explains how to interact with US Bank for custom and in-kind basket orders for ETF creation and redemption. US Bank handles order management, but you need to provide them with validated custom baskets and receive confirmations.

---

## Important Note

**US Bank handles order management**, including:
- PCF publication to NSCC
- AP order processing
- Order routing and settlement coordination

**Your responsibilities**:
- **Review and approve/deny/modify** all custom basket requests (fund has final discretion)
- **Validate** custom baskets (Rule 6c-11 compliance)
- **Generate** tax-optimized baskets for redemptions (if not using AP's request)
- **Provide final approved baskets** to US Bank
- **Notify AP** of final approved basket composition (what they must deliver/receive)
- Monitor order status
- Reconcile settlements

**Key Principle**: **The Fund has final discretion on all custom baskets**
- AP can **request** a custom basket (for inventory constraints, settlement issues, tax lots, hard-to-source names)
- Fund **reviews, approves, denies, or modifies** the request
- Fund **tells AP** what the final approved basket is
- AP **delivers exactly** what's approved

---

## Real-World Workflow for Custom/In-Kind Baskets

**The standard workflow** (applies to both Creation and Redemption orders):

1. **AP requests** custom basket (often due to inventory constraints, settlement issues, tax lots, or hard-to-source names)
2. **Transfer agent/US Bank routes** the request to you (and sometimes to portfolio management/trading)
3. **You review and approve/deny/modify** the request (fund has discretion)
4. **You send final agreed basket** to AP and US Bank (what to deliver + cash balancing)
5. **AP delivers exactly** what's approved

**Key Point**: AP can request, but **you tell AP what's in the final basket**. The fund has the discretion to accept, deny, or modify any custom basket request.

---

## Workflow: Custom Basket Request and Approval

### 1. AP Submits Custom Basket Request

**AP submits order with custom basket request** (via US Bank portal, email, or API):

```json
{
  "ap_id": "AP001",
  "order_type": "creation",
  "creation_units": 10,
  "basket_type": "custom",
  "custom_securities": [
    {"cusip": "037833100", "quantity": "100", "description": "APPLE INC"},
    {"cusip": "594918104", "quantity": "50", "description": "MICROSOFT CORP"}
  ],
  "purpose": "inventory_management",
  "reason": "AP has these securities in inventory and wants to avoid sourcing others",
  "order_date": "2024-01-15",
  "requested_settlement_date": "2024-01-17"
}
```

**Common reasons AP requests custom baskets**:
- Inventory constraints (AP has specific securities in inventory)
- Settlement issues (avoiding hard-to-settle securities)
- Tax lots (AP wants to deliver specific tax lots)
- Hard-to-source names (securities difficult to locate/borrow)

**Note**: This is a **request**, not a final basket. The fund has discretion to approve, deny, or modify.

---

### 2. Transfer Agent/US Bank Routes Request to You

**US Bank receives the request and routes it to you** (via email, API, or portal notification):

```python
# You receive the order from US Bank
order = om.create_ap_order(
    ap_id="AP001",
    order_type="creation",
    creation_units=10,
    basket=custom_basket_request  # AP's requested basket
)
```

---

### 3. Review and Approve/Deny/Modify Custom Basket (Your System)

**You review the request and make a decision**:

```python
from lib.etf.functions.operations.order_management import OrderManagement
from lib.etf.adapters import FileBasedDataSourceAdapter
from datetime import date

# Initialize
adapter = FileBasedDataSourceAdapter(data_path="./data")
om = OrderManagement(adapter)

# Get current PCF
pcf = om.generate_pcf(date.today())

# Option A: Approve AP's request as-is
approval_result = om.review_and_approve_custom_basket(
    order=order,
    pcf=pcf,
    approval_action="approve"  # Approve AP's basket as-is
)

# Option B: Modify AP's request
modified_basket = [
    {"cusip": "037833100", "quantity": "100"},  # Keep this
    {"cusip": "594918104", "quantity": "60"}    # Modify quantity
]
approval_result = om.review_and_approve_custom_basket(
    order=order,
    pcf=pcf,
    approved_basket=modified_basket,
    approval_action="modify"  # Fund modifies AP's request
)

# Option C: Deny AP's request (use standard basket instead)
approval_result = om.review_and_approve_custom_basket(
    order=order,
    pcf=pcf,
    approval_action="deny"  # Deny custom basket, will use standard
)

# Option D: Generate your own optimized basket (for redemptions)
from lib.etf.functions.operations.tax_optimization import TaxEfficiencyOptimizer
from lib.etf.functions.tax.tax_lot import TaxLotManager

tax_optimizer = TaxEfficiencyOptimizer(adapter)
tax_lot_mgr = TaxLotManager(storage_path="./data/tax_lots")
tax_lots = tax_lot_mgr.get_all_tax_lots()

# Generate optimized basket (highest cost basis for tax efficiency)
optimized_basket = tax_optimizer.optimize_redemption_basket_for_tax(
    pcf=pcf.__dict__,
    creation_units=5,
    tax_lots=tax_lots
)

# Approve your optimized basket instead of AP's request
approval_result = om.review_and_approve_custom_basket(
    order=order,
    pcf=pcf,
    approved_basket=optimized_basket,
    approval_action="modify"  # Fund uses its own optimized basket
)
```

**Review considerations**:
- ✅ Rule 6c-11 compliance (substantial similarity, value deviation)
- ✅ Portfolio management considerations
- ✅ Tax optimization (for redemptions: highest cost basis)
- ✅ Operational efficiency
- ✅ AP's stated reason (inventory constraints, settlement issues, etc.)

**Before sending to US Bank, validate the custom basket**:

```python
from lib.etf.functions.operations.order_management import OrderManagement
from lib.etf.functions.operations.rule_6c11_compliance import Rule6c11Compliance
from lib.etf.adapters import FileBasedDataSourceAdapter
from datetime import date

# Initialize
adapter = FileBasedDataSourceAdapter(data_path="./data")
om = OrderManagement(adapter)

# Get current PCF
pcf = om.generate_pcf(date.today())

# Validate custom basket
custom_securities = [
    {"cusip": "037833100", "quantity": "100"},
    {"cusip": "594918104", "quantity": "50"}
]

# Build and validate custom basket
basket = om.build_custom_creation_basket(
    pcf=pcf,
    creation_units=10,
    custom_securities=custom_securities
)

# Check validation
if not basket.validated:
    print(f"Basket validation failed: {basket.errors}")
    # Reject order or request AP to fix
else:
    print("Basket validated successfully")
    # Proceed to send to US Bank
```

**Validation checks performed**:
- ✅ Rule 6c-11 compliance (substantial similarity, value deviation)
- ✅ CUSIP validation (all CUSIPs must be in PCF)
- ✅ Price validation (all securities must have valid prices)
- ✅ Quantity validation (all quantities must be positive)
- ✅ Value calculation (basket value must match PCF value within tolerance)

---

## Workflow B: Redemption Orders (You Generate Optimized Basket)

### 1. AP Submits Redemption Order

**AP submits standard redemption order** (via US Bank portal, email, or API):

```json
{
  "ap_id": "AP001",
  "order_type": "redemption",
  "creation_units": 5,
  "basket_type": "standard",  // AP doesn't specify - you will determine
  "order_date": "2024-01-15",
  "requested_settlement_date": "2024-01-17"
}
```

**Note**: For redemption orders, AP submits a standard order. **You then generate the optimized basket** based on tax efficiency (highest cost basis securities to minimize realized gains).

---

### 2. Generate Tax-Optimized Redemption Basket (Your System)

**You generate the custom redemption basket** for tax optimization:

```python
from lib.etf.functions.operations.order_management import OrderManagement
from lib.etf.functions.operations.tax_optimization import TaxEfficiencyOptimizer
from lib.etf.functions.tax.tax_lot import TaxLotManager
from lib.etf.adapters import FileBasedDataSourceAdapter
from datetime import date

# Initialize
adapter = FileBasedDataSourceAdapter(data_path="./data")
om = OrderManagement(adapter)
tax_optimizer = TaxEfficiencyOptimizer(adapter)
tax_lot_mgr = TaxLotManager(storage_path="./data/tax_lots")

# Get current PCF
pcf = om.generate_pcf(date.today())

# Get tax lots for optimization
tax_lots = tax_lot_mgr.get_all_tax_lots()  # Get all tax lots with cost basis

# Generate optimized redemption basket (highest cost basis to minimize gains)
optimized_basket = tax_optimizer.optimize_redemption_basket_for_tax(
    pcf=pcf.__dict__,  # Convert PCFFile to dict
    creation_units=5,
    tax_lots=tax_lots
)

# Validate the optimized basket
basket = om.build_custom_redemption_basket(
    pcf=pcf,
    creation_units=5,
    custom_securities=optimized_basket
)

if not basket.validated:
    print(f"Optimized basket validation failed: {basket.errors}")
    # Fall back to standard basket if optimization fails
    basket = om.build_standard_redemption_basket(pcf, 5)
else:
    print(f"Optimized basket generated: {len(basket.securities)} securities")
    print(f"Expected tax benefit: Minimized realized gains")
```

**What this does**:
- Analyzes all tax lots in portfolio
- Selects securities with **highest cost basis** to deliver to AP
- Minimizes realized capital gains for the fund
- Validates basket against Rule 6c-11 requirements

---

### 3. Notify AP of Custom Redemption Basket

**You tell the AP what securities they'll receive**:

```json
{
  "order_id": "ORD-20240115-001",
  "ap_id": "AP001",
  "order_type": "redemption",
  "creation_units": 5,
  "basket_type": "custom",
  "basket_securities": [
    {
      "cusip": "037833100",
      "quantity": "100",
      "description": "APPLE INC",
      "cost_basis": "150.00",
      "optimization_reason": "highest_cost_basis"
    },
    {
      "cusip": "594918104",
      "quantity": "50",
      "description": "MICROSOFT CORP",
      "cost_basis": "280.00",
      "optimization_reason": "highest_cost_basis"
    }
  ],
  "cash_component": "0.00",
  "total_value": "250000.00",
  "rule_6c11_validation": {
    "passed": true,
    "validation_date": "2024-01-15"
  },
  "purpose": "tax_optimization",
  "settlement_date": "2024-01-17",
  "notification_date": "2024-01-15T10:30:00Z"
}
```

**Send this to AP via**:
- Email notification
- US Bank portal (if they support custom basket notifications)
- API response (if AP queries order status)

---

### 4. Send Custom Basket to US Bank

**Send the optimized basket to US Bank for processing**:

---

### 3. Send Validated Basket to US Bank (Creation) or Optimized Basket (Redemption)

**Format for US Bank API/SFTP/Email**:

#### Option A: API (Preferred)

```python
# Format basket data for US Bank API
basket_data = {
    "order_id": order.order_id,
    "ap_id": "AP001",
    "order_type": "creation",
    "creation_units": 10,
    "basket_type": "custom",
    "basket_securities": [
        {
            "cusip": sec["cusip"],
            "quantity": str(sec["quantity"]),
            "description": sec.get("description", ""),
            "estimated_value": str(sec.get("estimated_value", "0"))
        }
        for sec in basket.securities
    ],
    "cash_component": str(basket.cash_component),
    "total_value": str(basket.total_value),
    "rule_6c11_validation": {
        "passed": True,
        "cusip_overlap": 0.98,
        "value_deviation": 0.02
    },
    "purpose": "tax_optimization",
    "requested_settlement_date": "2024-01-17"
}

# Send to US Bank API
# TODO: Implement actual US Bank API call
# response = us_bank_api.submit_custom_basket_order(basket_data)
```

#### Option B: SFTP File Upload

**File format**: `CUSTOM_BASKET_ORDER_YYYYMMDD_HHMMSS.json`

```json
{
  "order_id": "ORD-20240115-001",
  "ap_id": "AP001",
  "order_type": "creation",
  "creation_units": 10,
  "basket_type": "custom",
  "basket_securities": [
    {
      "cusip": "037833100",
      "quantity": "100",
      "description": "APPLE INC",
      "estimated_value": "15000.00"
    }
  ],
  "cash_component": "0.00",
  "total_value": "500000.00",
  "rule_6c11_validation": {
    "passed": true,
    "validation_date": "2024-01-15",
    "cusip_overlap": 0.98,
    "value_deviation": 0.02
  },
  "purpose": "tax_optimization",
  "requested_settlement_date": "2024-01-17",
  "submitted_by": "DAM Operations",
  "submitted_date": "2024-01-15T10:30:00Z"
}
```

#### Option C: Email (Fallback)

**Email to**: `etf-orders@usbank.com` (or your US Bank contact)

**Subject**: `Custom Basket Order - [Order ID] - [AP ID]`

**Body**: Include JSON formatted basket data (same as SFTP format)

**Attachments**: 
- Basket file: `CUSTOM_BASKET_ORDER_[OrderID].json`
- Rule 6c-11 validation report: `RULE_6C11_VALIDATION_[OrderID].json`

---

### 4. Receive Confirmation from US Bank

**US Bank will respond with**:

```json
{
  "order_id": "ORD-20240115-001",
  "us_bank_order_id": "USB-20240115-001",
  "status": "accepted",
  "accepted_date": "2024-01-15T10:35:00Z",
  "settlement_date": "2024-01-17",
  "confirmation": {
    "basket_validated": true,
    "nscc_notified": true,
    "settlement_scheduled": true
  },
  "notes": "Order accepted, settlement scheduled for T+2"
}
```

**Or if rejected**:

```json
{
  "order_id": "ORD-20240115-001",
  "status": "rejected",
  "rejection_reason": "Basket value deviation exceeds tolerance",
  "rejected_date": "2024-01-15T10:35:00Z"
}
```

---

### 5. Monitor Order Status

**Query US Bank for order status**:

```python
# TODO: Implement US Bank API call
# order_status = us_bank_api.get_order_status(order_id)

# Expected status values:
# - "pending" - Order received, awaiting processing
# - "accepted" - Order accepted, settlement scheduled
# - "rejected" - Order rejected (see rejection_reason)
# - "settled" - Order settled successfully
# - "failed" - Order settlement failed
```

---

### 6. Reconcile Settlement

**After settlement date, reconcile with US Bank**:

```python
from lib.etf.functions.core.settlement_reconciliation import SettlementReconciliationManager

# Reconcile T+2 settlement
settlement_mgr = SettlementReconciliationManager(adapter)
result = settlement_mgr.reconcile_t2_settlement(settlement_date)

# Check if custom basket order settled
if result.status == "complete":
    print("Custom basket order settled successfully")
else:
    print(f"Settlement issues: {result.exceptions}")
```

---

## Data Format Specifications

### Custom Basket Format

**Required Fields**:
- `order_id`: Unique order identifier
- `ap_id`: Authorized Participant ID
- `order_type`: "creation" or "redemption"
- `creation_units`: Number of creation units
- `basket_type`: "custom"
- `basket_securities`: Array of securities with:
  - `cusip`: Security CUSIP (required)
  - `quantity`: Quantity per creation unit (required)
  - `description`: Security description (optional)
  - `estimated_value`: Estimated value (optional, calculated if not provided)
- `cash_component`: Cash component amount
- `total_value`: Total basket value
- `rule_6c11_validation`: Validation results
- `purpose`: Business purpose ("tax_optimization", "inventory_management", "operational_efficiency")
- `requested_settlement_date`: Requested settlement date (T+2 standard)

**Optional Fields**:
- `notes`: Additional notes
- `submitted_by`: Name of person submitting
- `submitted_date`: Submission timestamp

---

## Rule 6c-11 Compliance Requirements

**All custom baskets must comply with SEC Rule 6c-11**:

1. **Substantial Similarity**: ≥95% CUSIP overlap with standard PCF basket
2. **Value Deviation**: ≤5% value deviation from standard PCF basket
3. **Legitimate Purpose**: Must serve legitimate business purpose (tax optimization, inventory management)
4. **Fair Treatment**: Must not disadvantage other shareholders
5. **Disclosure**: Must be disclosed to all APs

**Your system automatically validates these requirements** before sending to US Bank.

---

## Integration Points

### 1. US Bank API (If Available)

**Endpoint**: `POST /api/v1/etf/orders/custom-basket`

**Authentication**: API key or OAuth token (per US Bank requirements)

**Request Format**: JSON (see basket format above)

**Response Format**: JSON confirmation

**Error Handling**: 
- 400: Invalid basket format
- 401: Authentication failed
- 403: AP not authorized
- 422: Basket validation failed
- 500: US Bank server error

---

### 2. US Bank SFTP (If Available)

**Server**: `sftp.usbank.com` (or provided by US Bank)

**Directory**: `/incoming/etf-orders/`

**File Naming**: `CUSTOM_BASKET_ORDER_YYYYMMDD_HHMMSS_[OrderID].json`

**Response File**: `CUSTOM_BASKET_RESPONSE_YYYYMMDD_HHMMSS_[OrderID].json` (in `/outgoing/etf-orders/`)

---

### 3. US Bank Email (Fallback)

**Email Address**: Provided by US Bank relationship manager

**Format**: JSON attachment or structured email body

**Response**: Email confirmation with order status

---

## Contact Information

**US Bank Global Fund Services**:
- **Primary Contact**: Your US Bank relationship manager
- **Order Management**: `etf-orders@usbank.com` (or provided email)
- **Phone**: Provided by relationship manager
- **Support**: US Bank Global Fund Services support line

**Get from US Bank**:
- API credentials and documentation
- SFTP server details and credentials
- Email addresses for order submission
- File format specifications
- Order status API endpoints
- Settlement confirmation process

---

## Example: Complete Workflows

### Example A: Creation Order (AP Requests Custom Basket)

```python
from lib.etf.functions.operations.order_management import OrderManagement
from lib.etf.adapters import FileBasedDataSourceAdapter
from datetime import date, timedelta

# 1. Initialize
adapter = FileBasedDataSourceAdapter(data_path="./data")
om = OrderManagement(adapter)

# 2. Get current PCF
pcf = om.generate_pcf(date.today())

# 3. AP provides custom basket (AP tells you what they want to deliver)
custom_securities = [
    {"cusip": "037833100", "quantity": "100"},
    {"cusip": "594918104", "quantity": "50"}
]

# 4. Validate custom basket
basket = om.build_custom_creation_basket(
    pcf=pcf,
    creation_units=10,
    custom_securities=custom_securities
)

if not basket.validated:
    # Reject order
    print(f"Basket validation failed: {basket.errors}")
    # Notify AP of rejection
else:
    # 5. Format for US Bank
    basket_data = {
        "order_id": f"ORD-{date.today().isoformat()}-001",
        "ap_id": "AP001",
        "order_type": "creation",
        "creation_units": 10,
        "basket_type": "custom",
        "basket_securities": [
            {
                "cusip": sec["cusip"],
                "quantity": str(sec["quantity"]),
                "description": sec.get("description", ""),
                "estimated_value": str(sec.get("estimated_value", "0"))
            }
            for sec in basket.securities
        ],
        "cash_component": str(basket.cash_component),
        "total_value": str(basket.total_value),
        "rule_6c11_validation": {
            "passed": True,
            "validation_date": date.today().isoformat()
        },
        "purpose": "inventory_management",  # AP's purpose
        "requested_settlement_date": (date.today() + timedelta(days=2)).isoformat()
    }
    
    # 6. Send to US Bank (TODO: Implement actual API/SFTP/Email)
    # us_bank_response = send_to_us_bank(basket_data)
    
    # 7. Monitor order status
    # order_status = check_order_status(basket_data["order_id"])
    
    # 8. Reconcile settlement after T+2
    # settlement_result = reconcile_settlement(settlement_date)
```

### Example B: Redemption Order (You Generate Optimized Basket)

```python
from lib.etf.functions.operations.order_management import OrderManagement
from lib.etf.functions.operations.tax_optimization import TaxEfficiencyOptimizer
from lib.etf.functions.tax.tax_lot import TaxLotManager
from lib.etf.adapters import FileBasedDataSourceAdapter
from datetime import date, timedelta

# 1. Initialize
adapter = FileBasedDataSourceAdapter(data_path="./data")
om = OrderManagement(adapter)
tax_optimizer = TaxEfficiencyOptimizer(adapter)
tax_lot_mgr = TaxLotManager(storage_path="./data/tax_lots")

# 2. Get current PCF
pcf = om.generate_pcf(date.today())

# 3. AP submits standard redemption order (no custom basket specified)
# You receive order from US Bank or AP

# 4. Generate tax-optimized redemption basket (YOU tell AP what they'll receive)
tax_lots = tax_lot_mgr.get_all_tax_lots()  # Get all tax lots with cost basis

optimized_basket = tax_optimizer.optimize_redemption_basket_for_tax(
    pcf=pcf.__dict__,
    creation_units=5,
    tax_lots=tax_lots
)

# 5. Validate optimized basket
basket = om.build_custom_redemption_basket(
    pcf=pcf,
    creation_units=5,
    custom_securities=optimized_basket
)

if not basket.validated:
    # Fall back to standard basket
    print(f"Optimized basket validation failed, using standard basket")
    basket = om.build_standard_redemption_basket(pcf, 5)
else:
    print(f"Optimized basket generated: {len(basket.securities)} securities")

# 6. Notify AP of what they'll receive
ap_notification = {
    "order_id": f"ORD-{date.today().isoformat()}-002",
    "ap_id": "AP001",
    "order_type": "redemption",
    "creation_units": 5,
    "basket_type": "custom",
    "basket_securities": [
        {
            "cusip": sec["cusip"],
            "quantity": str(sec["quantity"]),
            "description": sec.get("description", ""),
            "cost_basis": str(sec.get("cost_basis", "0")),
            "optimization_reason": "highest_cost_basis"
        }
        for sec in basket.securities
    ],
    "cash_component": str(basket.cash_component),
    "total_value": str(basket.total_value),
    "purpose": "tax_optimization",  # Your purpose (minimize fund's realized gains)
    "settlement_date": (date.today() + timedelta(days=2)).isoformat()
}

# 7. Send to US Bank and notify AP
# send_to_us_bank(ap_notification)
# notify_ap(ap_notification)

# 8. Monitor order status and reconcile settlement
```

---

## Troubleshooting

### Basket Validation Fails

**Common Issues**:
- CUSIP not in PCF → Request AP to use PCF securities only
- Value deviation > 5% → Request AP to adjust quantities
- CUSIP overlap < 95% → Request AP to increase overlap

**Resolution**: Work with AP to fix basket, then resubmit

---

### US Bank Rejects Order

**Common Reasons**:
- Basket format incorrect
- AP not authorized
- Settlement date invalid
- Missing required fields

**Resolution**: Review US Bank rejection reason, fix issues, resubmit

---

### Settlement Fails

**Common Issues**:
- AP didn't deliver securities
- Cash component incorrect
- Securities don't match basket

**Resolution**: 
1. Check settlement reconciliation report
2. Contact US Bank for details
3. Work with AP to resolve
4. Document exception

---

## Best Practices

1. **Creation Orders**: Always validate AP's custom basket requests before sending to US Bank
2. **Redemption Orders**: Always generate tax-optimized baskets (highest cost basis) to minimize realized gains
3. **Notify APs**: For redemption orders, notify APs of the custom basket composition before settlement
4. **Document everything** - Keep records of all custom basket orders (both creation and redemption)
5. **Monitor closely** - Check order status regularly
6. **Reconcile promptly** - Reconcile settlements on T+2 date
7. **Communicate clearly** - Maintain clear communication with APs and US Bank
8. **Test first** - Test custom basket workflow with US Bank before going live

## Summary: Custom Basket Workflow

| Step | Who | What |
|------|-----|------|
| **1. Request** | **AP** | AP requests custom basket (inventory constraints, settlement issues, tax lots, hard-to-source names) |
| **2. Route** | **US Bank/Transfer Agent** | Routes request to fund manager |
| **3. Review & Approve** | **Fund (You)** | Fund reviews, approves, denies, or modifies request (fund has discretion) |
| **4. Notify** | **Fund (You)** | Fund tells AP what the final approved basket is |
| **5. Deliver** | **AP** | AP delivers exactly what's approved |

**Key Principle**: AP can request, but **the fund has final discretion** and tells AP what's in the final basket.

**For Redemptions**: Fund often generates its own tax-optimized basket (highest cost basis) rather than using AP's request, to minimize realized gains for the fund.

---

## Notes

- **US Bank handles order management**, but you validate custom baskets
- **Rule 6c-11 compliance** is your responsibility (validated before sending to US Bank)
- **Settlement reconciliation** is your responsibility (verify trades settled correctly)
- **All custom baskets** must be disclosed to all APs per Rule 6c-11
- **Contact US Bank** to get specific API/SFTP/Email details for your account

