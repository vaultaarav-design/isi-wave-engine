"""
ISI Wave & Structure Engine — ENTRY POINT
══════════════════════════════════════════════════════════════
Deploys as a normal FastAPI web service (Render free tier: "Web
Service", not "Background Worker" — free background workers aren't
available, but a web service that ALSO runs a background loop works
fine and is free).

Render free web services sleep after ~15 min with no HTTP traffic.
To keep this running continuously:
  1. Deploy this as a Web Service on Render (see README.md).
  2. Add a free uptime pinger (cron-job.org / UptimeRobot / Render's
     own health checks) hitting GET /health every 5-10 minutes.
That's it — the loop below keeps running for as long as the process
is alive, independent of whether anyone is hitting the HTTP routes.

Endpoints:
  GET /            → basic info
  GET /health      → 200 OK, used for keep-alive pings
  GET /status      → last run time + per-instrument success/failure
══════════════════════════════════════════════════════════════
"""
import asyncio
import time
import traceback
from datetime import datetime, timezone

from fastapi import FastAPI

from engine.instruments import INSTRUMENTS
from engine.data_feed import fetch_candles
from engine.swings import zigzag_pivots, suggest_deviation_pct
from engine.elliott_wave import label_elliott_wave
from engine.smc import detect_structure
from engine.probability import combine_signals
from engine.firebase_writer import push_engine_output, push_engine_status

app = FastAPI(title="ISI Wave & Structure Engine")

REFRESH_SECONDS = {"binance": 60, "stooq": 300}
_last_status = {"started_at": None, "last_cycle_at": None, "instruments": {}}


def process_instrument(instrument: dict):
    candles = fetch_candles(instrument, limit=200)
    if len(candles) < 20:
        raise ValueError(f"Only {len(candles)} candles returned — too few to analyze.")

    deviation_pct = suggest_deviation_pct(candles)
    pivots = zigzag_pivots(candles, deviation_pct)
    elliott = label_elliott_wave(pivots)
    smc = detect_structure(candles, pivots)
    last_price = candles[-1]["c"]
    combined = combine_signals(elliott, smc, last_price)

    payload = {
        "instrument": instrument["key"],
        "name": instrument["name"],
        "last_price": last_price,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "deviation_pct_used": round(deviation_pct, 2),
        "elliott_wave": elliott,
        "smart_money": smc,
        "confluence": combined,
    }
    push_engine_output(instrument["key"], payload)
    return payload


async def engine_loop():
    _last_status["started_at"] = datetime.now(timezone.utc).isoformat()
    next_due = {inst["key"]: 0 for inst in INSTRUMENTS}

    while True:
        now = time.time()
        for inst in INSTRUMENTS:
            if now < next_due[inst["key"]]:
                continue
            try:
                process_instrument(inst)
                _last_status["instruments"][inst["key"]] = {"ok": True, "at": datetime.now(timezone.utc).isoformat()}
            except Exception as e:
                _last_status["instruments"][inst["key"]] = {
                    "ok": False, "error": str(e), "at": datetime.now(timezone.utc).isoformat()
                }
                traceback.print_exc()
            finally:
                next_due[inst["key"]] = now + REFRESH_SECONDS[inst["source"]]

        _last_status["last_cycle_at"] = datetime.now(timezone.utc).isoformat()
        try:
            push_engine_status(_last_status)
        except Exception:
            traceback.print_exc()

        await asyncio.sleep(5)  # short tick so per-instrument due-times are respected promptly


@app.on_event("startup")
async def start_background_loop():
    asyncio.create_task(engine_loop())


@app.get("/")
def root():
    return {"service": "ISI Wave & Structure Engine", "status": "running",
            "instruments": [i["key"] for i in INSTRUMENTS]}


@app.get("/health")
def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}


@app.get("/status")
def status():
    return _last_status
