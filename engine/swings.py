"""
ISI Wave & Structure Engine — SWING / ZIGZAG DETECTOR
══════════════════════════════════════════════════════════════
Everything downstream (Elliott Wave counting, BOS/CHoCH, Order Blocks,
Liquidity zones) is built on top of the same list of swing pivots —
the alternating high/low turning points in price. Get this right once,
reuse it everywhere, instead of every module re-deriving its own idea
of "where's the swing".

METHOD — percentage zigzag:
  Walk the candles. Track the running extreme (highest high since the
  last confirmed pivot, or lowest low). The moment price reverses away
  from that extreme by more than `deviation_pct`, the extreme itself is
  confirmed as a pivot, and tracking flips to look for the opposite
  extreme. This is the same method used by TradingView's built-in
  Zig Zag indicator.

  `deviation_pct` is intentionally left as a required, explicit input —
  the right value is a function of the instrument's volatility and the
  timeframe (see engine/probability.py for how it's chosen). No default
  is silently assumed here, so nothing downstream can be surprised by it.
══════════════════════════════════════════════════════════════
"""


def zigzag_pivots(candles: list, deviation_pct: float):
    """
    candles: normalized list [{"t","o","h","l","c","v"}, ...], oldest→newest
    deviation_pct: e.g. 1.5 for a 1.5% reversal threshold

    Returns: list of pivots [{"i": index, "t": timestamp, "price": float,
                              "kind": "high" | "low"}, ...], oldest→newest
    """
    if len(candles) < 3:
        return []

    pivots = []
    # Seed direction from the first two candles.
    trend = None          # "up" tracking toward a high, "down" toward a low
    extreme_idx = 0
    extreme_price = candles[0]["h"]
    extreme_low = candles[0]["l"]

    for i in range(1, len(candles)):
        hi, lo = candles[i]["h"], candles[i]["l"]

        if trend is None:
            # Establish initial direction once price has moved decisively.
            if hi >= extreme_price * (1 + deviation_pct / 100):
                trend = "up"
                extreme_price = hi
                extreme_idx = i
            elif lo <= extreme_low * (1 - deviation_pct / 100):
                trend = "down"
                extreme_low = lo
                extreme_idx = i
            else:
                extreme_price = max(extreme_price, hi)
                extreme_low = min(extreme_low, lo)
            continue

        if trend == "up":
            if hi > extreme_price:
                extreme_price = hi
                extreme_idx = i
            elif hi <= extreme_price * (1 - deviation_pct / 100):
                pivots.append({"i": extreme_idx, "t": candles[extreme_idx]["t"],
                                "price": extreme_price, "kind": "high"})
                trend = "down"
                extreme_low = lo
                extreme_idx = i
        else:  # trend == "down"
            if lo < extreme_low:
                extreme_low = lo
                extreme_idx = i
            elif lo >= extreme_low * (1 + deviation_pct / 100):
                pivots.append({"i": extreme_idx, "t": candles[extreme_idx]["t"],
                                "price": extreme_low, "kind": "low"})
                trend = "up"
                extreme_price = hi
                extreme_idx = i

    # Close out the final swing in progress so the most recent leg is visible.
    if trend == "up":
        pivots.append({"i": extreme_idx, "t": candles[extreme_idx]["t"],
                        "price": extreme_price, "kind": "high"})
    elif trend == "down":
        pivots.append({"i": extreme_idx, "t": candles[extreme_idx]["t"],
                        "price": extreme_low, "kind": "low"})

    return pivots


def suggest_deviation_pct(candles: list) -> float:
    """
    Picks a sane zigzag threshold from the instrument's own recent volatility
    (average true range as % of price) rather than a single hardcoded number
    for every asset — a 1% move in BTC and a 1% move in EUR/USD are very
    different animals.
    """
    if len(candles) < 15:
        return 2.0
    trs = []
    for i in range(1, len(candles)):
        h, l, prev_c = candles[i]["h"], candles[i]["l"], candles[i - 1]["c"]
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    atr = sum(trs[-14:]) / min(14, len(trs))
    last_close = candles[-1]["c"] or 1
    atr_pct = (atr / last_close) * 100
    # A pivot should be at least ~2.5x the average bar range, floored/ceiled
    # to keep it sane for very calm or very wild instruments.
    return max(0.5, min(6.0, atr_pct * 2.5))
