"""Personal baselines and anomalies (plan 5, level 1 — deterministic).

An anomaly is a deviation from a PERSONAL baseline (rolling mean/σ), not "ML magic on n=1".
Pure functions, tested without a DB.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Baseline:
    n: int
    mean: float
    std: float


@dataclass
class AnomalyCheck:
    value: float
    z: float | None
    is_anomaly: bool
    detail: str


def baseline(values: list[float]) -> Baseline | None:
    """Mean and population σ over history. None if too few points."""
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return Baseline(n=n, mean=mean, std=math.sqrt(var))


def check_anomaly(latest: float, history: list[float], z_threshold: float = 2.0,
                  min_n: int = 5) -> AnomalyCheck:
    """Whether latest is an anomaly relative to history (|z| > threshold).

    Needs ≥min_n historical points — otherwise "not enough baseline" (we don't shout on 2 points).
    """
    b = baseline(history)
    if b is None or len(history) < min_n:
        return AnomalyCheck(latest, None, False,
                            f"Not enough baseline ({len(history)} points, need ≥{min_n}).")
    if b.std == 0:
        anom = latest != b.mean
        return AnomalyCheck(latest, None, anom,
                            "History has no spread; any deviation is noticeable." if anom
                            else "Matches an unchanged history.")
    z = (latest - b.mean) / b.std
    is_anom = abs(z) > z_threshold
    return AnomalyCheck(
        latest, z, is_anom,
        f"z={z:+.1f} (baseline {b.mean:.2f}±{b.std:.2f}, n={b.n}). "
        + ("Deviation from the personal norm — worth watching/repeating."
           if is_anom else "Within the personal norm."),
    )
