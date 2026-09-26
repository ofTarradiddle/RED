"""Deterministic illustrative workbook tables. No market observations or live claims."""
from datetime import date, timedelta
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parents[1]


def seed():
    from publishing.workbook import SCHEMA
    definitions = [
        ("redi", "REDI", "Innovation Factor", "Innovation with a measurable foundation.", "A proposed systematic approach to innovation, business quality and the capacity to reinvest.", .0045),
        ("dam1", "DAM1", "World’s Largest 111", "A lens on global scale.", "A proposed portfolio focused on large global companies, with concentration and country exposures made explicit.", .0029),
        ("azoc", "AZOC", "Azoth", "Different signals. One considered portfolio.", "A proposed equity strategy combining valuation, quality and other systematic signals.", .0039),
        ("mpd", "MPD", "Growthy Compounders", "The discipline behind compounding.", "A proposed portfolio examining reinvestment, profitability and the durability of competitive advantages.", .0045),
        ("meri", "MERI", "Merriment of F&Q", "Quantitative structure. Fundamental context.", "A proposed approach pairing systematic screens with company-level fundamental research.", .0055),
    ]
    tables = {name: [headers] for name, headers in SCHEMA.items()}
    start, end = date(2024, 1, 2), date(2026, 9, 18)
    dates = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)
    # Weekday-only fictional observations, not an exchange-session calendar.
    for n, (fid, ticker, name, strategy, description, fee) in enumerate(definitions):
        benchmark_label = 'Morningstar US Market Index' if fid == 'redi' else 'Illustrative equity benchmark'
        tables["Funds"].append([fid, ticker, f"Hetzerk {name} ETF", strategy, description, fee, start.isoformat(), True, benchmark_label, .02])
        nav = 25.0
        benchmark = 100.0
        shares = 1_000_000
        for i, d in enumerate(dates):
            dividend = .08 if d.month in (3, 6, 9, 12) and d.day == 15 else 0.0
            if i:
                nav *= 1 + .00019 + .0028 * math.sin(i * .28 + n) + .002 * math.cos(i * .13)
                benchmark *= 1 + .00017 + .0025 * math.sin(i * .23) + .0015 * math.cos(i * .09)
                nav -= dividend
            market = nav * (1 + .0008 * math.sin(i * .63 + n))
            nav, market, benchmark = round(nav, 6), round(market, 6), round(benchmark, 6)
            tables["Daily Data"].append([fid, d.isoformat(), nav, market, benchmark, nav * shares, shares, dividend])
            if dividend:
                payable = d + timedelta(days=7)
                tables["Distributions"].append([fid, d.isoformat(), d.isoformat(), payable.isoformat(), dividend, 0, 0, 0])
        original = json.loads((ROOT / "etfs" / fid / "data/holdings_data.json").read_text())
        original = [h for h in original if h["weight"] > 0]
        weight_total = sum(h["weight"] for h in original)
        net_assets = nav * shares
        allocated = 0
        for i, h in enumerate(original):
            mv = net_assets * .98 * h["weight"] / weight_total
            price = float(30 + (i * 17 + n * 13) % 270)
            quantity = mv / price
            allocated += mv
            tables["Holdings"].append([fid, end.isoformat(), h["ticker"], f"DEMO:{h['ticker']}", h["name"], h["sector"], h.get("country", "USA"), "USD", "equity", quantity, price, 1, mv])
        cash = net_assets - allocated
        tables["Holdings"].append([fid, end.isoformat(), "CASH", "DEMO:USD-CASH", "US dollar cash", "Cash", "USA", "USD", "cash", cash, 1, 1, cash])
        for kind, title in [("prospectus", "Statutory prospectus"), ("summary_prospectus", "Summary prospectus"), ("sai", "Statement of additional information"), ("annual_report", "Annual shareholder report"), ("semiannual_report", "Semiannual shareholder report"), ("quarterly_holdings", "First / third fiscal-quarter holdings")]:
            tables["Documents"].append([fid, kind, title, "", "", "unavailable"])
    return tables


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    print(json.dumps(seed(), allow_nan=False))
