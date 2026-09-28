"""Trends (plan 5, level 1). Mann-Kendall (non-parametric) + linear regression slope.

Mann-Kendall is robust to outliers and assumes no normality — more appropriate than a naive
regression on medical time series. Caution: on STRONGLY autocorrelated series p is understated
(plan 5 level 2 — a separate topic with prewhitening); here it's a basic trend over sparse lab points.

Pure functions, no numpy/scipy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

INCREASING = "increasing"
DECREASING = "decreasing"
NO_TREND = "no_trend"


@dataclass
class TrendResult:
    direction: str
    z: float | None
    p_approx: float | None
    slope: float | None            # units per point (simple OLS)
    n: int
    detail: str


def _mann_kendall_stat(values: list[float]) -> tuple[int, float]:
    n = len(values)
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += (values[j] > values[i]) - (values[j] < values[i])
    # variance without tie correction (simplified)
    var = n * (n - 1) * (2 * n + 5) / 18
    return s, var


def _ols_slope(values: list[float]) -> float:
    n = len(values)
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(values) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((xs[i] - mx) * (values[i] - my) for i in range(n)) / denom


def _norm_p(z: float) -> float:
    # two-sided p via erfc
    return math.erfc(abs(z) / math.sqrt(2))


def trend(values: list[float], alpha: float = 0.05, min_n: int = 5) -> TrendResult:
    """Trend direction by Mann-Kendall. Needs ≥min_n points."""
    n = len(values)
    if n < min_n:
        return TrendResult(NO_TREND, None, None, None, n,
                           f"Not enough points ({n}, need ≥{min_n}).")
    s, var = _mann_kendall_stat(values)
    if var == 0:
        return TrendResult(NO_TREND, 0.0, 1.0, 0.0, n, "No variation.")
    # continuity correction
    if s > 0:
        z = (s - 1) / math.sqrt(var)
    elif s < 0:
        z = (s + 1) / math.sqrt(var)
    else:
        z = 0.0
    p = _norm_p(z)
    slope = _ols_slope(values)
    if p < alpha and z > 0:
        direction = INCREASING
    elif p < alpha and z < 0:
        direction = DECREASING
    else:
        direction = NO_TREND
    detail = (f"Mann-Kendall z={z:+.2f}, p≈{p:.3f}, slope≈{slope:+.3f}/point, n={n}. "
              + {INCREASING: "steady increase.", DECREASING: "steady decrease.",
                 NO_TREND: "no significant trend."}[direction])
    return TrendResult(direction, z, p, slope, n, detail)
