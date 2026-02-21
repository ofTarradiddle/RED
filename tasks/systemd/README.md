# Systemd Service Files for ETF Operations

Production-ready systemd service and timer files for scheduling ETF operations.

## Installation

1. **Update paths in service files:**
   - Replace `/path/to/etf-web` with your actual project path
   - Replace `/usr/bin/python3` with your Python interpreter path if different
   - Replace `etf-user` with your actual user/group

2. **Copy service files:**
   ```bash
   sudo cp daily-operations.service /etc/systemd/system/
   sudo cp daily-operations.timer /etc/systemd/system/
   sudo cp weekly-operations.service /etc/systemd/system/
   sudo cp weekly-operations.timer /etc/systemd/system/
   sudo cp monthly-operations.service /etc/systemd/system/
   sudo cp monthly-operations.timer /etc/systemd/system/
   ```

3. **Reload systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

4. **Enable and start timers:**
   ```bash
   sudo systemctl enable daily-operations.timer
   sudo systemctl enable weekly-operations.timer
   sudo systemctl enable monthly-operations.timer
   
   sudo systemctl start daily-operations.timer
   sudo systemctl start weekly-operations.timer
   sudo systemctl start monthly-operations.timer
   ```

## Management

### Check timer status:
```bash
sudo systemctl status daily-operations.timer
sudo systemctl list-timers
```

### Check service status:
```bash
sudo systemctl status daily-operations.service
```

### View logs:
```bash
# Service logs
sudo journalctl -u daily-operations.service

# Application logs
tail -f /path/to/etf-web/logs/daily_operations.log
```

### Manually trigger:
```bash
sudo systemctl start daily-operations.service
```

### Disable:
```bash
sudo systemctl stop daily-operations.timer
sudo systemctl disable daily-operations.timer
```

## Scheduling

### Daily Operations
- **Timer**: Runs daily at 6:00 PM (18:00)
- **Adjust**: Change `OnCalendar` in timer file
- **Example**: `OnCalendar=*-*-* 18:00:00` (daily at 6 PM)

### Weekly Operations
- **Timer**: Runs Fridays at 5:00 PM (17:00)
- **Adjust**: Change `OnCalendar` in timer file
- **Example**: `OnCalendar=Fri *-*-* 17:00:00` (Fridays at 5 PM)

### Monthly Operations
- **Timer**: Runs 1st of month at 4:00 PM (16:00)
- **Adjust**: Change `OnCalendar` in timer file
- **Example**: `OnCalendar=*-*-01 16:00:00` (1st of month at 4 PM)

## Time Zone

Systemd uses system timezone. To use ET:
1. Set system timezone: `sudo timedatectl set-timezone America/New_York`
2. Or adjust times in timer files to match your timezone

## Monitoring

Set up monitoring/alerts for:
- Service failures: `systemctl is-failed daily-operations.service`
- Timer failures: Check timer status
- Log errors: Monitor error log files
- Missing executions: Check log file timestamps

## Security

- Services run as non-root user (`etf-user`)
- `NoNewPrivileges=true` prevents privilege escalation
- `PrivateTmp=true` uses private temporary directory

