"""
ISI Wave & Structure Engine — SMART MONEY CONCEPTS (SMC)
══════════════════════════════════════════════════════════════
Same ICT/SMC vocabulary as the pre-entry page's JS logic, but now
computed from REAL candle history (not just two typed-in numbers),
so these reads are structural, not just "where is price in a box
I drew by hand".

PATTERNS MARKED, AND EXACTLY HOW:

1. SWING HIGH / LOW  — reused directly from swings.zigzag_pivots().
   These are the reference points everything else is measured against.

2. BOS (Break of Structure) — price CLOSES beyond the most recent
   swing point in the SAME direction as the prevailing trend.
   Marked the bar the close crosses that level. Meaning: trend
   continuation confirmed.

3. CHoCH (Change of Character) — price closes beyond the most recent
   swing point in the OPPOSITE direction to the prevailing trend
   (i.e. the first break of an opposing swing after a run of same-
   direction BOS). Marked the same way, just on the opposite side.
   Meaning: first warning that the trend may be turning.

4. ORDER BLOCK — the last opposite-colour candle immediately before
   the impulsive move that caused a BOS/CHoCH.
   Bullish OB = last bearish (red) candle before a strong up-move
                that broke structure.
   Bearish OB = last bullish (green) candle before a strong down-move
                that broke structure.
   Marked by that single candle's high/low range.

5. FVG (Fair Value Gap) — a 3-candle pattern:
   Bullish FVG: candle[1].high < candle[3].low (a visible gap between
                them that price rarely fills without revisiting).
   Bearish FVG: candle[1].low > candle[3].high.
   Marked as the price range between those two candles.

6. LIQUIDITY ZONE (equal highs/lows) — two or more swing points of the
   same kind within a small tolerance (0.1% of price) of each other.
   These are where retail stop-losses cluster — "liquidity pools" that
   price is statistically drawn toward before reversing.
══════════════════════════════════════════════════════════════
"""


def _pct_diff(a, b):
    return abs(a - b) / ((a + b) / 2) * 100 if (a + b) else 0


def detect_structure(candles: list, pivots: list):
    if len(pivots) < 3:
        return {"bos": [], "choch": [], "order_blocks": [], "fvgs": [], "liquidity_zones": [],
                "trend": "unknown", "latest_event": None}

    # ── Trend + BOS/CHoCH ──
    # Walk the pivot sequence; track "trend" as the direction of the most
    # recent confirmed break, then look at whether the newest pivot breaks
    # the second-to-last SAME-kind pivot (continuation) or the opposite one.
    events = []
    trend = None
    for i in range(2, len(pivots)):
        cur, prev_same_kind = pivots[i], None
        for j in range(i - 1, -1, -1):
            if pivots[j]["kind"] == cur["kind"]:
                prev_same_kind = pivots[j]
                break
        if prev_same_kind is None:
            continue
        broke_up = cur["kind"] == "high" and cur["price"] > prev_same_kind["price"]
        broke_down = cur["kind"] == "low" and cur["price"] < prev_same_kind["price"]
        if broke_up:
            kind = "BOS" if trend in (None, "up") else "CHoCH"
            trend = "up"
            events.append({"type": kind, "direction": "bullish", "price": cur["price"], "t": cur["t"]})
        elif broke_down:
            kind = "BOS" if trend in (None, "down") else "CHoCH"
            trend = "down"
            events.append({"type": kind, "direction": "bearish", "price": cur["price"], "t": cur["t"]})

    bos = [e for e in events if e["type"] == "BOS"]
    choch = [e for e in events if e["type"] == "CHoCH"]
    latest_event = events[-1] if events else None

    # ── Order Blocks — last opposite candle before the move behind the
    #    most recent structural event ──
    order_blocks = []
    if latest_event:
        # Find the candle index nearest the event's timestamp.
        idx = next((i for i, c in enumerate(candles) if c["t"] == latest_event["t"]), len(candles) - 1)
        lookback_start = max(0, idx - 8)
        want_bearish_candle = latest_event["direction"] == "bullish"  # bullish move → look for last red candle
        for k in range(idx, lookback_start, -1):
            c = candles[k]
            is_bear = c["c"] < c["o"]
            if want_bearish_candle and is_bear:
                order_blocks.append({"type": "bullish_ob", "high": c["h"], "low": c["l"], "t": c["t"]})
                break
            if not want_bearish_candle and not is_bear:
                order_blocks.append({"type": "bearish_ob", "high": c["h"], "low": c["l"], "t": c["t"]})
                break

    # ── Fair Value Gaps — scan the last ~40 candles for 3-candle gaps ──
    fvgs = []
    window = candles[-40:] if len(candles) > 40 else candles
    for i in range(2, len(window)):
        c1, c3 = window[i - 2], window[i]
        if c1["h"] < c3["l"]:
            fvgs.append({"type": "bullish_fvg", "top": c3["l"], "bottom": c1["h"], "t": c3["t"]})
        elif c1["l"] > c3["h"]:
            fvgs.append({"type": "bearish_fvg", "top": c1["l"], "bottom": c3["h"], "t": c3["t"]})
    fvgs = fvgs[-5:]  # keep the most recent, most relevant ones

    # ── Liquidity zones — equal highs/lows within 0.1% tolerance ──
    liquidity_zones = []
    for i in range(len(pivots)):
        for j in range(i + 1, len(pivots)):
            if pivots[i]["kind"] != pivots[j]["kind"]:
                continue
            if _pct_diff(pivots[i]["price"], pivots[j]["price"]) <= 0.1:
                liquidity_zones.append({
                    "kind": pivots[i]["kind"], "price_a": pivots[i]["price"], "price_b": pivots[j]["price"],
                    "t_a": pivots[i]["t"], "t_b": pivots[j]["t"],
                })
    liquidity_zones = liquidity_zones[-5:]

    return {
        "trend": trend or "unknown",
        "bos": bos[-3:], "choch": choch[-3:],
        "order_blocks": order_blocks,
        "fvgs": fvgs,
        "liquidity_zones": liquidity_zones,
        "latest_event": latest_event,
    }
