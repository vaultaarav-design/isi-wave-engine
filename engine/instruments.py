"""
ISI Wave & Structure Engine — INSTRUMENT REGISTRY
══════════════════════════════════════════════════════════════
Every instrument the engine tracks, with the exact source + symbol
needed to fetch it. Two data sources are used:

  - "binance"  → crypto, fetched from Binance Futures REST API directly.
                 Genuinely live (seconds-level), free, no key, no CORS
                 issue since this is a server calling a server.

  - "stooq"    → forex / gold / indices, fetched from Stooq's plain CSV
                 endpoints DIRECTLY (no proxy needed — CORS is a browser
                 concept, it doesn't apply to server-to-server calls).
                 Stooq's intraday "last quote" endpoint gives a price
                 updated every ~1-15 min (good enough for swing/wave
                 analysis on H1+ timeframes; NOT true tick-by-tick).

Add a new instrument by adding one line here — nothing else needs to
change to start tracking it.
══════════════════════════════════════════════════════════════
"""

INSTRUMENTS = [
    # key           display name        source      symbol         interval (Binance) / stooq ticker
    {"key": "BTCUSDT",  "name": "BTC/USDT",       "source": "binance", "symbol": "BTCUSDT",  "interval": "15m"},
    {"key": "ETHUSDT",  "name": "ETH/USDT",       "source": "binance", "symbol": "ETHUSDT",  "interval": "15m"},
    {"key": "EURUSD",   "name": "EUR/USD",        "source": "stooq",   "symbol": "eurusd",   "interval": "d"},
    {"key": "GBPUSD",   "name": "GBP/USD",        "source": "stooq",   "symbol": "gbpusd",   "interval": "d"},
    {"key": "USDJPY",   "name": "USD/JPY",        "source": "stooq",   "symbol": "usdjpy",   "interval": "d"},
    {"key": "XAUUSD",   "name": "Gold (XAU/USD)", "source": "stooq",   "symbol": "xauusd",   "interval": "d"},
    {"key": "SPX",      "name": "S&P 500",        "source": "stooq",   "symbol": "^spx",     "interval": "d"},
    {"key": "NDX",      "name": "Nasdaq 100",     "source": "stooq",   "symbol": "^ndq",     "interval": "d"},
]

def get_instrument(key: str):
    return next((i for i in INSTRUMENTS if i["key"] == key), None)
