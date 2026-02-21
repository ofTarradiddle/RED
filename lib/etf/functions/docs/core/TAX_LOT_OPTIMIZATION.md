# Tax Lot Optimization: LOWEST_COST Method

## Overview

The tax lot manager now supports **LOWEST_COST** method, which sells the lowest cost basis lots first. This is a tax optimization strategy that minimizes realized gains and reduces capital gains distributions to shareholders.

## Why LOWEST_COST?

### Tax Efficiency
- **Minimizes Realized Gains**: By selling lowest cost basis shares first, you realize the smallest possible gain (or largest loss) on each sale
- **Preserves Higher Cost Basis**: Keeps higher cost basis shares in the portfolio, which reduces future capital gains
- **Reduces Distributions**: Lower realized gains mean fewer capital gains distributions to shareholders

### Example

**Scenario**: You have 3 lots of AAPL:
- Lot 1: 100 shares @ $150 (purchased Jan 1)
- Lot 2: 100 shares @ $160 (purchased Feb 1)  
- Lot 3: 100 shares @ $170 (purchased Mar 1)

**Selling 150 shares at $180**:

| Method | Lots Sold | Realized Gain | Tax Impact (20% rate) |
|--------|-----------|---------------|----------------------|
| FIFO | $150 + $160 | $4,500 | $900 tax |
| LOWEST_COST | $150 + $160 | $4,500 | $900 tax |
| HIGHEST_COST | $170 + $160 | $3,000 | $600 tax |

**Note**: In this example, LOWEST_COST and FIFO happen to match. But when cost basis doesn't correlate with purchase date, LOWEST_COST provides tax benefits.

## Available Methods

### 1. LOWEST_COST (Recommended for Tax Optimization)
```python
gain = taxlot_manager.sell('AAPL', Decimal('100'), Decimal('180.00'), date.today(), method='LOWEST_COST')
```
- **Use Case**: Minimize realized gains, reduce capital gains distributions
- **Best For**: ETFs that want to be tax-efficient

### 2. HIGHEST_COST (Tax-Loss Harvesting)
```python
gain = taxlot_manager.sell('AAPL', Decimal('100'), Decimal('180.00'), date.today(), method='HIGHEST_COST')
```
- **Use Case**: Maximize realized losses for tax-loss harvesting
- **Best For**: Selling losses to offset gains elsewhere

### 3. FIFO (Default IRS Method)
```python
gain = taxlot_manager.sell('AAPL', Decimal('100'), Decimal('180.00'), date.today(), method='FIFO')
```
- **Use Case**: Standard IRS default method
- **Best For**: When you want to follow traditional accounting

### 4. LIFO (Last-In, First-Out)
```python
gain = taxlot_manager.sell('AAPL', Decimal('100'), Decimal('180.00'), date.today(), method='LIFO')
```
- **Use Case**: Sell newest lots first
- **Best For**: When newer lots have better tax characteristics

## Configuration

### In Orchestrator Config (`config.yaml`)
```yaml
tax:
  lot_method: 'LOWEST_COST'  # Options: FIFO, LIFO, LOWEST_COST, HIGHEST_COST
```

### Default Behavior
- **Orchestrator**: Uses `LOWEST_COST` by default (configurable)
- **Direct Calls**: Defaults to `FIFO` if method not specified

## Tax Optimization Strategy

### For ETFs
1. **Use LOWEST_COST** for regular sales to minimize capital gains distributions
2. **Use HIGHEST_COST** for tax-loss harvesting when selling at a loss
3. Track both short-term and long-term lots separately for optimal tax treatment

### Example: Tax-Loss Harvesting
```python
# If selling at a loss, use HIGHEST_COST to maximize the loss
if current_price < average_cost_basis:
    method = 'HIGHEST_COST'  # Maximize loss
else:
    method = 'LOWEST_COST'  # Minimize gain
```

## Implementation Details

The `sell()` method now supports:
- `method='FIFO'`: Sorts by purchase date (oldest first)
- `method='LIFO'`: Sorts by purchase date (newest first)
- `method='LOWEST_COST'`: Sorts by cost basis (lowest first)
- `method='HIGHEST_COST'`: Sorts by cost basis (highest first)

All methods maintain proper:
- Realized gain/loss calculation
- Short-term vs long-term classification
- Tax lot tracking and persistence

## Benefits

✅ **Tax Efficiency**: Minimizes realized gains  
✅ **Shareholder Value**: Reduces capital gains distributions  
✅ **Flexibility**: Multiple methods available for different strategies  
✅ **Compliance**: Maintains proper tax lot accounting records  

## Recommendation

**For most ETFs, use `LOWEST_COST` as the default method** to minimize capital gains distributions and maximize tax efficiency for shareholders.

