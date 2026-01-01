"""
Test script to plot NVDA returns since 2000 using YahooPriceLoader
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime
from lib.etf.functions.research import YahooPriceLoader

def plot_nvda_returns():
    """Plot NVDA returns since 2000"""
    
    # Initialize Yahoo price loader
    price_loader = YahooPriceLoader()
    
    # Get NVDA prices since 2000
    start_date = "2000-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Fetching NVDA prices from {start_date} to {end_date}...")
    price_df = price_loader.get_adjusted_close(
        symbols=["NVDA"],
        start_date=start_date,
        end_date=end_date
    )
    
    if price_df.empty:
        print("No data retrieved for NVDA")
        return
    
    print(f"Retrieved {len(price_df)} days of data")
    print(f"Date range: {price_df.index.min()} to {price_df.index.max()}")
    print(f"\nFirst few prices:")
    print(price_df.head())
    print(f"\nLast few prices:")
    print(price_df.tail())
    
    # Calculate returns
    returns = price_loader.calculate_returns(price_df)
    
    # Calculate cumulative returns
    cumulative_returns = (1 + returns).cumprod() - 1
    
    # Create figure with subplots
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    fig.suptitle('NVDA Analysis Since 2000', fontsize=16, fontweight='bold')
    
    # Plot 1: Price over time
    axes[0].plot(price_df.index, price_df['NVDA'], linewidth=1.5, color='blue')
    axes[0].set_title('NVDA Adjusted Close Price (Total Return)', fontsize=12, fontweight='bold')
    axes[0].set_ylabel('Price ($)', fontsize=10)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlabel('Date', fontsize=10)
    
    # Plot 2: Daily returns
    axes[1].plot(returns.index, returns['NVDA'], linewidth=0.5, color='green', alpha=0.6)
    axes[1].axhline(y=0, color='black', linestyle='--', linewidth=0.8)
    axes[1].set_title('NVDA Daily Returns', fontsize=12, fontweight='bold')
    axes[1].set_ylabel('Daily Return', fontsize=10)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlabel('Date', fontsize=10)
    
    # Plot 3: Cumulative returns
    axes[2].plot(cumulative_returns.index, cumulative_returns['NVDA'] * 100, 
                 linewidth=2, color='purple')
    axes[2].axhline(y=0, color='black', linestyle='--', linewidth=0.8)
    axes[2].set_title('NVDA Cumulative Returns', fontsize=12, fontweight='bold')
    axes[2].set_ylabel('Cumulative Return (%)', fontsize=10)
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlabel('Date', fontsize=10)
    
    # Calculate and print statistics
    total_return = cumulative_returns['NVDA'].iloc[-1]
    annual_return = (1 + total_return) ** (252 / len(returns)) - 1
    volatility = returns['NVDA'].std() * (252 ** 0.5)
    sharpe = annual_return / volatility if volatility > 0 else 0
    
    print(f"\n{'='*60}")
    print("NVDA Performance Statistics (Since 2000)")
    print(f"{'='*60}")
    print(f"Total Return: {total_return*100:.2f}%")
    print(f"Annualized Return: {annual_return*100:.2f}%")
    print(f"Annualized Volatility: {volatility*100:.2f}%")
    print(f"Sharpe Ratio (assuming risk-free rate = 0): {sharpe:.2f}")
    print(f"Number of Trading Days: {len(returns)}")
    print(f"{'='*60}\n")
    
    plt.tight_layout()
    
    # Create output directory if it doesn't exist
    output_dir = Path("./data/research")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save plot
    output_file = output_dir / "nvda_returns_plot.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {output_file}")
    
    # Also save data to CSV
    output_data = pd.DataFrame({
        'Date': price_df.index,
        'Price': price_df['NVDA'],
        'Daily_Return': returns['NVDA'],
        'Cumulative_Return': cumulative_returns['NVDA']
    })
    csv_file = output_dir / "nvda_returns_data.csv"
    output_data.to_csv(csv_file, index=False)
    print(f"Data saved to: {csv_file}")
    
    # Note: plt.show() removed since we're using non-GUI backend
    # To view interactively, change matplotlib.use('Agg') to matplotlib.use('TkAgg') or remove that line

if __name__ == "__main__":
    plot_nvda_returns()

