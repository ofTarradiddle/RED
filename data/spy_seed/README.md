# Initial public inventory archive

These unmodified State Street SPY daily holdings files were retrieved for the
September 2026 local reconciliation. The filenames use each workbook's embedded
holdings date. They bootstrap the inventory archive; they are never relabelled
as a current day's holdings.

Source: https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx

`daily_spy.refresh` validates each workbook and archives its bytes by date and
SHA-256. The September 23 valuation uses the September 22 inventory under the
explicit prior-session policy. Later runs retain new inventory through the
GitHub Actions public-market cache. A cold start after these dates may require
a daily warm-up run before the private comparison has its prior-session file.

No operating accounts, actual execution blotter or private dashboard is included
in these files. See `docs/SHADOW_NAV.md` for date alignment and source limitations.
