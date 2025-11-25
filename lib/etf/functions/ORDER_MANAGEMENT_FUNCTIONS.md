# Order Management Functions Reference

## Complete Function List

### Core Functions

1. **`generate_pcf(pcf_date)`** - Generate Portfolio Composition File for NSCC
2. **`create_ap_order(...)`** - Create AP order (standard or custom basket)
3. **`process_ap_order(order, pcf)`** - Process and validate AP order
4. **`validate_ap_order(order, pcf)`** - Validate order against PCF

### Basket Construction

5. **`build_standard_creation_basket(pcf, creation_units)`** - Build standard creation basket
6. **`build_standard_redemption_basket(pcf, creation_units)`** - Build standard redemption basket
7. **`build_custom_creation_basket(pcf, creation_units, custom_securities)`** - Build custom creation basket
8. **`build_custom_redemption_basket(pcf, creation_units, custom_securities)`** - Build custom redemption basket
9. **`compare_baskets(basket1, basket2)`** - Compare two baskets

### Order Routing

10. **`route_order_to_custodian(order, basket)`** - Route order to custodian (TODO: implement)
11. **`route_order_to_nscc(order, basket)`** - Route order to NSCC (TODO: implement)

### Order Querying

12. **`get_order(order_id)`** - Get order by ID
13. **`get_orders_by_date(order_date)`** - Get all orders for a date
14. **`get_orders_by_ap(ap_id, start_date, end_date)`** - Get orders for specific AP

## Where to Create Custom vs Normal Baskets

### Standard Basket (Normal)

**Use when:** AP wants to use exact PCF composition (most common)

```python
# Create order with standard basket (basket=None)
order = om.create_ap_order(
    ap_id="AP001",
    order_type="creation",
    creation_units=10
    # basket=None is default = standard basket
)

# Or build basket manually first
pcf = om.generate_pcf(date.today())
basket = om.build_standard_creation_basket(pcf, creation_units=10)
```

### Custom Basket

**Use when:** AP wants different securities than PCF (tax optimization, inventory management)

```python
# Define custom basket
custom_basket = [
    {"cusip": "037833100", "quantity": "100"},
    {"cusip": "594918104", "quantity": "50"}
]

# Create order with custom basket
order = om.create_ap_order(
    ap_id="AP001",
    order_type="creation",
    creation_units=10,
    basket=custom_basket  # Custom basket specified
)

# Or build custom basket manually first
pcf = om.generate_pcf(date.today())
basket = om.build_custom_creation_basket(
    pcf=pcf,
    creation_units=10,
    custom_securities=custom_basket
)
```

## Workflow

### Standard Workflow (Most Common)

1. **Generate PCF** (daily, before market open)
   ```python
   pcf = om.generate_pcf(date.today())
   ```

2. **AP Creates Order** (standard basket)
   ```python
   order = om.create_ap_order(
       ap_id="AP001",
       order_type="creation",
       creation_units=10
   )
   ```

3. **Process Order** (automatically builds standard basket)
   ```python
   result = om.process_ap_order(order, pcf)
   # Basket is automatically built from PCF
   ```

### Custom Basket Workflow

1. **Generate PCF**
   ```python
   pcf = om.generate_pcf(date.today())
   ```

2. **AP Creates Custom Order**
   ```python
   custom_basket = [
       {"cusip": "037833100", "quantity": "100"},
       {"cusip": "594918104", "quantity": "50"}
   ]
   
   order = om.create_ap_order(
       ap_id="AP001",
       order_type="creation",
       creation_units=10,
       basket=custom_basket
   )
   ```

3. **Process Order** (validates and builds custom basket)
   ```python
   result = om.process_ap_order(order, pcf)
   # Custom basket is validated and built
   ```

## Key Points

- **Standard baskets**: Use `basket=None` (default) - uses exact PCF composition
- **Custom baskets**: Provide `basket=[...]` list - must validate against PCF
- **Basket construction**: Happens automatically in `process_ap_order()` or manually via build functions
- **Validation**: Custom baskets are validated (CUSIPs must be in PCF, prices must exist)
- **Routing**: Orders can be routed to custodian and NSCC (implement routing functions)

## Missing Functions (To Implement)

1. **`route_order_to_custodian()`** - TODO: Implement custodian integration
2. **`route_order_to_nscc()`** - TODO: Implement NSCC integration

These functions have TODO sections where you can add your actual integration code.

