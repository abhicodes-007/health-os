"""#11: approved numeric values must not silently lack a canonical value."""
from sqlalchemy import text

from analytics.weekly_report import build as weekly
from core.recompute import count_missing_canonical, recompute_canonical
from core.services import approve_staged, ingest_observation, manual_source, stage_panel


def _canon(conn, oid):
    return conn.execute(text("SELECT value_canonical FROM observations WHERE id=:i"), {"i": oid}).scalar()


def test_dimensionless_types_get_a_canonical_value(conn, user_id):
    # INR has no canonical unit; before #11 its canonical value was always NULL
    res = ingest_observation(conn, user_id, "INR", 1.1, None)
    assert float(_canon(conn, res.observation_id)) == 1.1


def test_approval_blocked_by_unconvertible_units(conn, user_id):
    out = stage_panel(conn, user_id, "2026-09-01", [
        {"raw_name": "Glucose", "value": 5.0, "unit": "mmol/L"},
        {"raw_name": "Ferritin", "value": 80, "unit": "furlongs"},
    ], alerter=lambda *a: None)
    res = approve_staged(conn, user_id, out["source_id"])
    assert res["approved_observations"] == 0
    assert res["blocked_without_canonical"] == ["ferritin 80 furlongs"]
    res = approve_staged(conn, user_id, out["source_id"], allow_missing_canonical=True)
    assert res["approved_observations"] == 2 and res["approved_without_canonical"] == 1


def _raw_insert(conn, user_id, code, value, unit):
    """What a custom importer does: INSERT without normalization."""
    sid = manual_source(conn, user_id, channel="custom_import")
    return str(conn.execute(text(
        """INSERT INTO observations (user_id, type_id, effective_at, value_numeric, unit,
                                     review_status, source_id)
           SELECT :u, id, now(), :v, :unit, 'approved', :s FROM observation_types WHERE code=:c
           RETURNING id"""), {"u": user_id, "v": value, "unit": unit, "s": sid, "c": code}).scalar())


def test_recompute_fills_directly_inserted_rows(conn, user_id):
    same_unit = _raw_insert(conn, user_id, "ferritin", 120, "ng/mL")
    needs_conv = _raw_insert(conn, user_id, "hemoglobin", 15.2, "g/dL")
    printed = _raw_insert(conn, user_id, "glucose", 99, "mg/dl")
    bad = _raw_insert(conn, user_id, "ferritin", 1, "furlongs")
    assert count_missing_canonical(conn, user_id)["total"] == 4

    dry = recompute_canonical(conn, user_id=user_id)
    assert dry.n_fixed == 3 and dry.n_unconvertible == 1 and _canon(conn, same_unit) is None

    rep = recompute_canonical(conn, apply=True, user_id=user_id)
    assert rep.n_fixed == 3
    assert float(_canon(conn, same_unit)) == 120
    assert float(_canon(conn, needs_conv)) == 152
    assert abs(float(_canon(conn, printed)) - 5.495) < 0.01
    assert _canon(conn, bad) is None
    assert count_missing_canonical(conn, user_id) == {"total": 1, "by_channel": {"custom_import": 1}}


def test_weekly_report_exposes_the_metric(conn, user_id):
    _raw_insert(conn, user_id, "ferritin", 1, "furlongs")
    health = weekly(conn, user_id)["system_health"]
    assert health["approved_without_canonical"]["total"] == 1
