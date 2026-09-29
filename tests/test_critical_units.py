"""Critical values must fire regardless of how the lab printed the unit or the name.

Regression: "mmol/l", "ммоль/л", "g/dL", "mEq/L", "10^9/L", "K", "Potasio" used to fail the
unit gate / name lookup and silently skipped the critical-value check.
"""
import pytest

from core.health_summary import build
from core.normalize import _KNOWN_UNITS, _unit_key, canonicalize_unit
from core.services import stage_panel


@pytest.mark.parametrize("printed,canonical", [
    ("mmol/l", "mmol/L"), ("ммоль/л", "mmol/L"), (" Ммоль / Л ", "mmol/L"),
    ("мкмоль/л", "umol/L"), ("µmol/L", "umol/L"), ("г/л", "g/L"), ("г/дл", "g/dL"),
    ("10^9/L", "10*9/L"), ("×10⁹/л", "10*9/L"), ("10E9/L", "10*9/L"), ("10^12/л", "10*12/L"),
    ("/μL", "/uL"), ("10^3/µL", "10*3/uL"), ("x10³/µL", "10*3/uL"), ("10^6/µL", "10*6/uL"),
    ("мкМО/мл", "uIU/mL"), ("Од/л", "U/L"), ("мм рт.ст.", "mmHg"), ("нг/мл", "ng/mL"),
])
def test_unit_spellings(printed, canonical):
    assert canonicalize_unit(printed) == canonical


def test_unknown_unit_is_left_as_is_and_known_units_do_not_collide():
    assert canonicalize_unit("weird/unit") == "weird/unit"
    assert canonicalize_unit("  ") is None
    assert len({_unit_key(u) for u in _KNOWN_UNITS}) == len(_KNOWN_UNITS)


@pytest.mark.parametrize("name,value,unit", [
    ("Калій", 6.8, "ммоль/л"), ("Potassium", 6.8, "mEq/L"), ("K", 6.8, "mmol/L"),
    ("Potasio", 6.8, "mmol/L"), ("Glucose", 1.9, "mmol/l"), ("Натрій", 118, "ммоль/л"),
    ("Hemoglobin", 6.5, "g/dL"), ("Hemoglobina", 6.5, "г/дл"),
    ("Тромбоцити", 20, "10^9/L"), ("Plaquetas", 20, "×10⁹/л"), ("Platelets", 20000, "/µL"),
    ("Platelets", 20, "10^3/µL"),
])
def test_critical_fires_for_printed_variants(conn, user_id, name, value, unit):
    alerts = []
    row = stage_panel(conn, user_id, "2026-09-28", [{"raw_name": name, "value": value, "unit": unit}],
                      alerter=lambda *a: alerts.append(a))["rows"][0]
    assert row["critical"] is True, row
    assert alerts


def test_unknown_unit_on_critical_analyte_alerts_instead_of_passing(conn, user_id):
    alerts = []
    row = stage_panel(conn, user_id, "2026-09-28",
                      [{"raw_name": "Калій", "value": 6.8, "unit": "mmol per liter"}],
                      alerter=lambda *a: alerts.append(a))["rows"][0]
    assert row["critical"] is False and row["critical_unverified"] is True
    assert "CRITICAL CHECK IMPOSSIBLE" in row["note"] and alerts


def test_summary_surfaces_pending_critical_values(conn, user_id):
    stage_panel(conn, user_id, "2026-09-28", [
        {"raw_name": "Калій", "value": 6.8, "unit": "mmol/L"},
        {"raw_name": "Натрій", "value": 140, "unit": "mmol/L"},
    ], alerter=lambda *a: None)
    stage_panel(conn, user_id, "2026-09-27", [
        {"raw_name": "Калій", "value": 6.8, "unit": "mmol per liter"},
    ], alerter=lambda *a: None)
    text = build(conn, user_id).text
    assert "Awaiting review (3 values" in text
    assert "potassium 6.8 mmol/L (2026-09-28): **CRITICAL value**" in text
    assert "critical check impossible" in text
    assert "1 other value(s)" in text


def test_duplicate_marker_in_panel_keeps_the_rest(conn, user_id):
    out = stage_panel(conn, user_id, "2026-09-28", [
        {"raw_name": "Glucose", "value": 5.0, "unit": "mmol/L"},
        {"raw_name": "Glucose", "value": 9.1, "unit": "mmol/L"},   # 2 h OGTT on the same form
        {"raw_name": "Калій", "value": 6.8, "unit": "mmol/L"},
    ], alerter=lambda *a: None)
    rows = out["rows"]
    assert rows[1]["stored"] is False and "separate panel" in rows[1]["note"]
    assert rows[2]["critical"] is True   # the critical row after the duplicate is not lost
