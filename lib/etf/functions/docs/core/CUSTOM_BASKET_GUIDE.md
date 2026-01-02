# Custom Basket Building Guide

## Quick Start: Building Custom Baskets

### Method 1: Direct Basket Building (Recommended)

```python
from lib.etf.functions.operations.order_management import OrderManagement
from lib.etf.adapters import FMPDataSourceAdapter
from datetime import date
from decimal import Decimal

# Initialize
adapter = FMPDataSourceAdapter(api_key='your_key', etf_symbol='REDI')
om = OrderManagement(data_adapter=adapter)

# 1. Generate PCF first (required for validation)
pcf = om.generate_pcf(date.today())

# 2. Define your custom securities
custom_securities = [
    {"cusip": "023135106", "quantity": "100", "description": "AMAZON.COM INC"},  # AMZN
    {"cusip": "02079K107", "quantity": "50", "description": "ALPHABET INC"},     # GOOG
    {"cusip": "459200101", "quantity": "75", "description": "IBM CORP"},        # IBM
    # Add more securities as needed
]

# 3. Build custom creation basket
creation_units = 10  # Number of creation units (1 unit = 50,000 shares)
custom_basket = om.build_custom_creation_basket(
    pcf=pcf,
    creation_units=creation_units,
    custom_securities=custom_securities
)

# 4. Check if basket is valid
if custom_basket.validated:
    print(f"✅ Custom basket is valid!")
    print(f"   Securities: {len(custom_basket.securities)}")
    print(f"   Total value: ${custom_basket.total_value:,.2f}")
    print(f"   Cash component: ${custom_basket.cash_component:,.2f}")
else:
    print(f"❌ Basket validation failed:")
    for error in custom_basket.errors:
        print(f"   - {error}")
```

### Method 2: Build from Holdings (Tax-Optimized)

```python
from lib.etf.functions.core.administration import FundAdministration
from lib.etf.functions.tax.tax_lot import TaxLotManager

# Get current holdings
admin = FundAdministration(data_adapter=adapter, storage_path='./data/admin')
holdings = adapter.get_portfolio_holdings(date.today())

# Get tax lots to optimize which shares to deliver
taxlot_manager = TaxLotManager(storage_path='./data/tax_lots')

# Build custom basket from holdings (for redemption)
# Use LOWEST_COST method to minimize realized gains
custom_securities = []
for holding in holdings:
    ticker = holding.get('ticker')
    cusip = holding.get('cusip')
    total_qty = Decimal(str(holding.get('quantity', 0)))
    
    # Get tax lots for this security
    lots = taxlot_manager.get_lots_for_ticker(ticker)
    
    # Select lots to deliver (using LOWEST_COST for tax optimization)
    # This minimizes realized gains by delivering lowest cost basis shares
    lots.sort(key=lambda lot: lot.cost_basis)  # Lowest cost first
    
    # Calculate quantity to deliver from selected lots
    qty_to_deliver = min(total_qty, Decimal('100'))  # Example: deliver 100 shares
    
    if qty_to_deliver > 0 and cusip:
        custom_securities.append({
            "cusip": cusip,
            "quantity": str(qty_to_deliver),
            "description": holding.get('name', ticker)
        })

# Build custom redemption basket
custom_basket = om.build_custom_redemption_basket(
    pcf=pcf,
    creation_units=5,
    custom_securities=custom_securities
)
```

### Method 3: Interactive Basket Builder

