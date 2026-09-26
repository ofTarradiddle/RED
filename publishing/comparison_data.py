"""Daily, validated Yahoo histories for the fixed USD ETF comparison universe.

``market_price`` is Yahoo Close, which already accounts for stock splits. It
must not be split-adjusted a second time. ``adjusted_close`` is Yahoo Adj Close
(distribution and split adjusted), or null when Yahoo does not provide it.
``distribution`` sums Yahoo Dividends and Capital Gains on the ex-date, on
Yahoo's split-adjusted per-share basis. ``split`` records the reported new/old
share ratio (zero means no action); it is informational, not a price multiplier.
These observations are market-price data, not the funds' official NAVs.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Callable
from zoneinfo import ZoneInfo


PEERS = {
    "SPY": "SPDR S&P 500 ETF Trust",
    "VOO": "Vanguard S&P 500 ETF",
    "QQQ": "Invesco QQQ Trust",
    "ITAN": "Sparkline Intangible Value ETF",
    "SYLD": "Cambria Shareholder Yield ETF",
}
DEFAULT_START = "2022-01-01"


def _timestamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _number(value, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"Invalid {field}")
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"Invalid {field}") from exc
    if not math.isfinite(result) or (result <= 0 if positive else result < 0):
        raise ValueError(f"Invalid {field}")
    return result


def validate_observations(observations: list, *, latest: date | None = None) -> list[dict]:
    """Reject invalid rows and ambiguous ordering rather than filling prices."""
    if not isinstance(observations, list) or not observations:
        raise ValueError("No usable daily observations")
    result = []
    previous = ""
    for row in observations:
        if not isinstance(row, dict):
            raise ValueError("Invalid observation row")
        text = row.get("date", "")
        if not isinstance(text, str):
            raise ValueError("Invalid observation date")
        parsed = date.fromisoformat(text)
        if parsed.isoformat() != text or text <= previous:
            raise ValueError("Observation dates must be unique and ascending")
        if latest is not None and parsed > latest:
            raise ValueError("Observation date is in the future")
        adjusted = row.get("adjusted_close")
        result.append({
            "date": text,
            "market_price": _number(row.get("market_price"), "market price", positive=True),
            "adjusted_close": None if adjusted is None else _number(adjusted, "adjusted close", positive=True),
            "distribution": _number(row.get("distribution"), "distribution"),
            "split": _number(row.get("split"), "split ratio"),
        })
        previous = text
    return result


def history_observations(frame, metadata: dict, symbol: str, now: datetime) -> list[dict]:
    """Normalize Yahoo rows, excluding a still-open current trading session."""
    import pandas as pd

    if metadata.get("symbol", "").upper() != symbol:
        raise ValueError("Yahoo security identity did not match the requested ticker")
    if metadata.get("currency") != "USD" or metadata.get("instrumentType") != "ETF":
        raise ValueError("Comparison universe requires a USD-denominated ETF")
    if frame is None or frame.empty or "Close" not in frame:
        raise ValueError("Yahoo did not return daily closing prices")
    local_now = now.astimezone(ZoneInfo(metadata.get("exchangeTimezoneName") or "America/New_York"))
    session = metadata.get("currentTradingPeriod", {}).get("regular", {})
    close_epoch = session.get("end")
    session_close = datetime.fromtimestamp(close_epoch, tz=timezone.utc) if close_epoch else None
    session_date = session_close.astimezone(local_now.tzinfo).date() if session_close else None
    observations = []
    for stamp, row in frame.iterrows():
        observation_date = stamp.date()
        if observation_date == local_now.date():
            # A five-minute publication buffer also avoids treating a closing
            # auction still in flight as the final daily bar.
            if session_date != observation_date or now < session_close + timedelta(minutes=5):
                continue
        adjusted = row.get("Adj Close")
        observations.append({
            "date": observation_date.isoformat(),
            "market_price": row["Close"],
            "adjusted_close": None if adjusted is None or pd.isna(adjusted) else adjusted,
            "distribution": _number(row.get("Dividends", 0), "dividend") + _number(row.get("Capital Gains", 0), "capital gain"),
            "split": row.get("Stock Splits", 0),
        })
    return validate_observations(observations, latest=local_now.date())


def fetch_yahoo(symbol: str, start: str, now: datetime) -> list[dict]:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    # auto_adjust=False preserves both explicit Close and Adj Close columns.
    # No repair/fill/backfill: gaps and corrections remain visible as supplied.
    frame = ticker.history(start=start, interval="1d", auto_adjust=False, actions=True, repair=False)
    return history_observations(frame, ticker.get_history_metadata(), symbol, now)


def _base(symbol: str) -> dict:
    return {
        "id": symbol, "name": PEERS[symbol], "currency": "USD", "kind": "etf",
        "source": "Yahoo Finance", "source_url": f"https://finance.yahoo.com/quote/{symbol}/history/",
        "as_of": None, "status": "unavailable", "is_illustrative": False, "observations": [],
    }


def validate_series(series: dict) -> dict:
    """Return a whitelisted public peer series or raise ValueError.

    Names and source URLs come from the fixed universe rather than cache input.
    The build can use this without importing pandas or yfinance.
    """
    if not isinstance(series, dict):
        raise ValueError("Invalid peer series")
    symbol = series.get("id")
    if not isinstance(symbol, str) or symbol not in PEERS:
        raise ValueError("Peer ticker is outside the permitted ETF universe")
    if (series.get("currency") != "USD" or series.get("kind") != "etf"
            or series.get("source") != "Yahoo Finance" or series.get("is_illustrative") is not False):
        raise ValueError("Peer series has invalid security/source metadata")
    status = series.get("status")
    if not isinstance(status, str) or status not in {"ok", "stale", "unavailable"}:
        raise ValueError("Invalid peer status")
    result = _base(symbol)
    if status == "unavailable":
        if series.get("observations") != [] or series.get("as_of") is not None:
            raise ValueError("Unavailable peer cannot contain a price history")
        result["error"] = "No validated history available."
        return result
    observations = validate_observations(series.get("observations"), latest=datetime.now(timezone.utc).date())
    if series.get("as_of") != observations[-1]["date"]:
        raise ValueError("Peer as-of date must match the final observation")
    result.update(status=status, as_of=observations[-1]["date"], observations=observations)
    if status == "stale":
        result["error"] = "Latest refresh failed; last validated history retained."
    return result


def _cached_series(previous: dict, symbol: str, now: datetime) -> list[dict] | None:
    if not isinstance(previous, dict) or previous.get("schema_version") != 1:
        return None
    if not isinstance(previous.get("series"), list):
        return None
    for item in previous.get("series", []):
        if not isinstance(item, dict) or item.get("id") != symbol:
            continue
        if (item.get("currency") != "USD" or item.get("kind") != "etf"
                or item.get("source") != "Yahoo Finance" or item.get("is_illustrative") is not False):
            return None
        try:
            return validate_observations(item.get("observations"), latest=now.date())
        except (ValueError, TypeError, AttributeError):
            return None
    return None


def refresh_dataset(previous: dict | None = None, *, start: str = DEFAULT_START,
                    now: datetime | None = None, fetcher: Callable = fetch_yahoo) -> dict:
    """Fetch all peers; retain a valid cache with explicit stale status on errors.

    Overall ``ok`` means all peers fetched successfully; ``partial`` means at
    least one usable peer exists but one or more fetches failed; ``unavailable``
    means no usable observations remain. A stale cached peer counts as usable.
    ``generated_at`` and ``last_attempt_at`` identify this refresh attempt;
    per-series ``as_of`` always identifies its final observed trading date.
    """
    parsed_start = date.fromisoformat(start)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Refresh time must include a timezone")
    if parsed_start > now.date():
        raise ValueError("Start date cannot be in the future")
    previous = previous or {}
    result = {"schema_version": 1, "generated_at": _timestamp(now), "last_attempt_at": _timestamp(now),
              "status": "ok", "series": []}
    for symbol in PEERS:
        item = _base(symbol)
        try:
            observations = validate_observations(fetcher(symbol, start, now), latest=now.date())
            if any(row["date"] < start for row in observations):
                raise ValueError("Yahoo returned observations before the requested start date")
            cached = _cached_series(previous, symbol, now)
            if cached and observations[-1]["date"] < cached[-1]["date"]:
                raise ValueError("Yahoo returned history older than the validated cache")
            item.update(status="ok", as_of=observations[-1]["date"], observations=observations)
        except Exception as exc:
            cached = _cached_series(previous, symbol, now)
            if cached:
                item.update(status="stale", as_of=cached[-1]["date"], observations=cached)
            # Do not serialize provider exception text: it may include URLs,
            # headers or machine-specific paths. This is enough for UI and CI.
            item["error"] = f"Refresh failed ({type(exc).__name__}); " + (
                "last validated history retained." if cached else "no validated history available.")
        result["series"].append(item)
    if any(item["status"] != "ok" for item in result["series"]):
        result["status"] = "partial" if any(item["observations"] for item in result["series"]) else "unavailable"
    return result


def read_cache(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
