from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

def load_performance_data():
    """Load performance data from Excel file"""
    try:
        print("Loading performance data from Excel...")
        
        # Read the Excel file
        df = pd.read_excel('data/performance_data.xlsx', sheet_name='Performance Data')
        print(f"Excel loaded with {len(df)} rows")
        
        # Convert date column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Calculate returns for different periods
        latest_date = df['Date'].max()
        print(f"Latest date in data: {latest_date}")
        
        # Calculate returns for different periods
        periods = {
            '1M': latest_date - timedelta(days=30),
            '3M': latest_date - timedelta(days=90),
            '6M': latest_date - timedelta(days=180),
            '1Y': latest_date - timedelta(days=365),
            'YTD': datetime(latest_date.year, 1, 1)
        }
        
        returns = {}
        for period_name, start_date in periods.items():
            period_data = df[df['Date'] >= start_date]
            if len(period_data) > 1:
                initial_values = period_data.iloc[0]
                final_values = period_data.iloc[-1]
                
                returns[period_name] = {
                    'RED_ETF': round(((final_values['RED_ETF'] / initial_values['RED_ETF']) - 1) * 100, 2),
                    'NAV': round(((final_values['NAV'] / initial_values['NAV']) - 1) * 100, 2),
                    'SP500': round(((final_values['SP500'] / initial_values['SP500']) - 1) * 100, 2)
                }
            else:
                returns[period_name] = {'RED_ETF': 0, 'NAV': 0, 'SP500': 0}
        
        print(f"Calculated returns for periods: {list(returns.keys())}")
        
        # Format data for charts - ensure dates are strings
        chart_data = {
            'labels': df['Date'].dt.strftime('%Y-%m-%d').tolist(),
            'datasets': [
                {
                    'label': 'RED ETF',
                    'data': df['RED_ETF'].round(2).tolist(),
                    'borderColor': '#dc2626',
                    'backgroundColor': 'rgba(220, 38, 38, 0.1)',
                    'borderWidth': 3,
                    'fill': False,
                    'tension': 0.4
                },
                {
                    'label': 'NAV',
                    'data': df['NAV'].round(2).tolist(),
                    'borderColor': '#2563eb',
                    'backgroundColor': 'rgba(37, 99, 235, 0.1)',
                    'borderWidth': 3,
                    'fill': False,
                    'tension': 0.4
                },
                {
                    'label': 'S&P 500',
                    'data': df['SP500'].round(2).tolist(),
                    'borderColor': '#6b7280',
                    'backgroundColor': 'rgba(107, 114, 128, 0.1)',
                    'borderWidth': 3,
                    'fill': False,
                    'tension': 0.4
                }
            ]
        }
        
        # Format premium/discount data
        premium_data = {
            'labels': df['Date'].dt.strftime('%Y-%m-%d').tolist(),
            'datasets': [
                {
                    'label': 'Premium/Discount',
                    'data': df['Premium_Discount'].round(2).tolist(),
                    'borderColor': '#8b0000',
                    'backgroundColor': 'rgba(139, 0, 0, 0.05)',
                    'borderWidth': 2,
                    'fill': True,
                    'tension': 0.1
                }
            ]
        }
        
        print(f"Chart data prepared with {len(chart_data['labels'])} labels")
        print(f"Sample labels: {chart_data['labels'][:3]}")
        print(f"Sample RED ETF data: {chart_data['datasets'][0]['data'][:3]}")
        print(f"Sample Premium/Discount data: {premium_data['datasets'][0]['data'][:3]}")
        
        result = {
            'chart_data': chart_data,
            'premium_data': premium_data,
            'returns': returns,
            'latest_values': {
                'RED_ETF': round(df['RED_ETF'].iloc[-1], 2),
                'NAV': round(df['NAV'].iloc[-1], 2),
                'SP500': round(df['SP500'].iloc[-1], 2),
                'Premium_Discount': round(df['Premium_Discount'].iloc[-1], 2)
            }
        }
        
        print("Data loading completed successfully")
        return result
        
    except Exception as e:
        print(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/api/performance-data')
def get_performance_data():
    """API endpoint to get performance data"""
    print("API request received for performance data")
    data = load_performance_data()
    if data:
        print("Returning performance data successfully")
        return jsonify(data)
    else:
        print("Failed to load performance data")
        return jsonify({'error': 'Failed to load data'}), 500

@app.route('/api/returns/<period>')
def get_returns(period):
    """API endpoint to get returns for a specific period"""
    data = load_performance_data()
    if data and period in data['returns']:
        return jsonify(data['returns'][period])
    else:
        return jsonify({'error': 'Period not found'}), 404

@app.route('/')
def home():
    """Simple home endpoint for testing"""
    return jsonify({'message': 'Performance data server is running'})

if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Check if Excel file exists, if not create it
    if not os.path.exists('data/performance_data.xlsx'):
        print("Creating sample performance data file...")
        # Create sample data with more realistic progression
        dates = pd.date_range(start='2024-01-01', end='2024-12-19', freq='D')
        
        # Create more realistic price movements
        import numpy as np
        np.random.seed(42)  # For reproducible results
        
        # Start with base values
        red_etf_base = 100
        nav_base = 100
        sp500_base = 100
        
        red_etf = []
        nav = []
        sp500 = []
        
        for i in range(len(dates)):
            # Add some daily variation
            red_etf_change = np.random.normal(0.15, 0.8)  # Daily return with volatility
            nav_change = np.random.normal(0.14, 0.75)
            sp500_change = np.random.normal(0.08, 0.6)
            
            if i == 0:
                red_etf.append(red_etf_base)
                nav.append(nav_base)
                sp500.append(sp500_base)
            else:
                red_etf.append(red_etf[-1] * (1 + red_etf_change/100))
                nav.append(nav[-1] * (1 + nav_change/100))
                sp500.append(sp500[-1] * (1 + sp500_change/100))
        
        df = pd.DataFrame({
            'Date': dates,
            'RED_ETF': [round(x, 2) for x in red_etf],
            'NAV': [round(x, 2) for x in nav],
            'SP500': [round(x, 2) for x in sp500]
        })
        
        df.to_excel('data/performance_data.xlsx', sheet_name='Performance Data', index=False)
        print("Created sample performance data file with realistic price movements")
    
    print("Performance data server starting on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True) 