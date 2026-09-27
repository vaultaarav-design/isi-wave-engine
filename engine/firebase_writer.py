"""
ISI Wave & Structure Engine — FIREBASE WRITER
══════════════════════════════════════════════════════════════
Writes into the EXACT SAME Realtime Database the ISI Terminal app
already reads/writes (trading-terminal-b8006), under a new path:

    isi_v6/engine_output/{instrumentKey}

...so the frontend's existing Firebase `onValue()` listener pattern
(same one zone-report-widget.js already uses) can pick this up live,
with zero polling and zero new frontend infrastructure.

Uses plain REST calls (no firebase-admin SDK, no service-account JSON)
because the project's current database rules are fully open
(".read": true, ".write": true — see FIREBASE_RULES.md). If those
rules are ever locked down, swap this for firebase-admin + a service
account key stored as a Render environment variable/secret file.
══════════════════════════════════════════════════════════════
"""
import requests

DATABASE_URL = "https://trading-terminal-b8006-default-rtdb.firebaseio.com"
HTTP_TIMEOUT = 10


def push_engine_output(instrument_key: str, payload: dict):
    url = f"{DATABASE_URL}/isi_v6/engine_output/{instrument_key}.json"
    r = requests.put(url, json=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()


def push_engine_status(payload: dict):
    """Small heartbeat node so the frontend (or a monitoring page) can show
    'engine last updated N seconds ago' instead of trusting silently."""
    url = f"{DATABASE_URL}/isi_v6/engine_status.json"
    r = requests.put(url, json=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()
