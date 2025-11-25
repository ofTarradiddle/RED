# Tasks

Production-ready scripts for running daily, weekly, and monthly operations.

## Daily Operations

Runs all daily operations for Accounting, Admin, TA, OM, and Distributor.

```bash
# Run for today
python tasks/daily_operations.py

# Run for specific date
python tasks/daily_operations.py --date 2024-01-15

# Use custom data adapter
python tasks/daily_operations.py --adapter custom
```

**Operations:**
1. Admin: Calculate NAV
2. Admin: Reconcile holdings and cash
3. TA: Daily reconciliation
4. TA: Update Cede file
5. TA: Process creation/redemption orders
6. OM: Generate PCF
7. OM: Process AP orders
8. Accounting: Daily accounting operations
9. Distributor: Check for pending distributions

## Weekly Operations

Runs weekly reporting and analysis.

```bash
# Run for current week
python tasks/weekly_operations.py

# Run for specific week end date
python tasks/weekly_operations.py --date 2024-01-15
```

**Operations:**
- Generate trial balance
- Calculate expense ratio
- Weekly reconciliation reports

## Monthly Operations

Runs monthly financial reporting.

```bash
# Run for current month
python tasks/monthly_operations.py

# Run for specific month end date
python tasks/monthly_operations.py --date 2024-01-31
```

**Operations:**
- Generate balance sheet
- Generate income statement
- Generate distribution schedule
- Monthly reconciliation

## Scheduling

### Option 1: Cron Jobs (Linux/Mac)

**Quick Setup:**
1. Edit `tasks/cron_jobs.sh` and update `PROJECT_PATH` and `PYTHON_PATH`
2. Copy to crontab: `crontab tasks/cron_jobs.sh`
3. Or copy to `/etc/cron.d/etf-operations` (system-wide)

**Manual Setup:**
```bash
# Daily operations at 6 PM
0 18 * * * cd /path/to/etf-web && python tasks/daily_operations.py >> logs/daily_$(date +\%Y\%m\%d).log 2>&1

# Weekly operations on Fridays at 5 PM
0 17 * * 5 cd /path/to/etf-web && python tasks/weekly_operations.py >> logs/weekly_$(date +\%Y\%m\%d).log 2>&1

# Monthly operations on last day of month at 4 PM
0 16 28-31 * * [ $(date -d tomorrow +\%d) -eq 1 ] && cd /path/to/etf-web && python tasks/monthly_operations.py >> logs/monthly_$(date +\%Y\%m\%d).log 2>&1
```

**See `tasks/cron_jobs.sh` for complete configuration.**

### Option 2: Systemd (Linux - Recommended)

**Production-ready systemd service files are provided in `tasks/systemd/`**

**Installation:**
1. Update paths in service files (replace `/path/to/etf-web` and `etf-user`)
2. Copy service files:
   ```bash
   sudo cp tasks/systemd/*.service /etc/systemd/system/
   sudo cp tasks/systemd/*.timer /etc/systemd/system/
   ```
3. Reload and enable:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable daily-operations.timer
   sudo systemctl enable weekly-operations.timer
   sudo systemctl enable monthly-operations.timer
   sudo systemctl start daily-operations.timer
   sudo systemctl start weekly-operations.timer
   sudo systemctl start monthly-operations.timer
   ```

**See `tasks/systemd/README.md` for complete documentation.**

### Option 3: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task for each script:
   - Daily: Trigger daily at 6 PM
   - Weekly: Trigger weekly on Fridays at 5 PM
   - Monthly: Trigger monthly on last day at 4 PM
3. Set action: Start a program
   - Program: `python.exe` (or full path)
   - Arguments: `tasks\daily_operations.py`
   - Start in: Project directory
4. Set working directory to project folder

## Logging

All tasks log to stdout/stderr. Redirect to files:

```bash
python tasks/daily_operations.py >> logs/daily_$(date +\%Y\%m\%d).log 2>&1
```

## Error Handling

All tasks include error handling and will:
- Log errors to console
- Save error information in results file
- Continue processing other operations when possible

## Results

Results are saved to `./data/` directory:
- `daily_operations_YYYY-MM-DD.json`
- `weekly_operations_YYYY-MM-DD.json`
- `monthly_operations_YYYY-MM-DD.json`

