# Basket Creation Guide

## Overview

APs (Authorized Participants) can create orders with either:
- **Standard Baskets**: Use exact PCF composition (most common)
- **Custom Baskets**: Use different securities than PCF (for tax optimization, inventory management)

## Creating AP Orders

### Standard Basket (Most Common)

**For Creation Orders:**
```python
from lib.etf import OrderManagement, FileBasedDataSourceAdapter
from datetime import date

om = OrderManagement(FileBasedDataSourceAdapter())

# Generate PCF first (done daily)
pcf = om.generate_pcf(date.today())

# Create standard creation order (basket=None means standard)
order = om.create_ap_order(
    ap_id="AP001",
    order_type="creation",
    creation_units=10  # 10 creation units = 500,000 shares
)

# Process the order
result = om.process_ap_order(order, pcf)
# Result includes standard basket built from PCF
```

**For Redemption Orders:**
```python
# Standard redemption order
order = om.create_ap_order(
    ap_id="AP001",
    order_type="redemption",
    creation_units=5
)

result = om.process_ap_order(order, pcf)
```

### Custom Basket

**For Creation Orders:**
```python
# Define custom basket (different securities than PCF)
custom_basket = [
    {"cusip": "037833100", "quantity": "100", "description": "APPLE INC"},
    {"cusip": "594918104", "quantity": "50", "description": "MICROSOFT CORP"}
    # ... other securities
]

# Create custom creation order
order = om.create_ap_order(
    ap_id="AP001",
    order_type="creation",
    creation_units=10,
    basket=custom_basket  # Custom basket specified
)

# Process the order
result = om.process_ap_order(order, pcf)
# Result includes custom basket with validation
```

**For Redemption Orders:**
```python
# Custom redemption basket (specify which securities to receive)
custom_redemption_basket = [
    {"cusip": "037833100", "quantity": "100"},
    {"cusip": "594918104", "quantity": "50"}
]

order = om.create_ap_order(
    ap_id="AP001",
    order_type="redemption",
    creation_units=5,
    basket=custom_redemption_basket
)

result = om.process_ap_order(order, pcf)
```

## Manual Basket Construction

You can also build baskets manually before creating orders:

### Standard Creation Basket
```python
pcf = om.generate_pcf(date.today())

# Build standard creation basket
basket = om.build_standard_creation_basket(pcf, creation_units=10)

# Access basket details
print(f"Basket type: {basket.basket_type}")  # "standard"
print(f"Securities: {basket.securities}")
print(f"Cash component: {basket.cash_component}")
print(f"Total value: {basket.total_value}")
```

### Standard Redemption Basket
```python
basket = om.build_standard_redemption_basket(pcf, creation_units=5)
```

### Custom Creation Basket
```python
custom_securities = [
    {"cusip": "037833100", "quantity": "100"},
    {"cusip": "594918104", "quantity": "50"}
]

basket = om.build_custom_creation_basket(
    pcf=pcf,
    creation_units=10,
    custom_securities=custom_securities
)

# Check validation
if not basket.validated:
    print(f"Basket errors: {basket.errors}")
```

### Custom Redemption Basket
```python
basket = om.build_custom_redemption_basket(
    pcf=pcf,
    creation_units=5,
    custom_securities=custom_securities
)
```

## Basket Validation

All baskets are automatically validated:
- **Standard baskets**: Always valid (use exact PCF composition)
- **Custom baskets**: Validated against PCF
  - CUSIPs must exist in PCF
  - Prices must be available
  - Quantities must be positive

## Order Processing Flow

1. **Create Order**: `create_ap_order()` - Creates APOrder object
2. **Process Order**: `process_ap_order()` - Validates and processes
   - If `basket=None`: Builds standard basket from PCF
   - If `basket=List`: Builds custom basket and validates
3. **Result**: Returns order details with basket information

## Key Functions

### `create_ap_order()`
Creates an AP order. Set `basket=None` for standard, or provide custom basket list.

### `build_standard_creation_basket()`
Builds standard creation basket from PCF.

### `build_standard_redemption_basket()`
Builds standard redemption basket from PCF.

### `build_custom_creation_basket()`
Builds and validates custom creation basket.

### `build_custom_redemption_basket()`
Builds and validates custom redemption basket.

### `process_ap_order()`
Processes order (validates, builds basket, accepts/rejects).

## Example: Complete Workflow

```python
from lib.etf import OrderManagement, FileBasedDataSourceAdapter
from datetime import date

# Initialize
om = OrderManagement(FileBasedDataSourceAdapter())

# 1. Generate PCF (done daily, before market open)
pcf = om.generate_pcf(date.today())

# 2. AP creates order (standard basket)
order1 = om.create_ap_order(
    ap_id="AP001",
    order_type="creation",
    creation_units=10
)

# 3. Process order
result1 = om.process_ap_order(order1, pcf)
print(f"Order 1: {result1['status']}, Basket: {result1['basket_type']}")

# 4. AP creates custom order
custom_basket = [
    {"cusip": "037833100", "quantity": "100"},
    {"cusip": "594918104", "quantity": "50"}
]

order2 = om.create_ap_order(
    ap_id="AP002",
    order_type="creation",
    creation_units=10,
    basket=custom_basket
)

# 5. Process custom order
result2 = om.process_ap_order(order2, pcf)
print(f"Order 2: {result2['status']}, Basket: {result2['basket_type']}")
```

## Notes

- **Standard baskets** are most common and use exact PCF composition
- **Custom baskets** require validation and may be rejected if invalid
- All baskets include cash component calculations
- Basket values are calculated using current market prices
- Orders must be processed against the current PCF

