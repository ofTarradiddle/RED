from datetime import datetime, timezone
import json

import pandas as pd
import pytest

from publishing.comparison_data import history_observations, refresh_dataset, validate_observations, validate_series, write_atomic


NOW = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)


def rows():
    return [dict(date="2026-09-24", market_price=100, adjusted_close=98, distribution=0, split=0),
            dict(date="2026-09-25", market_price=99, adjusted_close=99, distribution=1, split=0)]


def metadata(**kwargs):
    return dict(symbol="SPY", currency="USD", instrumentType="ETF", exchangeTimezoneName="America/New_York", **kwargs)


def test_actions_use_yahoo_basis_without_double_adjusting_splits():
    frame = pd.DataFrame({"Close": [100.0, 99.0], "Adj Close": [98.0, 99.0],
                          "Dividends": [0.0, 0.75], "Capital Gains": [0.0, 0.25],
                          "Stock Splits": [2.0, 0.0]},
                         index=pd.to_datetime(["2026-09-24", "2026-09-25"]))
    observed = history_observations(frame, metadata(), "SPY", NOW)
    assert observed[0]["market_price"] == 100  # Already split adjusted by Yahoo.
    assert observed[0]["split"] == 2
    assert observed[1]["distribution"] == 1
    assert observed[0]["adjusted_close"] == 98


@pytest.mark.parametrize("field,value", [("market_price", 0), ("market_price", float("nan")),
                                          ("market_price", float("inf")), ("adjusted_close", -1),
                                          ("distribution", -1), ("split", -2)])
def test_invalid_values_rejected(field, value):
    sample = rows()
    sample[0][field] = value
    with pytest.raises(ValueError):
        validate_observations(sample)


def test_ambiguous_dates_rejected():
    with pytest.raises(ValueError, match="unique and ascending"):
        validate_observations([rows()[0], rows()[0]])
    with pytest.raises(ValueError, match="unique and ascending"):
        validate_observations(rows()[::-1])


def test_partial_failure_retains_only_valid_prior_data():
    cached = refresh_dataset(now=NOW, fetcher=lambda *_: rows())

    def fetch(symbol, *_):
        if symbol in {"SPY", "QQQ"}:
            raise RuntimeError("Private error detail https://example.test/?token=secret")
        return rows()

    cached["series"][2]["observations"][0]["market_price"] = 0
    result = refresh_dataset(cached, now=NOW, fetcher=fetch)
    peers = {p["id"]: p for p in result["series"]}
    assert result["status"] == "partial"
    assert peers["SPY"]["status"] == "stale"
    assert peers["SPY"]["observations"] == rows()
    assert peers["QQQ"]["status"] == "unavailable" and peers["QQQ"]["observations"] == []
    assert peers["VOO"]["status"] == "ok"
    assert "secret" not in json.dumps(result)


def test_all_failed_without_cache_are_explicitly_unavailable():
    def fail(*_):
        raise RuntimeError()
    result = refresh_dataset(now=NOW, fetcher=fail)
    assert result["status"] == "unavailable"
    assert all(not item["observations"] for item in result["series"])


@pytest.mark.parametrize("replacement", [{"symbol": "ABC"}, {"currency": "CAD"}, {"instrumentType": "EQUITY"}])
def test_security_metadata_is_validated(replacement):
    meta = metadata()
    meta.update(replacement)
    frame = pd.DataFrame({"Close": [100]}, index=pd.to_datetime(["2026-09-25"]))
    with pytest.raises(ValueError):
        history_observations(frame, meta, "SPY", NOW)


def test_intraday_bar_is_excluded_until_regular_session_has_closed():
    frame = pd.DataFrame({"Close": [100, 101]}, index=pd.to_datetime(["2026-09-24", "2026-09-25"]))
    close = datetime(2026, 9, 25, 20, tzinfo=timezone.utc)
    meta = metadata(currentTradingPeriod={"regular": {"end": close.timestamp()}})
    before = history_observations(frame, meta, "SPY", close)
    after = history_observations(frame, meta, "SPY", close.replace(minute=10))
    assert [row["date"] for row in before] == ["2026-09-24"]
    assert len(after) == 2
    assert after[-1]["adjusted_close"] is None


def test_atomic_writer_preserves_old_file_if_serialization_fails(tmp_path):
    path = tmp_path / "cache.json"
    write_atomic(path, {"value": "first"})
    with pytest.raises(ValueError):
        write_atomic(path, {"bad": float("nan")})
    assert json.loads(path.read_text()) == {"value": "first"}
    assert len(list(tmp_path.iterdir())) == 1


def test_public_series_validator_strips_unknown_fields_and_checks_asof():
    series = refresh_dataset(now=NOW, fetcher=lambda *_: rows())["series"][0]
    series.update(private_value="not exported", source_url="https://wrong.test", name="untrusted name")
    clean = validate_series(series)
    assert "private_value" not in clean
    assert clean["source_url"] == "https://finance.yahoo.com/quote/SPY/history/"
    assert clean["name"] == "SPDR S&P 500 ETF Trust"
    series["as_of"] = "2026-09-24"
    with pytest.raises(ValueError, match="as-of"):
        validate_series(series)


def test_public_series_validator_rejects_non_peer_and_illustrative_history():
    series = refresh_dataset(now=NOW, fetcher=lambda *_: rows())["series"][0]
    series["is_illustrative"] = True
    with pytest.raises(ValueError):
        validate_series(series)
    series["is_illustrative"] = False
    series["id"] = "REDI"
    with pytest.raises(ValueError, match="universe"):
        validate_series(series)


def test_older_response_does_not_overwrite_newer_validated_cache():
    cached = refresh_dataset(now=NOW, fetcher=lambda *_: rows())
    result = refresh_dataset(cached, now=NOW, fetcher=lambda *_: rows()[:1])
    assert result["status"] == "partial"
    assert all(item["status"] == "stale" and item["as_of"] == "2026-09-25" for item in result["series"])


def test_corrupt_cache_metadata_is_ignored():
    def fail(*_):
        raise RuntimeError()
    for cached in [{"schema_version": 1, "series": {}}, {"schema_version": 1, "series": [None]}]:
        assert refresh_dataset(cached, now=NOW, fetcher=fail)["status"] == "unavailable"
