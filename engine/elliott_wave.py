"""
ISI Wave & Structure Engine — ELLIOTT WAVE LABELER
══════════════════════════════════════════════════════════════
HONESTY FIRST: Elliott Wave counting is famously subjective — even
professional analysts disagree on the "correct" count for the same
chart. This module does NOT claim to find the one true count. It
applies the classic, textbook RULES mechanically to the most recent
run of zigzag pivots, and reports a CONFIDENCE score based on how
cleanly those rules are satisfied. Low confidence = take it as a
rough contextual read, not a forecast.

THE THREE HARD RULES OF A VALID 5-WAVE IMPULSE (Wave 1→5):
  1. Wave 2 never retraces more than 100% of Wave 1
     (price never revisits the start of Wave 1).
  2. Wave 3 is never the SHORTEST of waves 1, 3, 5.
  3. Wave 4 never enters Wave 1's price territory
     (no overlap, in a standard, non-diagonal impulse).

SOFT GUIDELINES (raise/lower confidence, don't invalidate the count):
  - Wave 3 is very often the longest, frequently ~1.618× Wave 1.
  - Wave 2 commonly retraces 50–61.8% of Wave 1.
  - Wave 4 commonly retraces 38.2–50% of Wave 3.
  - After a 5-wave impulse, expect a 3-wave A-B-C correction.

HOW A CHART GETS MARKED (for a human following along):
  Take the last 6 zigzag pivots (5 completed legs). Label them
  0-1-2-3-4-5 in time order. Check the 3 hard rules above against
  those 5 legs. If they all hold, this is a candidate impulse and
  "wave 5" is the most recent pivot — i.e. price is CURRENTLY
  somewhere in the wave that follows (either a Wave-2-of-a-new-cycle
  pullback, or the start of an A-B-C correction, depending on which
  direction price is now moving). Every ratio between legs is reported
  alongside the count so a trader can see exactly WHY the engine
  labeled it the way it did — not just the label itself.
══════════════════════════════════════════════════════════════
"""


def _leg_size(p_from, p_to):
    return abs(p_to["price"] - p_from["price"])


def _ratio(a, b):
    return round(a / b, 3) if b else None


def label_elliott_wave(pivots: list):
    """
    pivots: output of swings.zigzag_pivots(), oldest→newest, alternating
            high/low.

    Returns a report dict — always returns something, even with very
    little data, but confidence reflects how much was actually available.
    """
    if len(pivots) < 6:
        return {
            "valid_impulse": False,
            "confidence": 0,
            "current_wave_guess": None,
            "reasoning": "Not enough swing pivots yet to attempt a wave count "
                         "(need at least 6 — a full 5-wave sequence)."
        }

    # Take the most recent 6 pivots = points 0,1,2,3,4,5 of a candidate impulse.
    p0, p1, p2, p3, p4, p5 = pivots[-6:]
    up_impulse = p1["kind"] == "high"  # if wave 1 tops out, this is a bullish impulse

    w1 = _leg_size(p0, p1)
    w2 = _leg_size(p1, p2)
    w3 = _leg_size(p2, p3)
    w4 = _leg_size(p3, p4)
    w5 = _leg_size(p4, p5)

    violations = []

    # Rule 1 — Wave 2 doesn't retrace beyond the start of Wave 1.
    rule1_ok = (p2["price"] > p0["price"]) if up_impulse else (p2["price"] < p0["price"])
    if not rule1_ok:
        violations.append("Rule 1 violated: Wave 2 retraced past the start of Wave 1.")

    # Rule 2 — Wave 3 is not the shortest of 1, 3, 5.
    rule2_ok = not (w3 < w1 and w3 < w5)
    if not rule2_ok:
        violations.append("Rule 2 violated: Wave 3 is the shortest of waves 1/3/5.")

    # Rule 3 — Wave 4 doesn't overlap Wave 1's territory.
    rule3_ok = (p4["price"] > p1["price"]) if up_impulse else (p4["price"] < p1["price"])
    if not rule3_ok:
        violations.append("Rule 3 violated: Wave 4 overlaps Wave 1's price range.")

    valid_impulse = rule1_ok and rule2_ok and rule3_ok

    # Soft guideline scoring — these move confidence up or down but never
    # invalidate the count on their own.
    confidence = 40 if valid_impulse else 10
    notes = []

    w3_w1_ratio = _ratio(w3, w1)
    if w3_w1_ratio is not None:
        if 1.4 <= w3_w1_ratio <= 1.8:
            confidence += 20
            notes.append(f"Wave 3 ≈ {w3_w1_ratio}× Wave 1 — close to the classic 1.618 extension.")
        elif w3_w1_ratio > 1.0:
            confidence += 8
            notes.append(f"Wave 3 is {w3_w1_ratio}× Wave 1 (longer, as expected).")

    w2_w1_retrace = _ratio(w2, w1)
    if w2_w1_retrace is not None and 0.4 <= w2_w1_retrace <= 0.68:
        confidence += 12
        notes.append(f"Wave 2 retraced {round(w2_w1_retrace*100)}% of Wave 1 — typical range.")

    w4_w3_retrace = _ratio(w4, w3)
    if w4_w3_retrace is not None and 0.3 <= w4_w3_retrace <= 0.5:
        confidence += 12
        notes.append(f"Wave 4 retraced {round(w4_w3_retrace*100)}% of Wave 3 — typical range.")

    confidence = max(0, min(100, confidence))

    current_wave_guess = None
    if valid_impulse:
        # p5 is the end of wave 5. What price is doing right now (relative to
        # p5) tells us whether we're likely watching wave-2-of-next-cycle or
        # the start of an A-B-C correction.
        current_wave_guess = "Wave 5 just completed → expect an A-B-C correction next" if up_impulse else \
                              "Wave 5 (down) just completed → expect an A-B-C corrective bounce next"

    return {
        "valid_impulse": valid_impulse,
        "direction": "bullish" if up_impulse else "bearish",
        "confidence": confidence,
        "current_wave_guess": current_wave_guess,
        "violations": violations,
        "ratios": {"wave3_over_wave1": w3_w1_ratio, "wave2_retrace_of_wave1": w2_w1_retrace,
                   "wave4_retrace_of_wave3": w4_w3_retrace},
        "reasoning": " ".join(notes) if notes else "Basic 3-rule check only — not enough ratio confluence to say more.",
        "pivots_used": [p0, p1, p2, p3, p4, p5],
    }
