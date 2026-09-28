from safety.critical_values import CriticalHit, Threshold, evaluate

THRESHOLDS = [
    Threshold("potassium", "mmol/L", 2.8, 6.0, "Критичний калій — до лікаря сьогодні."),
    Threshold("glucose", "mmol/L", 3.0, 25.0, "Критична глюкоза."),
    Threshold("hemoglobin", "g/L", 70.0, None, "Критично низький Hb."),
]


def test_high_potassium_is_critical():
    hit = evaluate("potassium", 6.8, "mmol/L", THRESHOLDS)
    assert isinstance(hit, CriticalHit)
    assert hit.bound == "high"
    assert hit.threshold == 6.0


def test_low_potassium_is_critical():
    hit = evaluate("potassium", 2.5, "mmol/L", THRESHOLDS)
    assert hit and hit.bound == "low"


def test_normal_potassium_is_none():
    assert evaluate("potassium", 4.2, "mmol/L", THRESHOLDS) is None


def test_boundary_is_inclusive_high_recall():
    # exactly on the threshold — treated as critical (fail toward alerting)
    assert evaluate("potassium", 6.0, "mmol/L", THRESHOLDS) is not None
    assert evaluate("potassium", 2.8, "mmol/L", THRESHOLDS) is not None


def test_unit_gate_blocks_wrong_unit():
    # a value in mg/dL must not be compared to a threshold in mmol/L
    assert evaluate("glucose", 95.0, "mg/dL", THRESHOLDS) is None


def test_only_low_bound_defined():
    assert evaluate("hemoglobin", 65.0, "g/L", THRESHOLDS) is not None
    assert evaluate("hemoglobin", 300.0, "g/L", THRESHOLDS) is None  # no critical_high


def test_none_value_is_safe():
    assert evaluate("potassium", None, "mmol/L", THRESHOLDS) is None
    assert evaluate("potassium", 6.8, None, THRESHOLDS) is None


def test_unknown_type_is_none():
    assert evaluate("unknown_code", 999.0, "mmol/L", THRESHOLDS) is None