```python
def build_custom_basket_interactive():
    """Interactive function to build custom baskets"""
    
    # Initialize
    adapter = FMPDataSourceAdapter(api_key='your_key', etf_symbol='REDI')
    om = OrderManagement(data_adapter=adapter)
    pcf = om.generate_pcf(date.today())
    
    print("Custom Basket Builder")
    print("=" * 50)
    print(f"PCF Date: {pcf.date}")
    print(f"Available securities in PCF: {len(pcf.securities)}")
    print()
    
    # Show available securities
    print("Available Securities:")
    for i, sec in enumerate(pcf.securities[:10], 1):  # Show first 10
        print(f"  {i}. {sec.get('description', 'N/A')} (CUSIP: {sec.get('cusip')})")
    print()
    
    # Get user input
    custom_securities = []
    while True:
        cusip = input("Enter CUSIP (or 'done' to finish): ").strip()
        if cusip.lower() == 'done':
            break
        
        # Validate CUSIP is in PCF
        if not any(s.get('cusip') == cusip for s in pcf.securities):
            print(f"⚠️  CUSIP {cusip} not found in PCF. Please try again.")
            continue
        
        quantity = input(f"Enter quantity for {cusip}: ").strip()
        description = input(f"Enter description (optional): ").strip()
        
        custom_securities.append({
            "cusip": cusip,
            "quantity": quantity,
            "description": description or f"Security {cusip}"
        })
        print(f"✅ Added {quantity} shares of {cusip}")
        print()
    
    # Build basket
    creation_units = int(input("Enter number of creation units: "))
    basket = om.build_custom_creation_basket(pcf, creation_units, custom_securities)
    
    # Display results
    print("\n" + "=" * 50)
    print("Basket Results:")
    print(f"  Validated: {basket.validated}")
    print(f"  Securities: {len(basket.securities)}")
    print(f"  Total Value: ${basket.total_value:,.2f}")
    if basket.errors:
        print(f"  Errors: {basket.errors}")
    
    return basket

# Run interactive builder
# basket = build_custom_basket_interactive()
```

## Complete Workflow Examples

### Example 1: Creation Order with Custom Basket

```python
from lib.etf.functions.operations.order_management import OrderManagement, APOrder
from lib.etf.adapters import FMPDataSourceAdapter
from datetime import date

# Setup
adapter = FMPDataSourceAdapter(api_key='your_key', etf_symbol='REDI')
om = OrderManagement(data_adapter=adapter)

# 1. Generate PCF
pcf = om.generate_pcf(date.today())

# 2. Define custom basket
custom_basket = [
    {"cusip": "023135106", "quantity": "100", "description": "AMAZON.COM INC"},
    {"cusip": "02079K107", "quantity": "50", "description": "ALPHABET INC"},
]

# 3. Create AP order with custom basket
order = om.create_ap_order(
    ap_id="AP001",
    order_type="creation",
    creation_units=10,
    basket=custom_basket  # Custom basket specified
)

# 4. Review and approve custom basket (fund has discretion)
approval_result = om.review_and_approve_custom_basket(
    order=order,
    pcf=pcf,
    approval_action="approve"  # or "deny" or "modify"
)

# 5. Process order
if approval_result['approved']:
    result = om.process_ap_order(order, pcf)
    print(f"Order status: {result['status']}")
    print(f"Basket type: {result['basket_type']}")
```

### Example 2: Tax-Optimized Redemption Basket

```python
from lib.etf.functions.core.administration import FundAdministration
from lib.etf.functions.tax.tax_lot import TaxLotManager
from decimal import Decimal

# Get holdings and tax lots
admin = FundAdministration(data_adapter=adapter, storage_path='./data/admin')
taxlot_manager = TaxLotManager(storage_path='./data/tax_lots')
holdings = adapter.get_portfolio_holdings(date.today())

# Build tax-optimized redemption basket
# Strategy: Deliver lowest cost basis shares to minimize realized gains
custom_securities = []

for holding in holdings:
    ticker = holding.get('ticker')
    cusip = holding.get('cusip')
    total_qty = Decimal(str(holding.get('quantity', 0)))
    
    if not cusip or total_qty == 0:
        continue
    
    # Get tax lots and sort by cost basis (lowest first)
    lots = [lot for lot in taxlot_manager.open_lots if lot.ticker == ticker]
    lots.sort(key=lambda lot: lot.cost_basis)
    
    # Calculate quantity to deliver (example: 10% of holding)
    qty_to_deliver = (total_qty * Decimal('0.10')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    if qty_to_deliver > 0:
        custom_securities.append({
            "cusip": cusip,
            "quantity": str(qty_to_deliver),
            "description": holding.get('name', ticker)
        })

# Build custom redemption basket
pcf = om.generate_pcf(date.today())
redemption_basket = om.build_custom_redemption_basket(
    pcf=pcf,
    creation_units=5,
    custom_securities=custom_securities
)

print(f"Tax-optimized redemption basket:")
print(f"  Securities: {len(redemption_basket.securities)}")
print(f"  Total value: ${redemption_basket.total_value:,.2f}")
```

