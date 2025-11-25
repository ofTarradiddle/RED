#!/bin/bash
# Production-Ready Cron Jobs for ETF Operations
# 
# Installation:
# 1. Update PROJECT_PATH below to your actual project path
# 2. Update PYTHON_PATH to your Python interpreter path
# 3. Copy to /etc/cron.d/etf-operations (or add to crontab)
# 4. Set permissions: chmod 644 /etc/cron.d/etf-operations
#
# For user crontab: crontab -e, then paste the job definitions

# Configuration - UPDATE THESE
PROJECT_PATH="/path/to/etf-web"
PYTHON_PATH="/usr/bin/python3"
LOG_DIR="${PROJECT_PATH}/logs"
DATA_DIR="${PROJECT_PATH}/data"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Daily Operations - Run at 6:00 PM ET (after market close and data is available)
# Adjust time based on when your data sources are available
0 18 * * * cd ${PROJECT_PATH} && ${PYTHON_PATH} tasks/daily_operations.py >> ${LOG_DIR}/daily_$(date +\%Y\%m\%d).log 2>&1

# Weekly Operations - Run Fridays at 5:00 PM ET
0 17 * * 5 cd ${PROJECT_PATH} && ${PYTHON_PATH} tasks/weekly_operations.py >> ${LOG_DIR}/weekly_$(date +\%Y\%m\%d).log 2>&1

# Monthly Operations - Run on last business day of month at 4:00 PM ET
# This runs on days 28-31, but only executes if tomorrow is the 1st (i.e., last day of month)
0 16 28-31 * * [ $(date -d tomorrow +\%d) -eq 1 ] && cd ${PROJECT_PATH} && ${PYTHON_PATH} tasks/monthly_operations.py >> ${LOG_DIR}/monthly_$(date +\%Y\%m\%d).log 2>&1

# Alternative: Monthly Operations - Run on 1st of month for previous month
# 0 16 1 * * cd ${PROJECT_PATH} && ${PYTHON_PATH} tasks/monthly_operations.py --date $(date -d "yesterday" +\%Y-\%m-\%d) >> ${LOG_DIR}/monthly_$(date +\%Y\%m).log 2>&1

# Cleanup old logs (keep last 90 days) - Run daily at 2:00 AM
0 2 * * * find ${LOG_DIR} -name "*.log" -mtime +90 -delete

# Notes:
# - Times are in server local time (adjust for ET if needed)
# - All output goes to dated log files
# - Errors are captured in log files
# - Monitor log files for failures
# - Set up log rotation if needed

