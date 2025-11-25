"""
Example usage of self-service functions
Demonstrates how to use the base functions for Admin, TA, and OM
"""

import sys
import os

# Add parent directory to path to import lib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.self_service_functions import (
    SelfServiceFunctionsManager,
    FunctionType
)


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")


def main():
    """Main example function"""
    
    print_section("SELF-SERVICE FUNCTIONS: COST ANALYSIS")
    
    # Create manager with non-paying agent (as specified)
    manager = SelfServiceFunctionsManager(is_paying_agent=False)
    
    # Get cost summary
    cost_summary = manager.get_cost_summary()
    
    print_subsection("Startup Costs (One-Time)")
    print(f"Transfer Agent (TA):     ${cost_summary['startup_costs']['ta']:>12,.2f}")
    print(f"Administration (Admin):  ${cost_summary['startup_costs']['admin']:>12,.2f}")
    print(f"Order Management (OM):   ${cost_summary['startup_costs']['om']:>12,.2f}")
    print(f"{'Total Startup Cost':<25} ${cost_summary['startup_costs']['total']:>12,.2f}")
    
    print_subsection("Annual Recurring Costs")
    print(f"Transfer Agent (TA):     ${cost_summary['annual_costs']['ta']:>12,.2f}")
    print(f"Administration (Admin):  ${cost_summary['annual_costs']['admin']:>12,.2f}")
    print(f"Order Management (OM):   ${cost_summary['annual_costs']['om']:>12,.2f}")
    print(f"{'Total Annual Cost':<25} ${cost_summary['annual_costs']['total']:>12,.2f}")
    
    print_subsection("TA Responsibilities")
    for i, resp in enumerate(manager.ta.responsibilities, 1):
        print(f"{i:2}. {resp}")
    
    print_subsection("TA Daily Tasks")
    for task in manager.ta.get_daily_tasks():
        print(f"\n• {task.name}")
        print(f"  Description: {task.description}")
        if task.inputs:
            print(f"  Inputs: {', '.join(task.inputs)}")
        if task.outputs:
            print(f"  Outputs: {', '.join(task.outputs)}")
    
    print_subsection("TA Data Sources")
    for source in manager.ta.data_sources:
        print(f"\n• {source.name}")
        print(f"  Type: {source.source_type}")
        print(f"  Frequency: {source.frequency}")
        print(f"  Format: {source.format}")
        print(f"  Description: {source.description}")
    
    print_subsection("TA Cede File Update Process")
    cede_process = manager.ta.get_cede_file_update_process()
    print(f"\nDescription: {cede_process['description']}")
    print(f"Frequency: {cede_process['frequency']}")
    print(f"Data Source: {cede_process['data_source']}")
    print("\nProcess Steps:")
    for i, step in enumerate(cede_process['process'], 1):
        print(f"  {i}. {step}")
    print("\nReal-Time Data Sources:")
    for source in cede_process['real_time_data_sources']:
        print(f"  • {source}")
    
    print_subsection("Admin Responsibilities")
    for i, resp in enumerate(manager.admin.responsibilities, 1):
        print(f"{i:2}. {resp}")
    
    print_subsection("Admin Daily Tasks")
    for task in manager.admin.get_daily_tasks():
        print(f"\n• {task.name}")
        print(f"  Description: {task.description}")
        if task.inputs:
            print(f"  Inputs: {', '.join(task.inputs)}")
        if task.outputs:
            print(f"  Outputs: {', '.join(task.outputs)}")
    
    print_subsection("OM Responsibilities")
    for i, resp in enumerate(manager.om.responsibilities, 1):
        print(f"{i:2}. {resp}")
    
    print_subsection("OM Daily Tasks")
    for task in manager.om.get_daily_tasks():
        print(f"\n• {task.name}")
        print(f"  Description: {task.description}")
        if task.inputs:
            print(f"  Inputs: {', '.join(task.inputs)}")
        if task.outputs:
            print(f"  Outputs: {', '.join(task.outputs)}")
    
    print_subsection("OM PCF Publication Process")
    pcf_process = manager.om.get_pcf_publication_process()
    print(f"\nDescription: {pcf_process['description']}")
    print(f"Deadline: {pcf_process['deadline']}")
    print("\nPCF Contents:")
    for item in pcf_process['contents']:
        print(f"  • {item}")
    print("\nData Sources:")
    for source in pcf_process['data_sources']:
        print(f"  • {source}")
    print("\nProcess Steps:")
    for i, step in enumerate(pcf_process['process'], 1):
        print(f"  {i}. {step}")
    
    print_subsection("Key Differences: OM vs TA")
    print("""
Order Management (OM) focuses on:
  - Order processing and basket construction
  - PCF publication
  - Pre-trade and trade execution activities
  - Interface with APs and NSCC

Transfer Agent (TA) focuses on:
  - Shareholder recordkeeping
  - Account management
  - Post-trade settlement activities
  - Interface with shareholders, DTC, and broker-dealers

They are complementary but distinct functions:
  - OM handles the "front-end" - getting orders, building baskets, publishing PCF
  - TA handles the "back-end" - recording who owns what after orders settle
    """)
    
    print_section("SUMMARY")
    print(f"Total Startup Investment Required: ${manager.get_total_startup_cost():,.2f}")
    print(f"Total Annual Operating Cost: ${manager.get_total_annual_cost():,.2f}")
    print(f"\nNote: These are base estimates. Actual costs may vary based on:")
    print("  - Fund size and complexity")
    print("  - Trading volume")
    print("  - Technology choices")
    print("  - Staffing levels")
    print("  - Vendor relationships")


if __name__ == "__main__":
    main()

