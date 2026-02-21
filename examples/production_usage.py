"""
Production Usage Example
Shows how to use the production-ready self-service functions
"""

import sys
from pathlib import Path
from datetime import date

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.self_service_functions import SelfServiceFunctionsManager
from lib.data_adapter_example import FileBasedDataSourceAdapter, ExampleDataSourceAdapter


def main():
    """Example of using the production-ready functions"""
    
    # Option 1: Use file-based adapter for testing/development
    print("=" * 80)
    print("Example 1: File-Based Adapter (for testing)")
    print("=" * 80)
    
    file_adapter = FileBasedDataSourceAdapter(data_path="./data")
    manager = SelfServiceFunctionsManager(file_adapter, is_paying_agent=False)
    
    # Run daily operations
    today = date.today()
    results = manager.run_daily_operations(today)
    
    print(f"\nDaily Operations Results for {today}:")
    print(f"\nTA Reconciliation Status: {results['ta']['reconciliation'].status}")
    print(f"TA Cede Update Status: {results['ta']['cede_update']['status']}")
    print(f"NAV per Share: ${results['admin']['nav'].nav_per_share}")
    print(f"PCF Securities Count: {len(results['om']['pcf'].securities)}")
    
    # Option 2: Use your custom adapter (implement ExampleDataSourceAdapter)
    print("\n" + "=" * 80)
    print("Example 2: Custom Adapter (implement your data sources)")
    print("=" * 80)
    
    # Create your custom adapter with your data source connections
    config = {
        # Add your actual connection details here
        # "nscc_api_key": "your_key",
        # "dtc_username": "your_username",
        # "custodian_api_url": "https://...",
        # "market_data_api_key": "your_key"
    }
    
    custom_adapter = ExampleDataSourceAdapter(config=config)
    custom_manager = SelfServiceFunctionsManager(custom_adapter, is_paying_agent=False)
    
    # Run daily operations with your data sources
    # results = custom_manager.run_daily_operations(today)
    
    print("\nTo use with your data sources:")
    print("1. Implement the methods in ExampleDataSourceAdapter")
    print("2. Connect to your actual data sources (NSCC, DTC, Custodian, etc.)")
    print("3. Return data in the expected format")
    print("4. Use SelfServiceFunctionsManager to run daily operations")
    
    # Individual function usage examples
    print("\n" + "=" * 80)
    print("Individual Function Usage")
    print("=" * 80)
    
    # TA Operations
    print("\nTA Operations:")
    recon_result = manager.ta.daily_reconciliation(today)
    print(f"  Reconciliation: {recon_result.status}, Difference: {recon_result.difference}")
    
    cede_result = manager.ta.update_cede_file(today)
    print(f"  Cede Update: {cede_result['status']}, Position: {cede_result['cede_position']}")
    
    # Admin Operations
    print("\nAdmin Operations:")
    nav_result = manager.admin.calculate_nav(today)
    print(f"  NAV: ${nav_result.nav_per_share} per share")
    print(f"  Net Assets: ${nav_result.net_assets}")
    print(f"  Validation: {'PASSED' if nav_result.validation_passed else 'FAILED'}")
    
    # OM Operations
    print("\nOM Operations:")
    pcf_result = manager.om.generate_pcf(today)
    print(f"  PCF Generated: {len(pcf_result.securities)} securities")
    print(f"  Validation: {'PASSED' if pcf_result.validation_passed else 'FAILED'}")
    if pcf_result.errors:
        print(f"  Errors: {pcf_result.errors}")


if __name__ == "__main__":
    main()

