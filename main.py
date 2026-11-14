# polymarket-faa-attribution-02 entry (Python 3.13, standard library only).
#
# Idea, in one paragraph: prediction-market prices on a 1-minute grid are a
# step process -- most minutes nothing moves, then there is a tick, and now
# and then a jump. A single fixed spread for every market (the house
# baseline's 0.0025 per square-root minute) is therefore wrong in both
# directions at once: far too wide for the many markets that have barely
# moved in a day, and too narrow for an active one. So this program measures
# each market's own recent step size from the case it is given and builds
# the five quantiles around the market's last price from that measurement:
#
#   sigma  = mean absolute 1-minute price change over the last 960 minutes,
#            with each change winsorised to +/-0.10 so that one wild print
#            from a market's chaotic first minutes cannot dominate the
#            estimate, then clamped to [0.0002, 0.006];
#   q_tau(h) = clamp(x + m_tau * sigma * sqrt(h), 0, 1), rounded to 6 dp,
#
# where x is the price at the checkpoint, h = 1..horizon is the minute being
# forecast and the multipliers m_tau are (-1.645, -0.40, 0, 0.40, 1.645).
# The outer pair keeps the standard normal's 5%/95% spacing; the inner pair
# is pulled well in from the normal's 0.674, because the interquartile range
# of a step process grows much more slowly than its tails -- most of the
# time the price simply has not moved yet. The median stays at the last
# price: on the practice cases every drift or mean-reversion term tried
# (recent-trend momentum at several windows and shrinkages, reversion to a
# trailing mean) made the pinball loss worse, so the honest median is the
# checkpoint price itself.
#
# Calibration note: the constants above were chosen on the kit's six
# practice cases only, scored locally by chaining the cases (the minutes
# after a checkpoint are exactly the tail of the next case's price series).
# On practice cases p00..p04 that local score is 0.3068 against the house
# baseline's 0.3925 on the same five cases (its published six-case practice
# loss is 0.363589), with 90% interval coverage 0.873 against the 0.90
# nominal -- close to honest, slightly sharp rather than wastefully wide.
#
# The program is fully deterministic (no randomness, no clock, no network):
# two runs on the same case write byte-identical output. It reads every
# *.in file in $MAKEFUN_INPUT_DIR (else /input), in name order, and writes
# the matching <id>.out to $MAKEFUN_OUTPUT_DIR (else /output).

import json
import math
import os
import sys

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

# The quantile levels the contest scores, in row order.
QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
# Quantile multipliers per level: (5%, 25%, 50%, 75%, 95%).
MULTIPLIERS = [-1.645, -0.40, 0.0, 0.40, 1.645]
# Trailing window, in minutes, over which a market's step size is measured.
WINDOW_MINUTES = 960
# A single 1-minute change is winsorised to this magnitude before averaging.
WINSOR_LIMIT = 0.10
# Bounds for the per-market sigma estimate, in price units per sqrt(minute)
# -- expressed against the mean-absolute-change scale used here.
SIGMA_FLOOR = 0.0002
SIGMA_CAP = 0.006
# Fallback sigma when a market has no measurable change at all (a history
# shorter than two prices): the house baseline's fixed spread.
SIGMA_FALLBACK = 0.0025


def price6(value):
    """Clamp a price to [0, 1] and round it to 6 decimals (never -0.0)."""
    clamped = min(1.0, max(0.0, value))
    return round(clamped, 6) + 0.0


def estimate_sigma(prices):
    """Mean absolute 1-minute change over the trailing window.

    Changes are winsorised first: one jump of 0.40 in an otherwise quiet
    day says little about the next four hours, and an unwinsorised mean
    (let alone a standard deviation, which squares it) would let that one
    print widen every quantile for the whole horizon.
    """
    if len(prices) < 2:
        return SIGMA_FALLBACK
    diffs = []
    start = max(1, len(prices) - WINDOW_MINUTES)
    for i in range(start, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > WINSOR_LIMIT:
            change = WINSOR_LIMIT
        elif change < -WINSOR_LIMIT:
            change = -WINSOR_LIMIT
        diffs.append(abs(change))
    if not diffs:
        return SIGMA_FALLBACK
    mean_abs = sum(diffs) / len(diffs)
    return min(SIGMA_CAP, max(SIGMA_FLOOR, mean_abs))


def forecast_market(prices, horizon):
    """The horizon x 5 quantile rows for one market."""
    if prices:
        centre = prices[-1]
        sigma = estimate_sigma(prices)
    else:
        # No history at all: centre on 0.5 with the fallback spread rather
        # than crashing, which would invalidate the whole case.
        centre = 0.5
        sigma = SIGMA_FALLBACK
    rows = []
    for h in range(1, horizon + 1):
        spread = sigma * math.sqrt(h)
        rows.append([price6(centre + m * spread) for m in MULTIPLIERS])
    return rows


def run(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    names = sorted(name for name in os.listdir(input_dir) if name.endswith(".in"))
    for name in names:
        case_id = name[: -len(".in")]
        with open(os.path.join(input_dir, name), "r", encoding="utf-8") as handle:
            case = json.load(handle)
        if list(case["quantiles"]) != QUANTILES:
            raise ValueError(
                f"{name} asks for quantiles {case['quantiles']}, not {QUANTILES}"
            )
        horizon = int(case["horizon_minutes"])
        forecasts = [
            {"id": market["id"], "q": forecast_market(market["prices"], horizon)}
            for market in case["markets"]
        ]
        payload = json.dumps({"forecasts": forecasts}, separators=(",", ":"))
        out_path = os.path.join(output_dir, case_id + ".out")
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")


def main():
    run(INPUT_DIR, OUTPUT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
