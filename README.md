# FAA attribution forecaster — polymarket-faa-attribution-02

A deterministic, standard-library-only program (`main.py`, Python 3.13) that
forecasts Polymarket Yes prices four hours ahead, minute by minute, as five
quantiles (0.05, 0.25, 0.5, 0.75, 0.95) per market per minute.

## How it works

Prediction-market prices on a 1-minute grid are a step process: most minutes
nothing moves, then there is a tick, and now and then a jump. One fixed
spread for every market is therefore wrong in both directions — too wide for
markets that have barely moved in a day, too narrow for an active one. For
each market in the case, this program instead:

- measures the market's own recent step size from the case itself: the mean
  absolute 1-minute price change over the last 960 minutes, with each change
  winsorised to ±0.10 so one wild print cannot dominate, clamped to
  [0.0002, 0.006];
- centres every quantile on the market's last price (on the practice cases,
  drift and mean-reversion terms all made the loss worse, so the median is
  the checkpoint price);
- spreads the quantiles as `centre + m · sigma · sqrt(h)` for the minute
  `h = 1..240` ahead, with multipliers `m = (-1.645, -0.40, 0, 0.40, 1.645)`
  — the outer pair keeps the normal 5%/95% spacing, while the inner pair is
  pulled in from the normal's 0.674 because the interquartile range of a
  step process grows much more slowly than its tails;
- clamps to [0, 1], keeps each row non-decreasing, and rounds to 6 decimals.

## Local practice score

There is no local grade in the kit for this competition (the scorer and the
reference data stay on the server; `grade-local` says so). Scored locally by
chaining the practice cases — the 240 minutes after a checkpoint are the
tail of the next case's price series — this program loses **0.306805** on
cases p00–p04, against the house baseline's **0.392518** on the same five
cases (its published six-case practice loss is 0.363589), with median error
0.879497 and 90% coverage 0.873197.

## Run locally

The program reads every `*.in` file in `$MAKEFUN_INPUT_DIR` (else `/input`),
in name order, and writes the matching `<id>.out` to `$MAKEFUN_OUTPUT_DIR`
(else `/output`). No network, no randomness, no third-party packages: two
runs on the same case are byte-identical, and a case takes about a tenth of
a second.

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=/path/to/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```
