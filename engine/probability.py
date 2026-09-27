"""
ISI Wave & Structure Engine — PROBABILITY / CONFLUENCE COMBINER
══════════════════════════════════════════════════════════════
IMPORTANT — WHAT THIS NUMBER IS AND ISN'T:
This is a CONFLUENCE SCORE (0-100): how many independent structural
signals (Elliott Wave shape + Smart Money structure) currently point
the same way. It is NOT a probability in the statistical sense, and
it is NOT a promise about what price will do next. Markets can and do
invalidate every one of these reads. Treat it as "how much technical
agreement exists right now", not as a forecast to bet the account on.

SCORING (starts at 50 = neutral):
  +15  Elliott Wave labeled a valid impulse matching current direction
  + up to +15 more, scaled by Elliott Wave's own confidence
  +15  Most recent SMC event is a BOS in the same direction
  -20  Most recent SMC event is a CHoCH (early reversal warning)
  +10  Price is currently sitting inside a same-direction Order Block
  +8   A same-direction FVG exists nearby (acts as a magnet/support)
  Clamped to 0-100 at the end.
══════════════════════════════════════════════════════════════
"""


def _direction_sign(direction: str) -> int:
    return 1 if direction == "bullish" else -1 if direction == "bearish" else 0


def combine_signals(elliott: dict, smc: dict, last_price: float):
    score = 50
    reasons = []

    ew_dir = elliott.get("direction")
    ew_sign = _direction_sign(ew_dir)

    smc_trend = smc.get("trend")
    smc_sign = _direction_sign("bullish" if smc_trend == "up" else "bearish" if smc_trend == "down" else None)

    aligned = ew_sign != 0 and smc_sign != 0 and ew_sign == smc_sign

    if elliott.get("valid_impulse"):
        base = 15 + round(elliott.get("confidence", 0) / 100 * 15)
        score += base if aligned else round(base / 2)
        reasons.append(f"Elliott Wave: valid {ew_dir} impulse, confidence {elliott.get('confidence')}%.")
    else:
        reasons.append("Elliott Wave: no clean 5-wave impulse currently — structural read carries less weight.")

    latest_event = smc.get("latest_event")
    if latest_event:
        if latest_event["type"] == "BOS":
            score += 15 if (ew_sign == 0 or _direction_sign(latest_event["direction"]) == ew_sign) else 5
            reasons.append(f"SMC: latest event is a {latest_event['direction']} BOS — trend continuation signal.")
        elif latest_event["type"] == "CHoCH":
            score -= 20
            reasons.append(f"SMC: latest event is a {latest_event['direction']} CHoCH — possible reversal warning, "
                            f"reduces confidence in continuation.")

    # Is price currently sitting inside a same-direction order block?
    for ob in smc.get("order_blocks", []):
        in_zone = ob["low"] <= last_price <= ob["high"]
        matches = (ob["type"] == "bullish_ob" and ew_sign >= 0) or (ob["type"] == "bearish_ob" and ew_sign <= 0)
        if in_zone and matches:
            score += 10
            reasons.append(f"Price is sitting inside a {ob['type'].replace('_', ' ')} right now — structural support/resistance.")

    # Nearby same-direction FVG acting as a magnet.
    for fvg in smc.get("fvgs", []):
        matches = (fvg["type"] == "bullish_fvg" and ew_sign >= 0) or (fvg["type"] == "bearish_fvg" and ew_sign <= 0)
        near = fvg["bottom"] * 0.98 <= last_price <= fvg["top"] * 1.02
        if matches and near:
            score += 8
            reasons.append(f"A nearby {fvg['type'].replace('_', ' ')} aligns with the current read.")
            break

    score = max(0, min(100, round(score)))

    if score >= 75:
        label = "HIGH confluence"
    elif score >= 55:
        label = "MODERATE confluence"
    elif score >= 40:
        label = "LOW confluence / mixed signals"
    else:
        label = "CONFLICTING signals — no clean read"

    return {
        "score": score,
        "label": label,
        "aligned": aligned,
        "bias": ew_dir or (("bullish" if smc_sign > 0 else "bearish") if smc_sign else "neutral"),
        "reasons": reasons,
        "disclaimer": "Confluence score, not a prediction. Structure can and does invalidate.",
    }
