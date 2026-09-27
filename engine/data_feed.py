"""
ISI Wave & Structure Engine — DATA FEED
══════════════════════════════════════════════════════════════
Server-side HTTP calls only. No browser involved anywhere in this
process, so none of the CORS problems the frontend fought with apply
here — Stooq is called directly, plain and simple.

Every fetcher returns the SAME normalized shape:
    [{"t": iso_timestamp, "o": float, "h": float, "l": float,
      "c": float, "v": float}, ...]   (oldest → newest)
══════════════════════════════════════════════════════════════
"""
import csv
import io
import time
import requests

HTTP_TIMEOUT = 10
_session = requests.Session()
_session.headers.update({"User-Agent": "ISI-Wave-Engine/1.0 (+https://github.com)"})


def fetch_binance_klines(symbol: str, interval: str = "15m", limit: int = 200):
    """Binance USDT-M Futures klines — direct, no key needed."""
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = _session.get(url, params=params, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    raw = r.json()
    candles = []
    for row in raw:
        candles.append({
            "t": row[0] // 1000,          # open time, unix seconds
            "o": float(row[1]), "h": float(row[2]),
            "l": float(row[3]), "c": float(row[4]),
            "v": float(row[5]),
        })
    return candles


def fetch_stooq_daily(symbol: str, days: int = 120):
    """Stooq daily CSV — 'Date,Open,High,Low,Close,Volume' rows."""
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    r = _session.get(url, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    text = r.text.strip()
    if not text or text.lower().startswith("no data") or "exceeded" in text.lower():
        raise ValueError(f"Stooq returned no usable data for {symbol}: {text[:120]}")
    reader = csv.DictReader(io.StringIO(text))
    candles = []
    for row in reader:
        try:
            candles.append({
                "t": row["Date"],
                "o": float(row["Open"]), "h": float(row["High"]),
                "l": float(row["Low"]), "c": float(row["Close"]),
                "v": float(row.get("Volume") or 0),
            })
        except (ValueError, KeyError):
            continue  # skip malformed/header rows
    return candles[-days:]


def fetch_stooq_last_quote(symbol: str):
    """Stooq's single-line 'last quote' endpoint — a few minutes' delay,
    used only to know the current price between daily-bar refreshes."""
    url = f"https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
    r = _session.get(url, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    reader = csv.DictReader(io.StringIO(r.text.strip()))
    row = next(reader, None)
    if not row or row.get("Close") in (None, "N/D"):
        raise ValueError(f"Stooq quote unavailable for {symbol}")
    return float(row["Close"])


def fetch_candles(instrument: dict, limit: int = 200):
    """Dispatches to the right source based on the instrument registry entry."""
    if instrument["source"] == "binance":
        return fetch_binance_klines(instrument["symbol"], instrument["interval"], limit)
    elif instrument["source"] == "stooq":
        candles = fetch_stooq_daily(instrument["symbol"], days=limit)
        try:
            last = fetch_stooq_last_quote(instrument["symbol"])
            if candles and last:
                # Patch the most recent bar's close with the freshest quote
                # available, so the "current price" used downstream isn't
                # a full day stale.
                today = candles[-1]
                today["c"] = last
                today["h"] = max(today["h"], last)
                today["l"] = min(today["l"], last)
        except Exception:
            pass  # fall back to daily-close-only if the quote endpoint fails
        return candles
    raise ValueError(f"Unknown data source: {instrument['source']}")
