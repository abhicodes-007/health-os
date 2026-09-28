from analytics.baselines import baseline, check_anomaly
from analytics.calculators import bmi, calculator_applicable
from analytics.trends import DECREASING, INCREASING, NO_TREND, trend


# --- baselines ---
def test_baseline_basic():
    b = baseline([10, 12, 14])
    assert b.n == 3 and b.mean == 12


def test_anomaly_detected():
    hist = [70, 72, 71, 69, 73, 70]  # resting HR ~70
    res = check_anomaly(110, hist)
    assert res.is_anomaly and res.z > 2


def test_no_anomaly_within_norm():
    res = check_anomaly(71, [70, 72, 71, 69, 73, 70])
    assert not res.is_anomaly


def test_insufficient_baseline():
    res = check_anomaly(100, [70, 72])  # <5 points
    assert not res.is_anomaly and "Not enough" in res.detail


# --- trends ---
def test_increasing_trend():
    assert trend([3.0, 3.4, 3.9, 4.5, 5.1, 5.8]).direction == INCREASING


def test_decreasing_trend():
    assert trend([5.8, 5.1, 4.5, 3.9, 3.4, 3.0]).direction == DECREASING


def test_no_trend_flat_noise():
    assert trend([5.0, 5.1, 4.9, 5.0, 5.05, 4.95]).direction == NO_TREND


def test_trend_needs_min_points():
    assert trend([5.0, 6.0]).direction == NO_TREND


# --- calculators (age-gate) ---
def test_score2_refused_for_young():
    g = calculator_applicable("SCORE2", 27)
    assert not g.applicable and "false reassurance" in g.message


def test_score2_ok_in_range():
    assert calculator_applicable("SCORE2", 55).applicable


def test_frax_range():
    assert calculator_applicable("FRAX", 30).applicable is False
    assert calculator_applicable("FRAX", 60).applicable is True


def test_bmi_calc():
    r = bmi(80, 180)
    assert r["bmi"] == 24.7 and r["category"] == "normal"