### Example 3: Building from CSV

```python
import csv
from pathlib import Path

def build_basket_from_csv(csv_file: str):
    """Build custom basket from CSV file"""
    
    # Read CSV
    custom_securities = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            custom_securities.append({
                "cusip": row['CUSIP'],
                "quantity": row['Quantity'],
                "description": row.get('Description', row.get('Name', ''))
            })
    
    # Build basket
    adapter = FMPDataSourceAdapter(api_key='your_key', etf_symbol='REDI')
    om = OrderManagement(data_adapter=adapter)
    pcf = om.generate_pcf(date.today())
    
    basket = om.build_custom_creation_basket(
        pcf=pcf,
        creation_units=10,
        custom_securities=custom_securities
    )
    
    return basket

# CSV format:
# CUSIP,Quantity,Description
# 023135106,100,AMAZON.COM INC
# 02079K107,50,ALPHABET INC

# basket = build_basket_from_csv('custom_basket.csv')
```

## Key Functions

### `build_custom_creation_basket()`
Builds a custom creation basket (what AP delivers to create ETF shares).

```python
basket = om.build_custom_creation_basket(
    pcf=pcf,
    creation_units=10,
    custom_securities=[
        {"cusip": "023135106", "quantity": "100", "description": "AMAZON.COM INC"}
    ]
)
```

### `build_custom_redemption_basket()`
Builds a custom redemption basket (what AP receives when redeeming ETF shares).

```python
basket = om.build_custom_redemption_basket(
    pcf=pcf,
    creation_units=5,
    custom_securities=custom_securities
)
```

### `review_and_approve_custom_basket()`
Review and approve/deny/modify AP's custom basket request (fund has discretion).

```python
result = om.review_and_approve_custom_basket(
    order=order,
    pcf=pcf,
    approval_action="approve"  # or "deny" or "modify"
)
```

## Basket Validation

All custom baskets are automatically validated:
- ✅ CUSIPs must exist in PCF
- ✅ Quantities must be positive
- ✅ Prices must be available
- ✅ Rule 6c-11 compliance (for custom baskets)
- ✅ Cash component calculated

## Common Use Cases

### 1. Tax Optimization
Deliver lowest cost basis shares to minimize realized gains.

### 2. Inventory Management
AP requests different securities due to inventory constraints.

### 3. Settlement Issues
AP can't deliver certain securities due to settlement constraints.

### 4. Hard-to-Source Names
AP requests alternative securities for hard-to-source names.

## Tips

1. **Always validate**: Check `basket.validated` before using
2. **Review errors**: Check `basket.errors` if validation fails
3. **Fund discretion**: You can approve, deny, or modify any custom basket
4. **Rule 6c-11**: Custom baskets must comply with SEC Rule 6c-11
5. **Cash component**: Custom baskets may require cash balancing

## Next Steps

1. Generate PCF: `om.generate_pcf(date.today())`
2. Define custom securities: List of CUSIP, quantity, description
3. Build basket: `build_custom_creation_basket()` or `build_custom_redemption_basket()`
4. Validate: Check `basket.validated` and `basket.errors`
5. Use in order: Pass basket to `create_ap_order()` or `process_ap_order()`

